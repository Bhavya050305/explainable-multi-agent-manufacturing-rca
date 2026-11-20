# Phase 4 Step 5: Read-Only Defect Image Classification MCP Tool Implementation via Process Bridge

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` | **Baseline HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` (`ahead 0, behind 0`)  
**Previous Milestone:** Phase 4 Step 4.1 — Independent Maintenance History MCP Tool Audit (`APPROVED FOR STEP 5`)  
**Milestone:** Phase 4 Step 5 — Read-Only Defect Image Classification MCP Tool Implementation  
**Execution Date:** 2026-11-16  
**Final Verdict:** **`READY FOR STEP 6`**

---

## 1. Executive Summary

Phase 4 Step 5 has been completed successfully. The read-only visual workpiece defect classification tool **`check_defect_image`** has been implemented, integrated into the active `MCPServer`, and verified across comprehensive unit, process-bridge, real stdio JSON-RPC 2.0 integration, and regression test suites.

With the addition of `check_defect_image`, the ManuMind AI MCP Server now exposes **exactly seven production-oriented tools**:
1. `ping` — Harmless diagnostic echo tool.
2. `get_machine_data` — Asset metadata profile and historical 5-channel sensor telemetry.
3. `detect_anomaly` — Dual-model manufacturing anomaly inference (Isolation Forest & LSTM-Autoencoder).
4. `predict_failure_risk` — Formal capability stub (`NOT_AVAILABLE`).
5. `search_manuals` — Isolated subprocess bridge to ChromaDB RAG vector retrieval in `.venv-rag`.
6. `get_maintenance_history` — Read-only chronological maintenance intervention records from SQLite.
7. `check_defect_image` — Isolated subprocess bridge to Compact ResNet-18 visual defect classifier.

All **25 automated tests** in the dedicated Step 5 suite (`test_mcp_defect_image.py`) passed (100%). Across all five MCP server suites and pre-existing regression suites, all **109 automated tests passed** with zero failures, zero regressions, and zero mutations to database, ChromaDB, or model files.

---

## 2. Initial Architecture Reconnaissance & Model Identity

Prior to implementation, a thorough inspection of the existing Phase 2 visual defect inspection assets was performed:

### 2.1 Model Architecture & Checkpoint
- **Model Checkpoint:** `ml/models_store/resnet_defect_classifier.keras`
- **Model Checkpoint SHA-256:** `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98`
- **Metadata Checkpoint:** `ml/models_store/resnet_defect_classifier_metadata.json`
- **Metadata Checkpoint SHA-256:** `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73`
- **Network Architecture:** Compact ResNet-18
  - Total Parameters: **2,804,708**
  - Trainable Parameters: **2,799,908**
  - Non-Trainable Parameters: **4,800**
  - Stage channel widths: 32 -> 64 -> 128 -> 256
  - Stage residual blocks: [2, 2, 2, 2]
  - Stem filters: 32, Dropout: 0.35, L2 regularization: 1e-4

### 2.2 Input Dimensions & Preprocessing
- **Expected Input Shape:** `(1, 128, 128, 3)`
- **Color Format:** RGB (24-bit raster)
- **Normalization:** Min-max linear scaling: `(array / 127.5) - 1.0` mapping pixel values $[0, 255]$ into $[-1.0, 1.0]$.
- **Image Resampling:** Bilinear interpolation to target resolution $(128, 128)$.

### 2.3 Authoritative Class Mappings & Domain Associations
Audited from `backend/app/ml/defect_classifier/config.py`:

| Class Index | Canonical Label | Display Title | Is Defective | Candidate Machine | Batch Code | Operational Severity |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| `0` | `surface_crack` | Surface Crack | `True` | `M104` | `B-8821` | CRITICAL: Bearing raceway replacement required. Halt production on M104. |
| `1` | `spalling` | Spalling | `True` | `M104` | `B-8821` | HIGH: Roller assembly overhaul recommended on machine M104. |
| `2` | `dent` | Dent | `True` | `M102` | `B-7740` | MEDIUM: Mechanical impact indentation. Calibrate stamping pressure on M102. |
| `3` | `normal_surface` | Normal Surface | `False` | `M101` | `B-9910` | NORMAL: Pristine surface finish meeting QC tolerances. |

