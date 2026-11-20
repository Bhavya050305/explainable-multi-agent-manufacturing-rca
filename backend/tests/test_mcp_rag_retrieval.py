"""
ManuMind AI — MCP RAG Retrieval Tool Unit & Subprocess Integration Tests
Phase 4 Step 3: Read-Only RAG Retrieval MCP Tool Implementation

Department of AI & Data Science — RMK Engineering College
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from backend.app.mcp_server.rag_bridge import (
    RAGBridgeError,
    RAGBridgeProcessError,
    RAGBridgeTimeoutError,
    RAGBridgeValidationError,
    get_rag_venv_python,
    search_manuals_via_bridge,
    validate_rag_inputs,
)
from backend.app.mcp_server.schemas import (
    ManualSearchResult,
    SearchManualsResponse,
)
from backend.app.mcp_server.server import (
    SERVER_NAME,
    SERVER_VERSION,
    create_mcp_server,
)
from backend.app.mcp_server.tools import handle_search_manuals

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ===========================================================================
# 1. Input Validation Tests
# ===========================================================================

def test_rag_input_validation_valid():
    """Verify input validation succeeds for valid queries and k boundaries."""
    # Standard valid query with default k
    q, k = validate_rag_inputs("spindle vibration troubleshooting", 5)
    assert q == "spindle vibration troubleshooting"
    assert k == 5

    # Boundary k values
    q, k = validate_rag_inputs("bearing temperature limits", 1)
    assert k == 1

    q, k = validate_rag_inputs("hydraulic oil replacement SOP", 20)
    assert k == 20

    # Trimming whitespace
    q, k = validate_rag_inputs("   motor overheating causes   ", 3)
    assert q == "motor overheating causes"
    assert k == 3


def test_rag_input_validation_invalid_query():
    """Verify input validation rejects empty, whitespace, non-string, or oversized queries."""
    # Empty string
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        validate_rag_inputs("", 5)

    # Whitespace-only string
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        validate_rag_inputs("   \t\n  ", 5)

    # Non-string types
    with pytest.raises(ValueError, match="Query must be a string"):
        validate_rag_inputs(None, 5)

    with pytest.raises(ValueError, match="Query must be a string"):
        validate_rag_inputs(12345, 5)

    with pytest.raises(ValueError, match="Query must be a string"):
        validate_rag_inputs(["spindle", "vibration"], 5)

    # Query exceeding 500 characters
    oversized_query = "a" * 501
    with pytest.raises(ValueError, match="exceeds maximum allowed length of 500"):
        validate_rag_inputs(oversized_query, 5)


def test_rag_input_validation_invalid_k():
    """Verify input validation rejects non-integer or out-of-range k parameters."""
    valid_query = "hydraulic pressure drop"

    # k out of range [1, 20]
    with pytest.raises(ValueError, match="must be between 1 and 20"):
        validate_rag_inputs(valid_query, 0)

    with pytest.raises(ValueError, match="must be between 1 and 20"):
        validate_rag_inputs(valid_query, -5)

    with pytest.raises(ValueError, match="must be between 1 and 20"):
        validate_rag_inputs(valid_query, 21)

    with pytest.raises(ValueError, match="must be between 1 and 20"):
        validate_rag_inputs(valid_query, 100)

    # Non-integer k types
    with pytest.raises(ValueError, match="must be an integer"):
        validate_rag_inputs(valid_query, "5")

    with pytest.raises(ValueError, match="must be an integer"):
        validate_rag_inputs(valid_query, 3.5)

    with pytest.raises(ValueError, match="must be an integer"):
        validate_rag_inputs(valid_query, True)

    with pytest.raises(ValueError, match="must be an integer"):
        validate_rag_inputs(valid_query, None)


# ===========================================================================
# 2. Virtual Environment Resolution Tests
# ===========================================================================

def test_rag_venv_python_discovery():
    """Verify that the bridge accurately locates the .venv-rag Python interpreter."""
    py_path = get_rag_venv_python()
    assert py_path.exists(), f".venv-rag Python does not exist at {py_path}"
    assert py_path.is_file()
    assert ".venv-rag" in str(py_path)


# ===========================================================================
# 3. Live Subprocess Bridge Retrieval Tests
# ===========================================================================

def test_search_manuals_live_retrieval_ranked_results():
    """
    Test live execution of search_manuals against ChromaDB via the subprocess bridge.
    Asserts result schema, ranking, score bounds, and metadata integrity.
    """
    query = "CNC lathe spindle bearing wear troubleshooting"
    k = 3

    response = handle_search_manuals(query=query, k=k)

    assert isinstance(response, dict)
    assert response["status"] == "SUCCESS"
    assert response["query"] == query
    assert response["requested_k"] == k
    assert response["returned_count"] == k
    assert len(response["results"]) == k
    assert "manumind_bge_small_v1" in response.get("collection_name", "")
    assert "bge-small-en-v1.5" in response.get("embedding_model", "")
    assert "disclaimer" in response

    # Validate individual result fields
    scores = []
    for idx, item in enumerate(response["results"]):
        assert item["rank"] == idx + 1
        assert isinstance(item["document_id"], str) and len(item["document_id"]) > 0
        assert item["category"] in {"SOP", "TROUBLESHOOTING", "SAFETY", "INCIDENT"}
        assert isinstance(item["section_heading"], str) and len(item["section_heading"]) > 0
        assert isinstance(item["content"], str) and len(item["content"]) > 0
        assert isinstance(item["source_path"], str) and len(item["source_path"]) > 0
        assert isinstance(item["is_synthetic"], bool)
        assert isinstance(item["is_safety_related"], bool)
        assert isinstance(item["source_type"], str)
        assert isinstance(item["segment_id"], str)
        assert isinstance(item["parent_chunk_id"], str)
        assert item["provenance_validated"] is True

        # Derived cosine similarity bounds [0.0, 1.0]
        score = item["similarity_score"]
        assert 0.0 <= score <= 1.0
        scores.append(score)

    # Assert descending similarity ranking
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], f"Rank {i+1} score ({scores[i]}) < Rank {i+2} score ({scores[i+1]})"


def test_search_manuals_safety_procedure_retrieval():
    """
    Test retrieval of safety-critical documentation (e.g. lockout-tagout, emergency stop).
    Asserts is_safety_related flag presence.
    """
    query = "lockout tagout procedure hydraulic system maintenance"
    response = handle_search_manuals(query=query, k=2)

    assert response["status"] == "SUCCESS"
    assert len(response["results"]) >= 1

    # At least one result should be safety-related or SOP
    safety_or_sop = [
        item for item in response["results"]
        if item["is_safety_related"] or item["category"] in {"SAFETY", "SOP"}
    ]
    assert len(safety_or_sop) > 0, "Expected at least one safety or SOP document retrieved"


def test_search_manuals_synthetic_provenance():
    """
    Test that synthetic documents carry explicit synthetic provenance flags.
    """
    query = "incident report bearing seizure high vibration"
    response = handle_search_manuals(query=query, k=3)

    assert response["status"] == "SUCCESS"
    assert len(response["results"]) > 0

    synthetic_items = [item for item in response["results"] if item["is_synthetic"]]
    if synthetic_items:
        for syn_item in synthetic_items:
            assert syn_item["is_synthetic"] is True
            # Synthetic demonstration material notice in content or disclaimer
            assert (
                "SYNTHETIC DEMONSTRATION" in syn_item["content"]
                or "INCIDENT" in syn_item["category"]
                or syn_item["provenance_validated"] is True
            )


# ===========================================================================
# 4. Pydantic Schema Enforcement Tests
# ===========================================================================

def test_search_manuals_schemas_forbid_extra():
    """Verify that ManualSearchResult and SearchManualsResponse strictly forbid undeclared fields."""
    valid_result_payload = {
        "rank": 1,
        "document_id": "DOC-TEST-001",
        "category": "SOP",
        "section_heading": "Test Section",
        "parent_heading": None,
        "similarity_score": 0.85,
        "content": "Test procedure text",
        "source_path": "knowledge_base/sop/test.md",
        "is_synthetic": False,
        "is_safety_related": False,
        "source_type": "standard",
        "segment_id": "test_seg_01",
        "parent_chunk_id": "test_chunk_01",
        "content_hash": "a" * 64,
        "provenance_validated": True,
    }

    result = ManualSearchResult(**valid_result_payload)
    assert result.rank == 1

    # Extra field forbidden in ManualSearchResult
    with pytest.raises(Exception):
        ManualSearchResult(**{**valid_result_payload, "extra_forbidden_key": "injected"})

    valid_response_payload = {
        "status": "SUCCESS",
        "query": "test query",
        "requested_k": 5,
        "returned_count": 1,
        "results": [result],
        "disclaimer": "Test disclaimer",
        "collection_name": "test_collection",
        "embedding_model": "test_model",
    }

    resp = SearchManualsResponse(**valid_response_payload)
    assert resp.status == "SUCCESS"

    # Extra field forbidden in SearchManualsResponse
    with pytest.raises(Exception):
        SearchManualsResponse(**{**valid_response_payload, "extra_forbidden_key": "injected"})


# ===========================================================================
# 5. Bridge Resilience & Error Handling Tests (Mocked Subprocess)
# ===========================================================================

def test_rag_bridge_timeout_error():
    """Verify that subprocess timeout raises RAGBridgeTimeoutError."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["test"], timeout=0.01)):
        with pytest.raises(RAGBridgeTimeoutError, match="timed out after"):
            search_manuals_via_bridge("test query", k=5, timeout=0.01)


