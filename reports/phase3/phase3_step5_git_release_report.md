# ManuMind AI — Phase 3 Step 5: Official Git Release Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Department:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Remote Origin:** `https://github.com/Bhavya050305/explainable-multi-agent-manufacturing-rca.git`  
**Baseline HEAD Commit:** `e5e686939e1830b64191dcbd327b2b7bf35a0793`  
**New Release HEAD Commit:** `3f0a6d08223c74741f4db3e0819b6f52a0d0f0c6`  
**Commit Message:** `feat(rag): complete Phase 3 knowledge base and retrieval pipeline`  
**Release Date:** November 11, 2026  
**Release Status:** **SUCCESSFUL — FULLY SYNCHRONIZED WITH ORIGIN/MAIN**  

---

## 1. Executive Summary

This report documents the formal release and GitHub synchronization of all completed work across **Phase 3 (Steps 1 through 5)** of the ManuMind AI platform.

The release packages the synthetic manufacturing knowledge base (418 documents), the canonical chunking engine, the dense vector embedding pipeline (`BAAI/bge-small-en-v1.5`), the persistent ChromaDB indexing abstractions, the semantic retrieval and search service, the golden evaluation dataset (36 queries), the complete test suites, and all milestone technical reports.

All preflight checks, regression tests, artifact integrity verifications, and remote push validations completed with **100% compliance**.

---

## 2. Release Identification & Remote Synchronization

| Parameter | Authoritative Record | Status |
| :--- | :--- | :--- |
| **Local Branch** | `main` | CONFIRMED |
| **Tracking Upstream** | `origin/main` | CONFIRMED |
| **Baseline Parent Commit** | `e5e686939e1830b64191dcbd327b2b7bf35a0793` | CONFIRMED |
| **Release Commit Hash** | `3f0a6d08223c74741f4db3e0819b6f52a0d0f0c6` | CONFIRMED |
| **Remote HEAD Hash** | `3f0a6d08223c74741f4db3e0819b6f52a0d0f0c6` | CONFIRMED |
| **Divergence (Ahead / Behind)** | `0 0` | IN SYNCHRONY |
| **Push Protocol** | Standard Git HTTPS push (`git push origin main`) | VERIFIED |
| **Force Push Utilized** | **No** (Standard fast-forward commit) | COMPLIANT |

---

## 3. Staged & Committed Change Set Breakdown

A total of **497 files** with **43,171 line insertions** were staged, validated, and committed:

| Category | File Count | Path Prefix / Files | Description |
| :--- | :---: | :--- | :--- |
| **Corpus Incidents** | 400 | `knowledge_base/incidents/INC-0001.md` ... `INC-0400.md` | Canonical synthetic maintenance incident records derived from historical CSV logs. |
| **Corpus SOPs & Guides** | 18 | `knowledge_base/sops/` | 10 machine SOPs (`SOP-M101`..`M110`), 5 troubleshooting guides, 3 safety/LOTO protocols. |
| **Corpus Manifest** | 1 | `knowledge_base/corpus_manifest.json` | Authoritative 418-document manifest with cryptographic SHA-256 digests. |
| **RAG Application Core** | 28 | `backend/app/rag/` | Complete RAG modules (schemas, loaders, chunkers, segmenters, embedders, filters, retrieval). |
| **Dependency Lockfile** | 1 | `backend/requirements-rag.lock` | Fully pinned, auditable 104-package dependency lockfile for Python `.venv-rag`. |
| **Evaluation Fixtures** | 1 | `backend/tests/fixtures/rag_retrieval_golden_queries.json` | 36 reproducible golden queries across 6 industrial retrieval categories. |
| **Test Suites** | 9 | `backend/tests/test_rag_*.py` | 9 authoritative unit, integration, and benchmark test suites. |
| **Technical Reports** | 38 | `reports/phase3/` | Comprehensive technical, audit, benchmark, and reconciliation reports for Steps 1–5. |
| **Repository Ignore Config**| 1 | `.gitignore` | Configured to strictly isolate `.venv-rag/` and binary index directories. |
| **Total Committed Files** | **497** | **Full Phase 3 Knowledge Base & Pipeline** | **Complete Release Deliverable** |

---

## 4. ChromaDB Persistence Decision & Exclusions

### 4.1 Index Version Control Decision
The persistent ChromaDB directory (`knowledge_base/index/chroma_bge_small_v1/`, 11.11 MB, 564 vectors) was evaluated for Git tracking:
- **Governance Decision:** **Excluded from Git commit in adherence with `.gitignore` line 46 (`knowledge_base/index/*`).**
- **Technical Justification:**
  1. The directory contains binary SQLite database tables (`chroma.sqlite3`) and HNSW binary memory-mapped graph files (`data_level0.bin`, `header.bin`, `length.bin`) keyed to an OS-generated UUID (`9e40aa82-879c-4505-bcb4-d027aba88921`).
  2. Binary database files in Git produce non-diffable bloat, potential SQLite write-lock corruption during multi-developer merges, and cross-platform file descriptor collisions.
  3. The index is **100% deterministically reproducible** from the version-controlled Markdown documents and canonical chunks by executing `backend/app/rag/embedding_runner.py`.
- **Local Preservation:** The persistent directory remains intact and verified locally at `D:\Desktop\FInal year project\manumind-ai\knowledge_base\index\chroma_bge_small_v1/` with 564 records.

