from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .ingestion.hk_registry import (
    OFFICIAL_AUTHORITY,
    OFFICIAL_LANDING_URL,
    OFFICIAL_LICENCE,
    OFFICIAL_TERMS_URL,
    parse_hk_registry_snapshot,
)


def export_public_registry(xml_path: Path, output_path: Path) -> dict[str, object]:
    """Export a compact, browser-readable snapshot from validated official XML."""
    xml_data = xml_path.read_bytes()
    parsed = parse_hk_registry_snapshot(xml_data)
    exported_at = datetime.now(UTC).replace(microsecond=0)
    content_hash = hashlib.sha256(xml_data).hexdigest()
    payload: dict[str, object] = {
        "source": {
            "authority": OFFICIAL_AUTHORITY,
            "title": "List of Registered Pharmaceutical Products (English Only)",
            "url": OFFICIAL_LANDING_URL,
            "retrieved_at": exported_at.isoformat(),
            "published_or_effective_at": datetime.combine(
                parsed.last_updated_on,
                datetime.min.time(),
                tzinfo=UTC,
            ).isoformat(),
            "content_hash": content_hash,
            "licence": OFFICIAL_LICENCE,
            "licence_url": OFFICIAL_TERMS_URL,
        },
        "record_count": len(parsed.products),
        "products": [
            [
                product.registration_number,
                product.product_name,
                product.certificate_holder or "",
                [ingredient.name for ingredient in product.ingredients],
            ]
            for product in parsed.products
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_path.parent,
        prefix=f".{output_path.name}-",
        suffix=".partial",
        delete=False,
    ) as temporary:
        json.dump(payload, temporary, ensure_ascii=False, separators=(",", ":"))
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export validated Hong Kong medicine registry XML for the public web preview."
    )
    parser.add_argument("xml_path", type=Path)
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()
    payload = export_public_registry(args.xml_path, args.output_path)
    print(
        json.dumps(
            {
                "output": str(args.output_path.resolve()),
                "record_count": payload["record_count"],
                "content_hash": payload["source"]["content_hash"],  # type: ignore[index]
            }
        )
    )


if __name__ == "__main__":
    main()
