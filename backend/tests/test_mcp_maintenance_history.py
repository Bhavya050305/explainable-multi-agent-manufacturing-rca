"""
ManuMind AI — MCP Maintenance History Tool Unit & Subprocess Integration Tests
Phase 4 Step 4: Read-Only Maintenance History MCP Tool (Tool 4)

Department of AI & Data Science — RMK Engineering College
"""

import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from backend.app.mcp_server.schemas import (
    GetMaintenanceHistoryResponse,
    MaintenanceRecordItem,
)
from backend.app.mcp_server.server import (
    SERVER_NAME,
    SERVER_VERSION,
    create_mcp_server,
)
from backend.app.mcp_server.tools import handle_get_maintenance_history

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ===========================================================================
# Fixtures and Helpers
# ===========================================================================

def get_db_counts():
    """Returns row counts of relevant tables to verify immutability."""
    db_path = REPO_ROOT / "manumind.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    machines = cur.execute("SELECT COUNT(*) FROM machines").fetchone()[0]
    readings = cur.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
    maintenance = cur.execute("SELECT COUNT(*) FROM maintenance_history").fetchone()[0]
    alerts = cur.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    tickets = cur.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    conn.close()
    return {
        "machines": machines,
        "readings": readings,
        "maintenance": maintenance,
        "alerts": alerts,
        "tickets": tickets,
    }


# ===========================================================================
# 1. Input Validation Tests
# ===========================================================================

def test_tool4_valid_machine_ids():
    """Verify acceptance of valid machine identifiers (M101 to M110)."""
    for mid in [f"M10{i}" for i in range(1, 10)] + ["M110"]:
        res = handle_get_maintenance_history(machine_id=mid, limit=1)
        assert res["status"] == "SUCCESS"
        assert res["machine_id"] == mid
        assert len(res["records"]) == 1


def test_tool4_invalid_machine_ids():
    """Verify rejection of invalid machine identifiers."""
    invalid_ids = ["M100", "M111", "M999", "m101", "M1", "M1010", "MACHINE_01"]
    for bad_id in invalid_ids:
        with pytest.raises(ValueError, match="Invalid machine_id"):
            handle_get_maintenance_history(machine_id=bad_id)


def test_tool4_blank_and_injection_machine_ids():
    """Verify rejection of blank, whitespace, and injection-like identifiers."""
    injection_payloads = [
        "",
        "   ",
        "M101; DROP TABLE machines;--",
        "M101' OR '1'='1",
        "M101\x00",
        "../../etc/passwd",
        None,
        101,
        ["M101"],
    ]
    for bad in injection_payloads:
        with pytest.raises(ValueError):
            handle_get_maintenance_history(machine_id=bad)


def test_tool4_limit_boundaries():
    """Verify limit boundaries: default (100), min (1), max (500)."""
    # Default limit
    res_default = handle_get_maintenance_history(machine_id="M101")
    assert res_default["status"] == "SUCCESS"
    assert res_default["total_returned"] == 35  # M101 has 35 total records (< 100)

    # Minimum limit (1)
    res_min = handle_get_maintenance_history(machine_id="M101", limit=1)
    assert res_min["status"] == "SUCCESS"
    assert res_min["total_returned"] == 1
    assert len(res_min["records"]) == 1

    # Custom limit (10)
    res_custom = handle_get_maintenance_history(machine_id="M101", limit=10)
    assert res_custom["total_returned"] == 10
    assert len(res_custom["records"]) == 10

    # Maximum limit (500)
    res_max = handle_get_maintenance_history(machine_id="M101", limit=500)
    assert res_max["total_returned"] == 35


