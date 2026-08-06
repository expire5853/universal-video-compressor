"""Modern Windows GUI for general-purpose video compression."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QPointF,
    QRectF,
    QSettings,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QIcon,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QPolygonF,
    QResizeEvent,
    QShortcut,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .core import (
    AUDIO_MODE_LABELS,
    CODEC_LABELS,
    CONTAINERS,
    ENCODERS,
    QUALITY_MODE_LABELS,
    RESOLUTION_OPTIONS,
    SPEED_LABELS,
    BackendCapability,
    CapabilityReport,
    CompressionJob,
    CompressionSettings,
    EncodeResult,
    MediaInfo,
    ToolPaths,
    application_roots,
    available_encoders_for_backend,
    bundled_tool_candidates,
    can_copy_audio,
    capability_report_as_dict,
    command_for_display,
    create_compression_job,
    default_output_path,
    detect_capabilities,
    execute_job,
    get_backend,
    get_encoder,
    probe_media,
    quality_value_properties,
    resolve_tools,
    supported_pixel_depths,
    supported_quality_modes,
)
from .i18n import (
    LANGUAGE_NAMES,
    get_language,
    set_language,
    system_language,
    tr,
    translate_for,
)

APP_NAME = "Video Compressor"
APP_VERSION = __version__
ORGANIZATION_NAME = "UniversalVideoCompressor"


STYLE_SHEET = """
QMainWindow, QWidget#shell, QWidget#root {
    background: #0b0f14;
    color: #e8eef6;
    font-family: "Segoe UI", "Microsoft YaHei UI";
    font-size: 10pt;
}

QScrollArea#rootScroll,
QScrollArea#rootScroll > QWidget > QWidget {
    background: #0b0f14;
    border: none;
}

QFrame#card {
    background: #121923;
    border: 1px solid #263243;
    border-radius: 12px;
}

QFrame#stickyBar {
    background: #101720;
    border: none;
    border-top: 1px solid #2b394c;
}

QLabel#appTitle {
    color: #f5f8fc;
    font-size: 23pt;
    font-weight: 700;
}

QLabel#appSubtitle, QLabel#muted, QLabel#fieldLabel {
    color: #8f9eaf;
}

QLabel#sectionTitle {
    color: #e8eef6;
    font-size: 12pt;
    font-weight: 650;
}

QLabel#statusPill {
    color: #72f1d8;
    background: #12332f;
    border: 1px solid #225a51;
    border-radius: 11px;
    padding: 5px 11px;
    font-weight: 650;
}

QLabel#warningPill {
    color: #ffd694;
    background: #352a17;
    border: 1px solid #68522a;
    border-radius: 11px;
    padding: 5px 11px;
    font-weight: 650;
}

QLabel#hintPanel {
    color: #a8b6c7;
    background: #0d141d;
    border: 1px solid #223043;
    border-radius: 8px;
    padding: 9px 11px;
}

QLabel#workflowBanner {
    color: #b8fff6;
    background: #102925;
    border: 1px solid #20564f;
    border-radius: 8px;
    padding: 9px 12px;
    font-weight: 600;
}

QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {
    min-height: 22px;
    color: #edf3fa;
    background: #0d141d;
    border: 1px solid #2b394c;
    border-radius: 7px;
    padding: 7px 10px;
    selection-background-color: #287c78;
}

QComboBox {
    padding-right: 42px;
}

QSpinBox {
    padding-right: 40px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {
    border: 1px solid #3dd6c5;
}

QComboBox::drop-down {
    width: 34px;
    background: #172231;
    border: none;
    border-left: 1px solid #34445a;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox::drop-down:hover,
QSpinBox::up-button:hover,
QSpinBox::down-button:hover {
    background: #24364a;
}

QComboBox::down-arrow,
QSpinBox::up-arrow,
QSpinBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
}

QSpinBox::up-button,
QSpinBox::down-button {
    width: 34px;
    background: #172231;
    border: none;
    border-left: 1px solid #34445a;
}

QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    border-top-right-radius: 6px;
    border-bottom: 1px solid #34445a;
}

QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    border-bottom-right-radius: 6px;
}

QComboBox QAbstractItemView {
    color: #edf3fa;
    background: #121923;
    border: 1px solid #34445a;
    selection-background-color: #205e5b;
    outline: 0;
}

QPushButton {
    min-height: 36px;
    color: #dce7f3;
    background: #1a2532;
    border: 1px solid #314258;
    border-radius: 7px;
    padding: 0 15px;
    font-weight: 600;
}

QPushButton:hover {
    background: #233247;
    border-color: #46617f;
}

QPushButton:pressed {
    background: #162230;
}

QPushButton#primaryButton {
    color: #071311;
    background: #49dfcc;
    border-color: #62ead8;
}

QPushButton#primaryButton:hover {
    background: #67ead9;
}

QPushButton#dangerButton {
    color: #ffd9dd;
    background: #3a2027;
    border-color: #6b303c;
}

QPushButton:disabled {
    color: #596575;
    background: #121820;
    border-color: #222d3b;
}

QPushButton#primaryButton:disabled,
QPushButton#dangerButton:disabled {
    color: #596575;
    background: #121820;
    border-color: #222d3b;
}

QToolButton#sectionToggle {
    min-height: 28px;
    color: #8deee2;
    background: transparent;
    border: none;
    padding: 2px 0;
    font-weight: 650;
}

QToolButton#sectionToggle:hover {
    color: #c0fff7;
}

QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {
    color: #667384;
    background: #10161e;
    border-color: #222d3b;
}

QCheckBox {
    color: #c5d1df;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #40536c;
    background: #0d141d;
}

QCheckBox::indicator:checked {
    background: #3dd6c5;
    border-color: #3dd6c5;
}

QProgressBar {
    min-height: 13px;
    max-height: 13px;
    color: transparent;
    background: #0d141d;
    border: none;
    border-radius: 6px;
}

QProgressBar::chunk {
    background: #3dd6c5;
    border-radius: 6px;
}

QPlainTextEdit#log {
    font-family: "Cascadia Mono", "Consolas";
    font-size: 9pt;
}

QScrollBar:vertical {
    width: 10px;
    background: transparent;
}

