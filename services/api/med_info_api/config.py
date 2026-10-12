from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    source_stale_after_days: int = 14
    admin_api_key: str | None = None
    upload_directory: Path | None = None
    image_retention_hours: int = 24
    maximum_upload_bytes: int = 10 * 1024 * 1024
    maximum_image_pixels: int = 20_000_000

    @classmethod
    def from_environment(cls) -> "Settings":
        default_path = Path(__file__).resolve().parents[3] / "runtime" / "med_info.sqlite3"
        database_path = Path(os.getenv("MED_INFO_DB_PATH", default_path))
        return cls(
            database_path=database_path,
            source_stale_after_days=int(os.getenv("MED_INFO_SOURCE_STALE_DAYS", "14")),
            admin_api_key=os.getenv("MED_INFO_ADMIN_API_KEY") or None,
            upload_directory=Path(
                os.getenv("MED_INFO_UPLOAD_DIR", database_path.parent / "uploads")
            ),
            image_retention_hours=int(os.getenv("MED_INFO_IMAGE_RETENTION_HOURS", "24")),
            maximum_upload_bytes=int(os.getenv("MED_INFO_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))),
            maximum_image_pixels=int(os.getenv("MED_INFO_MAX_IMAGE_PIXELS", "20000000")),
        )
