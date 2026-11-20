"""
ManuMind AI — Subprocess Bridge for RAG Retrieval MCP Tool
Phase 4 Step 3: Read-Only RAG Retrieval MCP Tool Implementation

Department of AI & Data Science — RMK Engineering College

Isolates ChromaDB, PyTorch, Transformers, and HuggingFace dependencies in the
Phase 3 .venv-rag environment from the base Python 3.11 MCP server environment.
Communicates strictly via subprocess stdio JSON pipes.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backend.app.mcp_server.schemas import (
    ManualSearchResult,
    SearchManualsResponse,
)

logger = logging.getLogger("manumind-mcp-server")


class RAGBridgeError(Exception):
    """Base exception for RAG bridge errors."""
    pass


class RAGBridgeTimeoutError(RAGBridgeError):
    """Raised when RAG subprocess execution times out."""
    pass


class RAGBridgeProcessError(RAGBridgeError):
    """Raised when RAG subprocess exits with a non-zero code or invalid output."""
    pass


class RAGBridgeValidationError(RAGBridgeError, ValueError):
    """Raised when query or k input parameters fail validation prior to bridge execution."""
    pass


def get_rag_venv_python() -> Path:
    """
    Locates the Python interpreter in the .venv-rag virtual environment.
    Resolves relative to the repository root directory.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if sys.platform == "win32":
        py_path = repo_root / ".venv-rag" / "Scripts" / "python.exe"
    else:
        py_path = repo_root / ".venv-rag" / "bin" / "python"

    if not py_path.exists():
        raise RAGBridgeError(
            f"The .venv-rag Python interpreter was not found at expected path: {py_path}. "
            "Ensure the Phase 3 RAG environment is configured."
        )
    return py_path


def validate_rag_inputs(query: Any, k: Any) -> Tuple[str, int]:
    """
    Validates search query and top_k parameters according to Phase 4 Step 3 specifications.

    Rules:
    - query must be a string, non-empty, non-whitespace-only.
    - query length must not exceed 500 characters.
    - k must be an integer, 1 <= k <= 20.
    """
    if not isinstance(query, str):
        raise ValueError(f"Query must be a string, got {type(query).__name__}.")

    stripped_query = query.strip()
    if not stripped_query:
        raise ValueError("Query string cannot be empty or whitespace-only.")

    if len(stripped_query) > 500:
        raise ValueError(
            f"Query length ({len(stripped_query)} chars) exceeds maximum allowed length of 500 characters."
        )

    if isinstance(k, bool):
        raise ValueError("Parameter 'k' must be an integer, got bool.")

    if not isinstance(k, int):
        raise ValueError(f"Parameter 'k' must be an integer, got {type(k).__name__}.")

    if k < 1 or k > 20:
        raise ValueError(f"Parameter 'k' must be between 1 and 20, got {k}.")

    return stripped_query, k


def search_manuals_via_bridge(
    query: str,
    k: int = 5,
    timeout: float = 60.0,
    python_exe: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executes read-only manual search against ChromaDB via the isolated .venv-rag subprocess runner.

    Args:
        query: Non-empty search string (max 500 characters).
        k: Top-k ranking count (1 <= k <= 20, default 5).
        timeout: Subprocess execution timeout in seconds (default 60.0).
        python_exe: Optional override for .venv-rag Python interpreter.

    Returns:
        Validated dictionary conforming to SearchManualsResponse schema.

    Raises:
        ValueError: For invalid query or k inputs.
        RAGBridgeTimeoutError: When subprocess execution exceeds timeout.
        RAGBridgeProcessError: When subprocess exits non-zero or produces invalid JSON.
        RAGBridgeError: When RAG retrieval logic returns an error payload.
    """
    cleaned_query, cleaned_k = validate_rag_inputs(query, k)

    venv_python = python_exe or get_rag_venv_python()
    repo_root = Path(__file__).resolve().parent.parent.parent.parent

    payload = json.dumps({"query": cleaned_query, "k": cleaned_k})

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = (
        str(repo_root) + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")
    )
    # Silence third-party telemetry in subprocess
    env["ANONYMIZED_TELEMETRY"] = "False"
    env["CHROMA_TELEMETRY"] = "False"
    env["TOKENIZERS_PARALLELISM"] = "false"

    logger.info(
        f"[RAG-Bridge] Spawning .venv-rag subprocess for query='{cleaned_query[:40]}...' (k={cleaned_k})"
    )

    try:
        proc = subprocess.run(
            [str(venv_python), "-u", "-m", "backend.app.rag.bridge_runner"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(repo_root),
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error(f"[RAG-Bridge] Subprocess timed out after {timeout}s for query='{cleaned_query[:40]}'")
        raise RAGBridgeTimeoutError(
            f"RAG retrieval timed out after {timeout} seconds for query '{cleaned_query[:40]}...'"
        ) from exc
    except Exception as exc:
        logger.error(f"[RAG-Bridge] Failed to execute RAG bridge subprocess: {exc}")
        raise RAGBridgeProcessError(f"Failed to execute RAG bridge subprocess: {exc}") from exc

    # Log child diagnostic stderr to parent's logger without contaminating parent stdout
    if proc.stderr:
        for line in proc.stderr.strip().splitlines():
            logger.debug(f"[RAG-Bridge-Child] {line}")

    if proc.returncode != 0:
        error_msg = proc.stdout.strip() or proc.stderr.strip() or f"Process exited with code {proc.returncode}"
        try:
            err_json = json.loads(proc.stdout)
            error_msg = f"[{err_json.get('error_type', 'Error')}]: {err_json.get('message', 'Unknown error')}"
        except Exception:
            pass
        logger.error(f"[RAG-Bridge] Subprocess returned non-zero exit code ({proc.returncode}): {error_msg}")
        raise RAGBridgeProcessError(f"RAG bridge execution failed: {error_msg}")

    stdout_text = proc.stdout.strip()
    if not stdout_text:
        logger.error("[RAG-Bridge] Subprocess produced empty stdout.")
        raise RAGBridgeProcessError("RAG bridge subprocess returned empty output on stdout.")

    try:
        response_data = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        logger.error(f"[RAG-Bridge] Malformed JSON from bridge runner: {stdout_text[:200]}")
        raise RAGBridgeProcessError(f"Malformed JSON from RAG bridge runner: {exc}") from exc

    if response_data.get("status") == "ERROR":
        err_type = response_data.get("error_type", "UnknownError")
        err_msg = response_data.get("message", "No error message provided")
        raise RAGBridgeError(f"RAG retrieval error [{err_type}]: {err_msg}")

    results_raw = response_data.get("results", [])
    results = [ManualSearchResult(**item) for item in results_raw]

    status = "SUCCESS" if results else "NO_RESULTS"

    response_obj = SearchManualsResponse(
        status=status,
        query=response_data.get("query", cleaned_query),
        requested_k=response_data.get("requested_top_k", cleaned_k),
        returned_count=len(results),
        results=results,
        collection_name=response_data.get("collection_name"),
        embedding_model=response_data.get("embedding_model"),
    )

    return response_obj.model_dump()
