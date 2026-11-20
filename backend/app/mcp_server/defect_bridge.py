"""
ManuMind AI — Subprocess Bridge for Defect Image Classification MCP Tool
Phase 4 Step 5: Read-Only Defect Image Classification MCP Tool Implementation

Department of AI & Data Science — RMK Engineering College

Isolates TensorFlow 2.18.0 and Keras 3.6.0 model execution inside a dedicated subprocess
to prevent C-level logs, memory footprints, and unhandled native signals from corrupting
the MCP server's stdio JSON-RPC 2.0 protocol stream.
Communicates strictly via subprocess stdio JSON pipes.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PIL import Image

from backend.app.mcp_server.schemas import CheckDefectImageResponse

logger = logging.getLogger("manumind-mcp-server")

# Security and validation bounds
MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
MAX_IMAGE_DIMENSION: int = 2048              # Max 2048x2048 pixels
MAX_PIXELS: int = 4_194_304                  # 2048 * 2048
ALLOWED_EXTENSIONS = {".bmp", ".png", ".jpg", ".jpeg"}


class DefectBridgeError(Exception):
    """Base exception for defect image bridge errors."""
    pass


class DefectBridgeTimeoutError(DefectBridgeError):
    """Raised when defect image subprocess execution times out."""
    pass


class DefectBridgeProcessError(DefectBridgeError):
    """Raised when defect image subprocess exits with a non-zero code or invalid output."""
    pass


class DefectBridgeValidationError(DefectBridgeError, ValueError):
    """Raised when image path or image content fails validation prior to bridge execution."""
    pass


def get_base_python() -> Path:
    """
    Locates the Python interpreter in the current Base Python environment.
    Defaults to sys.executable.
    """
    py_path = Path(sys.executable).resolve()
    if not py_path.exists():
        raise DefectBridgeError(
            f"The Base Python interpreter was not found at expected path: {py_path}."
        )
    return py_path


def validate_defect_image_input(
    image_path: Any,
    repo_root: Optional[Path] = None,
) -> Path:
    """
    Validates image path security, existence, dimensions, and raster content integrity.

    Security Rules:
    1. image_path must be a non-empty string.
    2. Path must resolve strictly inside approved directory 'data/defect_images'.
    3. Directory traversal (..) and symlink-based escapes are strictly rejected.
    4. Directories and nonexistent files are rejected.
    5. File size must be between 1 byte and 5 MB.
    6. Content must be a valid readable image with dimensions <= 2048x2048.
    7. For BMP images, magic bytes 'BM' must match.

    Returns:
        Canonical resolved Path to the verified image file.
    """
    if not isinstance(image_path, str):
        raise ValueError(f"image_path must be a string, got {type(image_path).__name__}.")

    stripped_path = image_path.strip()
    if not stripped_path:
        raise ValueError("image_path string cannot be empty or whitespace-only.")

    if len(stripped_path) > 1000:
        raise ValueError("image_path exceeds maximum length of 1000 characters.")

    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent

    approved_dir = (repo_root / "data" / "defect_images").resolve()
    if not approved_dir.exists():
        raise DefectBridgeError(f"Approved defect images directory not found: {approved_dir}")

    # Determine candidate path
    raw_path = Path(stripped_path)
    normalized_path_str = str(stripped_path).replace("\\", "/").rstrip("/")
    if raw_path.is_absolute():
        candidate = raw_path
    elif normalized_path_str == "data/defect_images" or normalized_path_str.startswith("data/defect_images/"):
        candidate = repo_root / stripped_path
    else:
        candidate = approved_dir / stripped_path

    # Canonicalize and verify containment
    try:
        resolved_candidate = candidate.resolve()
    except Exception as exc:
        raise ValueError(f"Invalid image path structure: {exc}") from exc

    try:
        resolved_candidate.relative_to(approved_dir)
    except ValueError:
        raise ValueError(
            f"Access denied: Path '{image_path}' resolves outside the approved image directory '{approved_dir}'."
        )

    if not resolved_candidate.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if not resolved_candidate.is_file():
        raise ValueError(f"Specified path is a directory, not a file: {image_path}")

    suffix = resolved_candidate.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported image file extension '{suffix}'. Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}"
        )

    # Size bounds check
    file_size = resolved_candidate.stat().st_size
    if file_size == 0:
        raise ValueError(f"Image file is empty (0 bytes): {image_path}")
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"Image file size ({file_size} bytes) exceeds maximum permitted limit of {MAX_FILE_SIZE_BYTES} bytes (5 MB)."
        )

    # Validate image header and raster content
    try:
        with open(resolved_candidate, "rb") as f:
            header = f.read(2)
            if suffix == ".bmp" and header != b"BM":
                raise ValueError(f"Invalid BMP file header in '{image_path}': expected 'BM', got {header!r}.")

        # PIL integrity verification and dimension checks
        with Image.open(resolved_candidate) as img:
            width, height = img.size
            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                raise ValueError(
                    f"Image dimensions ({width}x{height}) exceed maximum allowed dimension of {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}."
                )
            if width * height > MAX_PIXELS:
                raise ValueError(
                    f"Total image pixels ({width * height}) exceed maximum threshold of {MAX_PIXELS}."
                )
            # Verify file integrity without full decompression
            img.verify()

        # Reopen to verify decode works cleanly
        with Image.open(resolved_candidate) as img:
            img.load()

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Corrupted or unreadable image file '{image_path}': {exc}") from exc

    return resolved_candidate


def check_defect_image_via_bridge(
    image_path: str,
    timeout: float = 120.0,
    python_exe: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executes read-only defect image classification via isolated subprocess runner.

    Args:
        image_path: Relative or canonical path to workpiece image inside data/defect_images/.
        timeout: Subprocess execution timeout in seconds (default 120.0).
        python_exe: Optional override for Base Python interpreter.

    Returns:
        Validated dictionary conforming to CheckDefectImageResponse schema.

    Raises:
        ValueError / FileNotFoundError: For invalid image paths, missing files, or corrupted content.
        DefectBridgeTimeoutError: When subprocess execution exceeds timeout.
        DefectBridgeProcessError: When subprocess exits non-zero or produces invalid JSON.
        DefectBridgeError: When classification logic returns an error payload.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    validated_path = validate_defect_image_input(image_path, repo_root=repo_root)

    base_python = python_exe or get_base_python()
    payload = json.dumps({"image_path": str(validated_path)})

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = (
        str(repo_root) + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")
    )
    env["TF_CPP_MIN_LOG_LEVEL"] = "2"
    env["TF_ENABLE_ONEDNN_OPTS"] = "0"
    if "MPLCONFIGDIR" not in env:
        import tempfile
        env["MPLCONFIGDIR"] = tempfile.gettempdir()

    logger.info(
        f"[Defect-Bridge] Spawning classification subprocess for image: '{validated_path.name}'"
    )

    try:
        proc = subprocess.run(
            [str(base_python), "-u", "-m", "backend.app.ml.defect_runner"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(repo_root),
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error(f"[Defect-Bridge] Subprocess timed out after {timeout}s for image '{validated_path.name}'")
        raise DefectBridgeTimeoutError(
            f"Defect image classification timed out after {timeout} seconds for image '{validated_path.name}'."
        ) from exc
    except Exception as exc:
        logger.error(f"[Defect-Bridge] Failed to execute defect bridge subprocess: {exc}")
        raise DefectBridgeProcessError(f"Failed to execute defect bridge subprocess: {exc}") from exc

    # Log child diagnostic stderr to parent's logger without contaminating parent stdout
    if proc.stderr:
        for line in proc.stderr.strip().splitlines():
            logger.debug(f"[Defect-Bridge-Child] {line}")

    if proc.returncode != 0:
        error_msg = proc.stdout.strip() or proc.stderr.strip() or f"Process exited with code {proc.returncode}"
        try:
            err_json = json.loads(proc.stdout)
            error_msg = f"[{err_json.get('error_type', 'Error')}]: {err_json.get('message', 'Unknown error')}"
        except Exception:
            pass
        logger.error(f"[Defect-Bridge] Subprocess returned non-zero exit code ({proc.returncode}): {error_msg}")
        raise DefectBridgeProcessError(f"Defect image classification failed: {error_msg}")

    stdout_text = proc.stdout.strip()
    if not stdout_text:
        logger.error("[Defect-Bridge] Subprocess produced empty stdout.")
        raise DefectBridgeProcessError("Defect image classification subprocess returned empty output on stdout.")

    try:
        response_data = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        logger.error(f"[Defect-Bridge] Malformed JSON from bridge runner: {stdout_text[:200]}")
        raise DefectBridgeProcessError(f"Malformed JSON from defect bridge runner: {exc}") from exc

    if response_data.get("status") == "ERROR":
        err_type = response_data.get("error_type", "UnknownError")
        err_msg = response_data.get("message", "No error message provided")
        raise DefectBridgeError(f"Defect classification error [{err_type}]: {err_msg}")

    response_obj = CheckDefectImageResponse(
        status=response_data["status"],
        image_name=response_data["image_name"],
        image_path=response_data["image_path"],
        predicted_class=response_data["predicted_class"],
        defect_type=response_data["defect_type"],
        confidence=response_data["confidence"],
        is_defective=response_data["is_defective"],
        affected_machine_id=response_data.get("affected_machine_id"),
        batch_number=response_data.get("batch_number"),
        recommendation=response_data["recommendation"],
        class_probabilities=response_data.get("class_probabilities", {}),
        is_synthetic=True,
    )

    return response_obj.model_dump()
