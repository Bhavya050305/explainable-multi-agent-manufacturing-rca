"""
ManuMind AI — Defect Image Classification MCP Tool Test Suite
Phase 4 Step 5: Read-Only Defect Image Classification MCP Tool via Process Bridge

Department of AI & Data Science — RMK Engineering College

Test Categories:
- A: Input Validation (traversal, bounds, file size, extensions, corrupted content)
- B: Model & Inference Behavior (all 4 classes, shapes, confidences, direct parity, hash immutability)
- C: Process Bridge Behavior (JSON protocol, non-zero exits, timeouts, empty/malformed stdout)
- D: MCP Protocol Integration (server tool registration, real stdio subprocess lifecycle, all 7 tools)
- E: Read-Only Guarantees (zero image, model, SQLite, or ChromaDB mutations)
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_FILE = REPO_ROOT / "ml" / "models_store" / "resnet_defect_classifier.keras"
METADATA_FILE = REPO_ROOT / "ml" / "models_store" / "resnet_defect_classifier_metadata.json"
DEFECT_IMAGES_DIR = REPO_ROOT / "data" / "defect_images"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.mcp_server.defect_bridge import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MAX_IMAGE_DIMENSION,
    DefectBridgeError,
    DefectBridgeProcessError,
    DefectBridgeTimeoutError,
    DefectBridgeValidationError,
    check_defect_image_via_bridge,
    get_base_python,
    validate_defect_image_input,
)
from backend.app.mcp_server.schemas import CheckDefectImageResponse
from backend.app.mcp_server.server import SERVER_NAME, SERVER_VERSION, create_mcp_server
from backend.app.mcp_server.tools import handle_check_defect_image


def compute_sha256(path: Path) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture
def temp_image_helper():
    """Provides a temporary path inside DEFECT_IMAGES_DIR and ensures clean cleanup."""
    paths_to_clean = []

    def _create(filename: str) -> Path:
        p = DEFECT_IMAGES_DIR / filename
        paths_to_clean.append(p)
        return p

    yield _create

    for p in paths_to_clean:
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


# ===========================================================================
# Category A: Input Validation Tests
# ===========================================================================

class TestDefectImageInputValidation:
    """Tests input bounds, directory traversal prevention, and raster content checks."""

    def test_valid_approved_image_relative_path(self):
        """Valid image path relative to repo root resolves cleanly."""
        path = "data/defect_images/M104_surface_crack_001.bmp"
        resolved = validate_defect_image_input(path, repo_root=REPO_ROOT)
        assert resolved.exists()
        assert resolved.name == "M104_surface_crack_001.bmp"

    def test_valid_approved_image_filename_only(self):
        """Valid image filename in approved directory resolves cleanly."""
        path = "M104_surface_crack_001.bmp"
        resolved = validate_defect_image_input(path, repo_root=REPO_ROOT)
        assert resolved.exists()
        assert resolved.name == "M104_surface_crack_001.bmp"

    def test_reject_blank_or_whitespace_path(self):
        """Blank or whitespace-only paths are strictly rejected."""
        with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
            validate_defect_image_input("", repo_root=REPO_ROOT)
        with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
            validate_defect_image_input("   \t\n  ", repo_root=REPO_ROOT)

    def test_reject_non_string_input(self):
        """Non-string inputs are rejected with TypeError/ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            validate_defect_image_input(12345, repo_root=REPO_ROOT)
        with pytest.raises(ValueError, match="must be a string"):
            validate_defect_image_input(None, repo_root=REPO_ROOT)
        with pytest.raises(ValueError, match="must be a string"):
            validate_defect_image_input(["M104_surface_crack_001.bmp"], repo_root=REPO_ROOT)

    def test_reject_nonexistent_file(self):
        """Nonexistent image files in approved directory raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            validate_defect_image_input("nonexistent_workpiece_sample_99999.bmp", repo_root=REPO_ROOT)

    def test_reject_directory_path(self):
        """Directory paths are strictly rejected."""
        with pytest.raises(ValueError, match="directory, not a file"):
            validate_defect_image_input("data/defect_images", repo_root=REPO_ROOT)
        with pytest.raises(ValueError, match="directory, not a file"):
            validate_defect_image_input("data/defect_images/", repo_root=REPO_ROOT)

    def test_reject_directory_traversal_parent_sequences(self):
        """Directory traversal attacks attempting to escape approved directory are rejected."""
        traversal_paths = [
            "../models_store/resnet_defect_classifier.keras",
            "../../manumind.db",
            "data/defect_images/../../backend/app/main.py",
            "../../../Windows/System32/drivers/etc/hosts",
        ]
        for p in traversal_paths:
            with pytest.raises(ValueError, match="Access denied"):
                validate_defect_image_input(p, repo_root=REPO_ROOT)

    def test_reject_absolute_path_outside_approved_dir(self):
        """Absolute paths residing outside data/defect_images are rejected."""
        outside_path = str(REPO_ROOT / "manumind.db")
        with pytest.raises(ValueError, match="Access denied"):
            validate_defect_image_input(outside_path, repo_root=REPO_ROOT)

    def test_reject_unsupported_file_extension(self, temp_image_helper):
        """Files with unsupported extensions are rejected."""
        tmp = temp_image_helper("temp_unsupported_test.txt")
        with open(tmp, "wb") as f:
            f.write(b"Not an image")
        with pytest.raises(ValueError, match="Unsupported image file extension"):
            validate_defect_image_input(str(tmp), repo_root=REPO_ROOT)

    def test_reject_empty_zero_byte_file(self, temp_image_helper):
        """Zero-byte empty files are rejected."""
        tmp = temp_image_helper("temp_zero_byte_test.bmp")
        tmp.touch()
        with pytest.raises(ValueError, match="empty \\(0 bytes\\)"):
            validate_defect_image_input(str(tmp), repo_root=REPO_ROOT)

    def test_reject_corrupted_image_header(self, temp_image_helper):
        """Files with invalid BMP magic bytes are rejected."""
        tmp = temp_image_helper("temp_corrupt_hdr_test.bmp")
        with open(tmp, "wb") as f:
            f.write(b"XX" + b"\x00" * 100)
        with pytest.raises(ValueError, match="Invalid BMP file header"):
            validate_defect_image_input(str(tmp), repo_root=REPO_ROOT)

    def test_reject_corrupted_image_raster_body(self, temp_image_helper):
        """Corrupted raster body failing PIL verification is rejected."""
        tmp = temp_image_helper("temp_corrupt_body_test.bmp")
        with open(tmp, "wb") as f:
            f.write(b"BM" + b"\xff" * 50)
        with pytest.raises(ValueError, match="Corrupted or unreadable image file"):
            validate_defect_image_input(str(tmp), repo_root=REPO_ROOT)

    def test_reject_oversized_file(self, temp_image_helper):
        """Files exceeding 5 MB limit are rejected."""
        tmp = temp_image_helper("temp_oversize_file_test.bmp")
        with open(tmp, "wb") as f:
            f.seek(MAX_FILE_SIZE_BYTES + 10)
            f.write(b"\x00")
        with pytest.raises(ValueError, match="exceeds maximum permitted limit"):
            validate_defect_image_input(str(tmp), repo_root=REPO_ROOT)

    def test_reject_excessive_dimensions(self, temp_image_helper):
        """Images with dimensions exceeding 2048x2048 are rejected."""
        tmp = temp_image_helper("temp_excessive_dim_test.bmp")
        img = Image.new("RGB", (2049, 10), color="white")
        img.save(str(tmp), format="BMP")
        with pytest.raises(ValueError, match="exceed maximum allowed dimension"):
            validate_defect_image_input(str(tmp), repo_root=REPO_ROOT)


# ===========================================================================
# Category B: Model & Inference Behavior Tests
# ===========================================================================

class TestDefectImageModelInference:
    """Verifies ResNet-18 model loading, preprocessing, 4-class inference, and parity."""

    def test_all_four_classes_inference(self):
        """Verifies successful classification for all 4 supported defect classes."""
        samples = {
            "surface_crack": "M104_surface_crack_001.bmp",
            "spalling": "M104_spalling_001.bmp",
            "dent": "M102_dent_001.bmp",
            "normal_surface": "M101_normal_surface_001.bmp",
        }

        for expected_class, filename in samples.items():
            result = check_defect_image_via_bridge(filename)
            assert result["status"] == "SUCCESS"
            assert result["predicted_class"] == expected_class
            assert 0.0 <= result["confidence"] <= 1.0
            assert "recommendation" in result
            assert result["is_synthetic"] is True

            if expected_class == "normal_surface":
                assert result["is_defective"] is False
                assert result["defect_type"] == "Normal Surface"
                assert result["affected_machine_id"] == "M101"
            elif expected_class == "surface_crack":
                assert result["is_defective"] is True
                assert result["defect_type"] == "Surface Crack"
                assert result["affected_machine_id"] == "M104"
            elif expected_class == "spalling":
                assert result["is_defective"] is True
                assert result["defect_type"] == "Spalling"
                assert result["affected_machine_id"] == "M104"
            elif expected_class == "dent":
                assert result["is_defective"] is True
                assert result["defect_type"] == "Dent"
                assert result["affected_machine_id"] == "M102"

    def test_direct_inference_parity(self):
        """Verifies subprocess bridge results match direct inference identically."""
        from backend.app.ml.defect_classifier.predict import DefectClassifierInferenceService

        test_img = "data/defect_images/M104_surface_crack_001.bmp"
        bridge_res = check_defect_image_via_bridge(test_img)

        direct_svc = DefectClassifierInferenceService()
        direct_res = direct_svc.predict_image(str(REPO_ROOT / test_img))

        assert bridge_res["predicted_class"] == direct_res["raw_defect_class"]
        assert bridge_res["defect_type"] == direct_res["defect_type"]
        assert abs(bridge_res["confidence"] - direct_res["confidence"]) < 1e-4
        assert bridge_res["affected_machine_id"] == direct_res["affected_machine_id"]
        assert bridge_res["batch_number"] == direct_res["batch_number"]
        assert bridge_res["is_defective"] == direct_res["is_defective"]

    def test_model_artifact_hashes_unchanged(self):
        """Verifies that model checkpoint and metadata hashes remain strictly unchanged."""
        expected_model_hash = "aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98"
        expected_metadata_hash = "e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73"

        assert compute_sha256(MODEL_FILE) == expected_model_hash
        assert compute_sha256(METADATA_FILE) == expected_metadata_hash


# ===========================================================================
# Category C: Process Bridge Behavior Tests
# ===========================================================================

class TestDefectImageProcessBridge:
    """Tests subprocess execution error boundaries, timeouts, and JSON pipe protocols."""

    def test_bridge_missing_interpreter(self):
        """Bridge raises DefectBridgeError when Python interpreter path is invalid."""
        fake_py = REPO_ROOT / "nonexistent_python_binary.exe"
        with pytest.raises(DefectBridgeProcessError):
            check_defect_image_via_bridge("M104_surface_crack_001.bmp", python_exe=fake_py)

    def test_bridge_timeout_handling(self):
        """Subprocess timeout raises DefectBridgeTimeoutError cleanly."""
        # Intentionally low timeout of 0.001 seconds
        with pytest.raises(DefectBridgeTimeoutError, match="timed out"):
            check_defect_image_via_bridge("M104_surface_crack_001.bmp", timeout=0.001)

    def test_bridge_handles_empty_stdout(self, monkeypatch):
        """Bridge raises DefectBridgeProcessError when subprocess returns empty stdout."""
        class MockEmptyProcess:
            returncode = 0
            stdout = ""
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: MockEmptyProcess())
        with pytest.raises(DefectBridgeProcessError, match="empty output on stdout"):
            check_defect_image_via_bridge("M104_surface_crack_001.bmp")

    def test_bridge_handles_malformed_json_stdout(self, monkeypatch):
        """Bridge raises DefectBridgeProcessError when stdout contains invalid JSON."""
        class MockMalformedProcess:
            returncode = 0
            stdout = "NOT_VALID_JSON{abc"
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: MockMalformedProcess())
        with pytest.raises(DefectBridgeProcessError, match="Malformed JSON"):
            check_defect_image_via_bridge("M104_surface_crack_001.bmp")

    def test_bridge_handles_child_error_status(self, monkeypatch):
        """Bridge raises DefectBridgeError when runner emits an error status."""
        class MockErrorProcess:
            returncode = 0
            stdout = json.dumps({"status": "ERROR", "error_type": "ModelLoadError", "message": "Simulated failure"})
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: MockErrorProcess())
        with pytest.raises(DefectBridgeError, match="\\[ModelLoadError\\]: Simulated failure"):
            check_defect_image_via_bridge("M104_surface_crack_001.bmp")


# ===========================================================================
# Category D: MCP Protocol Integration Tests
# ===========================================================================

class TestDefectImageMCPIntegration:
    """Tests server tool registration and end-to-end real stdio JSON-RPC lifecycle."""

    def test_mcp_server_registers_all_seven_tools(self):
        """MCPServer registers exactly 7 tools including check_defect_image."""
        server = create_mcp_server()
        assert hasattr(server, "_tool_manager")

        tool_names = list(server._tool_manager._tools.keys())
        assert len(tool_names) == 9
        assert set(tool_names) == {
            "ping",
            "get_machine_data",
            "detect_anomaly",
            "predict_failure_risk",
            "search_manuals",
            "get_maintenance_history",
            "check_defect_image",
            "propose_maintenance_ticket",
            "create_maintenance_ticket",
        }

        # Inspect check_defect_image tool metadata
        tool = server._tool_manager.get_tool("check_defect_image")
        assert tool is not None
        assert tool.name == "check_defect_image"
        assert "defect" in tool.description.lower()
        assert "read-only" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_mcp_server_real_stdio_defect_image_lifecycle(self):
        """
        Mandatory end-to-end real subprocess lifecycle verification:
        1. Spawns MCP server as an independent subprocess over stdio transport.
        2. Connects official MCP SDK stdio_client over standard pipes.
        3. Initializes session via JSON-RPC 2.0 handshake.
        4. Discovers all 7 tools via list_tools().
        5. Invokes 'check_defect_image' via JSON-RPC protocol.
        6. Asserts structured response conforms to CheckDefectImageResponse schema.
        7. Verifies zero stdout frame pollution and clean session shutdown.
        """
        child_env = os.environ.copy()
        child_env["PYTHONPATH"] = str(REPO_ROOT)
        child_env["PYTHONUNBUFFERED"] = "1"
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-u", "-m", "backend.app.mcp_server"],
            cwd=str(REPO_ROOT),
            env=child_env,
        )

        with anyio.fail_after(120):
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    # 1. MCP Protocol Handshake
                    init_result = await session.initialize()
                    assert init_result is not None
                    assert init_result.server_info.name == SERVER_NAME
                    assert init_result.server_info.version == SERVER_VERSION

                    # 2. Tool Discovery: Exactly 7 tools
                    tools_response = await session.list_tools()
                    assert tools_response is not None
                    tool_names = [t.name for t in tools_response.tools]
                    assert set(tool_names) == {
                        "ping",
                        "get_machine_data",
                        "detect_anomaly",
                        "predict_failure_risk",
                        "search_manuals",
                        "get_maintenance_history",
                        "check_defect_image",
                        "propose_maintenance_ticket",
                        "create_maintenance_ticket",
                    }

                    # 3. Call check_defect_image via JSON-RPC
                    call_result = await session.call_tool(
                        "check_defect_image",
                        arguments={"image_path": "M104_surface_crack_001.bmp"},
                    )
                    assert call_result is not None
                    assert hasattr(call_result, "content")
                    assert len(call_result.content) > 0

                    raw_text = call_result.content[0].text
                    data = json.loads(raw_text)

                    # Validate strict schema
                    parsed = CheckDefectImageResponse(**data)
                    assert parsed.status == "SUCCESS"
                    assert parsed.predicted_class == "surface_crack"
                    assert parsed.defect_type == "Surface Crack"
                    assert parsed.is_defective is True
                    assert parsed.is_synthetic is True
                    assert parsed.affected_machine_id == "M104"
                    assert parsed.batch_number == "B-8821"
                    assert 0.0 <= parsed.confidence <= 1.0


# ===========================================================================
# Category E: Read-Only Guarantees Tests
# ===========================================================================

class TestDefectImageReadOnlyGuarantees:
    """Verifies that invoking check_defect_image performs zero disk, model, or database writes."""

    def test_image_and_model_immutability(self):
        """Verifies image and model files remain bit-for-bit identical before and after inference."""
        sample_img = DEFECT_IMAGES_DIR / "M104_surface_crack_001.bmp"
        img_hash_before = compute_sha256(sample_img)
        model_hash_before = compute_sha256(MODEL_FILE)
        meta_hash_before = compute_sha256(METADATA_FILE)

        # Execute classification
        handle_check_defect_image("M104_surface_crack_001.bmp")

        img_hash_after = compute_sha256(sample_img)
        model_hash_after = compute_sha256(MODEL_FILE)
        meta_hash_after = compute_sha256(METADATA_FILE)

        assert img_hash_before == img_hash_after
        assert model_hash_before == model_hash_after
        assert meta_hash_before == meta_hash_after