### 2.4 Demonstration Dataset Characteristics
- **Authoritative Manifest:** `data/defect_images/defect_manifest.json`
- **Total Workpiece Samples:** Exactly **600 BMP images** (150 per class)
- **Partitioning:** Train: 420 (70%), Validation: 88 (14.67%), Test: 92 (15.33%)
- **Data Provenance:** Synthetic demonstration dataset generated for prototype verification. No real-world industrial metallurgical warranty or defect-free physical guarantee is claimed.

---

## 3. Process Bridge Design & Stream Isolation

### 3.1 Architecture Decision
To preserve complete stream purity on the MCP server's stdio transport, TensorFlow 2.18.0 and Keras 3.6.0 model execution is isolated inside a dedicated subprocess bridge (`backend/app/ml/defect_runner.py` spawned by `backend/app/mcp_server/defect_bridge.py`).

```
+-------------------------------------------------------------+
|               ManuMind AI MCP Server (Base Python)          |
|                                                             |
|   +-------------------+      JSON-RPC 2.0 stdio             |
|   |   MCP Client      |<============================+       |
|   +-------------------+                             |       |
|             |                                       |       |
|             v                                       |       |
|   +-------------------+                             |       |
|   | check_defect_image|                             |       |
|   +-------------------+                             |       |
|             |                                       |       |
|             v                                       |       |
|   +---------------------------------------------+   |       |
|   | defect_bridge.py (Path & Security Validation)|  |       |
|   +---------------------------------------------+   |       |
+-------------|---------------------------------------|-------+
              | stdin: {"image_path": "..."}          | stdout: JSON-RPC
              v                                       | frame ONLY
+-------------------------------------------------+   |
| Subprocess Bridge Runner (defect_runner.py)     |   |
|                                                 |   |
|   1. Reads JSON payload from stdin              |   |
|   2. Runs DefectClassifierInferenceService      |   |
|   3. TensorFlow & C-logs isolated to stderr     |   |
|   4. Writes single-line JSON result to stdout   |---+
|                                                 |
+-------------------------------------------------+
```

### 3.2 Protocol & Stream Isolation Guarantees
1. **Stdout Protection:** Standard output of the bridge runner is exclusively reserved for exactly one single-line JSON payload `{"status": "SUCCESS", ...}`.
2. **Diagnostics strictly to Stderr:** All TensorFlow C++ runtime logging, CUDA warnings, and Python diagnostics are suppressed via `TF_CPP_MIN_LOG_LEVEL=2`, `TF_ENABLE_ONEDNN_OPTS=0`, and custom stderr-only handlers.
3. **Execution Safety:** Subprocess invocation uses `subprocess.run(shell=False)` with an explicit argument vector `[sys.executable, "-u", "-m", "backend.app.ml.defect_runner"]`. No shell interpolation or command injection is possible.
4. **Timeouts & Failure Recovery:** Configured with a default 120.0-second timeout to accommodate cold-start TensorFlow model loading on Windows. Timeouts, non-zero return codes, and malformed JSON payloads are caught and raised as structured, typed exceptions (`DefectBridgeTimeoutError`, `DefectBridgeProcessError`).

---

## 4. Image Input Security & Validation

All image path validation is executed in `backend/app/mcp_server/defect_bridge.py` before any subprocess is spawned:

1. **Path Bound & Confinement:** Image paths must reside strictly within `data/defect_images/`. Relative paths (e.g., `M104_surface_crack_001.bmp` or `data/defect_images/M104_surface_crack_001.bmp`) and absolute paths are normalized and canonicalized via `Path.resolve()`. Any path outside `data/defect_images` raises `ValueError: Access denied`.
2. **Traversal Prevention:** Parent directory tokens (`..`), encoded slashes, and symlinks escaping the approved root directory are strictly rejected.
3. **Entity Type:** Directories and nonexistent files are detected and rejected (`ValueError` for directories, `FileNotFoundError` for nonexistent files).
4. **File Extension Filter:** Permitted extensions are constrained to `ALLOWED_EXTENSIONS = {".bmp", ".png", ".jpg", ".jpeg"}`.
5. **File Size Boundaries:** File size is strictly enforced between 1 byte and 5 MB (`MAX_FILE_SIZE_BYTES = 5,242,880`). Empty files (0 bytes) and oversized files (>5 MB) are rejected before loading.
6. **Raster Integrity & Magic Bytes:**
   - BMP files are verified for leading magic bytes `b"BM"`.
   - Raster content is validated via Pillow `img.verify()` and `img.load()` without altering the file on disk.
