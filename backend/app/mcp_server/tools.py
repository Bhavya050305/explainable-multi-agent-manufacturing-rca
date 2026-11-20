"""
ManuMind AI — Manufacturing MCP Tools Implementation
Phase 4 Step 2: Read-Only Manufacturing MCP Tools (Tools 1–3)

Department of AI & Data Science — RMK Engineering College
"""

import os
import re
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from backend.app.database import get_db
from backend.app.models.machine import Machine
from backend.app.models.sensor_reading import SensorReading
from backend.app.models.maintenance_history import MaintenanceHistory
from backend.app.models.alert import Alert
from backend.app.models.ticket import Ticket
from backend.app.models.ticket_proposal import TicketProposal, ConsumedToken
from backend.app.mcp_server.schemas import (
    GetMachineDataResponse,
    MachineProfile,
    TelemetryRecord,
    DetectAnomalyResponse,
    IsolationForestResult,
    LSTMSAutoencoderResult,
    PredictFailureRiskResponse,
    ManualSearchResult,
    SearchManualsResponse,
    MaintenanceRecordItem,
    GetMaintenanceHistoryResponse,
    CheckDefectImageResponse,
    ProposeMaintenanceTicketResponse,
    CreateMaintenanceTicketResponse,
)

# Canonical 5-channel features in invariant permutation-resistant ordering
CANONICAL_FEATURES: List[str] = [
    "vibration",
    "temperature",
    "pressure",
    "current",
    "rpm",
]

# Frozen Calibrated Model Thresholds (derived in Phase 1 validation, strictly immutable)
ISOLATION_FOREST_FROZEN_THRESHOLD: float = 0.0269
LSTM_AUTOENCODER_FROZEN_THRESHOLD: float = 0.901464

logger = logging.getLogger("manumind-mcp-server")

# Strict regex matching valid machine identifiers (M101 to M110)
MACHINE_ID_PATTERN = re.compile(r"^M1(0[1-9]|10)$")

# Relative window duration pattern (e.g., '1h', '6h', '24h', '7d')
RELATIVE_WINDOW_PATTERN = re.compile(r"^(\d+)([mhd])$", re.IGNORECASE)

# Global lazily-initialized inference service instance
_inference_service: Optional[Any] = None


def get_inference_service():
    """Thread-safe singleton getter for UnifiedInferenceService (lazily loaded)."""
    global _inference_service
    if _inference_service is None:
        logger.info("Lazily loading UnifiedInferenceService for MCP tools...")
        from backend.app.ml.inference.service import UnifiedInferenceService
        _inference_service = UnifiedInferenceService()
    return _inference_service


