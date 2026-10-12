from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError


ACCEPTED_FORMATS = {"JPEG", "PNG", "WEBP"}


class InvalidImageError(ValueError):
    pass


@dataclass(frozen=True)
class StoredImage:
    path: Path
    mime_type: str
    width: int
    height: int
    byte_size: int
    quality_warnings: tuple[str, ...]


class ImageStorage:
    def __init__(
        self,
        root: Path,
        *,
        maximum_bytes: int,
        maximum_pixels: int,
    ) -> None:
        self.root = root.resolve()
        self.maximum_bytes = maximum_bytes
        self.maximum_pixels = maximum_pixels

    def store_sanitized_image(
        self,
        *,
        session_id: str,
        upload_id: str,
        payload: bytes,
    ) -> StoredImage:
        if not payload:
            raise InvalidImageError("The uploaded image is empty")
        if len(payload) > self.maximum_bytes:
            raise InvalidImageError("The uploaded image exceeds the file-size limit")

        try:
            with Image.open(io.BytesIO(payload)) as probe:
                image_format = probe.format
                width, height = probe.size
                frame_count = getattr(probe, "n_frames", 1)
                if image_format not in ACCEPTED_FORMATS:
                    raise InvalidImageError("Only JPEG, PNG, and WebP images are accepted")
                if frame_count != 1:
                    raise InvalidImageError("Animated or multi-frame images are not accepted")
                if width * height > self.maximum_pixels:
                    raise InvalidImageError("The uploaded image exceeds the pixel limit")
                probe.verify()
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
            raise InvalidImageError("The upload is not a supported, readable image") from error

        try:
            with Image.open(io.BytesIO(payload)) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
                image.load()
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
            raise InvalidImageError("The upload could not be safely decoded") from error

        warnings = self._quality_warnings(image)
        sanitized = io.BytesIO()
        image.save(sanitized, format="JPEG", quality=95, optimize=True, exif=b"")
        sanitized_payload = sanitized.getvalue()

        session_directory = self._session_directory(session_id)
        session_directory.mkdir(parents=True, exist_ok=True)
        destination = session_directory / f"{upload_id}.jpg"
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=session_directory,
            prefix=".upload-",
            suffix=".partial",
            delete=False,
        ) as temporary:
            temporary.write(sanitized_payload)
            temporary_path = Path(temporary.name)
        try:
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)

        return StoredImage(
            path=destination,
            mime_type="image/jpeg",
            width=image.width,
            height=image.height,
            byte_size=len(sanitized_payload),
            quality_warnings=warnings,
        )

    def delete_path(self, stored_path: str | Path) -> None:
        target = Path(stored_path).resolve()
        if self.root not in target.parents:
            raise ValueError("Refusing to delete a path outside the upload directory")
        target.unlink(missing_ok=True)
        try:
            target.parent.rmdir()
        except OSError:
            pass

    def _session_directory(self, session_id: str) -> Path:
        candidate = (self.root / session_id).resolve()
        if candidate.parent != self.root:
            raise ValueError("Invalid scan session storage path")
        return candidate

    @staticmethod
    def _quality_warnings(image: Image.Image) -> tuple[str, ...]:
        warnings: list[str] = []
        if image.width < 800 or image.height < 600:
            warnings.append("insufficient_resolution")

        sample = image.copy()
        sample.thumbnail((1024, 1024))
        grayscale = ImageOps.grayscale(sample)
        histogram = grayscale.histogram()
        pixel_count = max(1, sample.width * sample.height)
        if sum(histogram[250:]) / pixel_count > 0.18:
            warnings.append("possible_glare_or_overexposure")
        if sum(histogram[:26]) / pixel_count > 0.35:
            warnings.append("image_too_dark")

        edges = grayscale.filter(ImageFilter.FIND_EDGES)
        if ImageStat.Stat(edges).var[0] < 120:
            warnings.append("possible_blur")
        return tuple(warnings)
