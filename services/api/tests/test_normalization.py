from unittest import TestCase

from med_info_api.normalization import (
    extract_registration_number,
    normalize_registration_number,
    normalize_search_text,
)


class RegistrationNormalizationTests(TestCase):
    def test_normalizes_supported_forms(self) -> None:
        for value in ("HK-12345", "hk 12345", "１２３４５", "HK:12345"):
            with self.subTest(value=value):
                self.assertEqual(normalize_registration_number(value), "HK-12345")

    def test_rejects_ambiguous_or_invalid_values(self) -> None:
        for value in ("HK-1234", "HK-123456", "other 12345", ""):
            with self.subTest(value=value):
                self.assertIsNone(normalize_registration_number(value))

    def test_extracts_from_ocr_text(self) -> None:
        self.assertEqual(extract_registration_number("Registration: HK 12345"), "HK-12345")

    def test_normalizes_bilingual_search_text(self) -> None:
        self.assertEqual(normalize_search_text("  EXAMPLE—Tablet  "), "example tablet")
        self.assertEqual(normalize_search_text("示例 藥片"), "示例 藥片")

