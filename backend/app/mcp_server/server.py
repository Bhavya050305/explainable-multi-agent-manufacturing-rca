"""
ManuMind AI — Model Context Protocol (MCP) Server Foundation
Phase 4 Step 2: Read-Only Manufacturing MCP Tools Implementation

Department of AI & Data Science — RMK Engineering College
"""

import sys
import logging
from typing import Annotated, Any, Dict, List, Optional
from pydantic import Field
from mcp.server import MCPServer

from backend.app.mcp_server.tools import (
    handle_get_machine_data,
    handle_detect_anomaly,
    handle_predict_failure_risk,
    handle_search_manuals,
    handle_get_maintenance_history,
    handle_check_defect_image,
    handle_propose_maintenance_ticket,
    handle_create_maintenance_ticket,
)

# Configure diagnostic logging strictly to stderr to keep stdout pristine for JSON-RPC protocol frames
logger = logging.getLogger("manumind-mcp-server")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [ManuMind-MCP] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

SERVER_NAME: str = "ManuMind AI MCP Server"
SERVER_VERSION: str = "0.1.0"


def create_mcp_server() -> MCPServer:
    """
    Constructs and configures the production-oriented MCP server instance.
    Registers Tool 1 (get_machine_data), Tool 2 (detect_anomaly), Tool 3 (predict_failure_risk),
    and temporary diagnostic tool (ping).
    """
    server = MCPServer(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        instructions="ManuMind AI manufacturing anomaly detection, diagnostic RCA, and telemetry MCP server.",
    )

    # -----------------------------------------------------------------------
    # Temporary Diagnostic Tool: ping
    # -----------------------------------------------------------------------
    @server.tool(
        name="ping",
        description="Harmless diagnostic echo tool to verify MCP protocol communication and server health.",
    )
    def ping(message: str = "pong") -> str:
        """
        Diagnostic ping tool.
        Returns a deterministic echo response. Performs zero database access, filesystem
        mutations, ML inference, or external network calls.
        """
        logger.info(f"Ping tool invoked with payload: '{message}'")
        return f"pong: {message}"

    # -----------------------------------------------------------------------
    # Tool 1: get_machine_data
    # -----------------------------------------------------------------------
    @server.tool(
        name="get_machine_data",
        description=(
            "Retrieve machine asset metadata profile and historical 5-channel sensor telemetry "
            "(vibration, temperature, pressure, current, rpm) from SQLite database with bounded "
            "time-window filtering and deterministic chronological ordering."
        ),
    )
    def get_machine_data(
        machine_id: Annotated[
            str,
            Field(
                pattern=r"^M1(0[1-9]|10)$",
                description="Machine identifier (strictly validated against M101 to M110)"
            )
        ],
        window: Annotated[
            Optional[str],
            Field(
                None,
                description=(
                    "Optional time-window filter: ISO 8601 interval 'start/end' "
                    "(e.g., '2026-10-25T00:00:00/2026-10-26T00:00:00') or trailing duration "
                    "relative to recorded telemetry ('1h', '6h', '24h', '7d'). If omitted, "
                    "retrieves latest readings up to limit."
                )
            )
        ] = None,
        limit: Annotated[
            int,
            Field(
                100,
                ge=1,
                le=500,
                description="Maximum number of telemetry records to return (1 to 500, default 100)"
            )
        ] = 100,
    ) -> Dict[str, Any]:
        """
        Retrieve machine profile and sensor telemetry.
        Enforces read-only database query execution with automatic session closure.
        """
        return handle_get_machine_data(machine_id=machine_id, window=window, limit=limit)

    # -----------------------------------------------------------------------
    # Tool 2: detect_anomaly
    # -----------------------------------------------------------------------
    @server.tool(
        name="detect_anomaly",
        description=(
            "Perform manufacturing anomaly inference using calibrated Isolation Forest "
            "(frozen threshold 0.0269) and LSTM Autoencoder sequence reconstruction "
            "(frozen threshold 0.901464). Requires 5 canonical sensor channels "
            "(vibration, temperature, pressure, current, rpm). Does not fabricate values or "
            "treat anomaly scores as failure probabilities."
        ),
    )
    def detect_anomaly(
        machine_id: Annotated[
            str,
            Field(
                pattern=r"^M1(0[1-9]|10)$",
                description="Machine identifier (strictly validated against M101 to M110)"
            )
        ],
        readings: Annotated[
            Optional[List[Dict[str, Any]]],
            Field(
                None,
                description=(
                    "Optional telemetry readings to evaluate. If omitted, queries latest 30 "
                    "readings from database for machine_id. Each reading must contain "
                    "canonical sensor channels (vibration, temperature, pressure, current, rpm)."
                )
            )
        ] = None,
        window: Annotated[
            Optional[str],
            Field(
                None,
                description="Optional time window filter when querying telemetry from database ('1h', '24h', or ISO 'start/end')."
            )
        ] = None,
        include_explainability: Annotated[
            bool,
            Field(
                False,
                description="Flag to generate Kernel SHAP and reconstruction attribution explanations."
            )
        ] = False,
    ) -> Dict[str, Any]:
        """
        Execute multi-model anomaly detection over machine telemetry.
        """
        return handle_detect_anomaly(
            machine_id=machine_id,
            readings=readings,
            window=window,
            include_explainability=include_explainability,
        )

    # -----------------------------------------------------------------------
    # Tool 3: predict_failure_risk
    # -----------------------------------------------------------------------
    @server.tool(
        name="predict_failure_risk",
        description=(
            "Expose formal capability status for failure-risk prediction. Returns deterministic "
            "NOT_AVAILABLE status reflecting Phase 2 Step 5 NO-GO decision for H=288 regression task. "
            "Does not fabricate predictions or probabilities."
        ),
    )
    def predict_failure_risk(
        machine_id: Annotated[
            str,
            Field(
                pattern=r"^M1(0[1-9]|10)$",
                description="Machine identifier (strictly validated against M101 to M110)"
            )
        ],
        horizon_hours: Annotated[
            int,
            Field(
                288,
                ge=1,
                le=720,
                description="Forecast prediction horizon in hours (default 288 hours / 12 days)"
            )
        ] = 288,
    ) -> Dict[str, Any]:
        """
        Formal capability-status stub for failure risk prediction.
        """
        return handle_predict_failure_risk(
            machine_id=machine_id,
            horizon_hours=horizon_hours,
        )

    # -----------------------------------------------------------------------
    # Tool 5: search_manuals (Phase 4 Step 3)
    # -----------------------------------------------------------------------
    @server.tool(
        name="search_manuals",
        description=(
            "Execute read-only semantic vector retrieval across manufacturing standard operating "
            "procedures (SOPs), troubleshooting manuals, and safety documentation indexed in ChromaDB. "
            "Returns ranked knowledge excerpts with cosine similarity scores, section headings, and "
            "synthetic provenance indicators. Excludes LLM generative synthesis or hallucinated advice."
        ),
    )
    def search_manuals(
        query: Annotated[
            str,
            Field(
                min_length=1,
                max_length=500,
                description="Semantic search query describing the machine symptom, procedure, or maintenance query"
            )
        ],
        k: Annotated[
            int,
            Field(
                5,
                ge=1,
                le=20,
                description="Number of top ranked passages to retrieve (1 to 20, default 5)"
            )
        ] = 5,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant manufacturing manual excerpts via isolated RAG subprocess bridge.
        """
        return handle_search_manuals(
            query=query,
            k=k,
        )

    # -----------------------------------------------------------------------
    # Tool 4: get_maintenance_history (Phase 4 Step 4)
    # -----------------------------------------------------------------------
    @server.tool(
        name="get_maintenance_history",
        description=(
            "Retrieve historical maintenance intervention logs, reported issues, corrective actions, "
            "and resolution outcomes for a specific manufacturing asset from the SQLite database. "
            "Returns records in deterministic chronological order (tie-broken by record ID). "
            "Strictly read-only; does not infer component failure probability or remaining useful life."
        ),
    )
    def get_maintenance_history(
        machine_id: Annotated[
            str,
            Field(
                pattern=r"^M1(0[1-9]|10)$",
                description="Machine identifier (strictly validated against M101 to M110)"
            )
        ],
        limit: Annotated[
            int,
            Field(
                100,
                ge=1,
                le=500,
                description="Maximum number of maintenance records to return (1 to 500, default 100)"
            )
        ] = 100,
    ) -> Dict[str, Any]:
        """
        Retrieve historical maintenance records for the specified machine.
        """
        return handle_get_maintenance_history(
            machine_id=machine_id,
            limit=limit,
        )

    # -----------------------------------------------------------------------
    # Tool 5: check_defect_image (Phase 4 Step 5)
    # -----------------------------------------------------------------------
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
        """
        Classify workpiece image defect via isolated ResNet-18 subprocess bridge.
        """
        return handle_check_defect_image(
            image_path=image_path,
        )

    # -----------------------------------------------------------------------
    # Tool 8: propose_maintenance_ticket (Phase 4 Step 6)
    # -----------------------------------------------------------------------
    @server.tool(
        name="propose_maintenance_ticket",
        description=(
            "Stage a maintenance ticket proposal for human engineer review and authorization. "
            "Requires machine_id, actionable recommendation, and supporting evidence. "
            "Computes a canonical SHA-256 payload hash and stores the proposal in PENDING_APPROVAL status. "
            "Does NOT create an active ticket. AI agents are strictly prohibited from authorizing their own tickets."
        ),
    )
    def propose_maintenance_ticket(
        machine_id: Annotated[
            str,
            Field(
                pattern=r"^M1(0[1-9]|10)$",
                description="Machine identifier (strictly validated against M101 to M110)"
            )
        ],
        recommendation: Annotated[
            str,
            Field(
                min_length=5,
                max_length=1000,
                description="Actionable maintenance recommendation proposed by supervisory agent"
            )
        ],
        evidence: Annotated[
            Dict[str, Any],
            Field(
                description="Structured evidence dictionary (e.g. sensor telemetry metrics, defect classification, manual citations)"
            )
        ],
        alert_id: Annotated[
            Optional[str],
            Field(
                None,
                description="Optional alert identifier to link with proposal (e.g. 'ALT-M104-001')"
            )
        ] = None,
        confidence: Annotated[
            float,
            Field(
                0.85,
                ge=0.0,
                le=1.0,
                description="Proposal confidence score [0.0, 1.0]"
            )
        ] = 0.85,
    ) -> Dict[str, Any]:
        """
        Stage a maintenance ticket proposal awaiting authenticated human approval.
        """
        return handle_propose_maintenance_ticket(
            machine_id=machine_id,
            recommendation=recommendation,
            evidence=evidence,
            alert_id=alert_id,
            confidence=confidence,
        )

    # -----------------------------------------------------------------------
    # Tool 9: create_maintenance_ticket (Phase 4 Step 6)
    # -----------------------------------------------------------------------
    @server.tool(
        name="create_maintenance_ticket",
        description=(
            "Create an authorized maintenance work order ticket following cryptographic verification of human approval. "
            "Requires proposal_id and a valid cryptographically signed authorization token from the trusted human approval gate. "
            "Rejects any agent-supplied approved_by identity. Verifies signature, expiry, payload binding, and replay protection. "
            "Creates an active ticket and marks proposal consumed atomically."
        ),
    )
    def create_maintenance_ticket(
        proposal_id: Annotated[
            str,
            Field(
                min_length=1,
                max_length=100,
                description="Unique ticket proposal identifier (e.g. 'PROP-2026-0001')"
            )
        ],
        approval_token: Annotated[
            str,
            Field(
                min_length=1,
                max_length=2000,
                description="Cryptographically signed HMAC authorization token issued by trusted human approval gate"
            )
        ],
    ) -> Dict[str, Any]:
        """
        Authorize and create a maintenance ticket using a valid cryptographic human approval token.
        """
        return handle_create_maintenance_ticket(
            proposal_id=proposal_id,
            approval_token=approval_token,
        )

    return server


# Global server instance
mcp_server: MCPServer = create_mcp_server()


def run_stdio() -> None:
    """
    Synchronous entry point executing the MCP server on stdio transport.
    Guarantees that stdout is reserved exclusively for JSON-RPC 2.0 frames.
    """
    logger.info(f"Starting {SERVER_NAME} v{SERVER_VERSION} on stdio transport...")
    try:
        mcp_server.run("stdio")
    except (KeyboardInterrupt, SystemExit):
        logger.info("Server received termination signal; shutting down gracefully.")
    except Exception as exc:
        logger.error(f"Server encountered unexpected error: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_stdio()
