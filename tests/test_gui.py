from __future__ import annotations

import os
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from video_compressor.core import ToolPaths
from video_compressor.gui import (
    ChoiceComboBox,
    DetectionWorker,
    MainWindow,
    StepSpinBox,
    responsive_column_count,
)
from video_compressor.i18n import set_language

APP = QApplication.instance() or QApplication([])


class _TestMainWindow(MainWindow):
    def _restore_settings(self) -> None:
        self.last_directory = None

    def _initialize_tools(self, _explicit_ffmpeg: str | None) -> None:
        self.tools = None

    def _save_settings(self) -> None:
        pass


class _IgnoredWheelEvent:
    def __init__(self) -> None:
        self.ignored = False

    def ignore(self) -> None:
        self.ignored = True


class ControlInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        set_language("en")

    def test_choice_does_not_change_from_unfocused_wheel_input(self) -> None:
        combo = ChoiceComboBox()
        combo.addItems(("One", "Two", "Three"))
        combo.setCurrentIndex(1)
        event = _IgnoredWheelEvent()

        combo.wheelEvent(event)  # type: ignore[arg-type]

        self.assertEqual(combo.currentIndex(), 1)
        self.assertTrue(event.ignored)
        self.assertTrue(combo.toolTip())
        self.assertEqual(combo.accessibleDescription(), combo.toolTip())

    def test_number_does_not_change_from_unfocused_wheel_input(self) -> None:
        spin = StepSpinBox()
        spin.setRange(0, 10)
        spin.setValue(5)
        event = _IgnoredWheelEvent()

        spin.wheelEvent(event)  # type: ignore[arg-type]

        self.assertEqual(spin.value(), 5)
        self.assertTrue(event.ignored)
        self.assertTrue(spin.toolTip())
        self.assertEqual(spin.accessibleDescription(), spin.toolTip())


class ResponsiveLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        set_language("en")

    def test_column_count_has_narrow_medium_and_wide_modes(self) -> None:
        self.assertEqual(responsive_column_count(719, 3), 1)
        self.assertEqual(responsive_column_count(720, 3), 2)
        self.assertEqual(responsive_column_count(979, 3), 2)
        self.assertEqual(responsive_column_count(980, 3), 3)
        self.assertEqual(responsive_column_count(1200, 2), 2)

    def test_main_window_keeps_actions_outside_the_scroll_area(self) -> None:
        window = _TestMainWindow()
        try:
            self.assertIs(window.sticky_bar.parentWidget(), window.centralWidget())
            self.assertFalse(
                window.scroll_area.widget().isAncestorOf(window.sticky_bar)
            )
            self.assertTrue(
                all(
                    isinstance(combo, ChoiceComboBox)
                    for combo in (
                        window.language_combo,
                        window.backend_combo,
                        window.codec_combo,
                        window.container_combo,
                        window.profile_combo,
                        window.quality_mode_combo,
                        window.speed_combo,
                        window.resolution_combo,
                        window.pixel_depth_combo,
                        window.audio_combo,
                    )
                )
            )
            self.assertTrue(
                all(
                    isinstance(spin, StepSpinBox)
                    for spin in (
                        window.quality_value_spin,
                        window.frame_rate_spin,
                        window.gop_spin,
                        window.audio_bitrate_spin,
                    )
                )
            )
        finally:
            window.close()

    def test_main_window_reflows_fields_at_the_minimum_width(self) -> None:
        window = _TestMainWindow()
        try:
            window.show()
            window.resize(940, 760)
            APP.processEvents()
            window._update_responsive_layout()
            self.assertEqual(window._responsive_device_columns, 2)
            self.assertEqual(window._responsive_quality_columns, 2)

            window.resize(1120, 960)
            APP.processEvents()
            window._update_responsive_layout()
            self.assertEqual(window._responsive_device_columns, 3)
            self.assertEqual(window._responsive_quality_columns, 3)
        finally:
            window.close()


class DetectionLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        set_language("en")

    def test_scheduled_detection_can_be_skipped_before_it_starts(self) -> None:
        window = _TestMainWindow()
        try:
            window.tools = ToolPaths(Path("ffmpeg.exe"), Path("ffprobe.exe"))
            window._schedule_startup_detection()

            self.assertTrue(window.pending_detection)
            self.assertTrue(window.startup_detection_timer.isActive())
            self.assertTrue(window.input_edit.isEnabled())
            self.assertFalse(window.backend_combo.isEnabled())
            self.assertFalse(window.cancel_detection_button.isHidden())

            window.cancel_detection()

            self.assertFalse(window.pending_detection)
            self.assertFalse(window.startup_detection_timer.isActive())
            self.assertTrue(window.cancel_detection_button.isHidden())
            self.assertIn("paused", window.status_label.text().lower())
        finally:
            window.close()

    def test_active_detection_exposes_progress_and_accepts_cancellation(self) -> None:
        window = _TestMainWindow()
        try:
            tools = ToolPaths(Path("ffmpeg.exe"), Path("ffprobe.exe"))
            worker = DetectionWorker(tools)
            window.running_detection = True
            window.detection_worker = worker
            window.detection_started_at = time.monotonic() - 2
            window.cancel_detection_button.setVisible(True)
            window._set_running(False)

            window._detection_progress(10, 100, "Testing encoder")

            self.assertEqual(window.progress_bar.value(), 100)
            self.assertIn("10/100", window.metrics_label.text())
            self.assertIn("Testing encoder", window.hardware_summary.text())
            self.assertTrue(window.input_edit.isEnabled())
            self.assertFalse(window.backend_combo.isEnabled())
            self.assertTrue(window.cancel_button.isEnabled())

            window.cancel_active_operation()

            self.assertTrue(worker.cancel_event.is_set())
            self.assertFalse(window.cancel_detection_button.isEnabled())
            self.assertFalse(window.cancel_button.isEnabled())
        finally:
            window.running_detection = False
            window.detection_worker = None
            window.close()


if __name__ == "__main__":
    unittest.main()
