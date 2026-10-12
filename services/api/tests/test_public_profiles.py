import json
from pathlib import Path
from unittest import TestCase


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PUBLIC_PROFILES = REPOSITORY_ROOT / "apps" / "web" / "dist" / "data" / "medicine-profiles.json"
REVIEW_DRAFT = REPOSITORY_ROOT / "apps" / "web" / "content" / "review-queue" / "HK-20966.json"


class PublicProfileTests(TestCase):
    def test_high_risk_profile_fails_closed_until_review(self) -> None:
        payload = json.loads(PUBLIC_PROFILES.read_text(encoding="utf-8"))
        profile = payload["profiles"]["HK-20966"]

        self.assertEqual(
            profile["relationship"]["status"],
            "insufficient_public_evidence",
        )
        self.assertEqual(
            profile["relationship"]["review_status"],
            "evidence_review_required",
        )
        self.assertEqual(
            profile["clinical_summary"]["status"],
            "clinical_review_required",
        )
        self.assertFalse(profile["clinical_summary"]["is_public"])
        self.assertNotIn("claims", profile["clinical_summary"])
        self.assertIn("不是", profile["relationship"]["interpretation_zh_hant"])

    def test_same_ingredient_products_are_not_presented_as_generic_equivalents(self) -> None:
        payload = json.loads(PUBLIC_PROFILES.read_text(encoding="utf-8"))
        profile = payload["profiles"]["HK-20966"]
        comparison = profile["same_ingredient_comparison"]

        self.assertEqual(comparison["status"], "ingredient_match_only")
        self.assertEqual(comparison["active_ingredient"], "isotretinoin")
        self.assertEqual(comparison["selected_strength"], "20 mg")
        registration_numbers = {
            product["registration_number"] for product in comparison["products"]
        }
        self.assertEqual(
            registration_numbers,
            {"HK-52035", "HK-68169", "HK-54370", "HK-50197", "HK-56026"},
        )
        self.assertIn("不代表已確認為學名藥", comparison["intro_zh_hant"])

    def test_registration_patent_and_composition_are_kept_separate(self) -> None:
        payload = json.loads(PUBLIC_PROFILES.read_text(encoding="utf-8"))
        disclosure = payload["profiles"]["HK-20966"]["regulatory_and_composition"]

        self.assertEqual(disclosure["registration"]["status"], "current_public_record")
        self.assertEqual(disclosure["patent"]["status"], "not_assessed_product_specific")
        self.assertEqual(
            disclosure["composition"]["status"],
            "manufacturer_information_not_hk_verified",
        )
        ingredient_names = {
            ingredient
            for group in disclosure["composition"]["groups"]
            for ingredient in group["ingredients_zh_hant"]
        }
        self.assertIn("精製大豆油", ingredient_names)
        self.assertIn("明膠", ingredient_names)
        self.assertIn("丙二醇", ingredient_names)
        self.assertIn("未能證明", disclosure["composition"]["jurisdiction_note_zh_hant"])

    def test_profile_sources_resolve_and_draft_stays_outside_public_directory(self) -> None:
        payload = json.loads(PUBLIC_PROFILES.read_text(encoding="utf-8"))
        profile = payload["profiles"]["HK-20966"]
        source_ids = {source["id"] for source in profile["sources"]}

        self.assertTrue(set(profile["relationship"]["source_ids"]).issubset(source_ids))
        self.assertTrue(
            set(profile["same_ingredient_comparison"]["source_ids"]).issubset(source_ids)
        )
        disclosure = profile["regulatory_and_composition"]
        self.assertTrue(set(disclosure["registration"]["source_ids"]).issubset(source_ids))
        self.assertTrue(set(disclosure["patent"]["source_ids"]).issubset(source_ids))
        self.assertTrue(set(disclosure["composition"]["source_ids"]).issubset(source_ids))
        self.assertTrue(set(profile["clinical_summary"]["source_ids"]).issubset(source_ids))
        self.assertTrue(REVIEW_DRAFT.is_file())
        self.assertNotIn(PUBLIC_PROFILES.parent, REVIEW_DRAFT.parents)

        draft = json.loads(REVIEW_DRAFT.read_text(encoding="utf-8"))
        self.assertEqual(draft["review_status"], "clinical_review_required")
        self.assertIsNone(draft["reviewer_id"])
        self.assertIsNone(draft["reviewed_at"])
