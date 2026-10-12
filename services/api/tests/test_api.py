import os
from io import BytesIO
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase

import httpx
from PIL import Image

from med_info_api.ingestion.hk_registry import import_hk_registry
from med_info_api.main import app, get_image_storage, get_repository, get_settings


FIXTURE = Path(__file__).parent / "fixtures" / "hk_registry.xml"


class ApiTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        os.environ["MED_INFO_DB_PATH"] = str(Path(self.temp_dir.name) / "api.sqlite3")
        os.environ["MED_INFO_ADMIN_API_KEY"] = "test-admin-key"
        os.environ["MED_INFO_UPLOAD_DIR"] = str(Path(self.temp_dir.name) / "uploads")
        get_settings.cache_clear()
        get_repository.cache_clear()
        get_image_storage.cache_clear()
        repository = get_repository()
        import_hk_registry(
            FIXTURE,
            repository,
            retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
        )
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        get_repository.cache_clear()
        get_settings.cache_clear()
        get_image_storage.cache_clear()
        os.environ.pop("MED_INFO_DB_PATH", None)
        os.environ.pop("MED_INFO_ADMIN_API_KEY", None)
        os.environ.pop("MED_INFO_UPLOAD_DIR", None)

    async def test_exact_registration_lookup_retains_separate_safety_axes(self) -> None:
        response = await self.client.get(
            "/v1/products/search",
            params={"registration_number": "hk 12345"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["lookup_basis"], "exact_registration_number")

        detail = await self.client.get(f"/v1/products/{payload['results'][0]['id']}")
        detail_payload = detail.json()
        self.assertEqual(detail_payload["regulatory_relationship"], "insufficient_public_evidence")
        self.assertEqual(detail_payload["package_consistency"], "insufficient_information")
        self.assertIn("不能只靠相片", detail_payload["safety_notice_zh_hant"])
        self.assertIn("attribution required", detail_payload["source"]["licence"])

    async def test_unknown_registration_fails_closed(self) -> None:
        response = await self.client.get(
            "/v1/products/search",
            params={"registration_number": "HK-00000"},
        )
        payload = response.json()
        self.assertEqual(payload["results"], [])
        self.assertIn("No matching official", payload["message"])

    async def test_rejects_invalid_registration_number(self) -> None:
        response = await self.client.get(
            "/v1/products/search",
            params={"registration_number": "123"},
        )
        self.assertEqual(response.status_code, 422)

    async def test_source_freshness_requires_admin_key(self) -> None:
        response = await self.client.get("/v1/admin/source-freshness")
        self.assertEqual(response.status_code, 401)

    async def test_source_freshness_reports_registry_provenance(self) -> None:
        response = await self.client.get(
            "/v1/admin/source-freshness",
            headers={"X-Admin-Key": "test-admin-key"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "current")
        self.assertEqual(payload["record_count"], 2)
        self.assertEqual(payload["source"]["published_or_effective_at"][:10], "2026-10-02")

    @staticmethod
    def _test_image() -> bytes:
        output = BytesIO()
        Image.new("RGB", (1200, 800), color=(220, 225, 218)).save(
            output,
            format="JPEG",
            quality=90,
            exif=b"Exif\x00\x00test-metadata",
        )
        return output.getvalue()

    async def test_three_image_capture_flow_and_deletion(self) -> None:
        created = await self.client.post("/v1/scan-sessions")
        self.assertEqual(created.status_code, 201)
        session = created.json()
        self.assertEqual(session["status"], "awaiting_uploads")
        self.assertEqual(set(session["required_slots"]), {"front", "ingredients", "identifier"})
        self.assertIn("遮蓋姓名", session["privacy_notice_zh_hant"])

        image = self._test_image()
        uploaded_ids: list[str] = []
        for slot in ("front", "ingredients", "identifier"):
            response = await self.client.post(
                f"/v1/scan-sessions/{session['id']}/uploads",
                data={"slot": slot},
                files={"image": (f"{slot}.jpg", image, "image/jpeg")},
                headers={"Idempotency-Key": f"test-{slot}-upload"},
            )
            self.assertEqual(response.status_code, 201)
            uploaded_ids.append(response.json()["id"])

        duplicate = await self.client.post(
            f"/v1/scan-sessions/{session['id']}/uploads",
            data={"slot": "front"},
            files={"image": ("front.jpg", image, "image/jpeg")},
            headers={"Idempotency-Key": "test-front-upload"},
        )
        self.assertEqual(duplicate.json()["id"], uploaded_ids[0])

        status_response = await self.client.get(f"/v1/scan-sessions/{session['id']}/status")
        self.assertEqual(status_response.json()["status"], "ready_for_processing")
        self.assertEqual(len(status_response.json()["uploads"]), 3)

        stored_files = list((Path(self.temp_dir.name) / "uploads").rglob("*.jpg"))
        self.assertEqual(len(stored_files), 3)
        with Image.open(stored_files[0]) as sanitized:
            self.assertFalse(sanitized.getexif())

        deleted = await self.client.delete(f"/v1/scan-sessions/{session['id']}")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(list((Path(self.temp_dir.name) / "uploads").rglob("*.jpg")))
        missing = await self.client.get(f"/v1/scan-sessions/{session['id']}/status")
        self.assertEqual(missing.status_code, 404)

    async def test_upload_rejects_non_image_content(self) -> None:
        session = (await self.client.post("/v1/scan-sessions")).json()
        response = await self.client.post(
            f"/v1/scan-sessions/{session['id']}/uploads",
            data={"slot": "front"},
            files={"image": ("not-an-image.jpg", b"not an image", "image/jpeg")},
            headers={"Idempotency-Key": "invalid-image-test"},
        )
        self.assertEqual(response.status_code, 415)
