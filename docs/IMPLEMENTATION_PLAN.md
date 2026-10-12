# Implementation Plan

**Planning horizon:** 12-week MVP  
**Initial jurisdiction:** Hong Kong

The dates below are effort estimates. They assume one product/full-stack engineer, one data/ML engineer, a part-time designer, and a part-time registered pharmacist. A solo implementation will take longer.

## Phase 0 — Decisions and governance, week 1

### Work

- Confirm Hong Kong as the first market.
- Decide whether the pilot includes prescription and OTC medicines or begins with OTC only.
- Assign product, engineering, privacy, and clinical owners.
- Confirm clinical-review availability.
- Review official-source access, licence, and attribution terms.
- Approve the product claim: information lookup and education, not diagnosis or counterfeit authentication.

### Exit gate

- Named clinical reviewer.
- Approved MVP scope.
- Approved terminology and safety policy.
- Documented data rights.

## Phase 1 — Project foundation and registry, weeks 2–3

### Engineering

- Create the web/API/worker project skeleton.
- Add local development environment and CI.
- Create initial database migrations.
- Build Hong Kong XML downloader, immutable snapshot storage, parser, validation, and atomic publication.
- Implement search by registration number, product name, active ingredient, and certificate holder.
- Add source metadata and freshness dashboard.

### Product/design

- Create low-fidelity mobile flows.
- Test terminology with five non-clinical users.
- Confirm large-text and screen-reader requirements.

### Exit gate

- A product can be found by exact `HK-XXXXX` and traced to the imported source version.
- Failed imports do not corrupt the published registry.

## Phase 2 — Capture and identification, weeks 4–6

### Engineering

- Implement guided three-image capture.
- Add blur, glare, and crop checks.
- Decode one-dimensional barcodes and GS1 DataMatrix.
- Add Chinese/English OCR.
- Extract name, registration number, ingredient, strength, dosage form, holder, lot, and expiry.
- Implement normalization and candidate scoring.
- Add hard-conflict rules.
- Build manual search fallback.
- Implement short-lived encrypted uploads and deletion jobs.

### Evaluation

- Assemble the first rights-cleared package-image evaluation set.
- Include look-alike names, multiple strengths, modified-release variants, glare, blur, and unsupported products.

### Exit gate

- Exact registration-number cases meet the internal precision target.
- Strength conflicts cannot produce a confirmed result.
- Loose-pill cases abstain.

## Phase 3 — Evidence and consumer content, weeks 7–8

### Engineering

- Build regulatory-relationship evidence records.
- Build pharmacist review and publication screens.
- Build versioned consumer monographs and source links.
- Implement separate identity and regulatory-relationship status displays.
- Add reviewed general-use, warning, common-side-effect, and urgent-help sections.

### Clinical/content

- Select 100–200 common pilot medicines or ingredients.
- Prepare source-linked drafts.
- Review high-risk medicines first or exclude them until review capacity exists.
- Define review intervals and source-change triggers.

### Exit gate

- No originator/generic status appears without evidence.
- All published consumer content has source and reviewer metadata.

## Phase 4 — Safety, usability, and accessibility, weeks 9–10

### Safety testing

- Wrong-market package.
- Cancelled or outdated registration.
- Similar name, different ingredient.
- Same ingredient, different strength.
- Standard versus modified release.
- Incomplete package photograph.
- Conflicting barcode and printed registration number.
- Missing source or expired content review.

### Usability testing

Test with non-clinical adults, older adults, caregivers, and limited-English users. Ask users to explain:

- What medicine was identified?
- What is its active ingredient?
- Does “generic” mean fake?
- Does the result prove authenticity?
- What should they do if the result conflicts with the box?
- Which symptom requires urgent help?

### Exit gate

- Release-gate comprehension and accessibility targets are met.
- Critical misunderstandings are resolved in the interface, not only in disclaimers.

## Phase 5 — Closed pilot, weeks 11–12

### Work

- Invite a limited group of users.
- Monitor abstention rate, retake rate, candidate ambiguity, and source failures.
- Review every reported wrong match.
- Track whether users misinterpret registration or generic status as proof of authenticity.
- Perform privacy and security review.
- Prepare incident-response runbook.

### Public-beta gate

- Identity precision gate passed.
- Clinical review complete for all public content.
- Privacy and security issues resolved.
- Source-freshness monitoring operational.
- Rollback and feature-disable mechanisms tested.

## Initial engineering backlog

### P0 — required for internal prototype

- Repository/tooling scaffold.
- PostgreSQL schema and migrations.
- Hong Kong registry importer.
- Product search API.
- Manual registration-number search UI.
- Guided image upload.
- Registration-number OCR.
- Candidate and conflict engine.
- Result confirmation.
- Source/provenance display.
- Image deletion.

### P1 — required for closed pilot

- Barcode and DataMatrix parsing.
- Ingredient, strength, and dosage-form OCR.
- Consumer monographs.
- Clinical review interface.
- Evidence-based originator/generic relationships.
- Privacy redaction warning.
- Recall notices where reliable matching is possible.
- Accessibility and analytics.

### P2 — after pilot

- Taiwan connector.
- Rights-cleared packaging reference library.
- User medicine list.
- Recall notifications.
- Multi-language support.
- Licensed interaction checking.
- Native mobile application if PWA capture limitations justify it.

## Work that must not be pulled into the MVP casually

- Counterfeit verdicts.
- Symptom diagnosis.
- Medicine recommendation.
- Personalised dosing.
- Global medicine coverage.
- Unreviewed real-time AI medical answers.
- Interaction checking based on text scraping or an abandoned API.

Each of these changes the safety, evidence, regulatory, or licensing profile of the product and requires a separate decision.

