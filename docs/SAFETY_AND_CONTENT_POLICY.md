# Safety and Content Policy

**Status:** Required product policy  
**Audience:** Product, engineering, design, clinical review, and support

## 1. Purpose

Med Info serves people who may have no medical training. It must reduce uncertainty without encouraging self-diagnosis, unsupervised medicine changes, or false confidence.

This policy applies to interface text, search results, AI-generated drafts, notifications, support responses, and administrative publication tools.

## 2. Three independent result axes

Every result must keep these concepts separate.

### A. Registration status

- Registered in the selected jurisdiction.
- Registration data found but status requires attention.
- No current official record found.
- Unable to check.

“No official record found” is not the same as “counterfeit.” It may be an overseas product, unsupported category, OCR failure, outdated registration, or incorrect market selection.

### B. Development/regulatory relationship

- Confirmed originator/reference product.
- Confirmed generic product.
- Confirmed authorised generic.
- Confirmed biosimilar.
- Not applicable.
- Insufficient public evidence.

This status requires a separately stored evidence record.

### C. Package consistency/authenticity

- Readable package fields are consistent with an official record.
- One or more package fields conflict with the official record.
- Insufficient information to compare.

Never state “genuine,” “authentic,” “counterfeit,” or “fake” based only on photograph matching.

## 3. Required user-facing explanation

When showing originator/generic status, include:

> 學名藥不等於假藥。這項分類描述藥物的研發和註冊關係，不代表相片可以證明產品真偽。

When a package is consistent with a registry record, include:

> 相片中的資料與官方記錄相符，但這不能單獨證明產品真偽。若來源可疑，請向註冊藥劑師或相關監管機構查詢。

## 4. Allowed content

The service may provide, when supported by sources:

- Product name and registration information.
- Active ingredients and strengths.
- Dosage form and route.
- Manufacturer or certificate holder.
- Legal/sale classification.
- General approved uses.
- General administration instructions from approved labeling.
- Common side effects.
- Serious warning signs.
- Contraindications and important precautions.
- Storage information.
- Official recall information.
- Source links and review dates.

## 5. Prohibited or restricted content

The service must not:

- Diagnose a user from symptoms or photographs.
- Say that a medicine is appropriate for a specific user.
- Recommend starting, stopping, replacing, or sharing a medicine.
- Calculate or modify a personalised dose.
- Infer pregnancy, renal, hepatic, allergy, or interaction safety without adequate clinical context.
- Rank manufacturers by effectiveness without appropriate comparative evidence.
- Present a full drug-interaction checker without a validated, licensed source and clinical governance.
- Claim counterfeit detection from visual similarity, barcode presence, serial number, or registration match alone.
- Hide uncertainty behind generic disclaimers.

## 6. Plain-language rules

- Put the most important action first.
- Use one idea per sentence.
- Prefer common words.
- Explain necessary medical terms immediately.
- Use absolute actions instead of vague severity labels.
- Separate common discomfort from urgent warning signs.
- Avoid unexplained percentages and relative-risk language.
- Do not describe a long list as if every effect were equally likely.
- Keep product name, ingredient, strength, and dosage form visually distinct.
- Never rely on colour alone to communicate danger.

Preferred heading translations:

| Technical term | Consumer heading |
|---|---|
| Indications | 通常用來做甚麼？ |
| Contraindications | 哪些情況不要自行使用？ |
| Precautions | 使用前先確認 |
| Adverse reactions | 可能出現的不舒服 |
| Serious adverse reactions | 何時需要立即求助？ |
| Dosage and administration | 怎樣使用？ |
| Active ingredient | 真正產生藥效的成分 |

## 7. Consumer information hierarchy

### Level 1: visible without expansion

- Exact identity and confidence state.
- Active ingredient and strength.
- Registration status.
- Originator/generic evidence state.
- One-sentence general use.
- Highest-priority warning, if any.

### Level 2: one tap away

- Before-use checks.
- Common side effects.
- Urgent warning signs.
- General administration guidance.
- Storage.

### Level 3: evidence and detail

- Regulatory fields.
- Full source links.
- Evidence notes.
- Content version and review date.
- More complete official labeling.

## 8. Dosing policy

- The application may transcribe an existing pharmacy-label instruction after user confirmation.
- Transcribed instructions must be visually labelled as “相片讀取內容” and not as a new recommendation.
- If the transcription is uncertain, show the image region and ask the user to check the original label.
- General label dosing may be displayed only with its source and context.
- The service must not choose a dose based on age, weight, symptoms, or disease.
- Never advise doubling a dose after a missed dose unless that exact guidance is present in an approved, applicable source and has been clinically reviewed.

## 9. Emergency and escalation language

Emergency language must be short and actionable. For example:

> 如果出現呼吸困難、面部或喉嚨腫脹、失去知覺或其他嚴重症狀，請立即尋求緊急醫療協助。

Do not rely on the application to triage an emergency. Region-specific emergency contact information should be reviewed before launch.

For non-emergency uncertainty:

> 不要自行停藥或改變劑量。請帶同藥盒或藥袋向醫生或藥劑師查詢。

## 10. Source hierarchy for medical content

1. Local product-specific approved label or patient leaflet.
2. Local regulator product information.
3. Local regulator ingredient/class consumer information.
4. Foreign regulator content, clearly marked with its jurisdiction.
5. Licensed clinical source.
6. Pharmacist-authored summary derived from cited sources.

Do not silently merge conflicting advice from different jurisdictions.

## 11. AI content workflow

1. Import or select source passages.
2. Generate a draft with traceable source references.
3. Run automated checks for unsupported quantities, negation changes, omitted warnings, and prohibited advice.
4. Pharmacist reviews against the source.
5. Reviewer approves a version for publication.
6. Any source update reopens the content for review when relevant sections change.

AI output is a draft until a human reviewer publishes it.

## 12. High-risk content

Require explicit pharmacist review and shorter review intervals for:

- Narrow therapeutic index medicines.
- Anticoagulants.
- Insulin and glucose-lowering medicines.
- Anti-seizure medicines.
- Immunosuppressants.
- Opioids, sedatives, and controlled drugs.
- Medicines with boxed or prominent serious warnings.
- Modified-release products.
- Paediatric, pregnancy, or breastfeeding guidance.
- Products affected by active safety warnings or recalls.

## 13. Review states

- `draft`
- `automated_checks_passed`
- `clinical_review_required`
- `published`
- `superseded`
- `suspended_due_to_source_change`

Only `published` content may appear as a reviewed consumer summary.

## 14. Privacy rules for images

- Ask for package-only photographs.
- Warn when a patient label may be visible.
- Redact personal information before optional retention.
- Delete source images promptly.
- Never show one user's image to another user.
- Never use patient-labelled images in demos, evaluation corpora, or model training without specific informed consent and de-identification review.

## 15. Incident handling

A safety incident includes:

- Wrong confirmed identity.
- Wrong strength or dosage form.
- Unsupported originator/generic classification.
- Missing critical warning.
- Incorrect dose transcription presented as certain.
- Stale recall information presented as current.
- Exposure of personal information.

Required response:

1. Disable or downgrade the affected result path.
2. Preserve audit evidence without retaining unnecessary personal data.
3. Notify the product, clinical, privacy, and engineering owners.
4. Identify other records affected by the same rule or source.
5. Correct, review, and publish a documented resolution.
6. Add a regression test before restoration.

