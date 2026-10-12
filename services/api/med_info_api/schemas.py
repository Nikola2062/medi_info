from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .models import CaptureSlot, PackageConsistency, RelationshipStatus, ScanStatus


class SourceResponse(BaseModel):
    authority: str
    title: str
    url: str
    retrieved_at: datetime
    published_or_effective_at: datetime | None = None
    content_hash: str
    licence: str | None = None


class IngredientResponse(BaseModel):
    name: str


class ProductSummaryResponse(BaseModel):
    id: str
    jurisdiction: Literal["HK"] = "HK"
    registration_number: str
    product_name: str
    certificate_holder: str | None = None
    registry_status: str
    ingredients: list[IngredientResponse]
    lookup_basis: Literal["exact_registration_number", "text_match"]


class ProductResponse(ProductSummaryResponse):
    regulatory_relationship: RelationshipStatus = RelationshipStatus.INSUFFICIENT_PUBLIC_EVIDENCE
    package_consistency: PackageConsistency = PackageConsistency.INSUFFICIENT_INFORMATION
    source: SourceResponse
    safety_notice_zh_hant: str = (
        "藥物真偽不能只靠相片或註冊記錄判斷。如有疑問，請向註冊藥劑師查詢。"
    )


class SearchResponse(BaseModel):
    jurisdiction: Literal["HK"] = "HK"
    query: str
    count: int
    results: list[ProductSummaryResponse]
    source: SourceResponse | None = None
    source_is_stale: bool | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["med-info-api"] = "med-info-api"


class SourceFreshnessResponse(BaseModel):
    jurisdiction: Literal["HK"] = "HK"
    status: Literal["current", "stale", "unavailable"]
    stale_after_days: int
    record_count: int | None = None
    snapshot_published_at: datetime | None = None
    source: SourceResponse | None = None


class ScanUploadResponse(BaseModel):
    id: str
    slot: CaptureSlot
    mime_type: str
    width: int
    height: int
    byte_size: int
    quality_warnings: list[str]
    created_at: datetime


class ScanSessionResponse(BaseModel):
    id: str
    jurisdiction: Literal["HK"] = "HK"
    created_at: datetime
    image_deletion_due_at: datetime
    status: ScanStatus
    required_slots: list[CaptureSlot] = list(CaptureSlot)
    uploads: list[ScanUploadResponse]
    privacy_notice_zh_hant: str = (
        "只應拍攝藥物包裝。請遮蓋姓名、電話、地址、病人編號和診所資料。"
    )


class ErrorResponse(BaseModel):
    detail: str
    code: str = Field(description="Stable machine-readable error code")
