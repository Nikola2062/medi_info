# Technical Design

**Status:** Proposed  
**Date:** 2026-10-11

## 1. Architecture goals

- Deterministic product identity and regulatory classification.
- AI-assisted extraction and explanation, not AI-decided medical facts.
- Complete provenance and versioning.
- Explicit abstention when evidence is insufficient.
- A jurisdiction-aware model that can add Taiwan without rewriting the core.
- Privacy-preserving image processing.

## 2. Proposed system

```text
Mobile web/PWA
    |
    | HTTPS, short-lived upload token
    v
Application API ---------------------- Admin review UI
    |                                      |
    +--> Image-processing worker           |
    |      - quality checks                |
    |      - barcode/DataMatrix            |
    |      - OCR                           |
    |      - field extraction              |
    |                                      |
    +--> Matching/evidence engine <---------+
    |      - official product search
    |      - conflict checks
    |      - confidence state
    |      - originator/generic evidence
    |
    +--> Consumer-content service
    |      - approved summaries
    |      - source citations
    |      - locale rendering
    |
    +--> PostgreSQL
    +--> short-lived encrypted image storage

Scheduled ingestion workers
    -> official datasets
    -> staging validation
    -> versioned publication
    -> freshness/quality alerts
```

## 3. Suggested stack

This is a starting recommendation, not an irreversible requirement.

- **Web/PWA:** Next.js and TypeScript.
- **API and workers:** Python with FastAPI, because OCR and data-processing libraries are strongest in Python.
- **Database:** PostgreSQL with `pg_trgm` for name similarity.
- **Queue:** Redis-backed worker queue for image processing and imports.
- **Object storage:** S3-compatible encrypted storage with lifecycle deletion.
- **OCR:** self-hosted Chinese/English OCR for the baseline; optional cloud fallback only after privacy and data-location review.
- **Barcode:** ZXing-compatible decoding with explicit GS1 Application Identifier parsing.
- **Observability:** structured logs, metrics, traces, source-freshness alerts, and privacy-safe error sampling.

## 4. Proposed repository layout

```text
med_info/
  apps/
    web/                    # Consumer and admin Next.js interfaces
  services/
    api/                    # FastAPI application
    image_worker/           # OCR, barcode, and field extraction
    data_ingestion/         # Official dataset importers
  packages/
    contracts/              # API schemas and generated client types
    ui/                     # Shared UI components
  migrations/               # Database migrations
  tests/
    fixtures/               # De-identified test packaging images
    evaluation/             # Matching and safety evaluation suites
  docs/
```

Do not create all services on day one. A modular monolith with separate background workers is sufficient for the MVP; the boundaries above prevent clinical, matching, and ingestion logic from becoming entangled.

## 5. Core data model

### `jurisdiction`

- `id`
- `code` such as `HK` or `TW`
- `name`
- `default_locale`

### `regulatory_product`

- `id`
- `jurisdiction_id`
- `registration_number`
- `product_name_original`
- `product_name_normalized`
- `legal_classification`
- `sale_requirement`
- `certificate_holder`
- `manufacturer`
- `registration_date`
- `status`
- `source_record_id`
- `valid_from`
- `valid_to`

Unique key: jurisdiction plus registration number plus source version.

### `product_ingredient`

- `product_id`
- `ingredient_name_original`
- `ingredient_name_normalized`
- `strength_value`
- `strength_unit`
- `salt_or_form`

### `product_package`

- `id`
- `product_id`
- `gtin`
- `local_barcode`
- `package_description`
- `reference_image_url`
- `image_rights_status`

Lot and expiry values from a scan belong to the scan event, not the static product package.

### `regulatory_relationship`

- `id`
- `jurisdiction_id`
- `subject_product_id`
- `reference_product_id`, nullable
- `relationship_type`: `originator`, `reference`, `generic`, `authorized_generic`, `biosimilar`, `not_applicable`
- `evidence_source_id`
- `evidence_excerpt_or_note`
- `review_status`
- `reviewer_id`
- `reviewed_at`
- `expires_or_review_due_at`

No public classification may be produced without a published relationship record.

### `source_document`

- `id`
- `authority`
- `title`
- `url`
- `jurisdiction_id`
- `retrieved_at`
- `published_or_effective_at`
- `content_hash`
- `licence`
- `raw_snapshot_location`

### `consumer_monograph`

- `id`
- `scope_type`: `product` or `ingredient`
- `scope_id`
- `locale`
- `uses_plain`
- `before_use_plain`
- `common_effects_plain`
- `urgent_help_plain`
- `use_guidance_plain`
- `source_document_ids`
- `review_status`
- `reviewer_id`
- `reviewed_at`
- `version`

### `recall_notice`

- `id`
- `jurisdiction_id`
- `product_id`, nullable
- `registration_number`, nullable
- `lot_number`, nullable
- `notice_url`
- `classification`
- `status`
- `published_at`

### `scan_session`

- `id`
- `jurisdiction_id`
- `created_at`
- `image_deletion_due_at`
- `extracted_fields_json`
- `matched_product_id`, nullable
- `identity_state`
- `user_confirmed_at`, nullable
- `privacy_redaction_state`

Do not store user identity in this table for anonymous scans.

## 6. Data ingestion

Each source connector follows the same stages:

1. Fetch metadata and resource.
2. Verify transport, file type, checksum, and expected schema.
3. Store an immutable raw snapshot.
4. Parse into staging tables.
5. Validate required fields and record counts.
6. Compare with the current published snapshot.
7. Quarantine suspicious changes.
8. Publish atomically.
9. Record provenance and freshness.
10. Alert on failures or unexpected deletions.

Never partially replace the production registry during an import.

## 7. Image-processing pipeline

