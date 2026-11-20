"""
ManuMind AI — MCP Manufacturing Tools Unit & Subprocess Integration Tests
Phase 4 Step 2: Read-Only Manufacturing MCP Tools (Tools 1–3)

Department of AI & Data Science — RMK Engineering College
"""

import sys
import os
import re
import math
import sqlite3
import pytest
from datetime import datetime, timedelta
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from backend.app.mcp_server.server import (
    SERVER_NAME,
    SERVER_VERSION,
    create_mcp_server,
)
from backend.app.mcp_server.tools import (
    handle_get_machine_data,
    handle_detect_anomaly,
    handle_predict_failure_risk,
    parse_time_window,
)
from backend.app.ml.inference.config import (
    ISOLATION_FOREST_FROZEN_THRESHOLD,
    LSTM_AUTOENCODER_FROZEN_THRESHOLD,
)


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
    alerts = cur.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    tickets = cur.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    conn.close()
    return {"machines": machines, "readings": readings, "alerts": alerts, "tickets": tickets}


def generate_synthetic_readings(n: int, is_anomaly: bool = False, base_time: datetime = None) -> list:
    """Generates synthetic 5-channel observations for testing."""
    if base_time is None:
        base_time = datetime(2026, 11, 1, 12, 0, 0)
    readings = []
    for i in range(n):
        ts = base_time + timedelta(minutes=5 * i)
        if is_anomaly:
            vib = 12.0 + 0.5 * math.sin(i)
            temp = 95.0 + 1.0 * math.cos(i)
            press = 12.0 + 0.2 * math.sin(i)
            curr = 40.0 + 0.5 * math.cos(i)
            rpm = 2800.0 + 10.0 * math.sin(i)
        else:
            vib = 1.7 + 0.05 * math.sin(i)
            temp = 50.0 + 0.2 * math.cos(i)
            press = 6.0 + 0.02 * math.sin(i)
            curr = 14.5 + 0.1 * math.cos(i)
            rpm = 1800.0 + 2.0 * math.sin(i)

        readings.append({
            "timestamp": ts.isoformat(),
            "vibration": round(vib, 4),
            "temperature": round(temp, 4),
            "pressure": round(press, 4),
            "current": round(curr, 4),
            "rpm": round(rpm, 4),
            "machine_id": "M101",
        })
    return readings


# ===========================================================================
# Tool 1: get_machine_data Tests
# ===========================================================================

def test_tool1_valid_machine_id():
    """Verify get_machine_data retrieves machine profile and telemetry for valid machine ID."""
    pre_counts = get_db_counts()
    res = handle_get_machine_data(machine_id="M101", limit=10)
    post_counts = get_db_counts()

    assert pre_counts == post_counts, "Tool must not write to database"
    assert res["status"] == "SUCCESS"
    assert res["machine_id"] == "M101"
    assert res["machine_profile"] is not None
    assert res["machine_profile"]["id"] == "M101"
    assert "CNC Lathe" in res["machine_profile"]["name"]
    assert len(res["telemetry"]) == 10
    # Verify all 5 channels present in each record
    for rec in res["telemetry"]:
        assert "timestamp" in rec
        assert "vibration" in rec
        assert "temperature" in rec
        assert "pressure" in rec
        assert "current" in rec
        assert "rpm" in rec


def test_tool1_invalid_machine_id():
    """Verify rejection of invalid machine IDs."""
    with pytest.raises(ValueError, match="Invalid machine_id"):
        handle_get_machine_data(machine_id="M999")

    with pytest.raises(ValueError, match="Invalid machine_id"):
        handle_get_machine_data(machine_id="INVALID")

    with pytest.raises(ValueError, match="Invalid machine_id"):
        handle_get_machine_data(machine_id="M101' OR 1=1--")


def test_tool1_valid_time_window_relative():
    """Verify relative duration window filtering ('24h')."""
    res = handle_get_machine_data(machine_id="M101", window="24h", limit=50)
    assert res["status"] == "SUCCESS"
    assert res["window_applied"]["type"] == "relative_duration"
    assert res["window_applied"]["duration"] == "24h"
    assert len(res["telemetry"]) > 0


def test_tool1_valid_time_window_iso_interval():
    """Verify explicit ISO interval filtering."""
    window = "2026-10-25T00:00:00/2026-10-26T00:00:00"
    res = handle_get_machine_data(machine_id="M101", window=window, limit=50)
    assert res["status"] == "SUCCESS"
    assert res["window_applied"]["type"] == "iso_interval"
    assert len(res["telemetry"]) > 0
    for rec in res["telemetry"]:
        assert rec["timestamp"] >= "2026-10-25"
        assert rec["timestamp"] <= "2026-10-26T23:59:59"


