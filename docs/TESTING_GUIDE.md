# Prototype Testing Guide

This guide covers internal testing of registry lookup and guided package capture.
It does not authorize clinical-content testing or public release.

## What to prepare

### Package set

Start with 15–30 intact Hong Kong western-medicine packages that you own or are
permitted to photograph. Include:

- Clear packages with a readable `HK-XXXXX` number.
- The same active ingredient in different strengths.
- Standard-release and modified-release variants.
- Similar product names with different ingredients.
- Packages with two or more active ingredients.
- Older and newer packaging for the same registered product, where available.
- At least five negative cases: overseas packages, supplements, Chinese
  proprietary medicines, loose pills, and unreadable packages.

Do not include controlled medicines unless the clinical and security owners have
approved their handling.

### Images per case

Capture three package-only images:

1. Front, showing the complete product name.
2. Ingredient/strength panel, showing ingredient, strength, and dosage form.
3. Identifier panel, showing `HK-XXXXX`, barcode/DataMatrix, batch, and expiry
   where present.

Add controlled variants for blur, glare, low light, rotation, perspective, and
partial crop. Keep the original clear image so each degradation has a reference.

### Expected-result record

Record these fields for each test case in a local file approved by the project
owner:

| Field | Example or purpose |
|---|---|
| Case ID | Non-personal identifier such as `HK-PACK-001` |
| Expected outcome | Exact match, candidate only, conflicting, or abstain |
| Registration number | `HK-XXXXX`, if applicable |
| Product name | As printed on the package |
| Active ingredient(s) | As printed and as listed in the official registry |
| Strength | Include value and unit |
| Dosage form | Tablet, cream, eye drops, and so on |
| Release type | Standard, modified, delayed, or not applicable |
| Expected source record | Official record URL or snapshot hash |
| Image condition | Clear, glare, blur, cropped, rotated, and so on |
| Reviewer | Internal reviewer ID, not patient information |

The expected result must come from the package and official source, never from
the application output being evaluated.

## Privacy rules

- Use package-only photographs.
- Cover or crop pharmacy labels before upload.
- Do not include names, phone numbers, addresses, patient numbers, prescription
  instructions, clinic details, faces, hands with identifying marks, or location
  metadata.
- Do not use real patient photographs, support tickets, or chat attachments as
  test fixtures.
- Keep rights-cleared evaluation images outside Git unless the repository owner
  has explicitly approved and documented their inclusion.

## People required

- An engineering owner for failures and logs.
- A privacy owner for image-handling review.
- A registered pharmacist or appropriate local reviewer before evaluating or
  publishing consumer medical summaries.
- At least five non-clinical usability participants before pilot release,
  including an older adult and a screen-reader or large-text user where possible.

## Current prototype checks

1. Import a synthetic or official registry snapshot.
2. Confirm an exact `HK-XXXXX` lookup shows source and retrieval metadata.
3. Confirm an unknown number says it cannot be confirmed and does not call the
   product counterfeit.
4. Confirm all capture buttons remain disabled until the package-only privacy
   acknowledgement is checked.
5. Upload front, ingredient, and identifier images.
6. Confirm quality warnings suggest a retake without claiming identification.
7. Use “刪除今次相片” and confirm the session is no longer available.
8. Run the expired-session cleanup command and verify no expired files remain.

Do not score identification accuracy yet: OCR and candidate matching have not
been connected to scan sessions in this prototype.