QScrollBar::handle:vertical {
    min-height: 30px;
    background: #34445a;
    border-radius: 5px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""


class ChoiceComboBox(QComboBox):
    """A clearly marked choice control that ignores unfocused wheel input."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        help_text = tr(
            "Click to choose an option. Mouse wheel changes the value only while "
            "this control has focus."
        )
        self.setToolTip(help_text)
        self.setAccessibleDescription(help_text)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self.hasFocus():
            event.ignore()
            return
        super().wheelEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#8deee2" if self.isEnabled() else "#596575")
        painter.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        center_x = self.width() - 17.0
        center_y = self.height() / 2.0
        painter.drawLine(
            QPointF(center_x - 4.0, center_y - 2.0),
            QPointF(center_x, center_y + 2.0),
        )
        painter.drawLine(
            QPointF(center_x, center_y + 2.0),
            QPointF(center_x + 4.0, center_y - 2.0),
        )
        painter.end()


class StepSpinBox(QSpinBox):
    """A numeric control with visible step buttons and focus-safe wheel input."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        help_text = tr(
            "Use the plus and minus buttons, arrow keys, or the mouse wheel while "
            "this control has focus."
        )
        self.setToolTip(help_text)
        self.setAccessibleDescription(help_text)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self.hasFocus():
            event.ignore()
            return
        super().wheelEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#8deee2" if self.isEnabled() else "#596575")
        painter.setPen(QPen(color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        center_x = self.width() - 17.0
        top_y = self.height() / 4.0
        bottom_y = self.height() * 3.0 / 4.0
        painter.drawLine(QPointF(center_x - 3.0, top_y), QPointF(center_x + 3.0, top_y))
        painter.drawLine(QPointF(center_x, top_y - 3.0), QPointF(center_x, top_y + 3.0))
        painter.drawLine(
            QPointF(center_x - 3.0, bottom_y), QPointF(center_x + 3.0, bottom_y)
        )
        painter.end()


def responsive_column_count(width: int, maximum: int) -> int:
    """Return a stable field-column count for the available scroll width."""
    if width >= 980:
        return maximum
    if width >= 720:
        return min(2, maximum)
    return 1


def capability_details_text(report: CapabilityReport) -> str:
    """Render the complete diagnostic report shown outside primary selectors."""
    lines: list[str] = []
    for device in report.devices:
        lines.append(
            f"{device.device_type} | {device.name} | "
            + tr(
                "driver {driver} | status {status}",
                driver=device.driver_version,
                status=device.status,
            )
        )
    lines.append("")
    for backend in report.backends:
        lines.append(
            tr(
                "{backend}\n  Driver: {driver}\n  {reason}",
                backend=backend.label,
                driver=backend.driver_version,
                reason=backend.reason,
            )
        )
        for probe in backend.encoders:
            spec = ENCODERS[probe.encoder_id]
            marker = tr("passed") if probe.available else tr("failed")
            lines.append(
                f"    {spec.ffmpeg_name}: {marker} ({probe.elapsed_ms} ms) · "
                f"{probe.detail}"
            )
            for failure in probe.option_failures:
                lines.append(f"      × {failure}")
    return "\n".join(lines)


PROFILE_DESCRIPTIONS: dict[str, str] = {
    "custom": "Manually combine device, format, quality, and video settings.",
    "demo": (
        "Screen demo: HEVC, 30 fps, constant high quality, slowest quality preset."
    ),
    "general": ("General high quality: HEVC, source frame rate, high-quality preset."),
    "compact": (
        "Small file: prefer AV1, keep source frame rate, and increase compression."
    ),
    "compatible": (
        "Compatibility first: H.264, MP4, 8-bit, for broad playback support."
    ),
    "streaming": ("Fixed bandwidth: H.264, 30 fps, CBR, 2-second keyframe interval."),
}


def build_app_icon(size: int = 256) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    bounds = QRectF(7, 7, size - 14, size - 14)
    gradient = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
    gradient.setColorAt(0.0, QColor("#1d3d58"))
    gradient.setColorAt(0.52, QColor("#173248"))
    gradient.setColorAt(1.0, QColor("#10242f"))
    painter.setPen(QPen(QColor("#3dd6c5"), 4))
    painter.setBrush(gradient)
    painter.drawRoundedRect(bounds, 48, 48)

    screen = QRectF(45, 58, 166, 119)
    painter.setPen(QPen(QColor("#9ff8e9"), 9, Qt.PenStyle.SolidLine))
    painter.setBrush(QColor("#0b151d"))
    painter.drawRoundedRect(screen, 20, 20)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#49dfcc"))
    painter.drawPolygon(
        QPolygonF([QPointF(105, 88), QPointF(105, 148), QPointF(157, 118)])
    )

    painter.setPen(
        QPen(QColor("#6ea7c8"), 9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    )
    painter.drawLine(QPointF(76, 207), QPointF(113, 207))
    painter.drawLine(QPointF(180, 207), QPointF(143, 207))
    painter.setBrush(QColor("#6ea7c8"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon(
        QPolygonF([QPointF(113, 194), QPointF(132, 207), QPointF(113, 220)])
    )
    painter.drawPolygon(
        QPolygonF([QPointF(143, 194), QPointF(124, 207), QPointF(143, 220)])
    )
    painter.end()
    return QIcon(pixmap)


class DetectionWorker(QObject):
    progress = Signal(int, int, str)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, tools: ToolPaths) -> None:
        super().__init__()
        self.tools = tools
        self.cancel_event = threading.Event()

    @Slot()
    def run(self) -> None:
        try:
            report = detect_capabilities(
                self.tools,
                self.cancel_event,
                self.progress.emit,
            )
        except InterruptedError as error:
            self.cancelled.emit(str(error))
        except Exception as error:  # noqa: BLE001 - report failures to the GUI.
            self.failed.emit(str(error))
        else:
            self.succeeded.emit(report)

    def request_cancel(self) -> None:
        self.cancel_event.set()


class EncodeWorker(QObject):
    progress = Signal(float, str)
    log = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, tools: ToolPaths, job: CompressionJob) -> None:
        super().__init__()
        self.tools = tools
        self.job = job
        self.cancel_event = threading.Event()
        self.process_lock = threading.Lock()
        self.process: subprocess.Popen[str] | None = None

    @Slot()
    def run(self) -> None:
        try:
            result = execute_job(
                self.tools,
                self.job,
                self.cancel_event,
                self.progress.emit,
                self.log.emit,
                self._set_process,
            )
        except InterruptedError as error:
            self.cancelled.emit(str(error))
        except Exception as error:  # noqa: BLE001 - convert worker errors to a signal.
            self.failed.emit(str(error))
        else:
            self.succeeded.emit(result)

    def _set_process(self, process: subprocess.Popen[str] | None) -> None:
        with self.process_lock:
            self.process = process

    def request_cancel(self) -> None:
        self.cancel_event.set()
        with self.process_lock:
            process = self.process
        if process is not None and process.poll() is None:
            process.terminate()


class MainWindow(QMainWindow):
    def __init__(
        self,
        initial_input: str | None = None,
        explicit_ffmpeg: str | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle(f"{APP_NAME} · {tr('Universal encoding workbench')}")
        self.setWindowIcon(build_app_icon())
        self.setMinimumSize(940, 760)
        self.resize(1120, 960)
        self.setAcceptDrops(True)

        self.settings = QSettings(ORGANIZATION_NAME, APP_NAME)
        self.tools: ToolPaths | None = None
        self.capability_report: CapabilityReport | None = None
        self.source_info: MediaInfo | None = None
        self.source_path: Path | None = None
        self.last_output_path: Path | None = None
        self.encode_thread: QThread | None = None
        self.encode_worker: EncodeWorker | None = None
        self.detection_thread: QThread | None = None
        self.detection_worker: DetectionWorker | None = None
        self.running_encode = False
        self.running_detection = False
        self.pending_detection = False
        self.previous_capability_report: CapabilityReport | None = None
        self.detection_started_at = 0.0
        self.close_after_cancel = False
        self.output_is_automatic = True
        self.setting_output = False
        self.updating_controls = False
        self.startup_detection_timer = QTimer(self)
        self.startup_detection_timer.setSingleShot(True)
        self.startup_detection_timer.timeout.connect(self.refresh_capabilities)

        self._build_ui()
        self._connect_signals()
        self._restore_settings()
        self._initialize_tools(explicit_ffmpeg)
        self._set_running(False)

        if self.tools is not None:
            self._configure_startup_detection()
        if initial_input:
            QTimer.singleShot(0, lambda: self.set_input_path(initial_input))

    def _build_ui(self) -> None:
        shell = QWidget(objectName="shell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        root = QWidget(objectName="root")
        root.setMinimumWidth(880)
        self.scroll_area = QScrollArea(objectName="rootScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setWidget(root)
        shell_layout.addWidget(self.scroll_area, 1)
        self.setCentralWidget(shell)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QGridLayout()
        header.setHorizontalSpacing(12)
        header.setVerticalSpacing(2)
        header.addWidget(
            QLabel(tr("Universal video compression workbench"), objectName="appTitle"),
            0,
            0,
        )
        header.addWidget(
            QLabel(
                tr("CPU · GPU · NPU capability detection · H.264 / HEVC / AV1 / VP9"),
                objectName="appSubtitle",
            ),
            1,
            0,
        )
        header.addWidget(QLabel(tr("Language"), objectName="fieldLabel"), 1, 1)
        self.language_combo = ChoiceComboBox()
        for language_id, language_name in LANGUAGE_NAMES.items():
            self.language_combo.addItem(language_name, language_id)
        self.language_combo.setCurrentIndex(
            max(0, self.language_combo.findData(get_language()))
        )
        header.addWidget(self.language_combo, 1, 2)
        self.capability_pill = QLabel(
            tr("Preparing hardware detection"), objectName="warningPill"
        )
        self.capability_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.capability_pill, 0, 1, 1, 2)
        header.setColumnStretch(0, 1)
        layout.addLayout(header)

        self.workflow_banner = QLabel(
            tr(
                "1  Select a video  ·  2  Finish hardware detection  ·  "
                "3  Choose a quick profile  ·  4  Start compression"
            ),
            objectName="workflowBanner",
        )
        self.workflow_banner.setWordWrap(True)
        layout.addWidget(self.workflow_banner)

        source_card, source_layout = self._new_card(tr("Source and output"))
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText(
            tr("Select a video or drop a file into the window")
        )
        self.input_edit.setClearButtonEnabled(True)
        self.browse_input_button = QPushButton(tr("Select video"))
        self.browse_input_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        )
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        input_row.addWidget(self.input_edit, 1)
        input_row.addWidget(self.browse_input_button)
        source_layout.addWidget(
            QLabel(tr("Input video"), objectName="fieldLabel"), 1, 0
        )
        source_layout.addLayout(input_row, 1, 1)

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText(
            tr("Leave blank to name automatically from the format and encoder")
        )
        self.output_edit.setClearButtonEnabled(True)
        self.auto_output_button = QPushButton(tr("Automatic name"))
        self.browse_output_button = QPushButton(tr("Save location"))
        self.browse_output_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        output_row = QHBoxLayout()
        output_row.setSpacing(8)
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.auto_output_button)
        output_row.addWidget(self.browse_output_button)
        source_layout.addWidget(
            QLabel(tr("Output file"), objectName="fieldLabel"), 2, 0
        )
        source_layout.addLayout(output_row, 2, 1)

        self.source_info_label = QLabel(
            tr("Media information appears after selecting a video.")
        )
        self.source_info_label.setObjectName("muted")
        self.source_info_label.setWordWrap(True)
        source_layout.addWidget(self.source_info_label, 3, 1)
        layout.addWidget(source_card)

        device_card, device_layout = self._new_card(tr("Encoding device and format"))
        self.device_controls = QGridLayout()
        self.device_controls.setHorizontalSpacing(16)
        self.device_controls.setVerticalSpacing(8)

        self.backend_combo = ChoiceComboBox()
        self.backend_combo.setMinimumContentsLength(30)
        backend_help = tr(
            "Only CPU and GPU devices that passed a real FFmpeg encoding test are "
            "listed. NPU information is shown as detection status only."
        )
        self.backend_combo.setToolTip(backend_help)
        self.backend_combo.setAccessibleDescription(backend_help)
        self.codec_combo = ChoiceComboBox()
        codec_help = tr(
            "Friendly codec names are shown here. Technical FFmpeg encoder names "
            "remain available in Detection details."
        )
        self.codec_combo.setToolTip(codec_help)
        self.codec_combo.setAccessibleDescription(codec_help)
        self.container_combo = ChoiceComboBox()
        for container in CONTAINERS.values():
            self.container_combo.addItem(tr(container.label), container.id)
        self.container_combo.setCurrentIndex(
            max(0, self.container_combo.findData("mp4"))
        )
        self.refresh_button = QPushButton(tr("Detect now"))
        self.details_button = QPushButton(tr("Detection details"))
        self.details_button.setEnabled(False)
        self.cancel_detection_button = QPushButton(
            tr("Cancel detection"), objectName="dangerButton"
        )
        self.cancel_detection_button.setVisible(False)
        self.auto_detect_checkbox = QCheckBox(tr("Detect automatically on startup"))
        self.auto_detect_checkbox.setChecked(True)
        self.auto_detect_checkbox.setToolTip(
            tr(
                "Turn this off to leave detection paused at the next startup; "
                "you can still start it manually."
            )
        )

        self.device_fields = (
            (
                QLabel(tr("Encoding device"), objectName="fieldLabel"),
                self.backend_combo,
            ),
            (QLabel(tr("Video codec"), objectName="fieldLabel"), self.codec_combo),
            (QLabel(tr("Container"), objectName="fieldLabel"), self.container_combo),
        )
        self._place_labeled_fields(self.device_controls, self.device_fields, 3)
        device_layout.addLayout(self.device_controls, 1, 0, 1, 2)

        self.device_selector_note = QLabel(
            tr(
                "Only verified encoding choices appear above. Unavailable devices, "
                "drivers, and technical test results remain in Detection details."
            ),
            objectName="muted",
        )
        self.device_selector_note.setWordWrap(True)
        device_layout.addWidget(self.device_selector_note, 2, 0, 1, 2)

        detection_buttons = QHBoxLayout()
        detection_buttons.addWidget(self.auto_detect_checkbox)
        detection_buttons.addStretch(1)
        detection_buttons.addWidget(self.refresh_button)
        detection_buttons.addWidget(self.details_button)
        detection_buttons.addWidget(self.cancel_detection_button)
        device_layout.addLayout(detection_buttons, 3, 0, 1, 2)

        self.hardware_summary = QLabel(
            tr(
                "Devices, drivers, FFmpeg encoders, and a real one-frame "
                "initialization are checked separately."
            ),
            objectName="hintPanel",
        )
        self.hardware_summary.setWordWrap(True)
        device_layout.addWidget(self.hardware_summary, 4, 0, 1, 2)
        layout.addWidget(device_card)

        quality_card, quality_layout = self._new_card(tr("Video and quality"))
        self.quality_controls = QGridLayout()
        self.quality_controls.setHorizontalSpacing(16)
        self.quality_controls.setVerticalSpacing(8)

        self.profile_combo = ChoiceComboBox()
        self.profile_combo.addItem(tr("Custom"), "custom")
        self.profile_combo.addItem(tr("High-quality demo"), "demo")
        self.profile_combo.addItem(tr("General high quality"), "general")
        self.profile_combo.addItem(tr("Small file"), "compact")
        self.profile_combo.addItem(tr("Compatibility first"), "compatible")
        self.profile_combo.addItem(tr("Fixed bandwidth / streaming"), "streaming")
        self.profile_combo.setCurrentIndex(self.profile_combo.findData("demo"))

        self.quality_mode_combo = ChoiceComboBox()
        self.quality_value_spin = StepSpinBox()
        self.speed_combo = ChoiceComboBox()
        for speed_id, label in SPEED_LABELS.items():
            self.speed_combo.addItem(tr(label), speed_id)
        self.speed_combo.setCurrentIndex(self.speed_combo.findData("max_quality"))

        self.resolution_combo = ChoiceComboBox()
        for height, label in RESOLUTION_OPTIONS.items():
            self.resolution_combo.addItem(tr(label), height)

        self.frame_rate_spin = StepSpinBox()
        self.frame_rate_spin.setRange(0, 240)
        self.frame_rate_spin.setSpecialValueText(tr("Keep source frame rate"))
        self.frame_rate_spin.setSuffix(" fps")
        self.frame_rate_spin.setValue(30)

        self.pixel_depth_combo = ChoiceComboBox()
        self.gop_spin = StepSpinBox()
        self.gop_spin.setRange(1, 30)
        self.gop_spin.setValue(10)
        self.gop_spin.setSuffix(tr(" seconds"))

        self.basic_quality_fields = (
            (QLabel(tr("Quick profile"), objectName="fieldLabel"), self.profile_combo),
            (
                QLabel(tr("Resolution"), objectName="fieldLabel"),
                self.resolution_combo,
            ),
            (
                QLabel(tr("Frame rate"), objectName="fieldLabel"),
                self.frame_rate_spin,
            ),
        )
        self.advanced_quality_fields = (
            (
                QLabel(tr("Quality mode"), objectName="fieldLabel"),
                self.quality_mode_combo,
            ),
            (
                QLabel(tr("Quality value / bitrate"), objectName="fieldLabel"),
                self.quality_value_spin,
            ),
            (
                QLabel(tr("Speed and quality"), objectName="fieldLabel"),
                self.speed_combo,
            ),
            (
                QLabel(tr("Pixel depth"), objectName="fieldLabel"),
                self.pixel_depth_combo,
            ),
            (
                QLabel(tr("Keyframe interval"), objectName="fieldLabel"),
                self.gop_spin,
            ),
        )
        self.quality_fields = self.basic_quality_fields + self.advanced_quality_fields
        self._place_labeled_fields(self.quality_controls, self.quality_fields, 3)
        quality_layout.addLayout(self.quality_controls, 1, 0, 1, 2)

        self.advanced_toggle_button = QToolButton(objectName="sectionToggle")
        self.advanced_toggle_button.setCheckable(True)
        self.advanced_toggle_button.setChecked(False)
        self.advanced_toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.advanced_toggle_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.advanced_toggle_button.setText(tr("Show advanced video settings"))
        self.advanced_toggle_button.setToolTip(
            tr(
                "Quick profiles already configure these options. Expand them only "
                "when you need manual control."
            )
        )
        for label, widget in self.advanced_quality_fields:
            label.setVisible(False)
            widget.setVisible(False)
        quality_layout.addWidget(self.advanced_toggle_button, 2, 0, 1, 2)

        self.quality_hint = QLabel(objectName="hintPanel")
        self.quality_hint.setWordWrap(True)
        quality_layout.addWidget(self.quality_hint, 3, 0, 1, 2)
        layout.addWidget(quality_card)

        audio_card, audio_layout = self._new_card(tr("Audio and publishing"))
        self.audio_controls = QGridLayout()
        self.audio_controls.setHorizontalSpacing(16)
        self.audio_controls.setVerticalSpacing(8)
        self.audio_combo = ChoiceComboBox()
        self.audio_bitrate_spin = StepSpinBox()
        self.audio_bitrate_spin.setRange(32, 512)
        self.audio_bitrate_spin.setValue(128)
        self.audio_bitrate_spin.setSuffix(" kb/s")
        self.audio_fields = (
            (QLabel(tr("Audio mode"), objectName="fieldLabel"), self.audio_combo),
            (
                QLabel(tr("Audio bitrate"), objectName="fieldLabel"),
                self.audio_bitrate_spin,
            ),
        )
        self._place_labeled_fields(self.audio_controls, self.audio_fields, 2)
        audio_layout.addLayout(self.audio_controls, 1, 0, 1, 2)

        options = QHBoxLayout()
        options.setSpacing(24)
        self.overwrite_checkbox = QCheckBox(tr("Allow overwriting an existing output"))
        self.hash_checkbox = QCheckBox(tr("Calculate SHA-256 when finished"))
        options.addWidget(self.overwrite_checkbox)
        options.addWidget(self.hash_checkbox)
        options.addStretch(1)
        audio_layout.addLayout(options, 2, 0, 1, 2)
        layout.addWidget(audio_card)

        self.sticky_bar = QFrame(objectName="stickyBar")
        progress_layout = QGridLayout(self.sticky_bar)
        progress_layout.setContentsMargins(28, 10, 28, 12)
        progress_layout.setHorizontalSpacing(12)
        progress_layout.setVerticalSpacing(8)
        progress_layout.addWidget(
            QLabel(tr("Task progress"), objectName="sectionTitle"), 0, 0
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar, 1, 0, 1, 3)

        self.status_label = QLabel(
            tr("Waiting for hardware detection."), objectName="muted"
        )
        self.metrics_label = QLabel("0.0%", objectName="muted")
        self.metrics_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_layout.addWidget(self.status_label, 0, 1)
        progress_layout.addWidget(self.metrics_label, 0, 2)
        progress_layout.setColumnStretch(1, 1)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.inspect_button = QPushButton(tr("Analyze source"))
        self.preview_button = QPushButton(tr("Preview command"))
        self.open_output_button = QPushButton(tr("Open output directory"))
        self.open_output_button.setEnabled(False)
        self.cancel_button = QPushButton(tr("Cancel"), objectName="dangerButton")
        self.start_button = QPushButton(
            tr("Start compression"), objectName="primaryButton"
        )
        self.start_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )
        self.cancel_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)
        )
        action_row.addWidget(self.inspect_button)
        action_row.addWidget(self.preview_button)
        action_row.addWidget(self.open_output_button)
        action_row.addStretch(1)
        action_row.addWidget(self.cancel_button)
        action_row.addWidget(self.start_button)
        progress_layout.addLayout(action_row, 2, 0, 1, 3)

        log_card, log_layout = self._new_card(tr("Runtime log"))
        self.log_edit = QPlainTextEdit(objectName="log")
        self.log_edit.setReadOnly(True)
        self.log_edit.setPlaceholderText(
            tr("Device probing, FFmpeg commands, and verification results appear here.")
        )
        self.log_edit.setMinimumHeight(150)
        log_layout.addWidget(self.log_edit, 1, 0)
        layout.addWidget(log_card, 1)

        footer = QHBoxLayout()
        footer.addWidget(QLabel(f"{APP_NAME} {APP_VERSION}", objectName="muted"))
        footer.addStretch(1)
        footer.addWidget(
            QLabel(
                tr("Ctrl+R start · Esc cancel · File drag and drop supported"),
                objectName="muted",
            )
        )
        layout.addLayout(footer)
        shell_layout.addWidget(self.sticky_bar)

        self._responsive_device_columns = 3
        self._responsive_quality_columns = 3
        self._responsive_audio_columns = 2
        QTimer.singleShot(0, self._update_responsive_layout)

    @staticmethod
    def _place_labeled_fields(
        grid: QGridLayout,
        fields: tuple[tuple[QLabel, QWidget], ...],
        columns: int,
    ) -> None:
        while grid.takeAt(0) is not None:
            pass
        for column in range(max(3, columns)):
            grid.setColumnStretch(column, 0)
        for index, (label, widget) in enumerate(fields):
            row = (index // columns) * 2
            column = index % columns
            grid.addWidget(label, row, column)
            grid.addWidget(widget, row + 1, column)
        for column in range(columns):
            grid.setColumnStretch(column, 1)

    @Slot()
    def _update_responsive_layout(self) -> None:
        available_width = self.scroll_area.viewport().width() or self.width()
        device_columns = responsive_column_count(available_width, 3)
        quality_columns = responsive_column_count(available_width, 3)
        audio_columns = responsive_column_count(available_width, 2)

        if device_columns != self._responsive_device_columns:
            self._place_labeled_fields(
                self.device_controls, self.device_fields, device_columns
            )
            self._responsive_device_columns = device_columns
        if quality_columns != self._responsive_quality_columns:
            self._place_labeled_fields(
                self.quality_controls, self.quality_fields, quality_columns
            )
            self._responsive_quality_columns = quality_columns
        if audio_columns != self._responsive_audio_columns:
            self._place_labeled_fields(
                self.audio_controls, self.audio_fields, audio_columns
            )
            self._responsive_audio_columns = audio_columns

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_responsive_device_columns"):
            self._update_responsive_layout()

    def _new_card(self, title: str) -> tuple[QFrame, QGridLayout]:
        card = QFrame(objectName="card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(18, 15, 18, 17)
        card_layout.setHorizontalSpacing(12)
        card_layout.setVerticalSpacing(10)
        card_layout.addWidget(QLabel(title, objectName="sectionTitle"), 0, 0, 1, 2)
        return card, card_layout

    def _connect_signals(self) -> None:
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        self.browse_input_button.clicked.connect(self.choose_input)
        self.browse_output_button.clicked.connect(self.choose_output)
        self.auto_output_button.clicked.connect(self.enable_automatic_output)
        self.input_edit.editingFinished.connect(self.inspect_source)
        self.output_edit.textEdited.connect(self._mark_output_manual)
        self.refresh_button.clicked.connect(self.refresh_capabilities)
        self.details_button.clicked.connect(self.show_capability_details)
        self.cancel_detection_button.clicked.connect(self.cancel_detection)
        self.auto_detect_checkbox.toggled.connect(
            self._auto_detection_preference_changed
        )
        self.backend_combo.currentIndexChanged.connect(self._backend_changed)
        self.container_combo.currentIndexChanged.connect(self._container_changed)
        self.codec_combo.currentIndexChanged.connect(self._encoder_changed)
        self.pixel_depth_combo.currentIndexChanged.connect(self._pixel_depth_changed)
        self.quality_mode_combo.currentIndexChanged.connect(self._quality_mode_changed)
        self.audio_combo.currentIndexChanged.connect(self._audio_mode_changed)
        self.advanced_toggle_button.toggled.connect(self._toggle_advanced_settings)
        self.profile_combo.activated.connect(self._profile_selected)
        self.inspect_button.clicked.connect(self.inspect_source)
        self.preview_button.clicked.connect(self.preview_command)
        self.start_button.clicked.connect(self.start_encode)
        self.cancel_button.clicked.connect(self.cancel_active_operation)
        self.open_output_button.clicked.connect(self.open_output_directory)

        for combo in (
            self.backend_combo,
            self.container_combo,
            self.codec_combo,
            self.quality_mode_combo,
            self.speed_combo,
            self.resolution_combo,
            self.pixel_depth_combo,
            self.audio_combo,
        ):
            combo.activated.connect(self._manual_setting_changed)
        for spin in (
            self.quality_value_spin,
            self.frame_rate_spin,
            self.gop_spin,
            self.audio_bitrate_spin,
        ):
            spin.valueChanged.connect(self._manual_setting_changed)
            spin.valueChanged.connect(self._refresh_automatic_output)

        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self.start_encode)
        QShortcut(QKeySequence("Escape"), self).activated.connect(
            self.cancel_active_operation
        )

    @Slot()
    def _language_changed(self) -> None:
        language = str(self.language_combo.currentData() or get_language())
        if language == get_language():
            return
        self.settings.setValue("ui/language", language)
        language_name = LANGUAGE_NAMES[language]
        QMessageBox.information(
            self,
            translate_for(language, "Language saved"),
            translate_for(
                language,
                "Restart the application to use {language}.",
                language=language_name,
            ),
        )

    def _initialize_tools(self, explicit_ffmpeg: str | None) -> None:
        try:
            self.tools = resolve_tools(explicit_ffmpeg)
        except Exception as error:  # noqa: BLE001 - show startup failures in the GUI.
            message = str(error)
            self.tools = None
            self.capability_pill.setObjectName("warningPill")
            self.capability_pill.setText(tr("FFmpeg unavailable"))
            self.status_label.setText(message)
            self.append_log(tr("Startup check failed: {message}", message=message))
            self.start_button.setEnabled(False)
            QTimer.singleShot(
                100,
                lambda: QMessageBox.critical(self, tr("FFmpeg unavailable"), message),
            )
            return
        mode = tr("bundled") if self.tools.bundled else tr("system")
        self.append_log(
            tr("FFmpeg ({mode}): {path}", mode=mode, path=self.tools.ffmpeg)
        )

    def _restore_settings(self) -> None:
        geometry = self.settings.value("window/geometry-v2")
        if geometry:
            self.restoreGeometry(geometry)
        auto_detect = self.settings.value("detection/auto_start", True)
        self.auto_detect_checkbox.setChecked(
            str(auto_detect).strip().lower() not in {"0", "false", "no"}
        )
        last_directory = self.settings.value("paths/last_directory", "")
        self.last_directory = Path(str(last_directory)) if last_directory else None

    def _save_settings(self) -> None:
        self.settings.setValue("window/geometry-v2", self.saveGeometry())
        self.settings.setValue(
            "detection/auto_start", self.auto_detect_checkbox.isChecked()
        )
        if self.source_path:
            self.settings.setValue("paths/last_directory", str(self.source_path.parent))

    def _set_capability_pill(self, object_name: str, text: str) -> None:
        self.capability_pill.setObjectName(object_name)
        self.capability_pill.style().unpolish(self.capability_pill)
        self.capability_pill.style().polish(self.capability_pill)
        self.capability_pill.setText(text)

    def _configure_startup_detection(self) -> None:
        if self.auto_detect_checkbox.isChecked():
            self._schedule_startup_detection()
        else:
            self._set_detection_deferred()

    def _schedule_startup_detection(self) -> None:
        if self.tools is None or self.capability_report is not None:
            return
        self.startup_detection_timer.stop()
        self.pending_detection = True
        self._set_capability_pill("warningPill", tr("Detection scheduled"))
        self.status_label.setText(tr("Hardware detection will start shortly."))
        self.hardware_summary.setText(
            tr("You can select a source now or skip this startup check.")
        )
        self.progress_bar.setValue(0)
        self.metrics_label.setText(tr("Starting soon"))
        self.refresh_button.setText(tr("Detect now"))
        self.cancel_detection_button.setText(tr("Skip startup detection"))
        self.cancel_detection_button.setVisible(True)
        self.cancel_detection_button.setEnabled(True)
        self._set_running(False)
        self.startup_detection_timer.start(2_000)

    def _set_detection_deferred(self) -> None:
        self.startup_detection_timer.stop()
        self.pending_detection = False
        self._set_capability_pill("warningPill", tr("Detection paused"))
        self.status_label.setText(
            tr("Hardware detection is paused. Select a source or choose Detect now.")
        )
        self.hardware_summary.setText(
            tr("Detection is required before compression can start.")
        )
        self.progress_bar.setValue(0)
        self.metrics_label.setText(tr("Not started"))
        self.refresh_button.setText(tr("Detect now"))
        self.cancel_detection_button.setVisible(False)
        self._set_running(False)

    @Slot(bool)
    def _auto_detection_preference_changed(self, enabled: bool) -> None:
        self.settings.setValue("detection/auto_start", enabled)
        if self.tools is None or self.capability_report is not None:
            return
        if not enabled and self.pending_detection:
            self.cancel_detection()
        elif (
            enabled
            and not self.pending_detection
            and not self.running_detection
            and not self.running_encode
        ):
            self._schedule_startup_detection()

    @Slot()
    def refresh_capabilities(self) -> None:
        if (
            self.tools is None
            or self.running_detection
            or self.running_encode
            or self.detection_thread is not None
        ):
            return
        self.startup_detection_timer.stop()
        self.pending_detection = False
        self.previous_capability_report = self.capability_report
        self.running_detection = True
        self.detection_started_at = time.monotonic()
        self.capability_pill.setObjectName("warningPill")
        self.capability_pill.style().unpolish(self.capability_pill)
        self.capability_pill.style().polish(self.capability_pill)
        self.capability_pill.setText(tr("Detecting devices and drivers"))
        self.hardware_summary.setText(
            tr(
                "Enumerating CPU/GPU/NPU and running a one-frame initialization "
                "test for every candidate encoder…"
            )
        )
        self.status_label.setText(tr("Detecting hardware capabilities…"))
        self.progress_bar.setValue(0)
        self.metrics_label.setText(tr("Estimating remaining time…"))
        self.refresh_button.setText(tr("Detecting…"))
        self.cancel_detection_button.setText(tr("Cancel detection"))
        self.cancel_detection_button.setVisible(True)
        self.cancel_detection_button.setEnabled(True)
        self._set_running(False)

        thread = QThread(self)
        worker = DetectionWorker(self.tools)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._detection_progress)
        worker.succeeded.connect(self._detection_succeeded)
        worker.failed.connect(self._detection_failed)
        worker.cancelled.connect(self._detection_cancelled)
        worker.succeeded.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._detection_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self.detection_thread = thread
        self.detection_worker = worker
        thread.start()

    @Slot()
    def cancel_detection(self) -> None:
        if self.pending_detection:
            self._set_detection_deferred()
            self.append_log(tr("Startup hardware detection was skipped."))
            return
        if not self.running_detection or self.detection_worker is None:
            return
        self.status_label.setText(tr("Cancelling hardware detection…"))
        self.hardware_summary.setText(
            tr("Stopping the active encoder test and preserving previous results…")
        )
        self.cancel_detection_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.detection_worker.request_cancel()

    @Slot(int, int, str)
    def _detection_progress(self, completed: int, total: int, status: str) -> None:
        if not self.running_detection or total <= 0:
            return
        current = min(max(completed, 0), total)
        elapsed = max(0.0, time.monotonic() - self.detection_started_at)
        self.progress_bar.setValue(round(current / total * 1000))
        if current <= 0:
            metrics = tr(
                "{current}/{total} · {elapsed:.1f}s elapsed · estimating…",
                current=current,
                total=total,
                elapsed=elapsed,
            )
        elif current < total:
            remaining = elapsed / current * (total - current)
            metrics = tr(
                "{current}/{total} · {elapsed:.1f}s elapsed · about "
                "{remaining:.1f}s remaining",
                current=current,
                total=total,
                elapsed=elapsed,
                remaining=remaining,
            )
        else:
            metrics = tr(
                "{current}/{total} · {elapsed:.1f}s elapsed",
                current=current,
                total=total,
                elapsed=elapsed,
            )
        self.metrics_label.setText(metrics)
        self.status_label.setText(status)
        self.hardware_summary.setText(
            tr(
                "Step {current} of {total}: {status}\nYou can select a source while "
                "detection continues, or cancel this check.",
                current=current,
                total=total,
                status=status,
            )
        )

    @Slot(object)
    def _detection_succeeded(self, report: CapabilityReport) -> None:
        self.capability_report = report
        self.running_detection = False
        self.previous_capability_report = None
        self.cancel_detection_button.setVisible(False)
        self.refresh_button.setText(tr("Detect again"))
        available_backends = [
            backend for backend in report.backends if backend.available
        ]
        available_encoders = sum(
            len(backend.available_encoder_ids) for backend in available_backends
        )
        self.capability_pill.setObjectName("statusPill")
        self.capability_pill.style().unpolish(self.capability_pill)
        self.capability_pill.style().polish(self.capability_pill)
        self.capability_pill.setText(
            tr(
                "{backends} backends · {encoders} encoders",
                backends=len(available_backends),
                encoders=available_encoders,
            )
        )
        self.status_label.setText(
            tr("Device, driver, and encoder detection completed.")
        )
        self.details_button.setEnabled(True)
        self._populate_backends()
        self._update_hardware_summary()
        self._log_capabilities(report)
        self._set_running(False)
        if self.profile_combo.currentData() != "custom":
            self._apply_profile(str(self.profile_combo.currentData()))

    @Slot(str)
    def _detection_failed(self, message: str) -> None:
        self.running_detection = False
        self.capability_report = self.previous_capability_report
        self.previous_capability_report = None
        self.cancel_detection_button.setVisible(False)
        self.refresh_button.setText(
            tr("Detect again")
            if self.capability_report is not None
            else tr("Detect now")
        )
        if self.capability_report is None:
            self._set_capability_pill("warningPill", tr("Hardware detection failed"))
            self.hardware_summary.setText(message)
        else:
            self._set_capability_pill("statusPill", tr("Previous results retained"))
            self._update_hardware_summary()
        self.status_label.setText(
            tr("Hardware detection failed: {message}", message=message)
        )
        self.append_log(tr("Hardware detection failed: {message}", message=message))
        self._set_running(False)

    @Slot(str)
    def _detection_cancelled(self, message: str) -> None:
        elapsed = max(0.0, time.monotonic() - self.detection_started_at)
        self.running_detection = False
        self.capability_report = self.previous_capability_report
        self.previous_capability_report = None
        self.cancel_detection_button.setVisible(False)
        self.refresh_button.setText(
            tr("Detect again")
            if self.capability_report is not None
            else tr("Detect now")
        )
        self.metrics_label.setText(
            tr("Cancelled after {seconds:.1f}s", seconds=elapsed)
        )
        if self.capability_report is None:
            self._set_capability_pill("warningPill", tr("Detection cancelled"))
            self.hardware_summary.setText(
                tr("No results were applied. Choose Detect now when you are ready.")
            )
        else:
            self._set_capability_pill("statusPill", tr("Previous results retained"))
            self._update_hardware_summary()
        self.status_label.setText(tr("Hardware detection cancelled."))
        self.append_log(tr("Hardware detection cancelled: {message}", message=message))
        self._set_running(False)

    @Slot()
    def _detection_thread_finished(self) -> None:
        self.detection_thread = None
        self.detection_worker = None
        self._set_running(False)

    @Slot(bool)
    def _toggle_advanced_settings(self, expanded: bool) -> None:
        for label, widget in self.advanced_quality_fields:
            label.setVisible(expanded)
            widget.setVisible(expanded)
        self.advanced_toggle_button.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self.advanced_toggle_button.setText(
            tr("Hide advanced video settings")
            if expanded
            else tr("Show advanced video settings")
        )
        self._configure_quality_value()
        QTimer.singleShot(0, self._update_responsive_layout)

    def _populate_backends(self) -> None:
        if self.capability_report is None:
            return
        previous = self.backend_combo.currentData()
        available_backends = [
            backend
            for backend in self.capability_report.backends
            if backend.available and backend.id != "npu"
        ]
        self.updating_controls = True
        self.backend_combo.clear()
        self.backend_combo.setPlaceholderText(tr("No verified encoder available"))
        for backend in available_backends:
            self.backend_combo.addItem(backend.label, backend.id)
            index = self.backend_combo.count() - 1
            self.backend_combo.setItemData(
                index,
                backend.reason,
                Qt.ItemDataRole.ToolTipRole,
            )

        target = str(previous) if previous else ""
        priorities = [target, "amd_amf", "nvidia_nvenc", "intel_qsv", "cpu"]
        for backend_id in priorities:
            index = self.backend_combo.findData(backend_id)
            if index >= 0:
                self.backend_combo.setCurrentIndex(index)
                break
        if not available_backends:
            self.backend_combo.setCurrentIndex(-1)
        self.updating_controls = False
        self._populate_encoders()

    def _populate_encoders(self, preferred_codec: str | None = None) -> None:
        if self.capability_report is None:
            return
        backend_id = self.backend_combo.currentData()
        container_id = self.container_combo.currentData()
        if not backend_id or not container_id:
            self.updating_controls = True
            self.codec_combo.clear()
            self.codec_combo.setPlaceholderText(tr("No verified codec available"))
            self.pixel_depth_combo.clear()
            self.quality_mode_combo.clear()
            self.updating_controls = False
            return
        previous_encoder = self.codec_combo.currentData()
        previous_codec = (
            ENCODERS[str(previous_encoder)].codec_id
            if previous_encoder in ENCODERS
            else None
        )
        specs = available_encoders_for_backend(
            self.capability_report, str(backend_id), str(container_id)
        )

        self.updating_controls = True
        self.codec_combo.clear()
        self.codec_combo.setPlaceholderText(tr("No verified codec available"))
        for spec in specs:
            self.codec_combo.addItem(CODEC_LABELS[spec.codec_id], spec.id)
        desired_codec = preferred_codec or previous_codec or "hevc"
        target_index = next(
            (
                index
                for index, spec in enumerate(specs)
                if spec.codec_id == desired_codec
            ),
            0,
        )
        if specs:
            self.codec_combo.setCurrentIndex(target_index)
        self.updating_controls = False
        self._populate_pixel_depths()
        self._populate_quality_modes()
        self._refresh_automatic_output()

    def _populate_quality_modes(self, preferred: str | None = None) -> None:
        encoder = self.selected_encoder()
        if encoder is None or self.capability_report is None:
            self.quality_mode_combo.clear()
            return
        previous = preferred or self.quality_mode_combo.currentData()
        pixel_depth = int(self.pixel_depth_combo.currentData() or 8)
        modes = supported_quality_modes(self.capability_report, encoder.id, pixel_depth)
        self.updating_controls = True
        self.quality_mode_combo.clear()
        for mode in modes:
            self.quality_mode_combo.addItem(tr(QUALITY_MODE_LABELS[mode]), mode)
        index = self.quality_mode_combo.findData(previous or "constant_quality")
        self.quality_mode_combo.setCurrentIndex(max(0, index))
        self.updating_controls = False
        self._configure_quality_value()

    def _populate_pixel_depths(self, preferred: int | None = None) -> None:
        encoder = self.selected_encoder()
        if encoder is None or self.capability_report is None:
            self.pixel_depth_combo.clear()
            return
        previous = preferred or self.pixel_depth_combo.currentData() or 8
        depths = supported_pixel_depths(self.capability_report, encoder.id)
        self.updating_controls = True
        self.pixel_depth_combo.clear()
        for depth in depths:
            label = tr("8-bit 4:2:0 (compatible)") if depth == 8 else "10-bit 4:2:0"
            self.pixel_depth_combo.addItem(label, depth)
        index = self.pixel_depth_combo.findData(previous)
        self.pixel_depth_combo.setCurrentIndex(max(0, index))
        self.updating_controls = False

    def _populate_audio_modes(self) -> None:
        container_id = str(self.container_combo.currentData() or "mp4")
        container = CONTAINERS[container_id]
        previous = self.audio_combo.currentData()
        self.updating_controls = True
        self.audio_combo.clear()
        for mode in container.audio_modes:
            if (
                mode == "copy"
                and self.source_info is not None
                and not can_copy_audio(container.id, self.source_info.audio_codec)
            ):
                continue
            self.audio_combo.addItem(tr(AUDIO_MODE_LABELS[mode]), mode)
        preferred = previous
        index = self.audio_combo.findData(preferred)
        if index < 0:
            preferred = (
                "copy" if self.source_info and self.source_info.has_audio else "none"
            )
            index = self.audio_combo.findData(preferred)
        self.audio_combo.setCurrentIndex(max(0, index))
        self.updating_controls = False
        self._audio_mode_changed()

    def selected_encoder(self):
        encoder_id = self.codec_combo.currentData()
        return ENCODERS.get(str(encoder_id)) if encoder_id else None

    @Slot()
    def _backend_changed(self) -> None:
        if self.updating_controls:
            return
        self._populate_encoders()
        self._update_hardware_summary()

    @Slot()
    def _container_changed(self) -> None:
        if self.updating_controls:
            return
        self._populate_encoders()
        self._populate_audio_modes()
        if not self.output_is_automatic:
            output = self._output_path()
            container_id = self.container_combo.currentData()
            if output and container_id:
                suffixes = {container.extension for container in CONTAINERS.values()}
                if output.suffix.lower() in suffixes:
                    replacement = output.with_suffix(
                        CONTAINERS[str(container_id)].extension
                    )
                    self.setting_output = True
                    self.output_edit.setText(str(replacement))
                    self.setting_output = False
        self._refresh_automatic_output()

    @Slot()
    def _encoder_changed(self) -> None:
        if self.updating_controls:
            return
        self._populate_pixel_depths()
        self._populate_quality_modes()
        self._refresh_automatic_output()

    @Slot()
    def _pixel_depth_changed(self) -> None:
        if self.updating_controls:
            return
        self._populate_quality_modes()
        self._refresh_automatic_output()

    @Slot()
    def _quality_mode_changed(self) -> None:
        if self.updating_controls:
            return
        self._configure_quality_value()

    def _configure_quality_value(self, desired: int | None = None) -> None:
        encoder = self.selected_encoder()
        mode = self.quality_mode_combo.currentData()
        if encoder is None or not mode:
            return
        minimum, maximum, default, unit, higher_is_better = quality_value_properties(
            encoder, str(mode)
        )
        value = desired if desired is not None else default
        self.updating_controls = True
        self.quality_value_spin.setRange(minimum, maximum)
        self.quality_value_spin.setValue(min(maximum, max(minimum, value)))
        self.quality_value_spin.setSuffix(f" {unit}")
        self.updating_controls = False
        if mode in {"vbr", "cbr"}:
            direction = tr(
                "Higher bitrate usually means better quality and a larger file"
            )
        elif higher_is_better:
            direction = tr(
                "Higher values mean better quality and usually a larger file"
            )
        else:
            direction = tr("Lower values mean better quality and usually a larger file")
        profile_id = str(self.profile_combo.currentData() or "custom")
        self.quality_hint.setText(
            tr(
                "{profile}\n{encoder} · {mode}: {direction}.",
                profile=tr(PROFILE_DESCRIPTIONS[profile_id]),
                encoder=CODEC_LABELS[encoder.codec_id],
                mode=tr(QUALITY_MODE_LABELS[str(mode)]),
                direction=direction,
            )
        )

    @Slot()
    def _audio_mode_changed(self) -> None:
        mode = self.audio_combo.currentData()
        self.audio_bitrate_spin.setEnabled(
            mode in {"aac", "opus"}
            and not self.running_encode
            and not self.running_detection
            and self.capability_report is not None
        )

    @Slot()
    def _profile_selected(self) -> None:
        profile_id = str(self.profile_combo.currentData())
        self._apply_profile(profile_id)

    def _apply_profile(self, profile_id: str) -> None:
        if profile_id == "custom" or self.capability_report is None:
            self._configure_quality_value()
            return

        self.updating_controls = True
        if profile_id == "compact":
            desired_codec = "av1"
            speed = "quality"
            fps = 0
            gop = 10
        elif profile_id == "compatible":
            desired_codec = "h264"
            speed = "balanced"
            fps = 0
            gop = 10
        elif profile_id == "streaming":
            desired_codec = "h264"
            speed = "fast"
            fps = 30
            gop = 2
        else:
            desired_codec = "hevc"
            speed = "max_quality" if profile_id == "demo" else "quality"
            fps = 30 if profile_id == "demo" else 0
            gop = 10

        if profile_id in {"compatible", "streaming", "demo", "general"}:
            index = self.container_combo.findData("mp4")
            if index >= 0:
                self.container_combo.setCurrentIndex(index)
        self.updating_controls = False
        self._populate_encoders(preferred_codec=desired_codec)

        encoder = self.selected_encoder()
        if encoder is not None and encoder.codec_id != desired_codec:
            fallback = "hevc" if desired_codec == "av1" else None
            if fallback:
                self._populate_encoders(preferred_codec=fallback)
                encoder = self.selected_encoder()

        self.updating_controls = True
        self.speed_combo.setCurrentIndex(max(0, self.speed_combo.findData(speed)))
        self.frame_rate_spin.setValue(fps)
        self.gop_spin.setValue(gop)
        self.pixel_depth_combo.setCurrentIndex(
            max(0, self.pixel_depth_combo.findData(8))
        )
        self.updating_controls = False

        quality_mode = "cbr" if profile_id == "streaming" else "constant_quality"
        self._populate_quality_modes(preferred=quality_mode)
        encoder = self.selected_encoder()
        if encoder is not None:
            if profile_id == "compact":
                adjustment = -7 if encoder.cq_higher_is_better else 6
                desired_value = encoder.cq_default + adjustment
            elif profile_id == "streaming":
                desired_value = encoder.bitrate_default
            else:
                desired_value = encoder.cq_default
            self._configure_quality_value(desired_value)
        self._populate_audio_modes()
        self._refresh_automatic_output()

    @Slot()
    def _manual_setting_changed(self) -> None:
        if self.updating_controls:
            return
        if self.sender() is not self.profile_combo:
            self.updating_controls = True
            self.profile_combo.setCurrentIndex(
                max(0, self.profile_combo.findData("custom"))
            )
            self.updating_controls = False
        self._configure_quality_value(self.quality_value_spin.value())
        self._refresh_automatic_output()

    def _update_hardware_summary(self) -> None:
        if self.capability_report is None:
            return
        available = [
            backend
            for backend in self.capability_report.backends
            if backend.available and backend.id != "npu"
        ]
        npu = get_backend(self.capability_report, "npu")
        backend_text = tr("; ").join(
            tr(
                "{backend}: {count} codec options",
                backend=backend.label,
                count=len(backend.available_encoder_ids),
            )
            for backend in available
        )
        verified_text = (
            tr("Verified for compression: {backends}", backends=backend_text)
            if backend_text
            else tr("No CPU or GPU encoder passed the initialization test.")
        )
        hidden_text = tr(
            "Unavailable CPU/GPU backends are hidden; open Detection details for "
            "the device, driver, or initialization reason."
        )
        npu_text = (
            tr(
                "NPU detected (driver {version}); status only, because no FFmpeg "
                "video encoder is available.",
                version=npu.driver_version or tr("Unknown"),
            )
            if npu.device_present
            else tr(
                "NPU not detected; NPU is status-only and is not offered as an "
                "encoding device."
            )
        )
        self.hardware_summary.setText(f"{verified_text}\n{hidden_text}\n{npu_text}")

    def _log_capabilities(self, report: CapabilityReport) -> None:
        self.append_log(report.ffmpeg_version)
        for backend in report.backends:
            marker = tr("available") if backend.available else tr("unavailable")
            self.append_log(
                tr(
                    "[{state}] {backend} · driver {driver} · {reason}",
                    state=marker,
                    backend=backend.label,
                    driver=backend.driver_version,
                    reason=backend.reason,
                )
            )
            for probe in backend.encoders:
                spec = ENCODERS[probe.encoder_id]
                state = "✓" if probe.available else "×"
                self.append_log(
                    f"  {state} {spec.ffmpeg_name} ({CODEC_LABELS[spec.codec_id]}) · "
                    f"{probe.detail}"
                )
                for failure in probe.option_failures:
                    self.append_log(f"    × {failure}")

    @Slot()
    def show_capability_details(self) -> None:
        if self.capability_report is None:
            return
        box = QMessageBox(self)
        box.setWindowTitle(tr("Device, driver, and encoder detection"))
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(
            tr(
                "Available options are determined by device enumeration, the "
                "FFmpeg build, and a real one-frame initialization."
            )
        )
        box.setDetailedText(capability_details_text(self.capability_report))
        box.exec()

    def current_settings(self) -> CompressionSettings:
        encoder = self.selected_encoder()
        if encoder is None:
            raise RuntimeError(tr("No video encoder is available."))
        quality_mode = self.quality_mode_combo.currentData()
        container_id = self.container_combo.currentData()
        backend_id = self.backend_combo.currentData()
        audio_mode = self.audio_combo.currentData()
        if not all((quality_mode, container_id, backend_id, audio_mode)):
            raise RuntimeError(tr("Compression options are not ready."))
        frame_rate = self.frame_rate_spin.value() or None
        return CompressionSettings(
            backend_id=str(backend_id),
            encoder_id=encoder.id,
            container_id=str(container_id),
            quality_mode=str(quality_mode),
            quality_value=self.quality_value_spin.value(),
            speed=str(self.speed_combo.currentData()),
            resolution_height=self.resolution_combo.currentData(),
            frame_rate=frame_rate,
            pixel_depth=int(self.pixel_depth_combo.currentData()),
            audio_mode=str(audio_mode),
            audio_bitrate=self.audio_bitrate_spin.value(),
            gop_seconds=self.gop_spin.value(),
            overwrite=self.overwrite_checkbox.isChecked(),
            hash_output=self.hash_checkbox.isChecked(),
        )

    @Slot()
    def choose_input(self) -> None:
        start_directory = (
            str(self.last_directory)
            if getattr(self, "last_directory", None)
            else str(Path.home() / "Videos")
        )
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select input video"),
            start_directory,
            tr(
                "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.ts);;"
                "All files (*.*)"
            ),
        )
        if path:
            self.set_input_path(path)

    @Slot()
    def choose_output(self) -> None:
        suggested = self.output_edit.text().strip()
        if not suggested and self.source_path:
            self._refresh_automatic_output(force=True)
            suggested = self.output_edit.text().strip()
        container_id = str(self.container_combo.currentData() or "mp4")
        container = CONTAINERS[container_id]
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Select output file"),
            suggested,
            f"{tr(container.label)} (*{container.extension})",
        )
        if path:
            if not path.lower().endswith(container.extension):
                path += container.extension
            self.setting_output = True
            self.output_edit.setText(path)
            self.setting_output = False
            self.output_is_automatic = False

    def set_input_path(self, raw_path: str) -> None:
        cleaned = raw_path.strip().strip('"').strip("'")
        self.input_edit.setText(cleaned)
        self.inspect_source()

    @Slot()
    def inspect_source(self) -> None:
        if self.tools is None:
            return
        raw = self.input_edit.text().strip().strip('"').strip("'")
        if not raw:
            return
        try:
            path = Path(raw).expanduser().resolve(strict=True)
            if not path.is_file():
                raise ValueError(tr("Input is not a file: {path}", path=path))
            info = probe_media(self.tools, path)
        except Exception as error:  # noqa: BLE001 - surface path/probe errors.
            self.source_path = None
            self.source_info = None
            self.source_info_label.setText(tr("Unable to read: {error}", error=error))
            self.status_label.setText(str(error))
            return

        self.source_path = path
        self.source_info = info
        self.last_directory = path.parent
        bitrate = (
            f"{info.video_bitrate / 1_000_000:.2f} Mb/s"
            if info.video_bitrate
            else tr("Unknown bitrate")
        )
        audio = (
            tr(
                "{codec} / {channels} channels",
                codec=info.audio_codec,
                channels=info.audio_channels,
            )
            if info.audio_codec
            else tr("No audio")
        )
        self.source_info_label.setText(
            f"{info.codec.upper()} {info.profile} · {info.pixel_format} · "
            f"{info.width}×{info.height} · {info.frame_rate} · "
            + tr(
                "{duration:.3f} seconds · {size:.3f} MiB · {bitrate} · {audio}",
                duration=info.duration,
                size=info.size / 1024 / 1024,
                bitrate=bitrate,
                audio=audio,
            )
        )
        self.status_label.setText(tr("Source analysis completed."))
        self.append_log(tr("Source: {path}", path=path))
        self._populate_audio_modes()
        self._refresh_automatic_output(force=self.output_is_automatic)

    def _mark_output_manual(self) -> None:
        if not self.setting_output:
            self.output_is_automatic = False

    @Slot()
    def enable_automatic_output(self) -> None:
        self.output_is_automatic = True
        self._refresh_automatic_output(force=True)

    def _refresh_automatic_output(
        self, _value: object = None, force: bool = False
    ) -> None:
        if not self.source_path or (not self.output_is_automatic and not force):
            return
        try:
            settings = self.current_settings()
        except (ValueError, RuntimeError, TypeError):
            return
        output = default_output_path(self.source_path, settings)
        self.setting_output = True
        self.output_edit.setText(str(output))
        self.setting_output = False
        self.output_is_automatic = True

    def _output_path(self) -> Path | None:
        raw = self.output_edit.text().strip().strip('"').strip("'")
        if not raw:
            return None
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute() and self.source_path:
            candidate = self.source_path.parent / candidate
        return candidate

    def prepare_job(self) -> CompressionJob:
        if self.tools is None:
            raise RuntimeError(tr("FFmpeg is not ready."))
        if self.capability_report is None:
            raise RuntimeError(tr("Hardware capability detection is not complete."))
        if self.source_path is None or self.source_info is None:
            self.inspect_source()
        if self.source_path is None:
            raise ValueError(tr("Select a readable input video."))
        return create_compression_job(
            tools=self.tools,
            input_path=self.source_path,
            output_path=self._output_path(),
            settings=self.current_settings(),
            report=self.capability_report,
        )

    @Slot()
    def preview_command(self) -> None:
        try:
            job = self.prepare_job()
        except Exception as error:  # noqa: BLE001 - show validation failures.
            self.show_error(str(error))
            return
        self.append_log(
            tr("Command preview (published to the final path only after verification):")
        )
        self.append_log(command_for_display(job.command))
        self.append_log(tr("Final output: {path}", path=job.output_path))
        self.status_label.setText(tr("Command preview written to the log."))

    @Slot()
    def start_encode(self) -> None:
        if self.running_encode or self.running_detection:
            return
        try:
            job = self.prepare_job()
        except Exception as error:  # noqa: BLE001 - show validation failures.
            self.show_error(str(error))
            return

        self.progress_bar.setValue(0)
        self.metrics_label.setText("0.0%")
        self.status_label.setText(tr("Starting compression…"))
        backend = get_backend(self.capability_report, job.settings.backend_id)  # type: ignore[arg-type]
        self.append_log(
            tr(
                "Start: {backend} · {encoder} · {mode} {value} · {speed}",
                backend=backend.label,
                encoder=job.encoder.ffmpeg_name,
                mode=tr(QUALITY_MODE_LABELS[job.settings.quality_mode]),
                value=job.settings.quality_value,
                speed=tr(SPEED_LABELS[job.settings.speed]),
            )
        )
        self.append_log(tr("Input: {path}", path=job.input_path))
        self.append_log(tr("Output: {path}", path=job.output_path))

        thread = QThread(self)
        worker = EncodeWorker(self.tools, job)  # type: ignore[arg-type]
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self.update_progress)
        worker.log.connect(self.append_log)
        worker.succeeded.connect(self.encode_succeeded)
        worker.failed.connect(self.encode_failed)
        worker.cancelled.connect(self.encode_cancelled)
        worker.succeeded.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._encode_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self.encode_thread = thread
        self.encode_worker = worker
        self.running_encode = True
        self._set_running(True)
        thread.start()

    @Slot()
    def cancel_active_operation(self) -> None:
        if self.pending_detection or self.running_detection:
            self.cancel_detection()
            return
        self.cancel_encode()

    @Slot()
    def cancel_encode(self) -> None:
        if not self.running_encode or self.encode_worker is None:
            return
        self.status_label.setText(tr("Cancelling and cleaning the partial output…"))
        self.cancel_button.setEnabled(False)
        self.encode_worker.request_cancel()

    @Slot(float, str)
    def update_progress(self, percent: float, status: str) -> None:
        self.progress_bar.setValue(round(percent * 10))
        self.metrics_label.setText(f"{percent:.1f}%")
        self.status_label.setText(status)

    @Slot(object)
    def encode_succeeded(self, result: EncodeResult) -> None:
        self.running_encode = False
        self._set_running(False)
        self.progress_bar.setValue(1000)
        self.metrics_label.setText("100.0%")
        self.last_output_path = result.output_path
        self.open_output_button.setEnabled(True)
        self.status_label.setText(tr("Completed: {name}", name=result.output_path.name))
        self.append_log(
            f"{tr('Completed and verified: {path}', path=result.output_path)}\n"
            f"{result.media.codec.upper()} {result.media.profile} · "
            f"{result.media.pixel_format} · "
            f"{result.media.width}×{result.media.height} · "
            f"{result.media.frame_rate}\n"
            f"{result.output_size / 1024 / 1024:.3f} MiB · "
            + tr(
                "Reduced by {percent:.2f}% · elapsed {seconds:.2f} seconds",
                percent=result.reduction_percent,
                seconds=result.elapsed_seconds,
            )
        )
        if result.sha256:
            self.append_log(f"SHA-256：{result.sha256}")
        QApplication.beep()

    @Slot(str)
    def encode_failed(self, message: str) -> None:
        self.running_encode = False
        self._set_running(False)
        self.status_label.setText(tr("Failed: {message}", message=message))
        self.append_log(tr("Compression failed: {message}", message=message))
        QMessageBox.critical(self, tr("Compression failed"), message)

    @Slot(str)
    def encode_cancelled(self, message: str) -> None:
        self.running_encode = False
        self._set_running(False)
        self.status_label.setText(tr("Cancelled; partial output removed."))
        self.append_log(message)
        if self.close_after_cancel:
            self.close_after_cancel = False
            QTimer.singleShot(0, self.close)

    @Slot()
    def _encode_thread_finished(self) -> None:
        self.encode_thread = None
        self.encode_worker = None

    def _set_running(self, running: bool) -> None:
        source_editable = not running
        for widget in (
            self.language_combo,
            self.input_edit,
            self.output_edit,
            self.browse_input_button,
            self.browse_output_button,
            self.auto_output_button,
            self.inspect_button,
        ):
            widget.setEnabled(source_editable)

        settings_editable = (
            not running
            and not self.running_detection
            and self.capability_report is not None
            and bool(self.capability_report.available_encoder_ids)
        )
        for widget in (
            self.backend_combo,
            self.codec_combo,
            self.container_combo,
            self.profile_combo,
            self.quality_mode_combo,
            self.quality_value_spin,
            self.speed_combo,
            self.resolution_combo,
            self.frame_rate_spin,
            self.pixel_depth_combo,
            self.gop_spin,
            self.audio_combo,
            self.audio_bitrate_spin,
            self.overwrite_checkbox,
            self.hash_checkbox,
            self.preview_button,
        ):
            widget.setEnabled(settings_editable)
        self.advanced_toggle_button.setEnabled(settings_editable)

        self.auto_detect_checkbox.setEnabled(not running)
        self.refresh_button.setEnabled(
            not running
            and not self.running_detection
            and self.detection_thread is None
            and self.tools is not None
        )
        self.details_button.setEnabled(
            not running and self.capability_report is not None
        )
        self.start_button.setEnabled(
            settings_editable
            and self.tools is not None
            and bool(self.capability_report.available_encoder_ids)
        )
        self.cancel_button.setEnabled(
            running or self.running_detection or self.pending_detection
        )
        if self.pending_detection:
            self.cancel_detection_button.setVisible(True)
            self.cancel_detection_button.setEnabled(not running)
        elif self.running_detection:
            self.cancel_detection_button.setVisible(True)
        else:
            self.cancel_detection_button.setVisible(False)
        self._audio_mode_changed()

    def append_log(self, message: str) -> None:
        self.log_edit.appendPlainText(message)
        scroll_bar = self.log_edit.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def show_error(self, message: str) -> None:
        self.status_label.setText(message)
        self.append_log(tr("Error: {message}", message=message))
        QMessageBox.warning(self, tr("Unable to start"), message)

    @Slot()
    def open_output_directory(self) -> None:
        if self.last_output_path:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self.last_output_path.parent))
            )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.set_input_path(path)
                event.acceptProposedAction()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.running_encode:
            answer = QMessageBox.question(
                self,
                tr("Cancel the active compression?"),
                tr(
                    "Closing the window cancels FFmpeg and removes this task's "
                    "partial output."
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.close_after_cancel = True
            self.cancel_encode()
            event.ignore()
            return
        if self.running_detection and self.detection_thread is not None:
            if self.detection_worker is not None:
                self.detection_worker.request_cancel()
            self.detection_thread.quit()
            if not self.detection_thread.wait(5_000):
                self.status_label.setText(
                    tr("Waiting for the active hardware test to stop…")
                )
                event.ignore()
                return
        self.startup_detection_timer.stop()
        self._save_settings()
        event.accept()


def choose_smoke_encoder(
    report: CapabilityReport,
    backend_id: str,
    codec_id: str,
) -> tuple[BackendCapability, str]:
    backend_priority = (
        [backend_id]
        if backend_id != "auto"
        else ["amd_amf", "nvidia_nvenc", "intel_qsv", "cpu"]
    )
    for candidate_id in backend_priority:
        backend = get_backend(report, candidate_id)
        for encoder_id in backend.available_encoder_ids:
            if ENCODERS[encoder_id].codec_id == codec_id:
                return backend, encoder_id
    raise RuntimeError(
        tr("No {codec} encoder is available.", codec=CODEC_LABELS[codec_id])
    )


def run_smoke_encode(arguments: argparse.Namespace) -> int:
    tools = resolve_tools(arguments.ffmpeg)
    report = detect_capabilities(tools)
    backend, encoder_id = choose_smoke_encoder(
        report, arguments.backend, arguments.codec
    )
    encoder = get_encoder(encoder_id)
    container_id = arguments.container
    if container_id == "auto":
        suffix = Path(arguments.smoke_encode[1]).suffix.lower()
        container_id = next(
            (
                container.id
                for container in CONTAINERS.values()
                if container.extension == suffix
            ),
            "mp4",
        )
    quality_mode = arguments.quality_mode
    if quality_mode not in encoder.quality_modes:
        quality_mode = encoder.quality_modes[0]
    _, _, default_quality, _, _ = quality_value_properties(encoder, quality_mode)
    settings = CompressionSettings(
        backend_id=backend.id,
        encoder_id=encoder.id,
        container_id=container_id,
        quality_mode=quality_mode,
        quality_value=(
            arguments.quality_value
            if arguments.quality_value is not None
            else default_quality
        ),
        speed=arguments.speed,
        resolution_height=arguments.resolution,
        frame_rate=arguments.fps or None,
        pixel_depth=arguments.pixel_depth,
        audio_mode=arguments.audio,
        audio_bitrate=arguments.audio_bitrate,
        gop_seconds=arguments.gop,
        overwrite=False,
        hash_output=True,
    )
    job = create_compression_job(
        tools,
        Path(arguments.smoke_encode[0]),
        Path(arguments.smoke_encode[1]),
        settings,
        report,
    )
    result = execute_job(
        tools,
        job,
        threading.Event(),
        lambda _percent, _status: None,
        lambda _message: None,
        lambda _process: None,
    )
    return (
        0
        if result.media.codec == encoder.codec_id and result.output_path.is_file()
        else 1
    )


def write_diagnostics_report(
    destination: str,
    explicit_ffmpeg: str | None,
) -> None:
    report_data: dict[str, object] = {
        "app_version": APP_VERSION,
        "language": get_language(),
        "module_file": __file__,
        "executable": sys.executable,
        "argv_0": sys.argv[0],
        "application_roots": [str(path) for path in application_roots()],
        "bundled_candidates": [
            {
                "ffmpeg": str(ffmpeg),
                "ffmpeg_exists": ffmpeg.is_file(),
                "ffprobe": str(ffprobe),
                "ffprobe_exists": ffprobe.is_file(),
            }
            for ffmpeg, ffprobe in bundled_tool_candidates()
        ],
    }
    try:
        tools = resolve_tools(explicit_ffmpeg)
        report_data["resolved_tools"] = {
            "ffmpeg": str(tools.ffmpeg),
            "ffprobe": str(tools.ffprobe),
            "bundled": tools.bundled,
        }
        report_data["capabilities"] = capability_report_as_dict(
            detect_capabilities(tools)
        )
    except Exception as error:  # noqa: BLE001 - diagnostics must capture all failures.
        report_data["error"] = str(error)

    report_path = Path(destination).expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_gui_self_test(
    initial_input: str | None,
    explicit_ffmpeg: str | None,
    screenshot_path: str | None,
) -> int:
    if os.name != "nt":
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE_SHEET)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow(None, explicit_ffmpeg)
    window.showNormal()
    window.resize(1120, 960)
    window.show()
    if window.tools is not None and window.capability_report is None:
        window.refresh_capabilities()

    deadline = time.monotonic() + 40
    app.processEvents()
    while (
        window.running_detection or window.capability_report is None
    ) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()
    if window.capability_report is None or not window.start_button.isEnabled():
        window.close()
        return 2
    if (
        window.pending_detection
        or window.progress_bar.value() != 1000
        or window.cancel_detection_button.isVisible()
    ):
        window.close()
        return 10

    npu_index = window.backend_combo.findData("npu")
    if npu_index >= 0:
        window.close()
        return 6
    if any(
        not get_backend(
            window.capability_report,
            str(window.backend_combo.itemData(index)),
        ).available
        for index in range(window.backend_combo.count())
    ):
        window.close()
        return 11

    selected_encoder = window.selected_encoder()
    if selected_encoder is None:
        window.close()
        return 7
    if selected_encoder.ffmpeg_name in window.codec_combo.currentText():
        window.close()
        return 12
    if any(
        not widget.isHidden()
        for field in window.advanced_quality_fields
        for widget in field
    ):
        window.close()
        return 13
    for depth in supported_pixel_depths(window.capability_report, selected_encoder.id):
        depth_index = window.pixel_depth_combo.findData(depth)
        if depth_index < 0:
            window.close()
            return 8
        window.pixel_depth_combo.setCurrentIndex(depth_index)
        app.processEvents()
        visible_modes = {
            str(window.quality_mode_combo.itemData(index))
            for index in range(window.quality_mode_combo.count())
        }
        expected_modes = set(
            supported_quality_modes(
                window.capability_report, selected_encoder.id, depth
            )
        )
        if visible_modes != expected_modes:
            window.close()
            return 9
    window._apply_profile(str(window.profile_combo.currentData()))

    if initial_input:
        window.set_input_path(initial_input)
        test_output = (
            Path(tempfile.gettempdir())
            / f"video-compressor-v2-self-test-{os.getpid()}.mp4"
        )
        window.setting_output = True
        window.output_edit.setText(str(test_output))
        window.setting_output = False
        window.output_is_automatic = False
        try:
            job = window.prepare_job()
        except Exception:  # noqa: BLE001 - self-test converts any failure to a code.
            window.close()
            return 3
        if job.encoder.ffmpeg_name not in job.command:
            window.close()
            return 4

    if screenshot_path:
        destination = Path(screenshot_path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        focused_widget = app.focusWidget()
        if focused_widget is not None:
            focused_widget.clearFocus()
        window.scroll_area.setFocus(Qt.FocusReason.OtherFocusReason)
        scroll_bar = window.scroll_area.verticalScrollBar()
        for _ in range(2):
            scroll_bar.setValue(scroll_bar.minimum())
            app.processEvents()
        if scroll_bar.value() != scroll_bar.minimum():
            window.close()
            return 14
        if not window.grab().save(str(destination)):
            window.close()
            return 5
    window.close()
    app.processEvents()
    return 0


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Initial input video path")
    parser.add_argument("--ffmpeg", help="Explicit path to ffmpeg.exe")
    parser.add_argument(
        "--language",
        choices=tuple(LANGUAGE_NAMES),
        help="Application language for this run",
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--screenshot", help="Save the self-test window as an image")
    parser.add_argument(
        "--diagnostics-report",
        help="Write device, driver and encoder diagnostics to a JSON file",
    )
    parser.add_argument(
        "--smoke-encode",
        nargs=2,
        metavar=("INPUT", "OUTPUT"),
        help="Run a non-interactive compiled-binary encode test",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "cpu", "amd_amf", "nvidia_nvenc", "intel_qsv"),
        default="auto",
    )
    parser.add_argument("--codec", choices=tuple(CODEC_LABELS), default="hevc")
    parser.add_argument(
        "--container", choices=("auto", *CONTAINERS.keys()), default="auto"
    )
    parser.add_argument(
        "--quality-mode",
        choices=tuple(QUALITY_MODE_LABELS),
        default="constant_quality",
    )
    parser.add_argument("--quality-value", type=int)
    parser.add_argument("--speed", choices=tuple(SPEED_LABELS), default="fast")
    parser.add_argument("--resolution", type=int, choices=(2160, 1440, 1080, 720, 480))
    parser.add_argument("--fps", type=int, default=0)
    parser.add_argument("--pixel-depth", type=int, choices=(8, 10), default=8)
    parser.add_argument("--audio", choices=tuple(AUDIO_MODE_LABELS), default="copy")
    parser.add_argument("--audio-bitrate", type=int, default=128)
    parser.add_argument("--gop", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    settings = QSettings(ORGANIZATION_NAME, APP_NAME)
    saved_language = settings.value("ui/language", "")
    set_language(arguments.language or saved_language or system_language())
    try:
        if arguments.diagnostics_report:
            write_diagnostics_report(arguments.diagnostics_report, arguments.ffmpeg)
        if arguments.smoke_encode:
            return run_smoke_encode(arguments)
        if arguments.self_test:
            return run_gui_self_test(
                arguments.input,
                arguments.ffmpeg,
                arguments.screenshot,
            )

        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName(ORGANIZATION_NAME)
        app.setStyle("Fusion")
        app.setStyleSheet(STYLE_SHEET)
        app.setWindowIcon(build_app_icon())
        app.setFont(QFont("Segoe UI", 10))
        window = MainWindow(arguments.input, arguments.ffmpeg)
        window.show()
        return app.exec()
    except Exception as error:  # noqa: BLE001 - final boundary for windowed builds.
        try:
            error_app = QApplication.instance() or QApplication([])
            QMessageBox.critical(
                None, tr("Video Compressor failed to start"), str(error)
            )
            error_app.processEvents()
        except Exception:  # noqa: BLE001, S110 - no console exists in the EXE.
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
