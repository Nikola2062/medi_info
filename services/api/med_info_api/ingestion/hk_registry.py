from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import BinaryIO, Callable
from urllib.parse import urlparse

from lxml import etree

from ..models import IngredientRecord, ProductRecord, SourceRecord
from ..normalization import normalize_registration_number, normalize_search_text
from ..repository import PublishedRegistry, RegistryRepository


OFFICIAL_LANDING_URL = (
    "https://data.gov.hk/en-data/dataset/"
    "hk-dh-dh_do-hk-dh-do-pharmaceutical-product"
)
OFFICIAL_RESOURCE_URL = "https://www.drugoffice.gov.hk/eps/psi/DrugList.xml"
OFFICIAL_SCHEMA_URL = "https://www.drugoffice.gov.hk/eps/psi/DrugList.xsd"
OFFICIAL_TERMS_URL = "https://data.gov.hk/en/terms-and-conditions"
OFFICIAL_AUTHORITY = "Hong Kong Department of Health via DATA.GOV.HK"
OFFICIAL_LICENCE = "DATA.GOV.HK Terms of Use v1.2 (2025-05-26); attribution required"
ALLOWED_DOWNLOAD_HOSTS = {"drugoffice.gov.hk", "www.drugoffice.gov.hk"}
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
MINIMUM_LIVE_RECORDS = 10_000
SCHEMA_PATH = Path(__file__).with_name("schemas") / "DrugList.xsd"


@dataclass(frozen=True)
class ParsedRegistry:
    products: tuple[ProductRecord, ...]
    last_updated_on: date


@dataclass(frozen=True)
class DownloadedSnapshot:
    path: Path
    retrieved_at: datetime
    content_hash: str
    resource_url: str


def _load_schema() -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(SCHEMA_PATH))


def parse_hk_registry_snapshot(xml_data: bytes) -> ParsedRegistry:
    """Validate and parse the exact XML contract published by the Drug Office."""
    if b"<!DOCTYPE" in xml_data.upper() or b"<!ENTITY" in xml_data.upper():
        raise ValueError("DTD and entity declarations are not accepted")

    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        remove_blank_text=True,
    )
    try:
        root = etree.fromstring(xml_data, parser=parser)
        _load_schema().assertValid(root)
    except (etree.XMLSyntaxError, etree.DocumentInvalid) as error:
        raise ValueError(f"Registry XML does not match the official schema: {error}") from error

    last_update_text = root.findtext("lastUpdate")
    try:
        last_updated_on = date.fromisoformat(last_update_text or "")
    except ValueError as error:
        raise ValueError("Registry lastUpdate must use YYYY-MM-DD") from error

    products: list[ProductRecord] = []
    seen: set[str] = set()
    for element in root.findall("drug"):
        registration_number = normalize_registration_number(element.findtext("permitNo") or "")
        if not registration_number:
            raise ValueError("Registry contains an invalid Hong Kong permit number")
        if registration_number in seen:
            raise ValueError(f"Registry contains duplicate permit number {registration_number}")
        seen.add(registration_number)

        product_name = (element.findtext("productName") or "").strip()
        holder = (element.findtext("regCertHolderName") or "").strip()
        ingredient_names = [
            (item.text or "").strip()
            for item in element.findall("./activeIngs/activeIng")
            if (item.text or "").strip()
        ]
        if not product_name or not holder or not ingredient_names:
            raise ValueError(f"Registry record {registration_number} has an empty required field")

        products.append(
            ProductRecord(
                registration_number=registration_number,
                product_name=product_name,
                normalized_name=normalize_search_text(product_name),
                certificate_holder=holder,
                normalized_holder=normalize_search_text(holder),
                source_record_key=registration_number,
                ingredients=tuple(
                    IngredientRecord(name, normalize_search_text(name))
                    for name in ingredient_names
                ),
            )
        )

    return ParsedRegistry(tuple(products), last_updated_on)


def parse_hk_registry(xml_data: bytes) -> list[ProductRecord]:
    """Compatibility wrapper returning the validated product records."""
    return list(parse_hk_registry_snapshot(xml_data).products)