def test_tool4_invalid_limits():
    """Verify rejection of out-of-range, non-integer, or boolean limits."""
    # Out of range
    with pytest.raises(ValueError, match="Invalid limit"):
        handle_get_maintenance_history(machine_id="M101", limit=0)

    with pytest.raises(ValueError, match="Invalid limit"):
        handle_get_maintenance_history(machine_id="M101", limit=-5)

    with pytest.raises(ValueError, match="Invalid limit"):
        handle_get_maintenance_history(machine_id="M101", limit=501)

    with pytest.raises(ValueError, match="Invalid limit"):
        handle_get_maintenance_history(machine_id="M101", limit=1000)

    # Boolean limits (must not be treated as int 1/0)
    with pytest.raises(ValueError, match="boolean"):
        handle_get_maintenance_history(machine_id="M101", limit=True)

    with pytest.raises(ValueError, match="boolean"):
        handle_get_maintenance_history(machine_id="M101", limit=False)

    # Non-integer types
    with pytest.raises(ValueError, match="Invalid limit"):
        handle_get_maintenance_history(machine_id="M101", limit="10")

    with pytest.raises(ValueError, match="Invalid limit"):
        handle_get_maintenance_history(machine_id="M101", limit=10.5)


# ===========================================================================
# 2. Retrieval Behavior & Ordering Tests
# ===========================================================================

def test_tool4_chronological_ordering_and_tie_breaking():
    """Verify that records are strictly sorted by date ascending, tie-broken by id ascending."""
    res = handle_get_maintenance_history(machine_id="M105", limit=100)
    assert res["status"] == "SUCCESS"
    records = res["records"]
    assert len(records) == 46  # M105 has 46 records

    for i in range(len(records) - 1):
        dt1 = datetime.fromisoformat(records[i]["date"])
        dt2 = datetime.fromisoformat(records[i + 1]["date"])
        assert dt1 <= dt2, f"Chronological violation: {dt1} > {dt2}"
        if dt1 == dt2:
            assert records[i]["id"] < records[i + 1]["id"], "Tie-breaking violation by record id"


def test_tool4_machine_isolation():
    """Verify that returned records strictly belong to the requested machine."""
    target = "M104"
    res = handle_get_maintenance_history(machine_id=target, limit=100)
    assert res["status"] == "SUCCESS"
    for r in res["records"]:
        assert r["machine_id"] == target


def test_tool4_exact_source_field_fidelity():
    """Verify exact preservation of source columns without fabrication or alteration."""
    db_path = REPO_ROOT / "manumind.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    # Fetch first record directly from SQLite
    raw_row = cur.execute(
        "SELECT id, machine_id, date, issue, action, outcome FROM maintenance_history WHERE machine_id = 'M101' ORDER BY date ASC, id ASC LIMIT 1"
    ).fetchone()
    conn.close()

    res = handle_get_maintenance_history(machine_id="M101", limit=1)
    rec = res["records"][0]

    assert rec["id"] == raw_row[0]
    assert rec["machine_id"] == raw_row[1]
    # Date formatting check
    expected_date = raw_row[2].replace(".000000", "").replace(" ", "T")
    assert expected_date in rec["date"]
    assert rec["issue"] == raw_row[3]
    assert rec["action"] == raw_row[4]
    assert rec["outcome"] == raw_row[5]


def test_tool4_outcomes_distribution():
    """Verify that recorded outcomes conform to valid categorical values ('Resolved', 'Monitoring')."""
    res = handle_get_maintenance_history(machine_id="M108", limit=100)
    for r in res["records"]:
        assert r["outcome"] in {"Resolved", "Monitoring", "Temporary Fix"}


def test_tool4_disclaimer_presence():
    """Verify presence of mandatory operational disclaimer preventing unwarranted root cause attribution."""
    res = handle_get_maintenance_history(machine_id="M102", limit=5)
    assert "disclaimer" in res
    assert "Historical maintenance records" in res["disclaimer"]
    assert "do not guarantee current physical asset health" in res["disclaimer"]


# ===========================================================================
# 3. Schema Enforcement Tests
# ===========================================================================