def test_tool1_invalid_time_window():
    """Verify rejection of malformed or chronologically inverted time windows."""
    # Inverted: start after end
    with pytest.raises(ValueError, match="must precede end_time"):
        handle_get_machine_data(machine_id="M101", window="2026-10-26T00:00:00/2026-10-25T00:00:00")

    # Malformed format
    with pytest.raises(ValueError, match="Invalid window specification"):
        handle_get_machine_data(machine_id="M101", window="not-a-valid-window")


def test_tool1_limit_boundaries():
    """Verify boundary conditions for limit parameter (min 1, max 500)."""
    # Lower bound
    res1 = handle_get_machine_data(machine_id="M101", limit=1)
    assert res1["status"] == "SUCCESS"
    assert len(res1["telemetry"]) == 1

    # Upper bound
    res500 = handle_get_machine_data(machine_id="M101", limit=500)
    assert res500["status"] == "SUCCESS"
    assert len(res500["telemetry"]) == 500

    # Below minimum
    with pytest.raises(ValueError, match="Invalid limit"):
        handle_get_machine_data(machine_id="M101", limit=0)

    # Above maximum
    with pytest.raises(ValueError, match="Invalid limit"):
        handle_get_machine_data(machine_id="M101", limit=501)


def test_tool1_empty_results():
    """Verify structured response when time range produces 0 records."""
    future_window = "2029-01-01T00:00:00/2029-01-02T00:00:00"
    res = handle_get_machine_data(machine_id="M101", window=future_window)
    assert res["status"] == "NO_DATA"
    assert res["telemetry_count"] == 0
    assert res["telemetry"] == []
    assert "No telemetry records matched" in res["message"]


def test_tool1_chronological_ordering():
    """Verify telemetry records are strictly in ascending chronological order."""
    res = handle_get_machine_data(machine_id="M101", limit=100)
    timestamps = [rec["timestamp"] for rec in res["telemetry"]]
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i - 1], f"Out of order at index {i}"


# ===========================================================================
# Tool 2: detect_anomaly Tests
# ===========================================================================

def test_tool2_normal_telemetry():
    """Verify normal telemetry produces NORMAL classification and score below threshold."""
    readings = generate_synthetic_readings(30, is_anomaly=False)
    res = handle_detect_anomaly(machine_id="M101", readings=readings)

    assert res["status"] == "SUCCESS"
    assert res["machine_id"] == "M101"
    assert res["classification"] == "NORMAL"
    assert res["is_anomaly"] is False
    assert res["isolation_forest"] is not None
    assert res["isolation_forest"]["threshold"] == ISOLATION_FOREST_FROZEN_THRESHOLD
    assert res["isolation_forest"]["score"] < ISOLATION_FOREST_FROZEN_THRESHOLD
    assert res["lstm_autoencoder"] is not None
    assert res["lstm_autoencoder"]["threshold"] == LSTM_AUTOENCODER_FROZEN_THRESHOLD
    assert res["lstm_autoencoder"]["reconstruction_error"] < LSTM_AUTOENCODER_FROZEN_THRESHOLD


def test_tool2_anomalous_telemetry():
    """Verify anomalous telemetry produces ANOMALY_DETECTED classification."""
    readings = generate_synthetic_readings(30, is_anomaly=True)
    res = handle_detect_anomaly(machine_id="M101", readings=readings)

    assert res["status"] == "SUCCESS"
    assert res["machine_id"] == "M101"
    assert res["classification"] == "ANOMALY_DETECTED"
    assert res["is_anomaly"] is True
    assert (
        res["isolation_forest"]["is_anomaly"] is True or
        res["lstm_autoencoder"]["is_anomaly"] is True
    )


def test_tool2_invalid_machine_id():
    """Verify rejection of invalid machine IDs."""
    readings = generate_synthetic_readings(5)
    with pytest.raises(ValueError, match="Invalid machine_id"):
        handle_detect_anomaly(machine_id="M999", readings=readings)


def test_tool2_missing_readings_channels():
    """Verify rejection when sensor channels are missing."""
    malformed = [{"vibration": 1.5, "temperature": 50.0}]  # missing pressure, current, rpm
    with pytest.raises(ValueError, match="missing required channel"):
        handle_detect_anomaly(machine_id="M101", readings=malformed)


def test_tool2_insufficient_sequence_length():
    """Verify behavior when fewer than 30 readings are provided (LSTM skipped, IF runs)."""
    short_readings = generate_synthetic_readings(5, is_anomaly=False)
    res = handle_detect_anomaly(machine_id="M101", readings=short_readings)

    assert res["status"] == "SUCCESS"
    assert res["isolation_forest"] is not None
    assert res["lstm_autoencoder"] is None
    assert any("LSTM Autoencoder skipped" in w for w in res["warnings"])


