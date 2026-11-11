# ManuMind AI — Phase 3 Step 5: Retrieval and Search Pipeline Implementation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Department:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Baseline HEAD:** `e5e686939e1830b64191dcbd327b2b7bf35a0793`  
**Milestone:** Phase 3 Step 5 — Retrieval and Search Pipeline Implementation  
**Role:** Senior RAG Architect, Information Retrieval Engineer, Vector Database Engineer, and QA Auditor  
**Date:** November 11, 2026  
**Implementation Verdict:** **PASS — STEP 5 IMPLEMENTATION COMPLETE**  

---

## 1. Executive Summary

This report documents the architectural design, implementation details, and verification of the semantic retrieval and search pipeline for ManuMind AI (Phase 3 Step 5). 

The retrieval pipeline transforms natural-language manufacturing queries into dense semantic vector representations using the official `BAAI/bge-small-en-v1.5` model (commit `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`) under strict CPU-only execution, queries the persistent ChromaDB collection (`manumind_bge_small_v1`), applies deterministic metadata filtering, derives cosine similarity scores ($1.0 - \text{distance}$), and resolves complete physical source provenance for every returned result.

All components have been implemented modularly in `backend/app/rag/`, adhering strictly to Pydantic v2 schemas, type hints, and industrial fault-tolerance standards.

---

## 2. Pipeline Architecture & Module Design

The retrieval architecture consists of five core components operating in a deterministic sequence:

```
[Raw User / Agent Query]
           │
           ▼
┌──────────────────────────────────────────────┐
│       1. Query Processor                     │
│  • Whitespace & Unicode Normalization        │
│  • Fleet Machine ID Extraction (M101-M110)   │
│  • Conflicting Machine Detection             │
│  • BGE Retrieval Instruction Prepending      │
└──────────────────────┬───────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐       ┌─────────────────────────────────────┐
│ 2. Dense Embedder│       │ 3. Metadata Filter Compiler         │
│  • BGE-small-en  │       │  • Machine Isolation (M101..M110)   │
│  • 384-dim CPU   │       │  • Plant-Wide Global Fallback (NONE)│
│  • Unit-Norm L2  │       │  • ChromaDB $and / $in / $eq Syntax │
└────────┬─────────┘       └──────────────────┬──────────────────┘
         │                                    │
         └─────────────┬──────────────────────┘
                       ▼
┌──────────────────────────────────────────────┐
│       4. ChromaDB Vector Store Query         │
│  • Persistent Collection: manumind_bge_small │
│  • Space: Cosine Distance                    │
│  • Top-K Selection with Diversification      │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│       5. Score Derivation & Provenance       │
│  • Score = 1.0 - Cosine Distance             │
│  • Physical File Existence Verification      │
│  • SHA-256 Hash Integrity Format Validation  │
│  • CSV Lineage & Row Index 1-400 Mapping     │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
           [Ranked RetrievalResponse]
```

### 2.1 File & Module Inventory

| File Path | Component | Responsibility |
| :--- | :--- | :--- |
| `backend/app/rag/retrieval_schemas.py` | Data Contracts | Pydantic v2 schemas for queries, filters, result items, responses, and execution modes. |
| `backend/app/rag/retrieval_config.py` | Configuration | Configurable thresholds, fleet machine identifiers, valid categories, and BGE instruction prefixes. |
| `backend/app/rag/query_processor.py` | Query Normalization | Cleans input strings, extracts target machine assets (`M101`–`M110`), and formats BGE input strings. |
| `backend/app/rag/metadata_filter.py` | Filter Compiler | Translates high-level retrieval criteria into ChromaDB `$and`, `$in`, `$eq` boolean dictionary structures. |
| `backend/app/rag/source_resolver.py` | Provenance Auditor | Validates physical disk presence, SHA-256 digests, and maintenance CSV row index boundaries (1–400). |
| `backend/app/rag/retrieval_service.py` | Service Orchestrator | Coordinates embedding inference, vector search, score derivation, latency tracking, and specialized endpoints. |
| `backend/app/rag/vector_store.py` | Vector Storage Extension | Provides `search()` method supporting dense 384-dimensional query vectors and metadata filters. |
| `backend/app/rag/__init__.py` | Package Exports | Exposes clean, discoverable retrieval classes and singletons. |

