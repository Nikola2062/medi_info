from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from .config import Settings
from .ingestion.hk_registry import import_hk_registry, synchronize_hk_registry
from .repository import PublishedRegistry, RegistryRepository
from .uploads import ImageStorage


def _result_payload(result: PublishedRegistry) -> str:
    return json.dumps(
        {
            "snapshot_id": result.snapshot_id,
            "record_count": result.record_count,
            "published_at": result.published_at.isoformat(),
            "source_last_updated_at": (
                result.source.published_or_effective_at.isoformat()
                if result.source.published_or_effective_at
                else None
            ),
            "content_hash": result.source.content_hash,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Med Info maintenance commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="Initialize the local database")

    import_parser = subparsers.add_parser("import-hk", help="Import a saved HK XML snapshot")
    import_parser.add_argument("path", type=Path)

    sync_parser = subparsers.add_parser("sync-hk", help="Download and publish the official HK registry")
    sync_parser.add_argument(
        "--snapshot-dir",
        type=Path,
        help="Immutable raw snapshot directory (defaults beside the configured database)",
    )
    subparsers.add_parser(
        "cleanup-expired-scans",
        help="Delete expired anonymous scan sessions and their sanitized images",
    )
    args = parser.parse_args()

    settings = Settings.from_environment()
    repository = RegistryRepository(settings.database_path)
    repository.initialize()

    if args.command == "init-db":
        print(json.dumps({"database": str(settings.database_path), "initialized": True}))
        return
    if args.command == "import-hk":
        print(_result_payload(import_hk_registry(args.path, repository)))
        return
    if args.command == "cleanup-expired-scans":
        assert settings.upload_directory is not None
        storage = ImageStorage(
            settings.upload_directory,
            maximum_bytes=settings.maximum_upload_bytes,
            maximum_pixels=settings.maximum_image_pixels,
        )
        deleted = 0
        for session_id in repository.expired_scan_session_ids(datetime.now(UTC)):
            for stored_path in repository.delete_scan_session(session_id) or []:
                storage.delete_path(stored_path)
            deleted += 1
        print(json.dumps({"deleted_scan_sessions": deleted}))
        return

    snapshot_directory = args.snapshot_dir or settings.database_path.parent / "snapshots" / "hk"
    print(_result_payload(synchronize_hk_registry(snapshot_directory, repository)))


if __name__ == "__main__":
    main()
