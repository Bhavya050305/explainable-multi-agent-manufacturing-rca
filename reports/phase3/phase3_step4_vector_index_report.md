# ManuMind AI — Phase 3 Step 4: Persistent ChromaDB Vector Index Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Department:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Milestone:** Phase 3 Step 4 — Embedding Generation and Vector Database Indexing  
**Author:** Senior RAG Architect, Vector Database Engineer, and Quality Auditor  
**Date:** November 11, 2026  
**Status:** COMPLETE / CLOSED — PASS  

---

## 1. Executive Summary

This report documents the implementation, population, persistence verification, and architectural validation of the persistent ChromaDB vector index for ManuMind AI. The vector index stores dense 384-dimensional BGE embeddings paired with rich manufacturing metadata to support future retrieval workflows.

Key achievements include:
1. Creation of persistent collection `manumind_bge_small_v1` configured for **cosine distance** space (`hnsw:space: cosine`).
2. Successful indexing of all **564 embedding segments** with zero drops, zero corruption, and complete metadata lineage.
3. Idempotent upsert logic verified: unchanged segments are detected via SHA-256 content hashes and skipped, preventing duplicate records or index bloat.
4. Persistence confirmed across cold restart: closing and reopening `PersistentClient` verified that all 564 records and their HNSW index files persist intact on disk.
5. All 12 vector store unit tests in `backend/tests/test_rag_vector_store.py` passed with 100% compliance.

---

## 2. Vector Store Configuration & Engine Specification

| Parameter | Specification | Verified Value |
| :--- | :--- | :--- |
| **Engine** | ChromaDB (`chromadb==0.5.23`) | `0.5.23` |
| **Client Type** | `chromadb.PersistentClient` | PersistentClient |
| **Collection Name** | `manumind_bge_small_v1` | `manumind_bge_small_v1` |
| **Persistence Directory** | `knowledge_base/index/chroma_bge_small_v1/` | Verified on disk |
| **Distance Metric** | Cosine Distance | `hnsw:space = "cosine"` |
| **Vector Dimension ($d$)** | 384 | 384 |
| **Telemetry Policy** | Disabled (`anonymized_telemetry=False`) | Enforced (Offline safe) |
| **Idempotency Strategy** | Content Hash Comparison (`content_hash`) | Verified |

---

## 3. Persistent Storage Layout & File Sizes

The persistent index is located at `knowledge_base/index/chroma_bge_small_v1/`. Inspection of the underlying storage hierarchy confirms complete HNSW graph and SQLite metadata persistence:

| File / Subdirectory Path | Size (Bytes) | Size (MB) | Purpose |
| :--- | :--- | :--- | :--- |
| `chroma.sqlite3` | 9,973,760 | 9.51 MB | SQLite metadata, documents, and segment IDs |
| `9e40aa82-879c-4505-bcb4-d027aba88921/` | — | — | HNSW index segment directory |
| `├── data_level0.bin` | 1,676,000 | 1.60 MB | HNSW level-0 graph nodes and dense vectors |
| `├── length.bin` | 4,000 | 0.004 MB | HNSW vector length / norm metadata |
| `├── header.bin` | 100 | < 0.001 MB | HNSW index header and configuration |
| `└── link_lists.bin` | 0 | 0.00 MB | HNSW multi-level link graph |
| **Total Persistent Footprint** | **11,653,860** | **11.11 MB** | Complete persistent vector index |

---

## 4. Index Population & Idempotency Audit

Population of the production collection was executed in batches of 100 records:

| Audit Parameter | Initial Run Metric | Repeated Run Metric | Result |
| :--- | :--- | :--- | :--- |
| **Total Segments Offered** | 564 | 564 | 564 |
| **Newly Inserted Records** | **564** | **0** | Verified Idempotent |
| **Updated Records** | **0** | **0** | Verified |
| **Unchanged Skipped Records** | **0** | **564** | Verified Idempotent |
| **Final Collection Record Count** | **564** | **564** | 100% Consistent |
| **Insertion Time (sec)** | 4.395 s | < 0.250 s | High-throughput |
| **Effective Insertion Rate** | 128.3 records/sec | > 2,000 records/sec | Validated |

---

## 5. Metadata Schema & Lineage Verification

Every indexed record contains complete provenance and technical metadata. Fields with `None` values (such as `machine_id` for plant-wide safety standards) are serialized safely without ChromaDB crashes.

### 5.1 Metadata Schema Fields

