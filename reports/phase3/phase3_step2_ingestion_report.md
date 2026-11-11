# ManuMind AI — Phase 3 Step 2: RAG Document Ingestion Pipeline Report

**Milestone:** Phase 3 Step 2 — RAG Document Ingestion Pipeline  
**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Department:** Department of AI & Data Science, RMK Engineering College  
**Repository:** [`D:/Desktop/FInal year project/manumind-ai`](file:///D:/Desktop/FInal%20year%20project/manumind-ai)  
**Branch:** `main` | **HEAD:** `e5e686939e1830b64191dcbd327b2b7bf35a0793`  
**Execution Timestamp:** `2026-11-11T12:32:40.206238+05:30`  
**Pipeline Mode:** `in_memory_ingestion` | **Duration:** `0.5971 s`  

---

## 1. Executive Summary & Audit Verdict

### Final Milestone Verdict:
# `PASS — INGESTION PIPELINE COMPLETE`

### Pipeline Execution Highlights:
1. **Document Discovery:** Successfully discovered **418** Markdown documents from `knowledge_base/` with zero missing files.
2. **Parsing & Validation:** Successfully parsed YAML front matter and validated metadata for all **418** documents. Total rejected: **0**.
3. **Provenance & Disclosures:** Verified synthetic provenance (`SYNTHETIC_DEMONSTRATION` and `DERIVED_SYNTHETIC`) and confirmed prominent visible synthetic disclaimers on **418/418** documents.
4. **Manifest Reconciliation:** 100% agreement with `knowledge_base/corpus_manifest.json` across file sizes and SHA-256 digests.
5. **Incident Mapping:** Confirmed exact 1-to-1 deterministic alignment of all **400** maintenance incident documents against `data/raw/maintenance_history.csv` rows.
6. **Strict Scope Protection:** Document ingestion and validation performed entirely in memory. Zero embedding downloads, zero vector writes, zero database mutations.

---

## 2. Acceptance Target Verification Matrix

| Metric | Target | Actual Measured | Status |
| :--- | :---: | :---: | :---: |
| Discovered documents | 418 | 418 | PASS |
| Valid documents | 418 | 418 | PASS |
| Rejected documents | 0 | 0 | PASS |
| Duplicate IDs | 0 | 0 | PASS |
| Provenance validations passed | 418 | 418 | PASS |
| Disclaimer validations passed | 418 | 418 | PASS |
| Incident mappings reconciled | 400/400 | 400/400 | PASS |
| Manifest reconciled | 100% | 100% Reconciled | PASS |

---

## 3. Corpus Distribution Breakdown

### 3.1 Document Categories
| Category | Count | Permitted Provenance (`source_type`) | Synthetic Flag |
| :--- | :---: | :--- | :---: |
| Standard Operating Procedures (SOP) | 10 | `SYNTHETIC_DEMONSTRATION` | `true` |
| Troubleshooting Guides | 5 | `SYNTHETIC_DEMONSTRATION` | `true` |
| Safety Demonstration Documents | 3 | `SYNTHETIC_DEMONSTRATION` | `true` |
| Derived Maintenance Incidents | 400 | `DERIVED_SYNTHETIC` | `true` |
| **Total Ingested** | **418** | — | — |

### 3.2 Machine Distribution Across Corpus
| Machine Identifier | SOP Count | Incident Count | Total Associated Documents |
| :--- | :---: | :---: | :---: |
| `M101` | 1 | 35 | 36 |
| `M102` | 1 | 42 | 43 |
| `M103` | 1 | 36 | 37 |
| `M104` | 1 | 35 | 36 |
| `M105` | 1 | 46 | 47 |
| `M106` | 1 | 39 | 40 |
| `M107` | 1 | 28 | 29 |
| `M108` | 1 | 48 | 49 |
| `M109` | 1 | 49 | 50 |
| `M110` | 1 | 42 | 43 |
| *Unassigned / Cross-plant (Safety & Troubleshooting)* | — | — | 0 |

### 3.3 Troubleshooting Fault Categories
| Fault Category | Associated Troubleshooting Guides |
| :--- | :---: |
| `bearing_wear` | 1 |
| `lubrication_failure` | 1 |
| `optical_surface_defects` | 1 |
| `overheating` | 1 |
| `pressure_drop` | 1 |

---

## 4. Manifest and CSV Mapping Audit

### 4.1 Manifest Integrity Audit (`corpus_manifest.json`)
- **Manifest Entries Total:** 418
- **Exact Matches on Disk:** 418
- **Missing on Disk:** 0
- **Untracked Documents:** 0
- **Hash Mismatches:** 0
- **Byte Size Mismatches:** 0
- **Reconciliation Status:** **PASSED — 100% INVARIANT**

### 4.2 Incident Source-Row Mapping Audit (`data/raw/maintenance_history.csv`)
- **Total CSV Rows:** 400
- **Mapped Incident Documents:** 400
- **Mismatched Records:** 0
- **Reconciliation Status:** **PASSED — 100% 1-TO-1 MAPPING**

---

## 5. Content Normalization & Hashing Specification

The document ingestion pipeline implements deterministic content normalization before calculating content SHA-256 hashes:
1. **Line Ending Standardization:** Converts CRLF (`\r\n`) and CR (`\r`) to standard Unix line feeds (`\n`).
2. **Trailing Line Whitespace Stripping:** Removes all trailing space and tab characters from each line.
3. **Document Whitespace Trimming:** Trims leading and trailing newline and space characters from the entire document body.
4. **Hashing Algorithm:** Computes standard 256-bit SHA-256 hex digest on the normalized UTF-8 byte stream.
5. **Content Preservation:** The original raw body content is preserved verbatim in `IngestionRecord.content` separately from the hash representation.

---

## 6. Model Artifact & Baseline Invariance Audit

| Model Artifact | Expected Phase 2 Digest | Verification Status |
| :--- | :--- | :---: |
| `sensor_scaler.joblib` | `f21f0899cd3af4d807e54f98b4627d5512650f08cad35ba17a6cd80268398faf` | **100% MATCH** |
| `isolation_forest.joblib` | `afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2` | **100% MATCH** |
| `isolation_forest_metadata.json` | `bbb05f4447d52c5ae0f4444649e2e59bf5f282aceb1cfd028e6309b86e8ed3d5` | **100% MATCH** |
| `lstm_autoencoder.keras` | `b1cae16de57b556f13b3f96e12a8c451d05f3bdd9887a65172817cd99e30e0b5` | **100% MATCH** |
| `lstm_autoencoder_metadata.json` | `d679e55a2b9935c2e8820d5b117a7c8fc8f84b94cd6565252255168f82fda0c1` | **100% MATCH** |
| `resnet_defect_classifier.keras` | `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98` | **100% MATCH** |
| `resnet_defect_classifier_metadata.json` | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | **100% MATCH** |

- **Isolation Forest Threshold ($\tau_{\text{IF}}$):** `0.0269` (**Preserved**)
- **LSTM Autoencoder Threshold ($\tau_{\text{LSTM}}$):** `0.901464` (**Preserved**)

---

## 7. Deliverables & Git Inventory

### Implemented Files:
1. [`backend/app/rag/__init__.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/__init__.py)
2. [`backend/app/rag/config.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/config.py)
3. [`backend/app/rag/schemas.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/schemas.py)
4. [`backend/app/rag/exceptions.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/exceptions.py)
5. [`backend/app/rag/document_loader.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/document_loader.py)
6. [`backend/app/rag/metadata_parser.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/metadata_parser.py)
7. [`backend/app/rag/provenance_validator.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/provenance_validator.py)
8. [`backend/app/rag/ingestion_service.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/ingestion_service.py)
9. [`backend/app/rag/ingestion_report.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/rag/ingestion_report.py)
10. [`backend/tests/test_rag_ingestion.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_rag_ingestion.py)

---

## 8. Mandatory Stop Condition

**Phase 3 Step 2 implementation, verification, and audit complete.**
- Strict scope boundaries maintained: zero embedding model downloads, zero vector writes, zero ChromaDB collections.
- Ingestion pipeline validated and operating deterministically.
- Progression to Phase 3 Step 3 is strictly stopped awaiting independent review and explicit authorization.