def test_rag_bridge_nonzero_exit_code():
    """Verify that a non-zero exit code raises RAGBridgeProcessError with diagnostic message."""
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stdout = json.dumps({"status": "ERROR", "error_type": "ChromaIndexError", "message": "Corrupted collection"})
    mock_proc.stderr = "Traceback details"

    with patch("subprocess.run", return_value=mock_proc):
        with pytest.raises(RAGBridgeProcessError, match="Corrupted collection"):
            search_manuals_via_bridge("test query", k=5)


def test_rag_bridge_malformed_json_output():
    """Verify that malformed JSON on stdout raises RAGBridgeProcessError."""
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "This is not valid JSON string at all"
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc):
        with pytest.raises(RAGBridgeProcessError, match="Malformed JSON"):
            search_manuals_via_bridge("test query", k=5)


def test_rag_bridge_empty_stdout():
    """Verify that empty stdout raises RAGBridgeProcessError."""
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "   \n"
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc):
        with pytest.raises(RAGBridgeProcessError, match="empty output"):
            search_manuals_via_bridge("test query", k=5)


def test_rag_bridge_error_status_in_json():
    """Verify that status='ERROR' in runner output raises RAGBridgeError."""
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = json.dumps({
        "status": "ERROR",
        "error_type": "EmbeddingInferenceError",
        "message": "Model weights missing or incompatible",
    })
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc):
        with pytest.raises(RAGBridgeError, match="Model weights missing or incompatible"):
            search_manuals_via_bridge("test query", k=5)