def parse_time_window(
    window: Optional[str],
    latest_db_time: Optional[datetime]
) -> Tuple[Optional[datetime], Optional[datetime], Dict[str, Any]]:
    """
    Parses and validates time-window specifications.

    Supported formats:
    1. None: Returns full chronological records up to query limit.
    2. ISO interval ('start/end'): e.g. '2026-10-25T00:00:00/2026-10-26T00:00:00'.
       Enforces start <= end.
    3. Relative duration ('1h', '6h', '24h', '7d'):
       Anchored to latest_db_time (or current UTC if database empty).
    """
    if not window or window.strip() == "" or window.lower() == "all":
        return None, None, {
            "type": "unbounded",
            "description": "Latest chronological records up to query limit"
        }

    window = window.strip()

    # 1. ISO 8601 Interval (start/end)
    if "/" in window:
        parts = window.split("/", 1)
        try:
            start_dt = datetime.fromisoformat(parts[0].strip().replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(parts[1].strip().replace("Z", "+00:00"))
        except Exception as exc:
            raise ValueError(
                f"Invalid ISO interval format in window '{window}'. "
                f"Expected 'YYYY-MM-DDTHH:MM:SS/YYYY-MM-DDTHH:MM:SS': {exc}"
            ) from exc

        # Normalize to naive UTC for consistent SQLite querying
        if start_dt.tzinfo is not None:
            start_dt = start_dt.astimezone(timezone.utc).replace(tzinfo=None)
        if end_dt.tzinfo is not None:
            end_dt = end_dt.astimezone(timezone.utc).replace(tzinfo=None)

        if start_dt > end_dt:
            raise ValueError(
                f"Invalid time window: start_time ({start_dt.isoformat()}) "
                f"must precede end_time ({end_dt.isoformat()})."
            )

        return start_dt, end_dt, {
            "type": "iso_interval",
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "description": f"Filtered strictly between {start_dt.isoformat()} and {end_dt.isoformat()}"
        }

    # 2. Relative duration shorthand
    match = RELATIVE_WINDOW_PATTERN.match(window)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        if unit == "m":
            delta = timedelta(minutes=amount)
        elif unit == "h":
            delta = timedelta(hours=amount)
        elif unit == "d":
            delta = timedelta(days=amount)
        else:
            raise ValueError(f"Unsupported duration unit '{unit}' in window '{window}'")

        anchor = latest_db_time or datetime.utcnow()
        start_dt = anchor - delta
        end_dt = anchor

        return start_dt, end_dt, {
            "type": "relative_duration",
            "duration": window,
            "anchor_timestamp": anchor.isoformat(),
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "description": f"Trailing {window} window relative to recorded telemetry anchor ({anchor.isoformat()})"
        }

    raise ValueError(
        f"Invalid window specification '{window}'. "
        f"Expected ISO interval 'start/end' (e.g., '2026-10-25T00:00:00/2026-10-26T00:00:00') "
        f"or relative shorthand ('1h', '6h', '24h', '7d')."
    )


# Cache for local SQLite engine
_local_sqlite_engine = None
_local_sqlite_sessionmaker = None


def get_mcp_db_session() -> Session:
    """
    Returns an active database session for MCP tools bound to manumind.db (or DATABASE_URL).
    Ensures deterministic, zero-network local condition monitoring.
    """
    global _local_sqlite_engine, _local_sqlite_sessionmaker
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.strip().startswith("sqlite"):
        engine = create_engine(db_url.strip(), connect_args={"check_same_thread": False})
        return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    if _local_sqlite_engine is None:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        sqlite_path = repo_root / "manumind.db"
        sqlite_url = f"sqlite:///{sqlite_path.as_posix()}"
        _local_sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        _local_sqlite_sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=_local_sqlite_engine)
    return _local_sqlite_sessionmaker()


# ===========================================================================
# Tool 1: get_machine_data
# ===========================================================================

