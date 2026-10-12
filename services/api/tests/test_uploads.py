from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from PIL import Image

from med_info_api.uploads import ImageStorage, InvalidImageError


class ImageStorageTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    @staticmethod
    def _image(width: int, height: int) -> bytes:
        output = BytesIO()
        Image.new("RGB", (width, height), "white").save(output, format="PNG")
        return output.getvalue()

    def test_rejects_pixel_bomb_before_storage(self) -> None:
        storage = ImageStorage(
            Path(self.temp_dir.name) / "uploads",
            maximum_bytes=1_000_000,
            maximum_pixels=100,
        )
        with self.assertRaisesRegex(InvalidImageError, "pixel limit"):
            storage.store_sanitized_image(
                session_id="safe-session",
                upload_id="safe-upload",
                payload=self._image(20, 20),
            )

    def test_delete_refuses_paths_outside_upload_root(self) -> None:
        storage = ImageStorage(
            Path(self.temp_dir.name) / "uploads",
            maximum_bytes=1_000_000,
            maximum_pixels=1_000_000,
        )
        with self.assertRaisesRegex(ValueError, "outside"):
            storage.delete_path(Path(self.temp_dir.name) / "unrelated.jpg")

