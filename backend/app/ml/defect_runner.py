"""
ManuMind AI — Defect Classifier Subprocess Bridge Runner
Phase 4 Step 5: Read-Only Defect Image Classification MCP Tool Implementation

Department of AI & Data Science — RMK Engineering College

Executed in the Base Python 3.11 environment to isolate TensorFlow/Keras
memory, thread initialization, and C-level logging from the MCP server stdio session.

Communication protocol:
- Input: JSON-serialized request on sys.stdin: {"image_path": "<path>"}
- Output: Single-line JSON-serialized response on sys.stdout.
- Diagnostics: Strictly routed to sys.stderr.
"""

import json
import logging
import os
import sys
import traceback
from pathlib import Path

import tempfile

# Silence TensorFlow C-level info and warning messages
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())

# Configure logging strictly to stderr to prevent stdout protocol frame pollution
logger = logging.getLogger("defect-bridge-runner")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [Defect-Bridge] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def run_classification() -> int:
    """Reads JSON request from stdin, executes DefectClassifierInferenceService, writes JSON response to stdout."""
    try:
        raw_input = sys.stdin.read().strip()
        if not raw_input:
            err_resp = {
                "status": "ERROR",
                "error_type": "EmptyInputError",
                "message": "Empty or missing request payload on stdin.",
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            return 1

        request_data = json.loads(raw_input)
        image_path = request_data.get("image_path")

        if not image_path or not isinstance(image_path, str) or not image_path.strip():
            err_resp = {
                "status": "ERROR",
                "error_type": "ValidationError",
                "message": "image_path must be a non-empty string.",
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            return 1

        image_path_str = str(image_path).strip()
        if not os.path.exists(image_path_str):
            err_resp = {
                "status": "ERROR",
                "error_type": "FileNotFoundError",
                "message": f"Image file not found: {image_path_str}",
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            return 1

        logger.info(f"Executing defect classification for: {os.path.basename(image_path_str)}")

        from backend.app.ml.defect_classifier.predict import DefectClassifierInferenceService

        service = DefectClassifierInferenceService()
        result = service.predict_image(image_input=image_path_str)

        # Normalize relative path for response
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        try:
            rel_path = Path(image_path_str).resolve().relative_to(repo_root).as_posix()
        except Exception:
            rel_path = os.path.basename(image_path_str)

        output = {
            "status": "SUCCESS",
            "image_name": result["image_name"],
            "image_path": rel_path,
            "predicted_class": result["raw_defect_class"],
            "defect_type": result["defect_type"],
            "confidence": float(result["confidence"]),
            "is_defective": bool(result["is_defective"]),
            "affected_machine_id": result.get("affected_machine_id"),
            "batch_number": result.get("batch_number"),
            "recommendation": result["recommendation"],
            "class_probabilities": result.get("class_probabilities", {}),
            "is_synthetic": True,
        }

        sys.stdout.write(json.dumps(output) + "\n")
        sys.stdout.flush()
        return 0

    except Exception as exc:
        logger.error(f"Defect classification bridge exception: {exc}", exc_info=True)
        err_resp = {
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
        sys.stdout.write(json.dumps(err_resp) + "\n")
        sys.stdout.flush()
        return 1


if __name__ == "__main__":
    exit_code = run_classification()
    sys.exit(exit_code)