---

## 3. Detailed Component Implementations

### 3.1 Data Schemas (`retrieval_schemas.py`)

All interfaces utilize Pydantic v2 models with strict field validation:
- **`RetrievalMode`**: Enumeration of operational scopes (`machine_specific`, `cross_machine`, `global_only`).
- **`RetrievalFilter`**: High-level filtering parameters including `machine_id`, `category` (validated against `{'SOP', 'TROUBLESHOOTING', 'SAFETY', 'INCIDENT'}`), `is_safety_related`, `is_synthetic`, `source_type`, `document_id`, and `source_record_id`.
- **`RetrievalQuery`**: Request container with query string validation (minimum 2 characters, maximum 2000 characters) and clamped `top_k` (between 1 and 20).
- **`RetrievalResultItem`**: Individual ranked item containing text content, rank, cosine distance, derived similarity score, parent chunk/document lineage, section headings, and verified provenance flags.
- **`RetrievalResponse`**: Top-level response detailing execution mode, returned count, latency metrics (embedding, vector search, provenance resolution, total), and collection metadata.

### 3.2 Industrial Query Processor (`query_processor.py`)

Industrial queries require normalization while strictly preserving critical engineering symbols:
- **Whitespace Normalization**: Collapses excessive internal tabs and spaces without altering symbols or numbers.
- **Fleet Asset Extraction**: Utilizes regex pattern `\b(M10[1-9]|M110)\b` (case-insensitive) to discover CNC milling fleet machine identifiers.
- **Conflict Handling**: When multiple machines are detected in a single query (e.g., *"Compare M101 and M105"*), the query processor marks `has_conflicting_machines=True` and sets `extracted_machine_id=None` to prevent erroneous single-machine isolation.
- **BGE Query Prefix**: Automatically prepends the official BGE query instruction:
  `"Represent this sentence for searching relevant passages: "`

### 3.3 Deterministic Metadata Filter Compiler (`metadata_filter.py`)

ChromaDB requires specific boolean structure syntax (`$and`, `$in`, `$eq`):
- **Machine-Specific Isolation**: When targeting asset `M104` with `include_global=True` (default), compiles to:
  `{"machine_id": {"$in": ["M104", "NONE"]}}`
  This guarantees that results strictly contain M104 procedures or plant-wide global guidelines (such as Bearing Wear or Electrical Safety), while rigorously excluding documents belonging to other machines (`M101`, `M102`, etc.).
- **Strict Isolation**: When `include_global=False`, compiles to:
  `{"machine_id": "M104"}`
- **Global-Only Mode**: Restricts search strictly to plant-wide manuals:
  `{"machine_id": "NONE"}`
- **Multi-Condition Aggregation**: When category, safety, or document filters are combined, conditions are cleanly assembled into a ChromaDB `{"$and": [...]}` structure. Single conditions are unwrapped to bare dictionaries.

### 3.4 Provenance & Physical Auditability Resolver (`source_resolver.py`)

In critical manufacturing environments, hallucinated citations or ungrounded chunks represent severe operational risks:
- **Disk Verification**: Resolves `source_path` against `BASE_DIR` and `KNOWLEDGE_BASE_DIR` to confirm that the underlying Markdown document or CSV exists on disk.
- **Hash Integrity Format**: Validates that `raw_file_hash` and `content_hash` are exact 64-character hexadecimal SHA-256 strings.
- **Incident Lineage Validation**: For `INCIDENT` category records, confirms:
  1. `source_record_id` matches canonical format (`ROW-XXXX`).
  2. `original_row_index` is strictly an integer within `[1, 400]`.
  3. `machine_id` is present and valid.

### 3.5 End-to-End Retrieval Orchestrator (`retrieval_service.py`)