7. **Decompression Bomb Defense:** Maximum dimensions are bounded to `2048 x 2048` pixels, and total pixel count is bounded to `MAX_PIXELS = 4,194,304` (`Image.MAX_IMAGE_PIXELS` safety).

---

## 5. Tool Schemas & Confidence Semantics

### 5.1 Strict Response Schema (`extra="forbid"`)
Defined in `backend/app/mcp_server/schemas.py`:

```python
class CheckDefectImageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    image_name: str
    image_path: str
    predicted_class: str
    defect_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_interpretation: str
    is_defective: bool
    affected_machine_id: Optional[str] = None
    batch_number: Optional[str] = None
    recommendation: str
    class_probabilities: Dict[str, float] = Field(default_factory=dict)
    is_synthetic: bool = True
    disclaimer: str
    message: Optional[str] = None
```

### 5.2 Confidence Interpretation & Limitations
The `confidence` output is explicitly documented as a Softmax output float $[0.0, 1.0]$. The response schema enforces:
- `confidence_interpretation`: Explicitly notifies supervisory agents that the score represents model classification likelihood across the 4 synthetic classes, is uncalibrated, and does NOT constitute a mathematical guarantee or physical inspection certification.
- `disclaimer`: Mandatory notice stating visual inspection results are produced by Compact ResNet-18 trained exclusively on synthetic demonstration data (600 BMP images) for supervisory assistance and do NOT replace certified non-destructive testing (NDT).

---

## 6. MCP Server Registration & Tool Set

Tool 7 was registered in `backend/app/mcp_server/server.py` with typed Pydantic annotations:

```python
@server.tool(
    name="check_defect_image",
    description=(
        "Execute read-only visual workpiece surface defect classification using Compact ResNet-18. "
        "Analyzes high-resolution manufacturing workpiece images from data/defect_images/ to diagnose "
        "surface cracks, spalling, impact dents, or nominal surface finishes. "
        "Returns predicted class, Softmax confidence, candidate machine association, and operational "
        "recommendations. Strictly read-only; delegates via isolated subprocess bridge."
    ),
)
def check_defect_image(
    image_path: Annotated[
        str,
        Field(
            min_length=1,
            max_length=500,
            description="Relative or canonical path to workpiece image located in data/defect_images/ (e.g., 'M104_surface_crack_001.bmp')"
        )
    ],
) -> Dict[str, Any]:
    return handle_check_defect_image(image_path=image_path)
```

### Verified Active Tool Inventory (7 Tools)
```
1. ping
2. get_machine_data
3. detect_anomaly
4. predict_failure_risk
5. search_manuals
6. get_maintenance_history
7. check_defect_image
```

---

## 7. Automated Test Results

### 7.1 Dedicated Defect Image Suite (`test_mcp_defect_image.py`)
All **25 tests passed in 132.72s**:

| Test ID | Test Category & Function | Scope | Result |
| :--- | :--- | :--- | :---: |
| `T1` | `TestDefectImageInputValidation::test_valid_approved_image_relative_path` | Approved relative path resolution | **PASSED** |
| `T2` | `TestDefectImageInputValidation::test_valid_approved_image_filename_only` | Approved filename-only resolution | **PASSED** |
| `T3` | `TestDefectImageInputValidation::test_reject_blank_or_whitespace_path` | Blank / whitespace string rejection | **PASSED** |
| `T4` | `TestDefectImageInputValidation::test_reject_non_string_input` | Non-string type boundary rejection | **PASSED** |
| `T5` | `TestDefectImageInputValidation::test_reject_nonexistent_file` | Missing image file rejection | **PASSED** |
| `T6` | `TestDefectImageInputValidation::test_reject_directory_path` | Directory path rejection | **PASSED** |
| `T7` | `TestDefectImageInputValidation::test_reject_directory_traversal_parent_sequences` | Path traversal (`..`) escape prevention | **PASSED** |
| `T8` | `TestDefectImageInputValidation::test_reject_absolute_path_outside_approved_dir` | External absolute path rejection | **PASSED** |
| `T9` | `TestDefectImageInputValidation::test_reject_unsupported_file_extension` | Extension blacklist verification | **PASSED** |
| `T10` | `TestDefectImageInputValidation::test_reject_empty_zero_byte_file` | Zero-byte file rejection | **PASSED** |
| `T11` | `TestDefectImageInputValidation::test_reject_corrupted_image_header` | Invalid BMP magic header rejection | **PASSED** |
| `T12` | `TestDefectImageInputValidation::test_reject_corrupted_image_raster_body` | Corrupted raster body verification | **PASSED** |
| `T13` | `TestDefectImageInputValidation::test_reject_oversized_file` | >5 MB file size boundary rejection | **PASSED** |
| `T14` | `TestDefectImageInputValidation::test_reject_excessive_dimensions` | >2048x2048 dimension rejection | **PASSED** |
| `T15` | `TestDefectImageModelInference::test_all_four_classes_inference` | End-to-end inference across 4 classes | **PASSED** |
| `T16` | `TestDefectImageModelInference::test_direct_inference_parity` | Subprocess bridge vs direct inference parity | **PASSED** |
| `T17` | `TestDefectImageModelInference::test_model_artifact_hashes_unchanged` | ResNet-18 model checkpoint immutability | **PASSED** |
| `T18` | `TestDefectImageProcessBridge::test_bridge_missing_interpreter` | Missing Python executable handling | **PASSED** |
| `T19` | `TestDefectImageProcessBridge::test_bridge_timeout_handling` | Subprocess timeout handling | **PASSED** |
| `T20` | `TestDefectImageProcessBridge::test_bridge_handles_empty_stdout` | Empty stdout process error handling | **PASSED** |
| `T21` | `TestDefectImageProcessBridge::test_bridge_handles_malformed_json_stdout` | Malformed JSON stdout parsing handling | **PASSED** |
| `T22` | `TestDefectImageProcessBridge::test_bridge_handles_child_error_status` | Runner error status propagation | **PASSED** |
| `T23` | `TestDefectImageMCPIntegration::test_mcp_server_registers_all_seven_tools` | Server tool registration & metadata | **PASSED** |
| `T24` | `TestDefectImageMCPIntegration::test_mcp_server_real_stdio_defect_image_lifecycle` | Real stdio subprocess JSON-RPC lifecycle | **PASSED** |
| `T25` | `TestDefectImageReadOnlyGuarantees::test_image_and_model_immutability` | Zero disk / model weight mutation | **PASSED** |

### 7.2 Full Regression Suite Summary (109 Tests Total)

| Suite File | Environment | Tests | Passed | Failed | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `backend/tests/test_mcp_defect_image.py` | Base Python | 25 | 25 | 0 | **PASS** |
| `backend/tests/test_mcp_maintenance_history.py` | Base Python | 14 | 14 | 0 | **PASS** |
| `backend/tests/test_mcp_manufacturing_tools.py` | Base Python | 20 | 20 | 0 | **PASS** |
| `backend/tests/test_mcp_rag_retrieval.py` | Base Python + `.venv-rag` bridge | 15 | 15 | 0 | **PASS** |
| `backend/tests/test_mcp_server_skeleton.py` | Base Python | 4 | 4 | 0 | **PASS** |
| `backend/tests/test_sensor_preprocessing.py` | Base Python | 8 | 8 | 0 | **PASS** |
| `backend/tests/test_rag_source_resolver.py` | `.venv-rag` | 9 | 9 | 0 | **PASS** |
| `backend/tests/test_rag_retrieval.py` | `.venv-rag` | 14 | 14 | 0 | **PASS** |
| **Total Automated Tests** | | **109** | **109** | **0** | **100% PASS** |

---

## 8. Protected Invariants & Integrity Audit