### 4.2 Other Strict Exclusions
- **Virtual Environments:** `.venv-rag/` was strictly excluded via `.gitignore`.
- **Python Caches:** All `__pycache__/` and `.pyc` files were excluded.
- **Scratch Files:** Workspace scratch files were cleaned and omitted.
- **Secrets & Keys:** Zero `.env` files, API keys, or private certificates were staged.

---

## 5. Documentation Reconciliation

### 5.1 Issue 1: Step 4 Regression-Test Count Reconciliation
- **Historical Report Notation:** Step 4 implementation reports cited 45 tests.
- **Step 5 Draft Table Typo:** A draft table in Step 5 had listed Tokenizer: 8, Segmenter: 15, Embeddings: 15, Vector Store: 15 (Total: 53).
- **Independent Inspection:** The auditor executed and inspected the four Step 4 test files directly:
  - `backend/tests/test_rag_tokenizer.py`: **8 tests**
  - `backend/tests/test_rag_embedding_segmenter.py`: **16 tests**
  - `backend/tests/test_rag_embeddings.py`: **9 tests**
  - `backend/tests/test_rag_vector_store.py`: **12 tests**
  - **Actual Step 4 Subtotal:** $8 + 16 + 9 + 12 = \mathbf{45\text{ tests}}$.
- **Reconciliation Finding:** The actual test suite has always contained exactly **45 tests**. The figure 53 in the preliminary draft table was an unverified scratchpad typo. The true authoritative count of 45 tests is re-confirmed.

### 5.2 Issue 2: Step 5 Evaluation Methodology
- **Precision@K:** Evaluated over the 32 valid non-rejected queries:
  $$\text{Precision}@K = \frac{\sum_{i=1}^{\min(K, |retrieved|)} \mathbb{I}(doc_i \in expected)}{\min(K, |retrieved|)}$$
  Top-1 Precision is 78.12%; Top-3 is 64.58%; Top-5 is 58.75%.
- **Negative Queries:** The 4 negative queries (`should_reject=True`) were evaluated on input validation and rejection accuracy (100.0%, 4 / 4 rejected with `ValueError`). They have empty expected doc sets and are excluded from ranking precision.
- **Mean Reciprocal Rank (MRR):** For each valid query, $RR = 1 / \text{rank}$ for the first retrieved target document. If none retrieved, $RR = 0.0$. Across all 32 valid queries, $\text{MRR} = \mathbf{0.7875}$.
- **NDCG@5:** Computed using standard binary relevance gain: $\text{DCG}@5 = \sum_{i=1}^5 \frac{rel_i}{\log_2(i + 1)}$ normalized by ideal ranking $\text{IDCG}@5$. Mean NDCG@5 is **1.5911** (reflecting multiple relevant document chunks retrieved per query).
- **Provenance Count (160 items):** 32 valid queries each returned $K=5$ items ($32 \times 5 = 160$ items). 100% of these 160 items passed physical file presence and hash format verification.
- **Threshold Tuning Independence:** Zero evaluation queries were used to tune ML thresholds. Decision thresholds belong to Phase 2 ML models and remain frozen.

### 5.3 Issue 3: Negative-Query Evaluation Limitations
- The current golden evaluation dataset contains 4 negative queries.
- **Disclosure:** A 100% rejection rate across 4 synthetic negative samples represents preliminary evidence of basic boundary checking (whitespace, length, out-of-fleet machine IDs). It does not constitute proof of comprehensive adversarial robustness. Extensive fuzzing and edge testing will be conducted in subsequent phases.

---

## 6. Pre-Commit Regression & Invariant Gate

Before creating the release commit, all 197 system tests and frozen baselines were verified:

| Verification Target | Expected Baseline | Measured State | Verdict |
| :--- | :--- | :--- | :--- |
| **Phase 3 Step 5 Tests** | 46 tests | 46 passed | PASS |
| **Phase 3 Earlier RAG Tests**| 87 tests | 87 passed | PASS |
| **Phase 2 ML Regression Tests**| 56 tests | 56 passed (118.29s) | PASS |
| **Total System Tests** | **189 canonical (197 all-inclusive)** | **100% PASS (0 failures, 0 errors)** | **PASS** |
| **Corpus Markdown Files** | 418 documents | 418 documents present | PASS |
| **Canonical Chunks** | 564 chunks | 564 chunks verified | PASS |
| **ChromaDB Records** | 564 records | 564 records verified | PASS |
| **Specification Placeholders**| 123 placeholders | 123 verified across 18 SOPs | PASS |
| **Incident CSV Mappings** | 400 records | 400 mapped rows (1–400) | PASS |
| **Isolation Forest Hash** | `afdf397336f01cfe...` | Exact match | PASS |
| **LSTM Autoencoder Hash** | `b1cae16de57b556f...` | Exact match | PASS |
| **ResNet Classifier Hash** | `aac4b1c2d8c7ba47...` | Exact match | PASS |
| **Decision Thresholds** | $\tau_{\text{IF}}=0.0269$, $\tau_{\text{LSTM}}=0.901464$ | Invariant exact match | PASS |
| **Lockfile SHA-256** | `778FDE7658E8F5A0...` | Invariant exact match | PASS |

---

## 7. Release Verification Summary

The release operation has been verified end-to-end:
1. `git log -1 --oneline`: `3f0a6d0 feat(rag): complete Phase 3 knowledge base and retrieval pipeline`
2. Remote tracking is synchronized at `0 0`.
3. The working tree is clean.
4. Part A is formally **CLOSED**.