def test_tool2_invalid_timestamps_ordering():
    """Verify rejection when timestamps are out of chronological order."""
    readings = generate_synthetic_readings(5)
    # Swap timestamps to make it non-chronological
    readings[1]["timestamp"], readings[0]["timestamp"] = readings[0]["timestamp"], readings[1]["timestamp"]
    with pytest.raises(ValueError, match="Telemetry sequence out of order"):
        handle_detect_anomaly(machine_id="M101", readings=readings)


def test_tool2_frozen_threshold_preservation():
    """Verify that model thresholds match frozen calibrated invariants exactly."""
    readings = generate_synthetic_readings(30)
    res = handle_detect_anomaly(machine_id="M101", readings=readings)

    assert res["isolation_forest"]["threshold"] == 0.0269
    assert res["lstm_autoencoder"]["threshold"] == 0.901464


def test_tool2_no_database_writes():
    """Verify detect_anomaly produces zero database mutations."""
    pre_counts = get_db_counts()
    readings = generate_synthetic_readings(30)
    handle_detect_anomaly(machine_id="M101", readings=readings)
    post_counts = get_db_counts()

    assert pre_counts == post_counts, "detect_anomaly must not mutate database"


# ===========================================================================
# Tool 3: predict_failure_risk Tests
# ===========================================================================

def test_tool3_valid_machine_id():
    """Verify predict_failure_risk returns deterministic NOT_AVAILABLE capability stub."""
    pre_counts = get_db_counts()
    res = handle_predict_failure_risk(machine_id="M101", horizon_hours=288)
    post_counts = get_db_counts()

    assert pre_counts == post_counts, "predict_failure_risk must not mutate database"
    assert res["status"] == "NOT_AVAILABLE"
    assert res["machine_id"] == "M101"
    assert res["model_available"] is False
    assert res["horizon_hours"] == 288
    assert "Phase 2 Step 5 recorded a formal NO-GO decision" in res["reason"]
    assert "detect_anomaly" in res["recommendation"]
    assert "disclaimer" in res


def test_tool3_invalid_machine_id():
    """Verify rejection of invalid machine IDs."""
    with pytest.raises(ValueError, match="Invalid machine_id"):
        handle_predict_failure_risk(machine_id="M999")


def test_tool3_no_fabricated_predictions():
    """Verify response contains zero fabricated probabilities or percentage fields."""
    res = handle_predict_failure_risk(machine_id="M101")
    forbidden_keys = [
        "failure_probability",
        "risk_percentage",
        "predicted_failure",
        "remaining_useful_life",
        "rul",
        "probability",
    ]
    for key in forbidden_keys:
        assert key not in res, f"Forbidden prediction field '{key}' must not be present in capability stub"


# ===========================================================================
# Real MCP Subprocess Integration Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_mcp_real_stdio_subprocess_manufacturing_tools():
    """
    Subprocess integration test connecting official MCP SDK stdio client
    to verify discovery and execution of all 4 registered tools:
    1. ping
    2. get_machine_data
    3. detect_anomaly
    4. predict_failure_risk
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

                # 2. Tool Discovery: Exactly 4 tools registered
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

                # 3. Call Tool 1 (get_machine_data) via JSON-RPC
                call_res1 = await session.call_tool(
                    "get_machine_data",
                    arguments={"machine_id": "M101", "limit": 5},
                )
                assert call_res1 is not None
                assert not getattr(call_res1, "is_error", False)
                text_out1 = call_res1.content[0].text
                assert "M101" in text_out1
                assert "SUCCESS" in text_out1

                # 4. Call Tool 2 (detect_anomaly) via JSON-RPC
                call_res2 = await session.call_tool(
                    "detect_anomaly",
                    arguments={"machine_id": "M101"},
                )
                assert call_res2 is not None
                assert not getattr(call_res2, "is_error", False)
                text_out2 = call_res2.content[0].text
                assert "M101" in text_out2
                assert ("NORMAL" in text_out2 or "ANOMALY_DETECTED" in text_out2)
                assert "0.0269" in text_out2
                assert "0.901464" in text_out2

                # 5. Call Tool 3 (predict_failure_risk) via JSON-RPC
                call_res3 = await session.call_tool(
                    "predict_failure_risk",
                    arguments={"machine_id": "M101", "horizon_hours": 288},
                )
                assert call_res3 is not None
                assert not getattr(call_res3, "is_error", False)
                text_out3 = call_res3.content[0].text
                assert "NOT_AVAILABLE" in text_out3
                assert "Phase 2 Step 5" in text_out3

                # 6. Call Ping Tool
                call_ping = await session.call_tool(
                    "ping",
                    arguments={"message": "step2_all_tools_ok"},
                )
                assert call_ping is not None
                assert call_ping.content[0].text == "pong: step2_all_tools_ok"
