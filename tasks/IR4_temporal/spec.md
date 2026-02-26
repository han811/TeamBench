# IR4: Temporal Priority QA

## Goal
Answer all questions using ONLY the provided offline corpus. No internet access.
Multiple documents cover the same topic with different dates and statuses.
You must apply the **Temporal Priority Rules** below to determine which document
is authoritative for each topic.

## Organisation
Nexus Software Ltd. — Product Documentation Hub (product documentation system)

## Questions
1. [Q1] For the support tiers specification at Nexus Software Ltd., doc_E.txt is dated 2021-03-28 while doc_B.txt is dated 2019-05-03. Which document is authoritative and why?
2. [Q2] What is the uptime SLA target for the Nexus Software Ltd. production environment?
3. [Q3] What pricing model does Nexus Software Ltd. use for its standard tier?
4. [Q4] According to the temporal priority rules for Nexus Software Ltd. documents, can a DRAFT document dated 2024 supersede an APPROVED document dated 2020 on the same topic?
5. [Q5] For the feature flags specification at Nexus Software Ltd., doc_F.txt is dated 2025-03-22 while doc_C.txt is dated 2022-07-14. Which document is authoritative and why?
6. [Q6] If a newer document dated 2025 contradicts a Founding Document dated 2018 on the same topic, which document is authoritative at Nexus Software Ltd.?
7. [Q7] Which document is the authoritative source for the pricing model specification at Nexus Software Ltd.?
8. [Q8] How many support tiers does Nexus Software Ltd. offer to customers?

## Hard Requirements

1. Produce `answer.json` with answers to ALL questions:
   ```json
   {
     "questions": [
       {"id": "Q1", "question": "...", "answer": "<string>"},
       ...
     ]
   }
   ```
2. Apply the **Temporal Priority Rules** strictly — do not simply use the most
   recently dated document without checking its status and founding classification.
3. Leave no answer field blank.
4. For meta-rule questions, explain the rule, not just the answer.

## Temporal Priority Rules

The following rules determine which document is authoritative when documents
on the same topic conflict:

### Rule 1 — Founding Documents Are Always Authoritative
Certain documents are classified as **Founding Documents** (marked in the
document header). Founding Documents are **always authoritative** for their
topic, regardless of the date of any other document. A newer document NEVER
supersedes a Founding Document.

### Rule 2 — Approved Status Beats Draft Status (Regardless of Date)
A document with status **APPROVED** is always authoritative over a document
with status **DRAFT**, even if the DRAFT document is more recent. Draft
documents represent work-in-progress and have NOT been formally ratified.

### Rule 3 — Most Recent Approved Document Supersedes Older Approved Documents
When two or more **APPROVED** (non-founding) documents cover the same topic,
the document with the **most recent date** is authoritative.

### Priority Order (highest to lowest)
1. Founding Document (any date, any topic it covers)
2. Most recent APPROVED document
3. Older APPROVED documents
4. DRAFT documents (never authoritative when an APPROVED doc exists)

## Document Metadata

| Document | Topic | Date | Status |
|----------|-------|------|--------|
| `doc_A.txt` | sla targets | 2024-01-19 | APPROVED |
| `doc_B.txt` | support tiers | 2019-05-03 | APPROVED |
| `doc_C.txt` | feature flags | 2022-07-14 | APPROVED |
| `doc_D.txt` | pricing model | 2021-03-28 | APPROVED (**FOUNDING**) |
| `doc_E.txt` | support tiers | 2021-03-28 | DRAFT |
| `doc_F.txt` | feature flags | 2025-03-22 | DRAFT |

**Founding Document topic**: `pricing model`

## Corpus
Located at `corpus/` (relative to workspace):
- `doc_A.txt`
- `doc_B.txt`
- `doc_C.txt`
- `doc_D.txt`
- `doc_E.txt`
- `doc_F.txt`

## Warning
Some documents are dated more recently but have DRAFT status — they must NOT
override APPROVED documents on the same topic. The Founding Document for
`pricing model` is always authoritative for that topic regardless of
what other documents say. Read the status and founding classification in each
document header before answering.
