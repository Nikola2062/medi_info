from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class RelationshipStatus(StrEnum):
    CONFIRMED_ORIGINATOR_OR_REFERENCE = "confirmed_originator_or_reference"
    CONFIRMED_GENERIC = "confirmed_generic"
    CONFIRMED_AUTHORIZED_GENERIC = "confirmed_authorized_generic"
    CONFIRMED_BIOSIMILAR = "confirmed_biosimilar"
    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT_PUBLIC_EVIDENCE = "insufficient_public_evidence"


class PackageConsistency(StrEnum):
    CONSISTENT = "consistent_with_official_record"
    CONFLICTING = "conflicting_with_official_record"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class CaptureSlot(StrEnum):
    FRONT = "front"
    INGREDIENTS = "ingredients"
    IDENTIFIER = "identifier"


class ScanStatus(StrEnum):
    AWAITING_UPLOADS = "awaiting_uploads"
    READY_FOR_PROCESSING = "ready_for_processing"


@dataclass(frozen=True)
class IngredientRecord:
    name: str
    normalized_name: str


@dataclass(frozen=True)
class ProductRecord:
    registration_number: str
    product_name: str
    normalized_name: str
    certificate_holder: str | None = None
    normalized_holder: str = ""
    status: str = "listed"
    source_record_key: str | None = None
    ingredients: tuple[IngredientRecord, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SourceRecord:
    authority: str
    title: str
    url: str
    jurisdiction_code: str
    retrieved_at: datetime
    content_hash: str
    published_or_effective_at: datetime | None = None
    licence: str | None = None
    raw_snapshot_location: str | None = None

    def __post_init__(self) -> None:
        if self.retrieved_at.tzinfo is None:
            object.__setattr__(self, "retrieved_at", self.retrieved_at.replace(tzinfo=UTC))


@dataclass(frozen=True)
class ScanUploadRecord:
    id: str
    session_id: str
    slot: CaptureSlot
    stored_path: str
    mime_type: str
    width: int
    height: int
    byte_size: int
    quality_warnings: tuple[str, ...]
    created_at: datetime
    idempotency_key: str


@dataclass(frozen=True)
class ScanSessionRecord:
    id: str
    jurisdiction_code: str
    created_at: datetime
    image_deletion_due_at: datetime
    uploads: tuple[ScanUploadRecord, ...] = field(default_factory=tuple)

    @property
    def status(self) -> ScanStatus:
        uploaded_slots = {upload.slot for upload in self.uploads}
        return (
            ScanStatus.READY_FOR_PROCESSING
            if uploaded_slots == set(CaptureSlot)
            else ScanStatus.AWAITING_UPLOADS
        )