def test_tool4_schemas_forbid_extra_fields():
    """Verify that MaintenanceRecordItem and GetMaintenanceHistoryResponse forbid extra undeclared keys."""
    valid_record = {
        "id": 100,
        "machine_id": "M101",
        "date": "2026-01-01T10:00:00",
        "issue": "Spindle bearing vibration",
        "action": "Greased bearing",
        "outcome": "Resolved",
    }
    rec_obj = MaintenanceRecordItem(**valid_record)
    assert rec_obj.id == 100

    # Extra key rejected
    with pytest.raises(Exception):
        MaintenanceRecordItem(**{**valid_record, "injected_field": "unauthorized"})

    valid_response = {
        "status": "SUCCESS",
        "machine_id": "M101",
        "total_returned": 1,
        "records": [rec_obj],
        "message": "Test message",
        "disclaimer": "Test disclaimer",
    }
    resp_obj = GetMaintenanceHistoryResponse(**valid_response)
    assert resp_obj.status == "SUCCESS"

    with pytest.raises(Exception):
        GetMaintenanceHistoryResponse(**{**valid_response, "injected_field": "unauthorized"})


# ===========================================================================
# 4. Database Safety and Immutability Tests
# ===========================================================================

def test_tool4_database_immutability():
    """Verify that invoking get_maintenance_history performs zero database writes."""
    pre_counts = get_db_counts()

    # Execute multiple queries across different machines and limits
    handle_get_maintenance_history(machine_id="M101", limit=10)
    handle_get_maintenance_history(machine_id="M105", limit=50)
    handle_get_maintenance_history(machine_id="M110", limit=1)

    post_counts = get_db_counts()

    assert pre_counts == post_counts, f"Database counts modified! Pre: {pre_counts}, Post: {post_counts}"
    assert post_counts["machines"] == 10
    assert post_counts["readings"] == 40000
    assert post_counts["maintenance"] == 400
    assert post_counts["alerts"] == 5
    assert post_counts["tickets"] == 1


# ===========================================================================
# 5. MCP Server Registration Tests
# ===========================================================================

def test_mcp_server_registers_all_six_tools():
    """
    Verify that create_mcp_server registers exactly 6 tools:
    1. ping
    2. get_machine_data
    3. detect_anomaly
    4. predict_failure_risk
    5. search_manuals
    6. get_maintenance_history
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

    # Inspect get_maintenance_history tool metadata
    tool = server._tool_manager.get_tool("get_maintenance_history")
    assert tool is not None
    assert tool.name == "get_maintenance_history"
    assert "maintenance" in tool.description.lower()
    assert "chronological" in tool.description.lower()


# ===========================================================================
# 6. Real Subprocess MCP Client/Server Stdio Integration Test
# ===========================================================================

@pytest.mark.asyncio
async def test_mcp_server_real_stdio_maintenance_history_lifecycle():
    """
    Mandatory end-to-end real subprocess lifecycle verification:
    1. Spawns MCP server as an independent subprocess over stdio transport.
    2. Connects official MCP SDK stdio_client over standard pipes.
    3. Initializes session via JSON-RPC 2.0 handshake.
    4. Discovers all 6 tools via list_tools().
    5. Invokes 'get_maintenance_history' via JSON-RPC protocol.
    6. Asserts structured response conforms to GetMaintenanceHistoryResponse schema.
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

    with anyio.fail_after(30):
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # 1. MCP Protocol Handshake
                init_result = await session.initialize()
                assert init_result is not None
                assert init_result.server_info.name == SERVER_NAME
                assert init_result.server_info.version == SERVER_VERSION

                # 2. Tool Discovery: Exactly 6 tools
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

                # 3. Call get_maintenance_history via JSON-RPC
                call_res = await session.call_tool(
                    "get_maintenance_history",
                    arguments={"machine_id": "M101", "limit": 3},
                )
                assert call_res is not None
                assert not getattr(call_res, "isError", False)
                assert not getattr(call_res, "is_error", False)
                assert len(call_res.content) >= 1

                # Extract and parse response
                text_content = call_res.content[0].text
                parsed_data = json.loads(text_content) if isinstance(text_content, str) else text_content
                assert parsed_data["status"] == "SUCCESS"
                assert parsed_data["machine_id"] == "M101"
                assert parsed_data["total_returned"] == 3
                assert len(parsed_data["records"]) == 3
                assert parsed_data["records"][0]["machine_id"] == "M101"
                assert "issue" in parsed_data["records"][0]
                assert "action" in parsed_data["records"][0]
                assert "outcome" in parsed_data["records"][0]
