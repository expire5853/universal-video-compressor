from __future__ import annotations

import ast
import string
import unittest
from pathlib import Path

from video_compressor.i18n import (
    ZH_CN_TRANSLATIONS,
    get_language,
    normalize_language,
    set_language,
    tr,
)


class InternationalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_language = get_language()

    def tearDown(self) -> None:
        set_language(self.previous_language)

    def test_language_normalization_and_translation(self) -> None:
        self.assertEqual(normalize_language("zh-CN"), "zh_CN")
        self.assertEqual(normalize_language("Chinese (Simplified)_China"), "zh_CN")
        self.assertEqual(normalize_language("en-US"), "en")

        set_language("en")
        self.assertEqual(tr("Start compression"), "Start compression")

        set_language("zh_CN")
        self.assertEqual(tr("Start compression"), "开始压制")
        self.assertEqual(
            tr("Completed: {name}", name="output.mp4"),
            "完成：output.mp4",
        )

    def test_translations_preserve_format_fields(self) -> None:
        formatter = string.Formatter()
        for source, translation in ZH_CN_TRANSLATIONS.items():
            source_fields = {
                name for _, name, _, _ in formatter.parse(source) if name is not None
            }
            translation_fields = {
                name
                for _, name, _, _ in formatter.parse(translation)
                if name is not None
            }
            self.assertEqual(source_fields, translation_fields, source)

    def test_literal_translation_calls_have_chinese_entries(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        messages: set[str] = set()
        for relative_path in (
            "src/video_compressor/core.py",
            "src/video_compressor/gui.py",
        ):
            source = (project_root / relative_path).read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "tr"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    continue
                messages.add(node.args[0].value)

        self.assertEqual(messages - ZH_CN_TRANSLATIONS.keys(), set())
