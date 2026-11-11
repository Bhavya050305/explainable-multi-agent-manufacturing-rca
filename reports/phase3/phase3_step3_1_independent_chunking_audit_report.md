# ManuMind AI — Phase 3 Step 3.1: Independent Chunking Audit and Metric Reconciliation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Department:** Department of AI & Data Science, RMK Engineering College  
**Repository:** [`D:/Desktop/FInal year project/manumind-ai`](file:///D:/Desktop/FInal%20year%20project/manumind-ai)  
**Branch:** `main` | **HEAD:** `e5e686939e1830b64191dcbd327b2b7bf35a0793` (synchronized with `origin/main` at `0 0`)  
**Audit Milestone:** Phase 3 Step 3.1 — Independent Chunking Audit and Metric Reconciliation  
**Role:** Independent Senior RAG Architect, Quality Assurance Auditor, and Technical Auditor  
**Audit Execution Timestamp:** `2026-11-10T22:58:00+05:30`  

---

## 1. Executive Summary & Audit Verdict

### Final Independent Audit Verdict:
# `PASS WITH LIMITATIONS`

This independent audit conducted a thorough, read-only inspection of the Phase 3 Step 3 document chunking implementation, its data artifacts, and the published Step 3 completion reports ([`reports/phase3/phase3_step3_chunking_report.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase3/phase3_step3_chunking_report.md) and [`reports/phase3/phase3_step3_chunking.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase3/phase3_step3_chunking.json)).

### Core Audit Findings:
1. **Core Chunk Data Integrity is 100% Validated:**  
   The underlying in-memory chunk registry and data objects strictly contain **564 total chunks** derived deterministically from all **418 source documents**. Exactly **400 atomic maintenance incident chunks** exist, representing a strict 1-to-1 mapping with zero splitting, zero merging, and zero cross-machine or cross-incident contamination.
2. **Machine-Level Incident Count Discrepancy Reconciled (Audit A):**  
   The apparent machine-level incident count of **470** in Table 3.2 of the Step 3 report was traced to a presentation-layer arithmetic bug in [`backend/app/rag/chunking_report.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/chunking_report.py#L186). The reporting script used a hardcoded formula (`total_c - 4`) assuming 4 SOP chunks per machine instead of querying actual category counts (each SOP produced 11 chunks). The actual underlying chunk records match the authoritative corpus audit counts (35, 42, 36, 35, 46, 39, 28, 48, 49, 42; sum = 400) **100% exactly**.
3. **Atomic Incident Chunks Exceed 450-Token Soft Bound (Audit B):**  
   Because all 400 maintenance incidents were preserved as complete atomic documents, their heuristic token sizes range from **473 to 532 tokens** (mean: **484.98**). Exactly **1 chunk** (`INC-0381_chk000`) reaches **532 tokens**, exceeding the 512-token context limit of `BAAI/bge-small-en-v1.5`.
4. **Safety Metadata Semantic Overclassification (Audit D):**  
   **516 out of 564 chunks (91.5%)** are marked `is_safety_related = True`. This was caused by the presence of the mandatory synthetic academic disclaimer banner (`> **SAFETY NOTICE: SYNTHETIC DEMONSTRATION MATERIAL...**`) on all 400 incident documents, which triggered a match on the keyword `"SAFETY"`.
5. **Phase 2 Baseline Invariance & Test Suites (Audits F & G):**  
   All 7 Phase 2 ML model artifact hashes and thresholds remain **100% intact**. All **98 test cases** across chunking, ingestion, and ML regression suites passed with zero failures.

---

## 2. Baseline and Environmental Verification

Before performing audit analysis, the runtime and repository baselines were verified:

| Baseline Verification Item | Authoritative Expected Value | Actual Verified Value | Status |
| :--- | :--- | :--- | :---: |
| **Repository Path** | `D:\Desktop\FInal year project\manumind-ai` | `D:\Desktop\FInal year project\manumind-ai` | **MATCH** |
| **Active Branch** | `main` | `main` | **MATCH** |
| **Commit HEAD** | `e5e686939e1830b64191dcbd327b2b7bf35a0793` | `e5e686939e1830b64191dcbd327b2b7bf35a0793` | **MATCH** |
| **Remote Tracking Sync** | `origin/main` (`0 0`) | Synchronized (`0 0`) | **MATCH** |
| **Git Status** | 1 tracked modification (`.gitignore`), untracked Phase 3 files | 0 staged, 1 modified (`.gitignore`), untracked clean | **MATCH** |
| **Virtualenv Isolation** | `.venv-rag/` ignored in `.gitignore:10` | Confirmed ignored | **MATCH** |
| **RAG Lockfile Integrity** | `backend/requirements-rag.lock` (104 packages) | 104 packages, SHA-256: `778FDE7658...` | **MATCH** |
| **Corpus Manifest Integrity** | 418 documents in `corpus_manifest.json` | 418/418 files match SHA-256 & byte sizes | **MATCH** |
| **Phase 2 ML Models (7/7)** | Authoritative hashes in `ml/models_store/` | All 7 hashes match baseline 100% | **MATCH** |
| **Calibrated Thresholds** | $\tau_{\text{IF}} = 0.0269$, $\tau_{\text{LSTM}} = 0.901464$ | Both thresholds match 100% | **MATCH** |

---

## 3. Critical Audit A — Machine-Level Incident Count Discrepancy

### 3.1 The Contradiction in the Step 3 Completion Report
In [`reports/phase3/phase3_step3_chunking_report.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase3/phase3_step3_chunking_report.md), Table 3.2 reported:

| Machine ID | Machine Type / Designation | Reported SOP Chunks | Reported Incident Chunks | Reported Total Chunks |
| :--- | :--- | :---: | :---: | :---: |
| `M101` | Industrial Machine Fleet Asset | 4 | 42 | **46** |
| `M102` | Industrial Machine Fleet Asset | 4 | 49 | **53** |
| `M103` | Industrial Machine Fleet Asset | 4 | 43 | **47** |
| `M104` | Industrial Machine Fleet Asset | 4 | 42 | **46** |
| `M105` | Industrial Machine Fleet Asset | 4 | 53 | **57** |
| `M106` | Industrial Machine Fleet Asset | 4 | 46 | **50** |
| `M107` | Industrial Machine Fleet Asset | 4 | 35 | **39** |
| `M108` | Industrial Machine Fleet Asset | 4 | 55 | **59** |
| `M109` | Industrial Machine Fleet Asset | 4 | 56 | **60** |
| `M110` | Industrial Machine Fleet Asset | 4 | 49 | **53** |
| **Total** | | **40** | **470** | **510** |

This total of **470 incident chunks** contradicted the 400 incident documents and the 400 incident chunks claimed in Section 1 and Table 3.1 of the very same report.

### 3.2 Independent Inspection of Actual Chunk Records
The auditor directly queried the in-memory chunk records generated by [`ChunkingService`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/chunking_service.py):
- **Total Chunks Generated:** 564
- **Chunks with `category == 'INCIDENT'`:** Exactly **400**
- **Unique `document_id` values among incidents:** Exactly **400**
- **Unique `source_record_id` values (`ROW-0001` to `ROW-0400`):** Exactly **400**
- **Multi-chunk incidents:** **0** (every incident document maps to exactly 1 chunk)
- **Content Mismatches against Source Ingestion Records:** **0**

### 3.3 Root-Cause Analysis of the Discrepancy
The auditor inspected [`backend/app/rag/chunking_report.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/chunking_report.py#L183-L187) and identified the defect in `ChunkingReportGenerator._build_markdown()`:

```python
# Lines 183-186 in chunking_report.py:
for mid in sorted([k for k in m.chunks_per_machine.keys() if k != "None"]):
    sop_c = m.chunks_per_category.get("SOP", 0) // 10  # approximate
    total_c = m.chunks_per_machine[mid]
    lines.append(f"| `{mid}` | Industrial Machine Fleet Asset | {total_c - (total_c - 4 if total_c > 4 else 0)} | {total_c - 4 if total_c > 4 else 0} | **{total_c}** |")
```

**The Defect Mechanism:**
1. The developer hardcoded `total_c - 4` to estimate incident chunks, assuming each machine had exactly 4 SOP chunks (`total_c - (total_c - 4) = 4`).
2. In reality, each of the 10 SOP documents generated **11 SOP chunks** (10 SOPs $\times$ 11 = 110 SOP chunks).
3. Therefore:
   $$\text{Reported Incidents} = \text{Total Chunks} - 4 = (\text{Actual Incidents} + 11) - 4 = \text{Actual Incidents} + 7$$
4. Across the 10 fleet machines ($10 \times 7 = 70$), the report artificially inflated the reported incident count from **400 to 470**!

### 3.4 Authoritative Machine-Level Chunk Distribution Reconciliation
When calculated from the actual chunk records and metadata, the reconciliation is 100% exact:

| Machine ID | Actual SOP Chunks | Actual Incident Chunks | Actual Total Machine Chunks | Authoritative Corpus Incidents | Discrepancy / Delta |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `M101` | **11** | **35** | 46 | 35 | **0** |
| `M102` | **11** | **42** | 53 | 42 | **0** |
| `M103` | **11** | **36** | 47 | 36 | **0** |
| `M104` | **11** | **35** | 46 | 35 | **0** |
| `M105` | **11** | **46** | 57 | 46 | **0** |
| `M106` | **11** | **39** | 50 | 39 | **0** |
| `M107` | **11** | **28** | 39 | 28 | **0** |
| `M108` | **11** | **48** | 59 | 48 | **0** |
| `M109` | **11** | **49** | 60 | 49 | **0** |
| `M110` | **11** | **42** | 53 | 42 | **0** |
| *Subtotal Fleet* | **110** | **400** | **510** | **400** | **0** |
| *Unassigned (Safety/TS)* | **15** (Safety) + **39** (TS) | — | **54** | — | **0** |
| **Total Corpus** | **164** | **400** | **564** | **400** | **0** |

**Conclusion for Audit A:**  
The underlying data and chunk generation are **completely sound**. The incident count discrepancy is purely a presentation-layer reporting template bug in `_build_markdown()`.

---

## 4. Critical Audit B — Token-Count Distribution and Chunk-Size Claims

### 4.1 Independent Calculation of Token Statistics
From all **564 generated chunk records**, the auditor independently computed the complete statistical distribution:

| Metric | Overall Corpus (564 chunks) | INCIDENT (400 chunks) | SOP (110 chunks) | TROUBLESHOOTING (39 chunks) | SAFETY (15 chunks) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Mean** | 400.16 | 484.98 | 192.04 | 206.00 | 169.47 |
| **Median** | 481.00 | 483.00 | 207.00 | 186.00 | 165.00 |
| **Minimum** | 61 | 473 | 61 | 81 | 80 |
| **Maximum** | 532 | 532 | 302 | 442 | 336 |
| **25th Percentile** | 271 | 480 | 114 | 115 | 106 |
| **75th Percentile** | 487 | 490 | 265 | 264 | 185 |
| **90th Percentile** | 492 | 493 | 270 | 426 | 306 |
| **95th Percentile** | 494 | 496 | 288 | 438 | 306 |
| **99th Percentile** | 500 | 501 | 302 | 442 | 336 |

### 4.2 Chunk-Size Range Bucket Breakdown

| Size Bucket | Count | Percentage | Primary Constituent Categories |
| :--- | :---: | :---: | :--- |
| **$< 150$ tokens** | 51 | 9.04% | SOP (30 chunks), Troubleshooting (15 chunks), Safety (6 chunks) |
| **$< 300$ tokens** | 155 | 27.48% | SOP (108 chunks), Troubleshooting (34 chunks), Safety (13 chunks) |
| **$300 \le t \le 400$ tokens** | 4 | 0.71% | SOP (2 chunks), Safety (2 chunks) |
| **$401 \le t \le 450$ tokens** | 5 | 0.89% | Troubleshooting (5 chunks) |
| **$> 450$ tokens** | 400 | 70.92% | **INCIDENT (400 chunks — 100% of incidents)** |
| **$> 512$ tokens** | 1 | 0.18% | `INC-0381_chk000` (532 tokens) |
| **$> 256$ tokens** | 453 | 80.32% | Incidents (400), SOPs (38), Troubleshooting (12), Safety (3) |

### 4.3 Analysis of the Chunk-Size Claims
1. **Procedural Documents Strictly Obey Bounds:**  
   Across all 164 procedural chunks (SOP, Troubleshooting, Safety), **0 chunks exceed 450 tokens** (max is 442 in Troubleshooting).
2. **The Atomic Incident Trade-off:**  
   The Step 3 specification explicitly mandated:
   > *"Maintain atomic 1-to-1 incident chunking for all 400 maintenance incidents, preserving source record IDs, CSV row indices, machine IDs, dates, issues, actions, outcomes, and synthetic provenance."*
   
   Because incident records contain complete administrative metadata, diagnostic logs, and provenance banners, their full body text averages ~485 tokens under the heuristic. Consequently, 100% of incident chunks exceed the 450-token soft bound.
3. **Investigation of the Oversized Chunk (`INC-0381_chk000`):**  
   - Token count: **532 tokens**.
   - Content: High-Speed Spindle Center `M104` bearing replacement with borescopic audit notes, replacement of SKF 7014 ceramic bearing, application of Klüber Isoflex grease, and a 4-hour run-in test.
   - Cause: Extensive punctuation (hyphens, asterisks, parentheses, backticks) each counted as 1 token under the heuristic.

### 4.4 Tokenizer Limitation Analysis
- **The Heuristic Strategy (`deterministic_subword_heuristic_v1`):**  
  Uses regex pattern `\w+|[^\w\s]`. Alphanumeric words with length $\le 4$ count as 1 token; words with length $> 4$ count as $\lceil \text{length} / 4 \rceil$; every punctuation mark counts as 1 token.
- **Inclusions:**  
  Heading context prefixes (`## Parent > Subheading`) and overlap paragraphs are included in the token count. Front matter is excluded.
- **Distinction from Model Tokenizer:**  
  This heuristic was implemented to avoid downloading model weights during Step 3. It has **no trained vocabulary relationship** to `BAAI/bge-small-en-v1.5` (which uses a WordPiece/BERT-based tokenizer).
- **Risk Assessment:**  
  `BAAI/bge-small-en-v1.5` has a hard context limit of **512 tokens**. While WordPiece tokenization typically merges punctuation and subwords more efficiently than the heuristic, any chunk whose actual BGE token count exceeds 512 would be silently truncated upon embedding in Step 4.  
  *Audit Recommendation:* A dedicated tokenizer calibration check must be conducted at the start of Step 4 once model weights are available.

---

## 5. Critical Audit C — Source-Text Coverage and Preservation

1. **Front Matter Separation:**  
   YAML front matter is parsed into typed Pydantic metadata (`DocumentMetadata`) and intentionally excluded from the chunk content to eliminate redundant metadata overhead and prompt pollution.
2. **Body Text Coverage:**  
   100% of the non-front-matter source markdown content is represented in the chunk set. No paragraphs, lists, or table rows were omitted.
3. **Heading Hierarchy Context:**  
   Subsections retain parent context prepended as `## Parent Heading > Subheading\n\n`. This ensures semantic self-sufficiency upon isolated vector retrieval.
4. **Table Preservation:**  
   All Markdown telemetry and inspection tables remain contiguous blocks.
5. **Specification Placeholders (`[SPEC_REQUIRED:...]`):**  
   All **123 placeholders** across all 18 technical procedure documents (reconciled in Step 2.1.1) are preserved **100% verbatim** across 41 chunks.
6. **Maintenance Incident Lineage:**  
   All 400 incident chunks preserve `ROW-XXXX` identifiers, CSV row indices, machine IDs, timestamps, and verbatim symptom/action text.

---

## 6. Critical Audit D — Safety Classification Accuracy

### 6.1 The Safety Tagging Implementation
In [`backend/app/rag/metadata_enricher.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/metadata_enricher.py#L53-L58):
```python
is_safety = (
    doc.document_type == "SAFETY"
    or split_res.is_safety_related
    or has_placeholder
    or any(kw in upper_content for kw in self.config.SAFETY_KEYWORDS)
)
```
Where `SAFETY_KEYWORDS` includes: `"SAFETY"`, `"DANGER"`, `"WARNING"`, `"CAUTION"`, `"HAZARD"`, `"LOTO"`, `"LOCKOUT"`, `"TAGOUT"`, `"ISOLATION"`, `"DEPRESSURIZATION"`, `"DE-ENERGIZATION"`, `"PPE"`, `"ELECTRICAL"`, `"HYDRAULIC"`, `"ARC-FLASH"`, `"SPEC_REQUIRED"`.

### 6.2 Cause of the 516 / 564 Count
- **Safety Documents:** 15 / 15 chunks (100%)
- **SOP Documents:** 80 / 110 chunks (72.7%)
- **Troubleshooting Documents:** 21 / 39 chunks (53.8%)
- **Maintenance Incidents:** 400 / 400 chunks (100%)
- **Total:** **516 chunks**

**The Mechanism of Overclassification:**  
Every single synthetic maintenance incident document begins with the standardized academic disclaimer:
```markdown
> **SAFETY NOTICE: SYNTHETIC DEMONSTRATION MATERIAL — DERIVED FROM SYNTHETIC MAINTENANCE LOGS. NOT AN APPROVED OPERATIONAL PROCEDURE.**
```
Because the word `"SAFETY"` is in `SAFETY_KEYWORDS`, `any(kw in upper_content for kw in self.config.SAFETY_KEYWORDS)` evaluated to `True` for **all 400 incident chunks**!

### 6.3 Audit Finding: Semantic Overclassification
While this behavior is mathematically deterministic and caused zero content corruption, it represents **semantic overclassification**:
- 91.5% of the knowledge base is marked as `is_safety_related = True`.
- The metadata flag currently reflects the presence of the synthetic academic disclaimer rather than actual industrial hazardous energy (LOTO/PPE) content.
- *Audit Recommendation:* Refine the safety classifier in Step 4 to scan only the document body below the disclaimer banner.

---

## 7. Critical Audit E — Chunk Identity, Metadata, and Determinism

| Audit Check | Requirement | Actual Status | Evidence |
| :--- | :--- | :---: | :--- |
| **Unique Chunk IDs** | Exactly 564 unique IDs | **PASS** | `len(set(chunk_ids)) == 564` |
| **Deterministic Format** | `{doc_id}_chk{idx:03d}` | **PASS** | Validated across 100% of chunks |
| **Continuous Indexing** | Zero-based, no gaps | **PASS** | 0 index continuity errors |
| **Hash Separation** | `raw_file_hash` vs `content_hash` | **PASS** | Raw file SHA-256 vs normalized content SHA-256 kept strictly separated |
| **Duplicate Template Isolation** | Distinct identities for M101/M102 SOPs | **PASS** | `DOC-SOP-M101-001_chk000` and `DOC-SOP-M102-001_chk000` have unique IDs and metadata |
| **Incident Lineage** | `source_record_id`, `row_index`, `event_date` | **PASS** | Attached to all 400 incident chunks |

---

## 8. Critical Audit F — Test and Regression Verification

The auditor independently ran all test suites in their respective environments:

```
======================================================================
TEST EXECUTION VERIFICATION SUMMARY:

1. RAG Chunking Suite (backend/tests/test_rag_chunking.py):
   Command: .\.venv-rag\Scripts\python.exe -m unittest -v backend.tests.test_rag_chunking
   Environment: .venv-rag (Python 3.11.9)
   Result: Ran 24 tests in 3.133s -> 24 PASSED, 0 FAILED, 0 ERRORS

2. RAG Ingestion Suite (backend/tests/test_rag_ingestion.py):
   Command: .\.venv-rag\Scripts\python.exe -m unittest -v backend.tests.test_rag_ingestion
   Environment: .venv-rag (Python 3.11.9)
   Result: Ran 18 tests in 3.094s -> 18 PASSED, 0 FAILED, 0 ERRORS

3. Phase 2 ML Regression Suites (PyTest):
   Command: python -m pytest backend/tests/test_isolation_forest.py backend/tests/test_resnet_defect_classifier.py
   Environment: Base Python 3.11.9
   Result: 21 passed in 86.43s

   Command: python -m pytest backend/tests/test_lstm_autoencoder.py
   Environment: Base Python 3.11.9
   Result: 10 passed in 41.57s

   Command: python -m pytest backend/tests/test_inference_service.py
   Environment: Base Python 3.11.9
   Result: 25 passed in 51.91s

Total Tests Verified: 98 PASSED (100% Pass Rate, 0 Regressions)
======================================================================
```

---

## 9. Critical Audit G — Scope and Baseline Preservation

1. **Embedding & Model Assets:** Zero embedding weights downloaded, zero vector indexes created, zero ChromaDB collections populated.
2. **Corpus & Manifest:** Zero modifications to the 418 Markdown files or `knowledge_base/corpus_manifest.json`.
3. **Phase 2 Models & Thresholds:**
   - All 7 ML model artifact hashes in `ml/models_store/` verified unchanged.
   - $\tau_{\text{IF}} = 0.0269$ and $\tau_{\text{LSTM}} = 0.901464$ verified unchanged.
4. **Git State:**
   - Current commit remains `e5e686939e1830b64191dcbd327b2b7bf35a0793`.
   - Zero files staged, committed, or pushed.

---

## 10. Classified Audit Findings

| ID | Severity | Category | Description | Recommendation |
| :---: | :---: | :--- | :--- | :--- |
| **FINDING-01** | **Medium** | Reporting Defect | In [`backend/app/rag/chunking_report.py`](file:///D:/Desktop/FInal year project/manumind-ai/backend/app/rag/chunking_report.py#L186), a hardcoded subtraction (`total_c - 4`) caused Table 3.2 of the Step 3 report to display 470 incident chunks instead of 400. Actual chunk records contain exactly 400. | Update the reporting script in a subsequent milestone to partition machine chunks by actual metadata categories rather than hardcoded subtraction. |
| **FINDING-02** | **Low** | Soft Bound Excursion | All 400 atomic incident chunks range from 473 to 532 tokens under the heuristic (mean: 484.98), exceeding the 450-token soft bound. Chunk `INC-0381_chk000` reached 532 tokens. | Verify actual token counts with the official `BAAI/bge-small-en-v1.5` tokenizer in Step 4. If actual BGE tokens exceed 512, implement selective section splitting. |
| **FINDING-03** | **Medium** | Metadata Precision | The synthetic disclaimer banner (`> **SAFETY NOTICE:...`) triggers keyword matching on `"SAFETY"`, causing 100% of incident chunks and 91.5% of corpus chunks to be marked `is_safety_related = True`. | Refine the safety enrichment logic in Step 4 to scan body text excluding the academic disclaimer banner. |
| **FINDING-04** | **Informational** | Tokenizer Approximation | Token counts are provisional estimates from `deterministic_subword_heuristic_v1` because embedding model weights were strictly not downloaded during Step 3. | Conduct an official tokenizer verification benchmark at the start of Phase 3 Step 4. |

---

## 11. Closure Recommendation

**Phase 3 Step 3 is recommended for formal closure under `PASS WITH LIMITATIONS`.**

The underlying chunk generation, schemas, continuous indexing, 1-to-1 incident isolation (400 chunks), placeholder preservation (123 placeholders), and test suites (98/98 passing) are completely verified and mathematically reproducible. The four classified findings are non-blocking and represent presentation/metadata refinements that can be addressed cleanly in Phase 3 Step 4 without re-architecting the chunking engine.

**Strict Stop Condition:** Progression to Phase 3 Step 4 remains strictly halted awaiting user authorization.
(no newline at end of file)