`RetrievalService` coordinates the full lifecycle:
1. **Lazy Model Initialization**: Initialises `BGEEmbeddingModel` on demand, ensuring zero startup penalty when the service is imported for configuration or testing.
2. **Dense CPU Embedding**: Calls `embed_single(query, normalize=True)` to produce a unit-normalized 384-dimensional vector.
3. **Score Derivation**: In ChromaDB's cosine distance space with unit vectors, raw distance is $d = 1 - \cos(\theta)$. Derived similarity is strictly calculated as:
   $$\text{Similarity Score} = 1.0 - d$$
   bounded within $[0.0, 1.0]$.
4. **Document Diversification**: When `diversify_documents=True`, limits the number of segments retrieved from any single document to `DEFAULT_MAX_SEGMENTS_PER_DOC` (default: 2), ensuring diverse cross-document context.
5. **Specialized High-Level APIs**:
   - `retrieve_machine_specific(query, machine_id, top_k)`
   - `retrieve_cross_machine(query, top_k, category)`
   - `retrieve_safety_procedures(query, top_k)`
   - `retrieve_historical_incidents(query, machine_id, top_k)`

---

## 4. Verification & Testing

The retrieval implementation was validated across four comprehensive test suites comprising 46 test cases:

| Test Suite | File Path | Tests | Passing | Failures | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Metadata Filter Tests** | `backend/tests/test_rag_metadata_filter.py` | 14 | 14 | 0 | PASS |
| **Source Resolver Tests** | `backend/tests/test_rag_source_resolver.py` | 9 | 9 | 0 | PASS |
| **Retrieval Service Tests** | `backend/tests/test_rag_retrieval.py` | 14 | 14 | 0 | PASS |
| **Golden Query Evaluation** | `backend/tests/test_rag_retrieval_evaluation.py` | 9 | 9 | 0 | PASS |
| **Total Step 5 Suite** | **All 4 Test Suites** | **46** | **46** | **0** | **PASS** |

### Execution Command & Runtime
```powershell
.\.venv-rag\Scripts\python.exe -m unittest backend/tests/test_rag_metadata_filter.py backend/tests/test_rag_source_resolver.py backend/tests/test_rag_retrieval.py backend/tests/test_rag_retrieval_evaluation.py
```
- **Total Tests Executed:** 46
- **Total Execution Time:** 3.873 seconds
- **Pass Rate:** 100.0%

---

## 5. Scope Boundary Compliance

| Scope Item | Permitted | Actual Implementation | Status |
| :--- | :--- | :--- | :--- |
| **Vector Search Pipeline** | Authorized | Implemented in `backend/app/rag/` | COMPLIANT |
| **Pydantic v2 Schemas** | Authorized | Implemented in `retrieval_schemas.py` | COMPLIANT |
| **Dense CPU Embedding** | Authorized | BGE-small-en-v1.5 on CPU | COMPLIANT |
| **Metadata Filtering** | Authorized | ChromaDB `$and`, `$in`, `$eq` compiled | COMPLIANT |
| **Source Provenance Check**| Authorized | Physical disk and hash checks | COMPLIANT |
| **Golden Evaluation Fixture**| Authorized | 36 queries in `fixtures/` | COMPLIANT |
| **LLM Answer Generation** | Prohibited | Zero LLM prompts or completions | STRICTLY ENFORCED |
| **LangGraph / Agents** | Prohibited | Zero agent graphs or supervisory logic | STRICTLY ENFORCED |
| **FastAPI Endpoints** | Prohibited | Zero HTTP routes or API exposures | STRICTLY ENFORCED |
| **Corpus / Index Mutation**| Prohibited | Read-only access to 564 Chroma records| STRICTLY ENFORCED |
| **Git Staging / Commits** | Prohibited | Zero files staged or committed | STRICTLY ENFORCED |

---

## 6. Conclusion

Phase 3 Step 5 (Retrieval and Search Pipeline) has been successfully implemented with complete modular separation, industrial rigor, and full test verification. The system is ready for formal evaluation and audit closure.