| Metadata Field | Type | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `parent_chunk_id` | `str` | `INC-0001_chk000` | ID of canonical parent chunk |
| `document_id` | `str` | `INC-0001` | ID of source corpus document |
| `segment_index` | `int` | `0` | Sequential segment index within parent chunk |
| `segment_count` | `int` | `1` | Total segments generated from parent chunk |
| `token_count_actual` | `int` | `412` | Authoritative BGE subword token count |
| `machine_id` | `str` | `M101` | Target machine identifier (M101-M110 or empty) |
| `source_record_id` | `str` | `MAINT-2026-0001` | Maintenance history incident record ID |
| `original_row_index` | `int` | `0` | Zero-indexed row in `maintenance_history.csv` |
| `event_date` | `str` | `2026-01-04` | Recorded incident or standard date |
| `source_type` | `str` | `DERIVED_SYNTHETIC` | Source provenance category |
| `is_synthetic` | `bool` | `True` | Academic synthetic dataset indicator |
| `category` | `str` | `INCIDENT` | Document category (INCIDENT, SOP, etc.) |
| `section_heading` | `str` | `Incident INC-0001` | Markdown section heading |
| `parent_heading` | `str` | `Maintenance History` | Parent Markdown heading |
| `content_hash` | `str` | `a3b8c9...` | SHA-256 digest of segment text |
| `is_safety_related` | `bool` | `False` | Discriminative safety procedure flag |
| `contains_spec_placeholder` | `bool` | `False` | Indicator of `[SPEC_REQUIRED:...]` presence |
| `chunking_strategy` | `str` | `embedding_segmentation_v1` | Chunking/segmentation strategy |
| `embedding_model` | `str` | `BAAI/bge-small-en-v1.5` | Embedding model identifier |

### 5.2 Category Breakdown in Vector Index

| Category | Indexed Records | Safety-Related Records | Spec Placeholder Records | Machine-Specific Records |
| :--- | :--- | :--- | :--- | :--- |
| **INCIDENT** | 400 | 103 | 0 | 400 (M101-M110) |
| **SOP** | 102 | 71 | 18 | 102 (M101-M110) |
| **TROUBLESHOOTING** | 39 | 17 | 0 | 0 (Plant-wide) |
| **SAFETY** | 23 | 15 | 0 | 0 (Plant-wide) |
| **TOTAL** | **564** | **206** | **18** | **502** |

---

## 6. Cold Restart & Persistence Verification

To ensure that index persistence does not rely on in-memory buffers:
1. `PersistentClient` instance was explicitly deleted and garbage collected.
2. A new `ChromaVectorStore` was instantiated pointing to `knowledge_base/index/chroma_bge_small_v1/`.
3. Collection inspection confirmed:
   - Collection name: `manumind_bge_small_v1`
   - Record count: **564**
   - Metadata retrieval: Random sample of 20 records retrieved with 100% attribute parity.
   - Vector probe: Target vector distance to self = $0.000000$ (exact match).
4. Distance space verified: Cosine distance space configured and functioning.

---

## 7. Unit Test Verification Results

All 12 unit tests in `backend/tests/test_rag_vector_store.py` passed with zero errors:

| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_01_persistent_collection_creation` | Verifies collection creation with cosine distance metric | PASS |
| `test_02_indexing_and_count_verification` | Verifies full batch indexing and collection record count | PASS |
| `test_03_correct_record_ids_and_metadata` | Verifies indexed records contain expected IDs and metadata | PASS |
| `test_04_vector_dimension_validation` | Verifies rejection of vectors with non-384 dimensions | PASS |
| `test_05_idempotent_insertion` | Verifies duplicate insertions skip unchanged records safely | PASS |
| `test_06_changed_content_detection` | Verifies content changes trigger record update | PASS |
| `test_07_persistence_after_reopen` | Verifies data persists when client is closed and reopened | PASS |
| `test_08_metadata_filtering` | Verifies metadata filtering (`category`, `machine_id`) | PASS |
| `test_09_empty_collection_handling` | Verifies safe handling of empty collection operations | PASS |
| `test_10_batch_insertion_ordering` | Verifies batch insertion maintains record IDs and order | PASS |
| `test_11_none_metadata_safety` | Verifies None values in metadata serialize without error | PASS |
| `test_12_isolation_from_production_index` | Verifies test isolation in temporary directory | PASS |

---

## 8. Audit Verdict

**VERDICT: PASS — VECTOR DATABASE INDEXING COMPLETE AND PERSISTENT**

The persistent ChromaDB collection `manumind_bge_small_v1` is fully populated with 564 dense vector representations and verified persistent on disk.