### 7.1 Client-side checks

- Minimum resolution.
- Blur score.
- Glare/overexposure.
- Document/package boundary coverage.
- Likely pharmacy-label personal information warning.

### 7.2 Machine-readable codes

Decode before OCR because exact identifiers are stronger evidence. Parse:

- One-dimensional retail codes.
- GS1 DataMatrix Application Identifiers.
- GTIN.
- Lot/batch.
- Expiry date.
- Serial number when present.

### 7.3 OCR

Run multiple rotations if orientation is uncertain. Preserve:

- Original text.
- Normalized text.
- Bounding box.
- OCR confidence.
- Source image/page reference.

Field extraction targets:

- `HK-XXXXX`
- Product/brand name.
- Active ingredient.
- Strength and unit.
- Dosage form.
- Certificate holder/manufacturer.
- Lot and expiry.

### 7.4 Visual matching

Visual similarity may reorder already plausible candidates. It must not independently produce a confirmed identity because packaging can change and counterfeit packaging can imitate a reference image.

## 8. Matching engine

Use explicit feature scoring plus hard conflicts.

### Strong positive evidence

- Exact registration number.
- Exact GTIN linked to a registry product.
- Exact product name plus strength and dosage form.

### Supporting evidence

- Active ingredient.
- Certificate holder.
- Manufacturer.
- Package size.
- Visual similarity.

### Hard conflicts

- Registration number belongs to a different product.
- Strength conflict.
- Immediate-release versus modified-release conflict.
- Different active ingredients.
- Product is withdrawn/cancelled when the package claims a current registration.

Hard conflicts prevent a “Confirmed” result even if the total similarity score is high.

Store a structured explanation of why each candidate was accepted, rejected, or downgraded. This explanation is required for audit and safe user messaging.

## 9. Public confidence states

The internal model may use calibrated scores, but the public API returns one of:

- `confirmed`
- `likely_user_confirmation_required`
- `candidate_only`
- `unable_to_identify`
- `conflicting_evidence`
- `unsupported_product_type`

Regulatory relationship is returned independently:

- `confirmed_originator_or_reference`
- `confirmed_generic`
- `confirmed_authorized_generic`
- `confirmed_biosimilar`
- `not_applicable`
- `insufficient_public_evidence`

## 10. API outline

### Consumer

- `POST /v1/scan-sessions`
- `POST /v1/scan-sessions/{id}/uploads`
- `GET /v1/scan-sessions/{id}/status`
- `GET /v1/scan-sessions/{id}/candidates`
- `POST /v1/scan-sessions/{id}/confirm`
- `GET /v1/products/{id}`
- `GET /v1/products/{id}/consumer-information`
- `GET /v1/products/{id}/evidence`
- `GET /v1/products/search`
- `DELETE /v1/scan-sessions/{id}`

### Administration

- `GET /v1/admin/imports`
- `GET /v1/admin/evidence/review-queue`
- `POST /v1/admin/evidence/{id}/review`
- `GET /v1/admin/monographs/review-queue`
- `POST /v1/admin/monographs/{id}/review`
- `GET /v1/admin/source-freshness`

Use idempotency keys for upload and confirmation operations.

## 11. Content generation and AI controls

Consumer summaries should be generated or revised offline, then reviewed and published as versioned content. They should not be freely generated on every user request.

Allowed AI tasks:

- OCR repair suggestions.
- Name and synonym candidate generation.
- Draft translation.
- Draft plain-language summarisation of supplied source passages.

Disallowed AI decisions:

- Final identity.
- Originator/generic classification.
- Medical diagnosis.
- Personal dose.
- Treatment recommendation.
- Unsupported interaction conclusions.

Every draft must retain sentence-level links to source sections so a reviewer can verify it.

## 12. Privacy design

- Use presigned, short-lived upload credentials.
- Encrypt images in transit and at rest.
- Separate image object keys from analytics identifiers.
- Delete successful-scan images immediately where possible.
- Apply a maximum 24-hour recovery window for failed processing unless the user opts in to longer retention.
- Never include images or extracted personal text in standard logs.
- Redact likely names, phone numbers, addresses, patient numbers, and clinic labels before any optional diagnostic retention.
- Do not train models on uploads without separate, informed opt-in consent.

## 13. Security controls

- Validate image MIME type by content, not extension.
- Strip metadata before downstream processing.
- Enforce file-size, pixel-count, and decompression limits.
- Run image parsing in an isolated worker.
- Rate-limit anonymous uploads.
- Protect admin actions with strong authentication and role-based access.
- Audit all evidence and clinical-content publication events.
- Scan dependencies and pin production versions.

## 14. Testing strategy

### Unit and contract tests

- Registration-number parsing.
- Strength and unit normalization.
- GS1 Application Identifier parsing.
- Candidate scoring and hard conflicts.
- Source/version linkage.

### Evaluation corpus

Build a rights-cleared and de-identified corpus containing:

- Clear front and side panels.
- Glare, blur, rotation, perspective, and partial crops.
- Old and new packaging.
- Look-alike product names.
- Same product at different strengths.
- Immediate- and modified-release variants.
- Unsupported supplements and proprietary Chinese medicines.
- Loose tablets that should trigger abstention.

### Safety regression tests

- No dose generation.
- No classification without evidence.
- No cross-jurisdiction registration claim.
- No result hides a strength conflict.
- No stale source appears as current.
- Emergency language remains present after content revisions.

## 15. Deployment stages

1. Local development with synthetic/test registry records.
2. Internal environment using official snapshots.
3. Pharmacist review environment.
4. Closed pilot with anonymous users.
5. Limited public beta after release gates pass.

Production deployment should not begin until a clinical reviewer and privacy owner are assigned.

