# Med Info

Med Info is a planned consumer-facing medicine identification and information service. A user photographs medicine packaging, confirms the matched product, and receives source-linked information written for people without medical training.

The first release is designed for Hong Kong registered western medicines. Taiwan is the planned second jurisdiction.

## Product position

Med Info is an information and verification tool. It is not a diagnostic service, a counterfeit detector, or a replacement for a doctor or pharmacist.

The product keeps three questions separate:

1. Is this product registered in the selected jurisdiction?
2. Is there reliable evidence that it is an originator/reference product or a generic product?
3. Does the photographed package appear consistent with the registered product?

A photograph alone cannot establish authenticity.

## Current status

Early implementation. The first vertical slice provides:

- A deterministic Hong Kong registration-number and text search API.
- An XML registry importer with validation and atomic snapshot publication.
- Source provenance and freshness metadata on API results.
- A mobile-first Traditional Chinese manual-lookup interface.
- Safety-first empty and uncertainty states with no authenticity claim.
- A static public-preview export containing the validated official registry;
  the hosted preview does not accept photos.
- A versioned medicine-profile layer that keeps regulatory identity, brand
  relationship evidence, and pharmacist-reviewed clinical content separate.

The included registry fixture is synthetic test data and must not be presented as
real medicine information.

## Run the prototype

The local prototype uses Python 3.12 and SQLite so it can run without external
infrastructure. PostgreSQL remains the planned production database.

```bash
cd services/api
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'

# Import synthetic development records that use the official XML schema.
MED_INFO_DB_PATH=../../runtime/med_info.sqlite3 \
  python -m med_info_api.cli import-hk tests/fixtures/hk_registry.xml

# Start the API.
MED_INFO_DB_PATH=../../runtime/med_info.sqlite3 \
  uvicorn med_info_api.main:app --reload
```

In a second terminal:

```bash
python3 -m http.server 3000 --directory apps/web/dist
```

Open `http://127.0.0.1:3000` and try the synthetic registration number
`HK-12345`. API documentation is available at `http://127.0.0.1:8000/docs`.

The operational freshness endpoint is disabled unless
`MED_INFO_ADMIN_API_KEY` is configured. When enabled, call
`GET /v1/admin/source-freshness` with the value in the `X-Admin-Key` header.
The key must not be placed in a browser URL or committed to the repository.

Anonymous capture sessions default to a 24-hour maximum image lifetime. Run the
cleanup command from a scheduler more frequently than the retention window:

```bash
cd services/api
MED_INFO_DB_PATH=../../runtime/med_info.sqlite3 \
MED_INFO_UPLOAD_DIR=../../runtime/uploads \
  python -m med_info_api.cli cleanup-expired-scans
```

Uploaded JPEG, PNG, and WebP files are decoded, checked for size and pixel
limits, re-encoded without metadata, and stored under random identifiers. The
prototype does not yet run OCR or claim that an uploaded package is identified.

The published preview deliberately enables only registration-number lookup.
Photo capture remains available on localhost for development but is disabled on
the public host until the recognition pipeline, privacy review, and production
deletion operations are complete.

The public result for `HK-20966` demonstrates the richer evidence layout. It
adds registration history, sale classification, brand-lineage evidence, and
source jurisdiction. Because isotretinoin is high-risk content, the drafted
consumer summary remains in `apps/web/content/review-queue/` and the public UI
fails closed until a registered pharmacist records approval.

To download, validate, retain, and atomically publish the real Hong Kong
registry snapshot:

```bash
cd services/api
MED_INFO_DB_PATH=../../runtime/med_info.sqlite3 \
  python -m med_info_api.cli sync-hk
```

The synchronizer accepts only HTTPS responses from the official Drug Office
host, caps response size, validates against the published XSD, quarantines
unexpectedly small datasets, stores snapshots by SHA-256 hash, and publishes
only after all checks pass. Use of DATA.GOV.HK data requires attribution under
its current Terms of Use.

To regenerate the browser-readable public snapshot from a downloaded and
validated XML file:

```bash
cd services/api
PYTHONPATH=. python -m med_info_api.export_public_registry \
  ../../runtime/registry-snapshots/<sha256>.xml \
  ../../apps/web/dist/data/hk-registry.json
```

Run the dependency-light test suite with:

```bash
cd services/api
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## Project documents

- [Product requirements](docs/PRD.md)
- [Technical design](docs/TECHNICAL_DESIGN.md)
- [Official data sources](docs/DATA_SOURCES.md)
- [Safety and content policy](docs/SAFETY_AND_CONTENT_POLICY.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Prototype testing guide](docs/TESTING_GUIDE.md)

## MVP summary

- Guided capture of the package front, ingredient panel, and registration number/barcode.
- Barcode/DataMatrix decoding and Chinese/English OCR.
- Matching against the Hong Kong registered pharmaceutical products dataset.
- User confirmation of name, strength, dosage form, and registration number.
- Registration status and evidence-based originator/generic classification.
- Plain-language ingredient, use, warning, and side-effect information with sources and review dates.
- A safe refusal state when identity or regulatory status cannot be established.

## Working assumptions

- Initial jurisdiction: Hong Kong.
- Initial language: Traditional Chinese, with English product names retained.
- Initial platform: mobile-first web application/PWA.
- Initial product scope: registered western medicines in intact retail packaging.
- Clinical content will be reviewed by a registered pharmacist before public release.

These assumptions are recorded so they can be changed deliberately rather than becoming hidden implementation choices.
