# Product Requirements Document

**Product:** Med Info  
**Version:** 0.1  
**Date:** 2026-10-11  
**Initial market:** Hong Kong  
**Primary audience:** People without professional medical training

## 1. Product summary

Med Info helps a person identify a medicine from its packaging and understand the result in plain language. It combines barcode decoding, optical character recognition, official medicine registries, and human-reviewed consumer information.

The product must be conservative. If it cannot reliably identify a product or substantiate an originator/generic relationship, it must say so instead of guessing.

## 2. Problem

Consumers often cannot easily answer basic questions about a medicine:

- What exactly is this product?
- Is it registered locally?
- What active ingredient and strength does it contain?
- Is it an originator/reference product or a generic product?
- What is it generally used for?
- Which warnings and side effects matter most?

Existing regulatory pages are authoritative but often use English names, technical terminology, long package inserts, or interfaces that are difficult to use on a phone. Informal web results may omit jurisdiction, dosage form, strength, or evidence.

## 3. Product principles

1. **Identity before explanation.** Do not show product-specific medical information until the user confirms the matched identity.
2. **Evidence before classification.** Do not infer originator/generic status from price, packaging, manufacturer reputation, or country of manufacture.
3. **Abstention is a valid result.** “Unable to confirm” is preferable to a confident error.
4. **Separate registration, development status, and authenticity.** They answer different questions.
5. **Use plain language by default.** Medical terminology may appear as secondary explanatory text.
6. **Every important claim has provenance.** Display the source and last-reviewed date.
7. **No personalised treatment decisions.** The product does not diagnose, prescribe, recommend switching, or alter dosage.

## 4. Target users

### Primary users

- Adults checking medicine supplied by a clinic, pharmacy, caregiver, or family member.
- Caregivers helping older relatives understand medicine packaging.
- People comparing a newly supplied brand with a previous brand.
- People who need Traditional Chinese explanations of English packaging.

### Accessibility considerations

- Older adults and users with reduced vision.
- Users with low health literacy or limited English proficiency.
- Users unfamiliar with terms such as active ingredient, dosage form, contraindication, or bioequivalence.

The initial interface should use large touch targets, scalable text, strong contrast, short sentences, and screen-reader-compatible labels.

## 5. Scope

### MVP includes

- Hong Kong registered western medicines.
- Intact boxes, bottles, sachets, and blister packs with readable printed information.
- Traditional Chinese interface with English product and ingredient names retained.
- Hong Kong registration-number recognition in the `HK-XXXXX` format.
- One-dimensional barcode and GS1 DataMatrix decoding.
- Chinese and English OCR.
- Official product lookup and candidate ranking.
- User confirmation of exact name, strength, dosage form, and registration number.
- Registration, legal classification, sale requirement, ingredient, strength, manufacturer/certificate-holder, and source information when available.
- Evidence-backed development-status classification.
- Plain-language consumer information for an initially curated set of common medicines.
- Source links, source dates, and content-review dates.
- Administrative review workflow.

### MVP excludes

- Diagnosis from symptoms.
- Recommendations about which medicine to take.
- Changes to a prescribed dose or treatment plan.
- Counterfeit authentication based only on an image.
- Definitive identification of loose, unlabelled tablets or capsules.
- Personalised drug-drug interaction checking.
- Chinese proprietary medicines, supplements, medical devices, veterinary medicines, and unregistered overseas products.
- Automatic comparison of clinical effectiveness between manufacturers.

## 6. Terminology shown to users

Avoid “正廠／副廠” as the primary classification because it is ambiguous and can imply genuine versus counterfeit.

Use these statuses instead:

- 原研／參考藥（有明確證據）
- 學名藥（有明確證據）
- 授權學名藥（有明確證據）
- 生物相似藥
- 此分類不適用
- 公開資料不足，未能確認

Always add the short explanation: “學名藥不等於假藥；藥物真偽不能只靠相片判斷。”

## 7. Core user journey

### 7.1 Start

1. Show the selected jurisdiction: Hong Kong.
2. Explain that local registration rules differ by market.
3. Ask the user to photograph the medicine package rather than a pharmacy label containing personal details.

### 7.2 Guided capture

Request up to three images:

1. Package front.
2. Ingredient/strength panel.
3. Registration number, barcode, lot, and expiry panel.

The camera view should warn about blur, glare, cropping, and insufficient light before upload.

### 7.3 Identification

1. Decode machine-readable identifiers.
2. Extract `HK-XXXXX`, product name, ingredient, strength, dosage form, holder/manufacturer, lot, and expiry using OCR.
3. Search the local registry.
4. Return up to three candidates when an exact identifier is unavailable.
5. Ask the user to confirm the exact product.

### 7.4 Result

Display information in this order:

1. Identification confidence and any unresolved mismatch.
2. Product name, ingredient, strength, and dosage form.
3. Hong Kong registration status and registration number.
4. Originator/generic status and evidence.
5. General approved or reviewed uses in plain language.
6. Important “check before use” information.
7. Common side effects.
8. Symptoms requiring urgent help.
9. Source and review information.

### 7.5 Safe failure

If the result cannot be established:

