import io
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from med_info_api.ingestion.hk_registry import (
    download_hk_registry,
    import_hk_registry,
    parse_hk_registry,
    parse_hk_registry_snapshot,
)
from med_info_api.export_public_registry import export_public_registry
from med_info_api.models import IngredientRecord, ProductRecord, SourceRecord
from med_info_api.normalization import normalize_search_text
from med_info_api.repository import RegistryRepository


FIXTURE = Path(__file__).parent / "fixtures" / "hk_registry.xml"


class FakeHeaders(dict):
    def get_content_type(self) -> str:
        return self.get("Content-Type", "application/octet-stream")


class FakeResponse(io.BytesIO):
    def __init__(self, payload: bytes, *, url: str, content_type: str = "application/xml") -> None:
        super().__init__(payload)
        self._url = url
        self.headers = FakeHeaders(
            {"Content-Type": content_type, "Content-Length": str(len(payload))}
        )

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class RegistryTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.repository = RegistryRepository(Path(self.temp_dir.name) / "test.sqlite3")
        self.repository.initialize()

    def test_parses_and_publishes_a_snapshot(self) -> None:
        products = parse_hk_registry(FIXTURE.read_bytes())
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0].registration_number, "HK-12345")
        self.assertEqual(len(products[0].ingredients), 2)
        self.assertEqual(
            parse_hk_registry_snapshot(FIXTURE.read_bytes()).last_updated_on.isoformat(),
            "2026-10-02",
        )

        published = import_hk_registry(
            FIXTURE,
            self.repository,
            retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
        )
        self.assertEqual(published.record_count, 2)
        self.assertEqual(
            published.source.published_or_effective_at.date().isoformat(),
            "2026-10-02",
        )
        self.assertIn("attribution required", published.source.licence)

        exact = self.repository.search(registration_number="HK-12345")
        self.assertEqual([item.record.product_name for item in exact], ["Example Relief Tablets 500 mg"])

        ingredient = self.repository.search(query="示例成分")
        self.assertEqual([item.record.registration_number for item in ingredient], ["HK-54321"])

    def test_refuses_empty_snapshots_without_replacing_current_data(self) -> None:
        import_hk_registry(FIXTURE, self.repository)
        current = self.repository.current_registry()
        self.assertIsNotNone(current)

        source = SourceRecord(
            authority="Test",
            title="Empty",
            url="https://example.invalid/empty.xml",
            jurisdiction_code="HK",
            retrieved_at=datetime.now(UTC),
            content_hash="empty",
        )
        with self.assertRaisesRegex(ValueError, "empty registry"):
            self.repository.publish_snapshot(source, [])
        self.assertEqual(self.repository.current_registry().snapshot_id, current.snapshot_id)

    def test_publishing_new_snapshot_supersedes_old_atomically(self) -> None:
        first = import_hk_registry(FIXTURE, self.repository)
        product = ProductRecord(
            registration_number="HK-99999",
            product_name="Replacement product",
            normalized_name=normalize_search_text("Replacement product"),
            ingredients=(IngredientRecord("Ingredient", "ingredient"),),
        )
        source = SourceRecord(
            authority="Hong Kong Department of Health",
            title="Replacement",
            url="https://example.invalid/replacement.xml",
            jurisdiction_code="HK",
            retrieved_at=datetime.now(UTC),
            content_hash="replacement",
        )
        second = self.repository.publish_snapshot(source, [product])
        self.assertNotEqual(first.snapshot_id, second.snapshot_id)
        self.assertEqual(self.repository.search(registration_number="HK-12345"), [])
        self.assertEqual(len(self.repository.search(registration_number="HK-99999")), 1)

    def test_unchanged_snapshot_refreshes_successful_retrieval_time(self) -> None:
        first_retrieval = datetime(2026, 10, 1, tzinfo=UTC)
        second_retrieval = datetime(2026, 10, 11, tzinfo=UTC)
        import_hk_registry(FIXTURE, self.repository, retrieved_at=first_retrieval)
        import_hk_registry(FIXTURE, self.repository, retrieved_at=second_retrieval)
        self.assertEqual(
            self.repository.current_registry().source.retrieved_at,
            second_retrieval,
        )

    def test_rejects_xml_entities(self) -> None:
        malicious = b'<!DOCTYPE x [<!ENTITY x "unsafe">]><products><product>&x;</product></products>'
        with self.assertRaisesRegex(ValueError, "entity"):
            parse_hk_registry(malicious)

    def test_rejects_xml_that_does_not_match_official_schema(self) -> None:
        invalid = b"<drugs><lastUpdate>2026-10-02</lastUpdate><drug /></drugs>"
        with self.assertRaisesRegex(ValueError, "official schema"):
            parse_hk_registry(invalid)

    def test_download_validates_and_saves_content_addressed_snapshot(self) -> None:
        payload = FIXTURE.read_bytes()

        def opener(_request: object, *, timeout: int) -> FakeResponse:
            self.assertEqual(timeout, 30)
            return FakeResponse(
                payload,
                url="https://www.drugoffice.gov.hk/eps/psi/DrugList.xml",
            )

        destination = Path(self.temp_dir.name) / "snapshots"
        with patch("med_info_api.ingestion.hk_registry.MINIMUM_LIVE_RECORDS", 1):
            result = download_hk_registry(destination, opener=opener)
        self.assertTrue(result.path.is_file())
        self.assertEqual(result.path.read_bytes(), payload)
        self.assertEqual(result.path.stem, result.content_hash)

    def test_download_rejects_non_official_host_before_request(self) -> None:
        with self.assertRaisesRegex(ValueError, "official HTTPS host"):
            download_hk_registry(
                Path(self.temp_dir.name),
                resource_url="https://example.invalid/DrugList.xml",
            )

    def test_download_rejects_redirect_to_non_official_host(self) -> None:
        def opener(_request: object, *, timeout: int) -> FakeResponse:
            return FakeResponse(FIXTURE.read_bytes(), url="https://example.invalid/DrugList.xml")

        with self.assertRaisesRegex(ValueError, "redirected away"):
            download_hk_registry(Path(self.temp_dir.name), opener=opener)

    def test_exports_validated_public_registry_snapshot(self) -> None:
        output = Path(self.temp_dir.name) / "dist" / "hk-registry.json"
        result = export_public_registry(FIXTURE, output)
        exported = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result["record_count"], 2)
        self.assertEqual(exported["record_count"], 2)
        self.assertEqual(exported["products"][0][0], "HK-12345")
        self.assertEqual(
            exported["products"][0][3],
            ["Example ingredient 500 mg", "Second example ingredient"],
        )
        self.assertEqual(
            exported["source"]["published_or_effective_at"],
            "2026-10-02T00:00:00+00:00",
        )
        self.assertIn("attribution required", exported["source"]["licence"])