| Invariant Parameter | Expected Baseline | Measured Value | Verification Source | Status |
| :--- | :---: | :---: | :--- | :---: |
| **Machines** | 10 | 10 | SQLite `machines` table | **PASS** |
| **Sensor Readings** | 40,000 | 40,000 | SQLite `sensor_readings` table | **PASS** |
| **Maintenance Records** | 400 | 400 | SQLite `maintenance_history` table | **PASS** |
| **Alerts** | 5 | 5 | SQLite `alerts` table | **PASS** |
| **Tickets** | 1 | 1 | SQLite `tickets` table | **PASS** |
| **ChromaDB Vectors** | 564 | 564 | Collection `manumind_bge_small_v1` | **PASS** |
| **Embedding Dimensions** | 384 | 384 | BAAI/bge-small-en-v1.5 embedding vectors | **PASS** |
| **Source Documents** | 418 | 418 | `corpus_manifest.json` | **PASS** |
| **Canonical Chunks** | 564 | 564 | Ingestion pipeline chunks | **PASS** |
| **Synthetic Placeholders** | 123 | 123 | Synthetic demonstration tags | **PASS** |
| **Isolation Forest Threshold** | 0.0269 | 0.0269 | Frozen model artifact baseline | **PASS** |
| **LSTM Autoencoder Threshold** | 0.901464 | 0.901464 | Frozen model artifact baseline | **PASS** |
| **Defect Image Classes** | 4 | 4 | `surface_crack`, `spalling`, `dent`, `normal_surface` | **PASS** |
| **Defect Image Count** | 600 | 600 | `defect_manifest.json` | **PASS** |
| **RAG Lockfile SHA-256** | `778fde76...` | `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` | Hash comparison | **PASS** |
| **ResNet Model SHA-256** | `aac4b1c2...` | `aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98` | Hash comparison | **PASS** |
| **ResNet Metadata SHA-256** | `e7e95b80...` | `e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73` | Hash comparison | **PASS** |
| **Base Python Health** | Clean | "No broken requirements found." | `pip check` | **PASS** |
| **`.venv-rag` Health** | Clean | "No broken requirements found." | `pip check` | **PASS** |

---

## 9. Git Status & Governance Verification

- **Branch:** `main`
- **Baseline HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` (`ahead 0, behind 0` with `origin/main`)
- **Staged Files:** `0`
- **Tracked Modifications:** `0`
- **Untracked Additions Preserved:**
  - `backend/app/mcp_server/`
  - `backend/app/ml/defect_runner.py`
  - `backend/app/rag/bridge_runner.py`
  - `backend/requirements-mcp.txt`
  - `backend/tests/test_mcp_defect_image.py`
  - `backend/tests/test_mcp_maintenance_history.py`
  - `backend/tests/test_mcp_manufacturing_tools.py`
  - `backend/tests/test_mcp_rag_retrieval.py`
  - `backend/tests/test_mcp_server_skeleton.py`
  - `reports/phase3/phase3_step9_independent_staged_release_audit.*`
  - `reports/phase4/`

---

## 10. Findings & Recommendations

| Finding ID | Severity | Component | Finding Summary | Impact | Action Required |
| :--- | :---: | :--- | :--- | :--- | :--- |
| `FINDING-P4S5-01` | **INFO** | `defect_bridge.py` | TensorFlow CPU cold-start on Windows requires ~35s for initial module import. | Bridge timeout was configured to 120.0s to ensure zero false timeout failures under high CPU loads. | **NO** |
| `FINDING-P4S5-02` | **INFO** | `defect_runner.py` | Matplotlib font cache rebuild was avoided by pre-setting `MPLCONFIGDIR` and `TF_ENABLE_ONEDNN_OPTS=0`. | Subprocess runner executes cleanly without font cache rebuild pauses. | **NO** |
| `FINDING-P4S5-03` | **INFO** | `schemas.py` | `extra="forbid"` is enforced on `CheckDefectImageResponse`. | Schema strictly guards against unexpected model attributes and preserves API contract. | **NO** |

---

## 11. Final Acceptance Criteria Evaluation

- [x] `check_defect_image` is registered on `MCPServer` and discoverable via `list_tools()`.
- [x] Existing Compact ResNet-18 inference service is reused without architectural duplication or retraining.
- [x] Process bridge operates reliably with stdio JSON communication and strict stderr routing.
- [x] Image path validation prevents traversal, symlink escapes, oversized files, and unauthorized access.
- [x] Invalid, missing, and corrupted images fail safely with informative diagnostic messages.
- [x] Model class mapping (4 classes) and normalized input preprocessing ($[-1.0, 1.0]$) are preserved.
- [x] Confidence semantics are documented as uncalibrated Softmax model outputs.
- [x] Zero model weight retraining or artifact modifications occurred.
- [x] Zero image, database, or vector-store mutations occurred.
- [x] All seven MCP tools coexist correctly and remain operational.
- [x] Real stdio subprocess JSON-RPC integration passes end-to-end.
- [x] All 109 automated regression tests pass.
- [x] Protected Phase 1, Phase 2, Phase 3, and Phase 4 invariants remain intact.
- [x] No Git staging, commit, or push operations occurred.

**Final Verdict:** **`READY FOR STEP 6`**