def _read_limited(response: BinaryIO, maximum_bytes: int = MAX_DOWNLOAD_BYTES) -> bytes:
    content_length = getattr(response, "headers", {}).get("Content-Length")
    if content_length and int(content_length) > maximum_bytes:
        raise ValueError("Registry download exceeds the configured size limit")
    payload = response.read(maximum_bytes + 1)
    if len(payload) > maximum_bytes:
        raise ValueError("Registry download exceeds the configured size limit")
    return payload


def download_hk_registry(
    snapshot_directory: Path,
    *,
    resource_url: str = OFFICIAL_RESOURCE_URL,
    opener: Callable[..., BinaryIO] = urllib.request.urlopen,
) -> DownloadedSnapshot:
    """Download one immutable official snapshot with transport and size checks."""
    requested = urlparse(resource_url)
    if requested.scheme != "https" or requested.hostname not in ALLOWED_DOWNLOAD_HOSTS:
        raise ValueError("Registry downloads are restricted to the official HTTPS host")

    request = urllib.request.Request(
        resource_url,
        headers={"User-Agent": "MedInfoRegistryImporter/0.1 (+source-provenance)"},
    )
    with opener(request, timeout=30) as response:
        final_url = response.geturl()
        final = urlparse(final_url)
        if final.scheme != "https" or final.hostname not in ALLOWED_DOWNLOAD_HOSTS:
            raise ValueError("Registry download redirected away from the official HTTPS host")
        content_type = response.headers.get_content_type()
        if content_type not in {"application/xml", "text/xml", "application/octet-stream"}:
            raise ValueError(f"Unexpected registry content type: {content_type}")
        xml_data = _read_limited(response)

    parsed = parse_hk_registry_snapshot(xml_data)
    if len(parsed.products) < MINIMUM_LIVE_RECORDS:
        raise ValueError(
            f"Live registry has only {len(parsed.products)} records; publication is quarantined"
        )

    retrieved_at = datetime.now(UTC)
    digest = hashlib.sha256(xml_data).hexdigest()
    snapshot_directory.mkdir(parents=True, exist_ok=True)
    destination = snapshot_directory / f"{digest}.xml"
    if not destination.exists():
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=snapshot_directory,
            prefix=".download-",
            suffix=".partial",
            delete=False,
        ) as temporary:
            temporary.write(xml_data)
            temporary_path = Path(temporary.name)
        try:
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)

    return DownloadedSnapshot(destination, retrieved_at, digest, final_url)


def import_hk_registry(
    xml_path: Path,
    repository: RegistryRepository,
    *,
    retrieved_at: datetime | None = None,
    source_url: str = OFFICIAL_RESOURCE_URL,
    minimum_records: int = 1,
) -> PublishedRegistry:
    xml_data = xml_path.read_bytes()
    parsed = parse_hk_registry_snapshot(xml_data)
    if len(parsed.products) < minimum_records:
        raise ValueError(
            f"Registry has only {len(parsed.products)} records; expected at least {minimum_records}"
        )
    source = SourceRecord(
        authority=OFFICIAL_AUTHORITY,
        title="List of Registered Pharmaceutical Products (English Only)",
        url=source_url,
        jurisdiction_code="HK",
        retrieved_at=retrieved_at or datetime.now(UTC),
        published_or_effective_at=datetime.combine(
            parsed.last_updated_on,
            datetime.min.time(),
            tzinfo=UTC,
        ),
        content_hash=hashlib.sha256(xml_data).hexdigest(),
        licence=OFFICIAL_LICENCE,
        raw_snapshot_location=str(xml_path.resolve()),
    )
    return repository.publish_snapshot(source, parsed.products)


def synchronize_hk_registry(
    snapshot_directory: Path,
    repository: RegistryRepository,
) -> PublishedRegistry:
    downloaded = download_hk_registry(snapshot_directory)
    return import_hk_registry(
        downloaded.path,
        repository,
        retrieved_at=downloaded.retrieved_at,
        source_url=downloaded.resource_url,
        minimum_records=MINIMUM_LIVE_RECORDS,
    )