def handle_get_machine_data(
    machine_id: str,
    window: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Retrieve machine asset profile and historical sensor telemetry from SQLite.

    Guarantees:
    - Machine ID strictly validated against ^M1(0[1-9]|10)$.
    - Limit bounded between 1 and 500 records.
    - Parameterized query execution (zero arbitrary SQL).
    - Database session lifecycle strictly closed on success or error.
    - Strictly read-only: zero mutations to SQLite database.
    """
    logger.info(f"[Tool:get_machine_data] Querying machine_id='{machine_id}', window='{window}', limit={limit}")

    # 1. Input Validation
    if not isinstance(machine_id, str) or not MACHINE_ID_PATTERN.match(machine_id):
        raise ValueError(f"Invalid machine_id '{machine_id}'. Must match pattern '^M1(0[1-9]|10)$' (M101 to M110).")

    if not isinstance(limit, int) or limit < 1 or limit > 500:
        raise ValueError(f"Invalid limit {limit}. Must be an integer between 1 and 500.")

    # 2. Database Session Execution
    db = get_mcp_db_session()
    try:
        # Query Machine Profile
        machine = db.query(Machine).filter(Machine.id == machine_id).first()
        if not machine:
            return GetMachineDataResponse(
                status="NO_DATA",
                machine_id=machine_id,
                machine_profile=None,
                telemetry_count=0,
                telemetry=[],
                message=f"Machine '{machine_id}' is not registered in the asset registry."
            ).model_dump()

        profile = MachineProfile(
            id=machine.id,
            name=machine.name,
            type=machine.type,
            criticality=machine.criticality,
            production_impact=machine.production_impact,
        )

        # Resolve latest recorded timestamp for relative window anchoring
        latest_ts = (
            db.query(func.max(SensorReading.timestamp))
            .filter(SensorReading.machine_id == machine_id)
            .scalar()
        )

        start_dt, end_dt, window_applied = parse_time_window(window, latest_ts)

        # Query Telemetry
        query = db.query(SensorReading).filter(SensorReading.machine_id == machine_id)
        if start_dt is not None:
            query = query.filter(SensorReading.timestamp >= start_dt)
        if end_dt is not None:
            query = query.filter(SensorReading.timestamp <= end_dt)

        # Enforce deterministic chronological ordering
        query = query.order_by(SensorReading.timestamp.asc())
        rows = query.limit(min(limit, 500)).all()

        telemetry = [
            TelemetryRecord(
                timestamp=r.timestamp.isoformat() if hasattr(r.timestamp, "isoformat") else str(r.timestamp),
                vibration=round(float(r.vibration), 4),
                temperature=round(float(r.temperature), 4),
                pressure=round(float(r.pressure), 4),
                current=round(float(r.current), 4),
                rpm=round(float(r.rpm), 4),
            )
            for r in rows
        ]

        status = "SUCCESS" if telemetry else "NO_DATA"
        msg = f"Retrieved {len(telemetry)} telemetry records." if telemetry else "No telemetry records matched the specified criteria."

        return GetMachineDataResponse(
            status=status,
            machine_id=machine_id,
            machine_profile=profile,
            telemetry_count=len(telemetry),
            telemetry=telemetry,
            window_applied=window_applied,
            message=msg
        ).model_dump()
    finally:
        db.close()


# ===========================================================================
# Tool 2: detect_anomaly
# ===========================================================================

def handle_detect_anomaly(
    machine_id: str,
    readings: Optional[List[Dict[str, Any]]] = None,
    window: Optional[str] = None,
    include_explainability: bool = False
) -> Dict[str, Any]:
    """
    Perform multi-model anomaly detection using UnifiedInferenceService.

    Guarantees:
    - Evaluates point-in-time tabular anomaly with Isolation Forest (frozen threshold 0.0269).
    - Evaluates sequence reconstruction anomaly with LSTM Autoencoder (frozen threshold 0.901464).
    - Respects model sequence length requirements (exactly 30 observations for LSTM).
    - Does NOT fabricate sensor values or classify insufficient data as normal.
    - Anomaly scores are NOT treated as failure probabilities.
    - Strictly read-only: zero database or model mutations.
    """
    logger.info(f"[Tool:detect_anomaly] Running anomaly detection for machine_id='{machine_id}'")

    # 1. Machine ID Validation
    if not isinstance(machine_id, str) or not MACHINE_ID_PATTERN.match(machine_id):
        raise ValueError(f"Invalid machine_id '{machine_id}'. Must match pattern '^M1(0[1-9]|10)$' (M101 to M110).")

    telemetry_source: List[Dict[str, Any]] = []
    warnings: List[str] = []

    # 2. Acquire Telemetry
    if readings is not None:
        if not isinstance(readings, list):
            raise ValueError(f"Readings must be a list of sensor reading objects, got {type(readings)}")
        telemetry_source = readings
    else:
        # Query database for recent chronological readings up to 30
        db_gen = get_db()
        db = next(db_gen)
        try:
            latest_ts = (
                db.query(func.max(SensorReading.timestamp))
                .filter(SensorReading.machine_id == machine_id)
                .scalar()
            )
            start_dt, end_dt, _ = parse_time_window(window, latest_ts)

            q = db.query(SensorReading).filter(SensorReading.machine_id == machine_id)
            if start_dt is not None:
                q = q.filter(SensorReading.timestamp >= start_dt)
            if end_dt is not None:
                q = q.filter(SensorReading.timestamp <= end_dt)

            # Retrieve up to 30 latest readings in chronological order
            q = q.order_by(SensorReading.timestamp.desc()).limit(30)
            rows = q.all()
            rows.reverse()

            telemetry_source = [
                {
                    "timestamp": r.timestamp.isoformat() if hasattr(r.timestamp, "isoformat") else str(r.timestamp),
                    "vibration": float(r.vibration),
                    "temperature": float(r.temperature),
                    "pressure": float(r.pressure),
                    "current": float(r.current),
                    "rpm": float(r.rpm),
                    "machine_id": machine_id
                }
                for r in rows
            ]
        finally:
            db.close()

    # 3. Handle Insufficient Data
    if not telemetry_source:
        return DetectAnomalyResponse(
            status="INSUFFICIENT_DATA",
            machine_id=machine_id,
            classification="INSUFFICIENT_DATA",
            is_anomaly=None,
            analysis_window={"reading_count": 0},
            warnings=["No telemetry readings available to perform anomaly detection."],
            timestamp=datetime.utcnow().isoformat()
        ).model_dump()

    # 4. Strict Telemetry Validation
    validated_readings: List[Dict[str, Any]] = []
    timestamps: List[datetime] = []

    for idx, r in enumerate(telemetry_source):
        if not isinstance(r, dict):
            raise ValueError(f"Observation at index {idx} must be a dictionary object.")

        missing_channels = [c for c in CANONICAL_FEATURES if c not in r]
        if missing_channels:
            raise ValueError(f"Observation at index {idx} missing required channel(s): {missing_channels}")

        clean_reading: Dict[str, Any] = {"machine_id": machine_id}
        for c in CANONICAL_FEATURES:
            val = r[c]
            try:
                fval = float(val)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Observation at index {idx} channel '{c}' must be numeric: {val}") from exc

            # Check finite
            import math
            if math.isnan(fval) or math.isinf(fval):
                raise ValueError(f"Observation at index {idx} channel '{c}' is non-finite: {fval}")
            clean_reading[c] = fval

        ts_raw = r.get("timestamp")
        if ts_raw:
            try:
                dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                timestamps.append(dt)
                clean_reading["timestamp"] = dt
            except Exception:
                warnings.append(f"Observation at index {idx} contains unparseable timestamp: '{ts_raw}'")

        validated_readings.append(clean_reading)

    # Verify chronological ordering if timestamps present
    if len(timestamps) == len(validated_readings):
        for i in range(1, len(timestamps)):
            if timestamps[i] < timestamps[i - 1]:
                raise ValueError(
                    f"Telemetry sequence out of order: observation at index {i} "
                    f"({timestamps[i].isoformat()}) preceded by index {i - 1} ({timestamps[i - 1].isoformat()})"
                )

    # 5. Execute ML Anomaly Inference
    service = get_inference_service()

    # A. Tabular point-in-time scoring on latest observation
    latest_reading = validated_readings[-1]
    if_response = service.predict_sensor_anomaly(latest_reading, explain=include_explainability)

    if_result = IsolationForestResult(
        score=round(float(if_response.anomaly_score), 6),
        threshold=ISOLATION_FOREST_FROZEN_THRESHOLD,
        is_anomaly=bool(if_response.is_anomaly),
        explanation_status=if_response.explanation_status.value if hasattr(if_response.explanation_status, "value") else str(if_response.explanation_status),
        shap_explanation=if_response.shap_explanation
    )

    # B. Temporal sequence reconstruction scoring (LSTM Autoencoder)
    lstm_result: Optional[LSTMSAutoencoderResult] = None
    if len(validated_readings) >= 30:
        # Use exact 30-step trailing window
        from backend.app.ml.inference.schemas import (
            SensorReadingInput,
            SequenceWindowInput,
        )
        seq_slice = validated_readings[-30:]
        seq_input = SequenceWindowInput(
            machine_id=machine_id,
            readings=[SensorReadingInput(**r) for r in seq_slice]
        )
        lstm_response = service.predict_sequence_anomaly(seq_input, explain=include_explainability)

        lstm_result = LSTMSAutoencoderResult(
            reconstruction_error=round(float(lstm_response.reconstruction_error), 6),
            threshold=LSTM_AUTOENCODER_FROZEN_THRESHOLD,
            is_anomaly=bool(lstm_response.is_anomaly),
            attribution_status=lstm_response.attribution_status.value if hasattr(lstm_response.attribution_status, "value") else str(lstm_response.attribution_status),
            sensor_attribution=lstm_response.sensor_attribution
        )
    else:
        warnings.append(
            f"LSTM Autoencoder skipped: requires exactly 30 observations, but {len(validated_readings)} were available."
        )

    # Composite anomaly decision
    composite_anomaly = if_result.is_anomaly or (lstm_result.is_anomaly if lstm_result else False)
    classification = "ANOMALY_DETECTED" if composite_anomaly else "NORMAL"

    start_ts_str = str(validated_readings[0].get("timestamp", "N/A"))
    end_ts_str = str(validated_readings[-1].get("timestamp", "N/A"))

    return DetectAnomalyResponse(
        status="SUCCESS",
        machine_id=machine_id,
        classification=classification,
        is_anomaly=composite_anomaly,
        analysis_window={
            "reading_count": len(validated_readings),
            "start_timestamp": start_ts_str,
            "end_timestamp": end_ts_str,
            "window_specification": window or "default_latest"
        },
        isolation_forest=if_result,
        lstm_autoencoder=lstm_result,
        warnings=warnings,
        timestamp=datetime.utcnow().isoformat()
    ).model_dump()


# ===========================================================================
# Tool 3: predict_failure_risk
# ===========================================================================

def handle_predict_failure_risk(
    machine_id: str,
    horizon_hours: int = 288
) -> Dict[str, Any]:
    """
    Expose formal failure-risk capability status without fabricating predictions.

    Guarantees:
    - Reports the formal Phase 2 Step 5 NO-GO decision for H=288 regression.
    - Zero model calls to Isolation Forest or LSTM.
    - Zero fabricated probabilities or percentage scores.
    - Does NOT claim a machine is safe because model is absent.
    - Strictly read-only: zero database mutations.
    """
    logger.info(f"[Tool:predict_failure_risk] Checking failure risk capability for machine_id='{machine_id}'")

    if not isinstance(machine_id, str) or not MACHINE_ID_PATTERN.match(machine_id):
        raise ValueError(f"Invalid machine_id '{machine_id}'. Must match pattern '^M1(0[1-9]|10)$' (M101 to M110).")

    if not isinstance(horizon_hours, int) or horizon_hours <= 0:
        raise ValueError(f"Invalid horizon_hours {horizon_hours}. Must be a positive integer.")

    return PredictFailureRiskResponse(
        machine_id=machine_id,
        horizon_hours=horizon_hours,
        status="NOT_AVAILABLE",
        model_available=False,
    ).model_dump()


# ===========================================================================
# Tool 5: search_manuals (Phase 4 Step 3)
# ===========================================================================

def handle_search_manuals(
    query: str,
    k: int = 5,
) -> Dict[str, Any]:
    """
    Search manufacturing SOPs, troubleshooting manuals, and safety documentation.
    Delegates via isolated subprocess bridge to the .venv-rag Python environment.

    Guarantees:
    - Bounded input validation: query non-empty, max 500 chars; 1 <= k <= 20.
    - Zero write operations to ChromaDB or SQLite.
    - Strict stream isolation preserving JSON-RPC stdout integrity.
    """
    from backend.app.mcp_server.rag_bridge import search_manuals_via_bridge
    return search_manuals_via_bridge(query=query, k=k)


# ===========================================================================
# Tool 4: get_maintenance_history (Phase 4 Step 4)
# ===========================================================================

def handle_get_maintenance_history(
    machine_id: str,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Retrieve historical maintenance intervention logs from SQLite database.

    Guarantees:
    - machine_id strictly validated against pattern ^M1(0[1-9]|10)$ (M101 to M110).
    - limit strictly bounded between 1 and 500 (rejects non-integer, bool, float, <=0, >500).
    - Deterministic chronological ordering (MaintenanceHistory.date.asc(), tie-broken by MaintenanceHistory.id.asc()).
    - Safe handling of empty history (returns structured NO_DATA response).
    - Database session lifecycle strictly closed with try/finally.
    - Strictly read-only: zero mutations to SQLite database.
    """
    logger.info(f"[Tool:get_maintenance_history] Querying machine_id='{machine_id}', limit={limit}")

    # 1. Input Validation
    if not isinstance(machine_id, str) or not MACHINE_ID_PATTERN.match(machine_id):
        raise ValueError(f"Invalid machine_id '{machine_id}'. Must match pattern '^M1(0[1-9]|10)$' (M101 to M110).")

    if isinstance(limit, bool):
        raise ValueError("Invalid limit: boolean values are not permitted.")

    if not isinstance(limit, int) or limit < 1 or limit > 500:
        raise ValueError(f"Invalid limit {limit}. Must be an integer between 1 and 500.")

    # 2. Database Session Execution
    db = get_mcp_db_session()
    try:
        # Check machine registration
        machine = db.query(Machine).filter(Machine.id == machine_id).first()
        if not machine:
            return GetMaintenanceHistoryResponse(
                status="NO_DATA",
                machine_id=machine_id,
                total_returned=0,
                records=[],
                message=f"Machine '{machine_id}' is not registered in the asset registry."
            ).model_dump()

        # Query maintenance records in deterministic chronological order
        query = (
            db.query(MaintenanceHistory)
            .filter(MaintenanceHistory.machine_id == machine_id)
            .order_by(MaintenanceHistory.date.asc(), MaintenanceHistory.id.asc())
            .limit(limit)
        )
        rows = query.all()

        records = [
            MaintenanceRecordItem(
                id=r.id,
                machine_id=r.machine_id,
                date=r.date.isoformat() if hasattr(r.date, "isoformat") else str(r.date),
                issue=r.issue,
                action=r.action,
                outcome=r.outcome,
            )
            for r in rows
        ]

        status = "SUCCESS" if records else "NO_DATA"
        msg = (
            f"Retrieved {len(records)} maintenance records for machine '{machine_id}'."
            if records
            else f"No maintenance records found for machine '{machine_id}'."
        )

        return GetMaintenanceHistoryResponse(
            status=status,
            machine_id=machine_id,
            total_returned=len(records),
            records=records,
            message=msg,
        ).model_dump()
    finally:
        db.close()


# ===========================================================================
# Tool 5: check_defect_image (Phase 4 Step 5)
# ===========================================================================

def handle_check_defect_image(
    image_path: str,
) -> Dict[str, Any]:
    """
    Perform visual surface defect classification on workpiece images using Compact ResNet-18.
    Delegates via isolated subprocess bridge in Base Python 3.11 environment.

    Guarantees:
    - Bounded input validation: path within approved data/defect_images/ directory.
    - Prevents traversal, symlink escape, and arbitrary file access.
    - Validates image dimensions, magic bytes, and file size (<= 5 MB).
    - Zero write operations to disk, database, model weights, or images.
    - Strict stream isolation preserving JSON-RPC stdout integrity.
    """
    from backend.app.mcp_server.defect_bridge import check_defect_image_via_bridge
    return check_defect_image_via_bridge(image_path=image_path)


# ===========================================================================
# Tool 8: propose_maintenance_ticket (Phase 4 Step 6)
# ===========================================================================

def handle_propose_maintenance_ticket(
    machine_id: str,
    recommendation: str,
    evidence: Dict[str, Any],
    alert_id: Optional[str] = None,
    confidence: float = 0.85,
    session_override: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Stage a maintenance ticket proposal for human engineer review and authorization.

    Security & Architectural Guarantees:
    - AI agents are STRICTLY PROHIBITED from creating active maintenance tickets directly.
    - machine_id is validated against ^M1(0[1-9]|10)$.
    - recommendation and evidence are validated and tamper-sealed via canonical SHA-256 hash.
    - Creates a TicketProposal with status PENDING_APPROVAL. Zero Ticket records are created.
    - Proposal has a bounded validity window (default 24 hours).
    - Does NOT accept or process agent-supplied approval decisions.
    """
    from backend.app.mcp_server.approval import compute_canonical_payload_hash

    # 1. Type and constraint validations
    if not isinstance(machine_id, str) or not MACHINE_ID_PATTERN.match(machine_id.strip()):
        raise ValueError(
            f"Invalid machine_id '{machine_id}'. Must strictly match regex ^M1(0[1-9]|10)$ (M101 to M110)."
        )
    machine_id = machine_id.strip()

    if not isinstance(recommendation, str) or len(recommendation.strip()) < 5:
        raise ValueError("recommendation must be a non-empty string with at least 5 characters.")
    recommendation = recommendation.strip()
    if len(recommendation) > 1000:
        raise ValueError("recommendation exceeds maximum allowed length of 1000 characters.")

    if not isinstance(evidence, dict) or not evidence:
        raise ValueError("evidence must be a non-empty structured dictionary.")

    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
        raise ValueError("confidence must be a float between 0.0 and 1.0.")
    confidence = float(confidence)

    if alert_id is not None:
        if not isinstance(alert_id, str) or not alert_id.strip():
            raise ValueError("alert_id must be a non-empty string when provided.")
        alert_id = alert_id.strip()

    db = session_override or get_mcp_db_session()
    close_db = session_override is None

    try:
        # 2. Verify target machine exists
        machine = db.query(Machine).filter(Machine.id == machine_id).first()
        if not machine:
            raise ValueError(f"Machine '{machine_id}' does not exist in asset database.")

        # 3. Verify / resolve alert_id
        if alert_id:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                raise ValueError(f"Alert with id '{alert_id}' not found in database.")
            if alert.machine_id != machine_id:
                raise ValueError(
                    f"Alert '{alert_id}' is associated with machine '{alert.machine_id}', not '{machine_id}'."
                )
        else:
            # Find an active pending alert for this machine if available
            alert = db.query(Alert).filter(
                Alert.machine_id == machine_id,
                Alert.status == "PENDING_APPROVAL"
            ).first()
            if alert:
                alert_id = alert.id

        # 4. Compute canonical proposal payload hash
        payload_hash = compute_canonical_payload_hash(
            machine_id=machine_id,
            recommendation=recommendation,
            evidence=evidence,
            alert_id=alert_id,
            confidence=confidence,
        )

        # 5. Generate proposal ID
        count = db.query(TicketProposal).count() + 1
        proposal_id = f"PROP-2026-{count:04d}"
        while db.query(TicketProposal).filter(TicketProposal.id == proposal_id).first():
            count += 1
            proposal_id = f"PROP-2026-{count:04d}"

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        # 6. Persist staged proposal (PENDING_APPROVAL)
        proposal = TicketProposal(
            id=proposal_id,
            machine_id=machine_id,
            alert_id=alert_id,
            recommendation=recommendation,
            evidence=evidence,
            confidence=confidence,
            payload_hash=payload_hash,
            status="PENDING_APPROVAL",
            created_at=now,
            expires_at=expires_at,
        )

        db.add(proposal)
        db.commit()
        db.refresh(proposal)

        logger.info(
            f"Created maintenance ticket proposal '{proposal.id}' for machine '{machine_id}' "
            f"(payload_hash: {payload_hash[:16]}..., status: PENDING_APPROVAL)"
        )

        return ProposeMaintenanceTicketResponse(
            status="PENDING_APPROVAL",
            proposal_id=proposal.id,
            machine_id=proposal.machine_id,
            alert_id=proposal.alert_id,
            recommendation=proposal.recommendation,
            confidence=proposal.confidence,
            payload_hash=proposal.payload_hash,
            requires_human_approval=True,
            is_synthetic=True,
            created_at=proposal.created_at.isoformat(),
            expires_at=proposal.expires_at.isoformat(),
            message=f"Maintenance ticket proposal '{proposal.id}' created and pending human engineer authorization.",
        ).model_dump()

    finally:
        if close_db:
            db.close()


# ===========================================================================
# Tool 9: create_maintenance_ticket (Phase 4 Step 6)
# ===========================================================================

def handle_create_maintenance_ticket(
    proposal_id: str,
    approval_token: str,
    session_override: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Execute maintenance ticket creation following cryptographic verification of human approval.

    Security & Transactional Guarantees:
    - Requires genuine cryptographic HMAC token from trusted human approval gate.
    - Rejects any agent-supplied approved_by identity.
    - Validates token signature, algorithm (HS256), and short-lived expiry.
    - Validates binding to exact proposal_id and canonical proposal payload_hash.
    - Replay protection: Token jti is recorded in consumed_tokens table; duplicates fail.
    - Proposal must be in PENDING_APPROVAL status; marks proposal CONSUMED atomically.
    - Uses existing authoritative ticket service (create_ticket_with_approval_gate).
    - Executed in an atomic database transaction.
    """
    from backend.app.mcp_server.approval import (
        compute_canonical_payload_hash,
        HMACApprovalTokenManager,
        ApprovalSecurityError,
    )
    from backend.app.services.ticket_service import create_ticket_with_approval_gate

    # 1. Input format validation
    if not isinstance(proposal_id, str) or not proposal_id.strip():
        raise ValueError("proposal_id must be a non-empty string.")
    proposal_id = proposal_id.strip()

    if not isinstance(approval_token, str) or not approval_token.strip():
        raise ValueError("approval_token must be a non-empty string.")
    approval_token = approval_token.strip()

    db = session_override or get_mcp_db_session()
    close_db = session_override is None

    try:
        # 2. Retrieve proposal record
        proposal = db.query(TicketProposal).filter(TicketProposal.id == proposal_id).first()
        if not proposal:
            raise ValueError(f"Ticket proposal '{proposal_id}' not found in database.")

        # 3. Status checks
        if proposal.status != "PENDING_APPROVAL":
            raise ValueError(
                f"Proposal '{proposal_id}' cannot be authorized: status is '{proposal.status}' "
                f"(strictly 'PENDING_APPROVAL' required)."
            )

        # 4. Temporal validity of proposal
        now = datetime.now(timezone.utc)
        exp_tz = proposal.expires_at.replace(tzinfo=timezone.utc) if proposal.expires_at.tzinfo is None else proposal.expires_at
        if now > exp_tz:
            proposal.status = "EXPIRED"
            db.commit()
            raise ValueError(f"Proposal '{proposal_id}' validity window expired at {proposal.expires_at.isoformat()}.")

        # 5. Stored proposal integrity check (recomputed payload hash)
        recomputed_hash = compute_canonical_payload_hash(
            machine_id=proposal.machine_id,
            recommendation=proposal.recommendation,
            evidence=proposal.evidence,
            alert_id=proposal.alert_id,
            confidence=proposal.confidence,
        )
        if recomputed_hash.lower() != proposal.payload_hash.lower():
            raise ValueError(
                "Proposal integrity violation: Stored payload hash does not match computed hash from proposal fields."
            )

        # 6. Cryptographic Token Verification
        claims = HMACApprovalTokenManager.verify_token(
            token=approval_token,
            expected_proposal_id=proposal.id,
            expected_payload_hash=proposal.payload_hash,
        )

        token_jti = claims["jti"]
        approver_id = claims["approver_id"]

        # 7. Replay Check
        existing_consumed = db.query(ConsumedToken).filter(ConsumedToken.jti == token_jti).first()
        if existing_consumed:
            raise ValueError(
                f"Authorization token replay detected: token '{token_jti}' was already consumed at "
                f"{existing_consumed.consumed_at.isoformat()} by '{existing_consumed.approver_id}'."
            )

        # 8. Check / resolve alert_id
        alert_id = proposal.alert_id
        if not alert_id:
            alert = db.query(Alert).filter(Alert.machine_id == proposal.machine_id).first()
            if alert:
                alert_id = alert.id
            else:
                alert_id = f"ALT-{proposal.machine_id}-001"
                alert = Alert(
                    id=alert_id,
                    machine_id=proposal.machine_id,
                    risk=proposal.confidence,
                    criticality=4,
                    impact=4,
                    priority_score=round(proposal.confidence * 16.0, 2),
                    status="PENDING_APPROVAL",
                    created_at=datetime.utcnow()
                )
                db.add(alert)
                db.flush()

        # Check if alert already has a ticket
        existing_ticket = db.query(Ticket).filter(Ticket.alert_id == alert_id).first()
        if existing_ticket and existing_ticket.id != proposal.ticket_id:
            raise ValueError(f"Alert '{alert_id}' already has an active ticket '{existing_ticket.id}'.")

        # 9. Create ticket using authoritative approval service
        ticket = create_ticket_with_approval_gate(
            db=db,
            alert_id=alert_id,
            recommendation=proposal.recommendation,
            evidence=proposal.evidence,
            confidence=proposal.confidence,
            approved_by=approver_id,
        )

        # 10. Atomically transition proposal and record token consumption
        proposal.status = "CONSUMED"
        proposal.ticket_id = ticket.id
        proposal.approved_by = approver_id
        proposal.approved_at = datetime.utcnow()
        proposal.token_id = token_jti

        token_exp_dt = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
        consumed = ConsumedToken(
            jti=token_jti,
            proposal_id=proposal.id,
            approver_id=approver_id,
            consumed_at=datetime.utcnow(),
            token_exp=token_exp_dt,
        )
        db.add(consumed)
        db.commit()
        db.refresh(ticket)
        db.refresh(proposal)

        logger.info(
            f"Successfully created maintenance ticket '{ticket.id}' for proposal '{proposal.id}' "
            f"authorized by '{approver_id}' (token jti: {token_jti})"
        )

        return CreateMaintenanceTicketResponse(
            status="APPROVED",
            ticket_id=ticket.id,
            proposal_id=proposal.id,
            machine_id=proposal.machine_id,
            alert_id=ticket.alert_id,
            recommendation=ticket.recommendation,
            confidence=ticket.confidence,
            approved_by=ticket.approved_by,
            approved_at=proposal.approved_at.isoformat() if proposal.approved_at else datetime.utcnow().isoformat(),
            created_at=ticket.created_at.isoformat(),
            is_synthetic=True,
            message=f"Maintenance ticket '{ticket.id}' successfully authorized and created following cryptographic human approval verification.",
        ).model_dump()

    finally:
        if close_db:
            db.close()