- Explain which field is missing or conflicting.
- Invite the user to retake a specific side of the package.
- Offer manual search by registration number or product name.
- Recommend asking a pharmacist when uncertainty remains.
- Do not display product-specific dosing or reassurance.

## 8. Functional requirements

| ID | Requirement |
|---|---|
| FR-001 | The system shall record and display the jurisdiction used for every result. |
| FR-002 | The system shall guide the user through front, ingredient, and identifier images. |
| FR-003 | The system shall decode supported barcodes and GS1 DataMatrix values. |
| FR-004 | The system shall extract Hong Kong registration numbers and key product text in Chinese and English. |
| FR-005 | The system shall match extracted data against a versioned official registry snapshot. |
| FR-006 | The system shall require user confirmation when identification is not based on an exact registration number. |
| FR-007 | The system shall distinguish confirmed, likely, candidate-only, and unable-to-identify states. |
| FR-008 | The system shall never infer originator/generic status without a stored evidence record. |
| FR-009 | The system shall show the source, retrieval date, and content-review date for material claims. |
| FR-010 | The system shall provide a plain-language result page designed for non-clinicians. |
| FR-011 | The system shall avoid generating or changing a personalised dose. |
| FR-012 | The system shall provide an administrative workflow for pharmacist review and publication. |
| FR-013 | The system shall detect likely personal information in uploaded pharmacy labels and warn or redact where feasible. |
| FR-014 | The system shall automatically delete original images after the configured retention period. |
| FR-015 | The system shall mark data as stale if official-source synchronisation fails beyond its threshold. |
| FR-016 | The system shall display current recall information when an official product or batch match is available. |

## 9. Confidence model

Do not present an unexplained percentage to consumers. Use calibrated labels:

### Confirmed

- Exact, valid registration number matched; and
- Product name and at least one of strength, ingredient, or holder is consistent.

### Likely match

- No exact registration-number read; and
- Name, ingredient, strength, dosage form, and holder produce one dominant candidate; and
- User explicitly confirms the package.

### Candidate only

- Multiple plausible products remain; or
- Strength/dosage form cannot be distinguished; or
- Only visual similarity or a partial name is available.

### Unable to identify

- No official result;
- Conflicting identifiers;
- Unsupported product type;
- Loose pill without reliable packaging information; or
- Image quality remains inadequate.

Identity confidence and originator/generic evidence confidence must be stored and displayed separately.

## 10. Consumer content structure

Each product/ingredient page should use these headings:

1. 這是甚麼？
2. 通常用來做甚麼？
3. 使用前先確認
4. 常見的不舒服
5. 何時需要立即求助？
6. 怎樣使用？
7. 資料從哪裏來？

The first screen should not contain an exhaustive package insert. It should prioritise the information most likely to prevent harm, with expandable detail below.

## 11. Non-functional requirements

### Safety

- Fail closed when evidence is absent or contradictory.
- Version all source records and consumer summaries.
- Keep a complete audit history of clinical-content changes.
- Require pharmacist approval for published high-risk content.

### Privacy

- Anonymous use must be possible.
- Uploaded images must not be used for model training by default.
- Image retention must be short and documented.
- User deletion must be supported.
- Personal data must not appear in analytics logs.

### Performance

- Show capture-quality feedback in under one second on supported devices.
- Return an exact identifier match in a target of three seconds under normal conditions.
- Fall back to manual search if OCR processing is unavailable.

### Availability and data freshness

- Keep the last valid official snapshot if an update fails.
- Show its retrieval date.
- Raise an operational alert when the source is stale.

## 12. Success measures for the pilot

- At least 99.9% precision for “Confirmed” identity results in the controlled evaluation set.
- No originator/generic label without an explicit evidence record.
- Zero unresolved critical clinical-content errors in pharmacist-reviewed pilot content.
- At least 90% of usability-test participants can find the active ingredient and urgent warning without assistance.
- At least 80% can correctly explain that a generic medicine is not the same as a counterfeit medicine.
- The system safely abstains on all unsupported loose-pill test cases.
- Official dataset updates and failures are visible to administrators.

These are release gates, not claims about current system performance.

## 13. Pilot test population

Recruit a small but varied group including:

- Adults with no healthcare background.
- Older adults.
- Family caregivers.
- Users with limited English proficiency.
- At least one accessibility user using text scaling or a screen reader.

Use teach-back questions rather than asking only “Do you understand?” For example: “請用自己的說話告訴我們，這個結果能否證明藥物是真貨？”

## 14. Dependencies

- A registered pharmacist or equivalent local clinical reviewer.
- Reliable access to official registry downloads.
- A legally reviewed data-attribution approach.
- A privacy review for uploaded images.
- A regulatory review before claims extend beyond education and product-information lookup.

## 15. Decisions required before implementation sprint 1

1. Confirm Hong Kong as the first release jurisdiction.
2. Confirm whether the first pilot covers prescription medicines, OTC medicines, or both.
3. Appoint the clinical reviewer responsible for publication approval.
4. Select image-processing deployment: local/self-hosted OCR, a cloud provider, or a hybrid.
5. Set the original-image retention period; the recommended default is deletion immediately after processing or within 24 hours for failed-job recovery.