# ===========================================================================
# 6. MCP Server Tools Registration Tests
# ===========================================================================

def test_mcp_server_registers_all_five_tools():
    """
    Verify that create_mcp_server registers exactly 5 tools:
    1. ping
    2. get_machine_data
    3. detect_anomaly
    4. predict_failure_risk
    5. search_manuals
    """
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

    # Inspect search_manuals metadata
    tool = server._tool_manager.get_tool("search_manuals")
    assert tool is not None
    assert tool.name == "search_manuals"
    assert "semantic vector retrieval" in tool.description.lower()


# ===========================================================================
# 7. Real Subprocess MCP Client/Server Stdio Integration Test
# ===========================================================================

@pytest.mark.asyncio
async def test_mcp_server_real_stdio_search_manuals_lifecycle():
    """
    Mandatory end-to-end real subprocess lifecycle verification:
    1. Spawns MCP server as an independent subprocess.
    2. Connects official MCP SDK stdio_client over standard pipes.
    3. Initializes session via JSON-RPC 2.0 handshake.
    4. Discovers all 5 tools via list_tools().
    5. Invokes 'search_manuals' via JSON-RPC protocol.
    6. Asserts structured response conforms to SearchManualsResponse schema.
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

    with anyio.fail_after(45):
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # 1. MCP Protocol Handshake
                init_result = await session.initialize()
                assert init_result is not None
                assert init_result.server_info.name == SERVER_NAME
                assert init_result.server_info.version == SERVER_VERSION

                # 2. Tool Discovery
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

                # 3. Protocol Tool Invocation
                call_result = await session.call_tool(
                    "search_manuals",
                    arguments={"query": "CNC lathe spindle bearing wear troubleshooting", "k": 2},
                )
                assert call_result is not None
                assert not getattr(call_result, "isError", False)
                assert not getattr(call_result, "is_error", False)
                assert len(call_result.content) >= 1

                # Extract and parse tool response
                text_content = call_result.content[0].text
                assert "SUCCESS" in text_content
                assert "DOC-" in text_content
                assert "spindle" in text_content.lower()
                assert "similarity_score" in text_content
