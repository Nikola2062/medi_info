# Official Data Sources

**Date reviewed:** 2026-10-11

This document records intended sources and their limitations. A source being public does not make every possible use accurate or legally unrestricted. Licence and access terms must be reviewed before production deployment.

## 1. Source priority

Use sources in this order:

1. Regulator or government open data for the same jurisdiction as the scanned product.
2. Product-specific approved local label or leaflet.
3. Official local consumer medicine information.
4. Official foreign regulator data, clearly marked as a different jurisdiction.
5. Pharmacist-reviewed secondary content with documented licensing.

Never replace a missing local regulatory classification with an unlabelled inference from a foreign market.

## 2. Hong Kong

### Registered pharmaceutical products open data

- **Provider:** Hong Kong Department of Health.
- **Landing page:** https://data.gov.hk/en-data/dataset/hk-dh-dh_do-hk-dh-do-pharmaceutical-product
- **Format:** XML.
- **Resource:** https://www.drugoffice.gov.hk/eps/psi/DrugList.xml
- **Schema:** https://www.drugoffice.gov.hk/eps/psi/DrugList.xsd
- **Published fields:** product name, registration certificate holder, Hong Kong registration number, active ingredients.
- **Update statement:** as and when necessary.
- **MVP use:** authoritative base registry for identity candidates.

Implementation verification on 2026-10-11 found a source `lastUpdate` value of
2026-10-02 and 14,274 unique records. The importer validates every download
against the published XSD and rejects duplicate or malformed permit numbers.

DATA.GOV.HK Terms of Use v1.2 allow commercial and non-commercial reuse subject
to the stated conditions, including clear acknowledgement of the Government,
the relevant organisation, and DATA.GOV.HK. This implementation records and
displays that attribution; legal review remains a release gate.

Limitations:

- The published field description does not include an originator/generic flag.
- It does not constitute a complete package-image reference library.
- Product indications, complete warnings, and dosing are not all present in the open dataset.

### Drug Office search and product detail

- **Search:** https://www.drugoffice.gov.hk/eps/do/en/consumer/search_drug_database.html
- **Consumer registration guidance:** https://www.drugoffice.gov.hk/eps/do/en/consumer/news_informations/knowledge_on_medicines/general_knowledge_on_medicine_registration.html
- **Useful fields:** product name, `HK-XXXXX`, certificate holder, legal classification, sale requirement, active ingredient, registration date, and recent recall indicator where available.
- **MVP use:** enrichment, direct source links, and manual evidence review.

The Drug Office states that registered packaging should carry a Hong Kong registration number and general label information such as the product name, active ingredient and quantity, manufacturer, batch, expiry, package size, and storage conditions. These are the intended OCR fields.

### Consumer medicine education

- **General use guidance:** https://www.drugoffice.gov.hk/eps/do/en/consumer/news_informations/knowledge_on_medicines/general_use_on_medicine.html
- **MVP use:** general safety language and selected medicine-class education.

This is not a substitute for product-specific approved labeling.

## 3. Taiwan

### All drug licence records

- **Landing page:** https://data.gov.tw/dataset/9122
- **Provider:** Taiwan Food and Drug Administration.
- **Update frequency:** weekly.
- **Important fields:** licence number, status, validity, Chinese and English names, indication, dosage form, packaging, active ingredients, applicant, manufacturer, country, dosage, packaging, and international barcode.
- **Planned use:** second-jurisdiction product registry and product information.

### Package insert or outer-box dataset

- **Landing page:** https://data.gov.tw/dataset/9117
- **Provider:** Taiwan Food and Drug Administration.
- **Update frequency:** weekly.
- **Important fields:** licence number, Chinese/English product name, insert-image link, outer-box-image link.
- **Planned use:** rights-aware packaging references and local approved information.

### Licence

- **Taiwan Open Government Data License 1.0:** https://data.gov.tw/license
- **Requirement:** preserve the required attribution.

## 4. United States

US sources are suitable for future US support and for documented research. They must not silently determine the regulatory status of a Hong Kong or Taiwan product.

### FDA Orange Book

- **Data page:** https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files
- **Update frequency:** monthly for downloadable data.
- **Important fields:** ingredient, dosage form/route, trade name, applicant, strength, NDA/ANDA type, application number, therapeutic-equivalence code, Reference Listed Drug, Reference Standard, approval date.
- **Use:** US-market originator/reference/generic evidence.

Reference Listed Drug and Reference Standard are related but not identical concepts and must not be collapsed in the internal schema.

### DailyMed

- **API documentation:** https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm
- **Provider:** US National Library of Medicine.
- **Content:** current Structured Product Labeling, names, application numbers, NDCs, packaging, media, and label sections.
- **Use:** US product labeling and source-linked content.

### openFDA labels and recalls

- **Label API:** https://open.fda.gov/apis/drug/label/
- **Recall/enforcement API:** https://open.fda.gov/apis/drug/enforcement/how-to-use-the-endpoint/
- **Use:** structured access and future US recall support.

Observe the openFDA disclaimer: results should not independently be relied upon for medical-care decisions.

### RxNorm

- **API documentation:** https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html
- **Use:** US medication-name normalization and identifier mapping.

RxNav drug-drug interaction features were discontinued in January 2024. Do not plan a production interaction checker around the former API.

## 5. Barcode standards

### GS1 DataMatrix

- **Overview:** https://www.gs1.org/industries/healthcare/2d-barcode-healthcare
- **Potential values:** GTIN, batch/lot, expiry or manufacturing date, serial number.
- **Use:** product lookup support, expiry display, and batch recall matching where local data permits.

A decoded DataMatrix is an identifier carrier. It does not by itself prove registration, authenticity, or originator status.

## 6. Data-source acceptance checklist

Before a source is used in a public result, record:

- Authority and jurisdiction.
- Exact resource URL.
- Access and licence terms.
- Update frequency.
- Schema and unique identifiers.
- Whether the content is product-specific or ingredient/class-level.
- Whether the source states regulatory status, or only lists a product.
- Retrieval date and content hash.
- Known omissions.
- Staleness threshold.
- Required attribution.

## 7. Content that requires a separate licence or partnership

The following should not be assumed to be freely available:

- Comprehensive drug-drug interaction checking.
- Commercial product-image libraries.
- Global GTIN-to-medicine directories.
- Complete patient leaflets for every Hong Kong product.
- Commercial clinical decision-support monographs.

These capabilities should remain outside the MVP until data rights, clinical validation, and cost are settled.
