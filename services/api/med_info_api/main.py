from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
import secrets
import uuid

from datetime import timedelta

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .normalization import normalize_registration_number
from .models import CaptureSlot, ScanSessionRecord, ScanUploadRecord
from .repository import RegistryRepository, StoredProduct
from .schemas import (
    HealthResponse,
    IngredientResponse,
    ProductResponse,
    ProductSummaryResponse,
    SearchResponse,
    ScanSessionResponse,
    ScanUploadResponse,
    SourceFreshnessResponse,
    SourceResponse,
)
from .uploads import ImageStorage, InvalidImageError


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()


@lru_cache
def get_repository() -> RegistryRepository:
    repository = RegistryRepository(get_settings().database_path)
    repository.initialize()
    return repository


@lru_cache
def get_image_storage() -> ImageStorage:
    settings = get_settings()
    assert settings.upload_directory is not None
    return ImageStorage(
        settings.upload_directory,
        maximum_bytes=settings.maximum_upload_bytes,
        maximum_pixels=settings.maximum_image_pixels,
    )


app = FastAPI(
    title="Med Info API",
    version="0.1.0",
    description="Evidence-first medicine registry lookup. Not medical advice or counterfeit detection.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


def _source_response(source) -> SourceResponse:
    return SourceResponse(
        authority=source.authority,
        title=source.title,
        url=source.url,
        retrieved_at=source.retrieved_at,
        published_or_effective_at=source.published_or_effective_at,
        content_hash=source.content_hash,
        licence=source.licence,
    )


def _summary(product: StoredProduct, lookup_basis: str) -> ProductSummaryResponse:
    return ProductSummaryResponse(
        id=product.id,
        registration_number=product.record.registration_number,
        product_name=product.record.product_name,
        certificate_holder=product.record.certificate_holder,
        registry_status=product.record.status,
        ingredients=[IngredientResponse(name=item.name) for item in product.record.ingredients],
        lookup_basis=lookup_basis,
    )


def _scan_upload_response(upload: ScanUploadRecord) -> ScanUploadResponse:
    return ScanUploadResponse(
        id=upload.id,
        slot=upload.slot,
        mime_type=upload.mime_type,
        width=upload.width,
        height=upload.height,
        byte_size=upload.byte_size,
        quality_warnings=list(upload.quality_warnings),
        created_at=upload.created_at,
    )


def _scan_session_response(session: ScanSessionRecord) -> ScanSessionResponse:
    return ScanSessionResponse(
        id=session.id,
        created_at=session.created_at,
        image_deletion_due_at=session.image_deletion_due_at,
        status=session.status,
        uploads=[_scan_upload_response(upload) for upload in session.uploads],
    )


def require_admin_access(
    x_admin_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="Admin API is disabled")
    if not x_admin_key or not secrets.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")


@app.get("/healthz", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post(
    "/v1/scan-sessions",
    response_model=ScanSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scan_session(
    jurisdiction: str = Query(default="HK", pattern="^HK$"),
    repository: RegistryRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
) -> ScanSessionResponse:
    now = datetime.now(UTC)
    session = repository.create_scan_session(
        jurisdiction=jurisdiction,
        created_at=now,
        image_deletion_due_at=now + timedelta(hours=settings.image_retention_hours),
    )
    return _scan_session_response(session)


@app.get("/v1/scan-sessions/{session_id}/status", response_model=ScanSessionResponse)
def get_scan_session_status(
    session_id: str,
    repository: RegistryRepository = Depends(get_repository),
) -> ScanSessionResponse:
    session = repository.get_scan_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Scan session not found")
    return _scan_session_response(session)


@app.post(
    "/v1/scan-sessions/{session_id}/uploads",
    response_model=ScanUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_scan_image(
    session_id: str,
    slot: CaptureSlot = Form(),
    image: UploadFile = File(),
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]+$",
    ),
    repository: RegistryRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
    storage: ImageStorage = Depends(get_image_storage),
) -> ScanUploadResponse:
    session = repository.get_scan_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Scan session not found")
    if session.image_deletion_due_at <= datetime.now(UTC):
        raise HTTPException(status_code=410, detail="Scan session has expired")

    existing = repository.find_scan_upload_by_idempotency(session_id, idempotency_key)
    if existing:
        return _scan_upload_response(existing)

    payload = await image.read(settings.maximum_upload_bytes + 1)
    if len(payload) > settings.maximum_upload_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds the upload size limit")

    upload_id = str(uuid.uuid4())
    try:
        stored = storage.store_sanitized_image(
            session_id=session_id,
            upload_id=upload_id,
            payload=payload,
        )
    except InvalidImageError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error

    upload = ScanUploadRecord(
        id=upload_id,
        session_id=session_id,
        slot=slot,
        stored_path=str(stored.path),
        mime_type=stored.mime_type,
        width=stored.width,
        height=stored.height,
        byte_size=stored.byte_size,
        quality_warnings=stored.quality_warnings,
        created_at=datetime.now(UTC),
        idempotency_key=idempotency_key,
    )
    try:
        replaced_path = repository.save_scan_upload(upload)
    except Exception:
        storage.delete_path(stored.path)
        raise
    if replaced_path:
        storage.delete_path(replaced_path)
    return _scan_upload_response(upload)


@app.delete("/v1/scan-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan_session(
    session_id: str,
    repository: RegistryRepository = Depends(get_repository),
    storage: ImageStorage = Depends(get_image_storage),
) -> Response:
    stored_paths = repository.delete_scan_session(session_id)
    if stored_paths is None:
        raise HTTPException(status_code=404, detail="Scan session not found")
    for stored_path in stored_paths:
        storage.delete_path(stored_path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/v1/products/search", response_model=SearchResponse)
def search_products(
    registration_number: str | None = Query(default=None, max_length=32),
    q: str | None = Query(default=None, min_length=2, max_length=120),
    jurisdiction: str = Query(default="HK", pattern="^HK$"),
    limit: int = Query(default=10, ge=1, le=20),
    repository: RegistryRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
) -> SearchResponse:
    if bool(registration_number) == bool(q):
        raise HTTPException(
            status_code=422,
            detail="Provide exactly one of registration_number or q",
        )

    canonical_registration = None
    if registration_number:
        canonical_registration = normalize_registration_number(registration_number)
        if not canonical_registration:
            raise HTTPException(status_code=422, detail="Use a Hong Kong number in the HK-XXXXX format")

    current = repository.current_registry(jurisdiction)
    if not current:
        return SearchResponse(
            query=canonical_registration or q or "",
            count=0,
            results=[],
            message="No published Hong Kong registry snapshot is available.",
        )

    products = repository.search(
        jurisdiction=jurisdiction,
        registration_number=canonical_registration,
        query=q,
        limit=limit,
    )
    age_days = (datetime.now(UTC) - current.source.retrieved_at).days
    basis = "exact_registration_number" if canonical_registration else "text_match"
    return SearchResponse(
        query=canonical_registration or q or "",
        count=len(products),
        results=[_summary(product, basis) for product in products],
        source=_source_response(current.source),
        source_is_stale=age_days > settings.source_stale_after_days,
        message=None if products else "No matching official registry record was found.",
    )


@app.get("/v1/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: str,
    repository: RegistryRepository = Depends(get_repository),
) -> ProductResponse:
    product = repository.get(product_id)
    current = repository.current_registry()
    if not product or not current:
        raise HTTPException(status_code=404, detail="Product not found in the current registry snapshot")
    summary = _summary(product, "exact_registration_number")
    return ProductResponse(**summary.model_dump(), source=_source_response(current.source))


@app.get(
    "/v1/admin/source-freshness",
    response_model=SourceFreshnessResponse,
    dependencies=[Depends(require_admin_access)],
)
def source_freshness(
    jurisdiction: str = Query(default="HK", pattern="^HK$"),
    repository: RegistryRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
) -> SourceFreshnessResponse:
    current = repository.current_registry(jurisdiction)
    if not current:
        return SourceFreshnessResponse(
            status="unavailable",
            stale_after_days=settings.source_stale_after_days,
        )
    age_days = (datetime.now(UTC) - current.source.retrieved_at).days
    return SourceFreshnessResponse(
        status="stale" if age_days > settings.source_stale_after_days else "current",
        stale_after_days=settings.source_stale_after_days,
        record_count=current.record_count,
        snapshot_published_at=current.published_at,
        source=_source_response(current.source),
    )
