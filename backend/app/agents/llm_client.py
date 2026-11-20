"""
ManuMind AI — Provider-Independent LLM Client Interface
Supports multi-provider LLM routing (Gemini, OpenAI, Local Ollama)
and deterministic mock execution for offline testing and verification.
"""

from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List, Optional, Protocol, Type, TypeVar, runtime_checkable

from pydantic import BaseModel
from backend.app.agents.enums import (
    AgentName,
    AnomalyType,
    ConfidenceStatus,
    RootCauseCategory,
    SupervisorAction,
    VerificationStatus,
)
from backend.app.agents.schemas import (
    CandidateRootCause,
    SupervisorDecision,
)

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class ManuMindLLMClient(Protocol):
    """Protocol for provider-agnostic LLM interactions in ManuMind multi-agent system."""

    def generate_structured_decision(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> SupervisorDecision:
        """Generates a validated SupervisorDecision model."""
        ...

    def generate_root_cause_hypotheses(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[CandidateRootCause]:
        """Generates structured CandidateRootCause hypotheses."""
        ...


class DeterministicMockLLMClient:
    """
    Deterministic Mock LLM Provider for testing, evaluation, and offline operation.
    Generates reproducible, pre-calibrated SupervisorDecision and CandidateRootCause objects
    based on state signals, and supports simulated provider errors or custom injected responses.
    """

    def __init__(
        self,
        canned_decision: Optional[SupervisorDecision] = None,
        canned_hypotheses: Optional[List[CandidateRootCause]] = None,
        simulate_failure: bool = False,
        failure_message: str = "Simulated upstream LLM provider rate limit / network error",
        invalid_output: Optional[Dict[str, Any]] = None,
        invalid_rca_output: Optional[Any] = None,
    ):
        self.canned_decision = canned_decision
        self.canned_hypotheses = canned_hypotheses
        self.simulate_failure = simulate_failure
        self.failure_message = failure_message
        self.invalid_output = invalid_output
        self.invalid_rca_output = invalid_rca_output
        self.call_history: List[Dict[str, Any]] = []

    def generate_structured_decision(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> SupervisorDecision:
        """Records call and returns deterministic decision or raises simulated failure."""
        now = datetime.now(timezone.utc)
        self.call_history.append({
            "prompt": prompt,
            "system_instruction": system_instruction,
            "context": context,
            "timestamp": now,
        })

        if self.simulate_failure:
            raise RuntimeError(self.failure_message)

        if self.invalid_output is not None:
            # Returns an invalid dictionary or triggers validation failure
            return SupervisorDecision.model_validate(self.invalid_output)

        if self.canned_decision is not None:
            return self.canned_decision

        # Default heuristic mock decision based on context if available
        ctx = context or {}
        target_stage = ctx.get("current_stage", "INITIAL_TRIAGE")
        has_anomaly = ctx.get("is_anomaly", False)
        workflow_status = ctx.get("workflow_status")

        if workflow_status in {"COMPLETED", "FAILED", "CANCELLED"}:
            if workflow_status == "COMPLETED":
                return SupervisorDecision(
                    next_action=SupervisorAction.COMPLETE_WORKFLOW,
                    target_agent=None,
                    reason="Deterministic Mock: Workflow already completed.",
                    decision_confidence=1.0,
                    decision_timestamp=now,
                    decision_trace={"provider": "DeterministicMockLLMClient", "stage": target_stage},
                )
            else:
                return SupervisorDecision(
                    next_action=SupervisorAction.FAIL_WORKFLOW,
                    target_agent=None,
                    reason=f"Deterministic Mock: Workflow in terminal failure state ({workflow_status}).",
                    decision_confidence=1.0,
                    decision_timestamp=now,
                    decision_trace={"provider": "DeterministicMockLLMClient", "stage": target_stage},
                )

        if target_stage == "INITIAL_TRIAGE":
            return SupervisorDecision(
                next_action=SupervisorAction.ROUTE_TO_ANOMALY_DETECTION,
                target_agent=AgentName.ANOMALY_DETECTION,
                reason="Deterministic Mock: Initial telemetry ingested. Routing to Anomaly Detection Agent.",
                decision_confidence=0.92,
                decision_timestamp=now,
                decision_trace={"provider": "DeterministicMockLLMClient", "stage": target_stage},
            )
        elif has_anomaly:
            return SupervisorDecision(
                next_action=SupervisorAction.ROUTE_TO_ROOT_CAUSE_ANALYSIS,
                target_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                reason="Deterministic Mock: Telemetry anomaly detected. Routing to Root Cause Analysis Agent.",
                decision_confidence=0.88,
                decision_timestamp=now,
                decision_trace={"provider": "DeterministicMockLLMClient", "stage": target_stage},
            )
        else:
            return SupervisorDecision(
                next_action=SupervisorAction.COMPLETE_WORKFLOW,
                target_agent=None,
                reason="Deterministic Mock: Normal machine health confirmed. Workflow completed.",
                decision_confidence=0.95,
                decision_timestamp=now,
                decision_trace={"provider": "DeterministicMockLLMClient", "stage": target_stage},
            )

    def generate_root_cause_hypotheses(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[CandidateRootCause]:
        """Records call and returns deterministic CandidateRootCause hypotheses or raises simulated failure."""
        now = datetime.now(timezone.utc)
        self.call_history.append({
            "prompt": prompt,
            "system_instruction": system_instruction,
            "context": context,
            "timestamp": now,
            "type": "root_cause_hypotheses",
        })

        if self.simulate_failure:
            raise RuntimeError(self.failure_message)

        if self.invalid_rca_output is not None:
            if isinstance(self.invalid_rca_output, list):
                return [CandidateRootCause.model_validate(item) for item in self.invalid_rca_output]
            raise ValueError(
                f"Malformed LLM output: expected list of hypotheses, got {type(self.invalid_rca_output).__name__}"
            )

        if self.canned_hypotheses is not None:
            return self.canned_hypotheses

        ctx = context or {}
        machine_id = ctx.get("machine_id", "M101")
        anomaly_type = ctx.get("anomaly_type")
        if isinstance(anomaly_type, str):
            try:
                anomaly_type = AnomalyType(anomaly_type)
            except ValueError:
                anomaly_type = AnomalyType.UNKNOWN

        ev_ids = ctx.get("supporting_evidence_ids", [])
        maint_refs = ctx.get("maintenance_history_references", [])
        cit_ids = ctx.get("citation_ids", [])

        # Formulate competing hypotheses based on domain telemetry signatures
        if anomaly_type == AnomalyType.VIBRATION_SPIKE:
            h1 = CandidateRootCause(
                cause_id=f"RC-{machine_id}-01",
                description="Subsurface fatigue and rolling element spalling in drive spindle bearing.",
                hypothesis="High-frequency radial vibration exceeds normal operational envelope due to localized outer-raceway micro-spalling in the primary spindle bearing assembly.",
                confidence=0.78,
                confidence_category=ConfidenceStatus.MODERATE,
                supporting_evidence_ids=ev_ids,
                contradicting_evidence_ids=[],
                maintenance_history_references=maint_refs[:1] if maint_refs else [],
                citation_ids=cit_ids[:2] if cit_ids else [],
                verification_status=VerificationStatus.UNVERIFIED,
                proposed_by_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                category=RootCauseCategory.BEARING_DEGRADATION,
                subsystem="Drive Spindle Bearing Assembly",
                identified_at=now,
            )
            h2 = CandidateRootCause(
                cause_id=f"RC-{machine_id}-02",
                description="Angular and parallel shaft misalignment across the flexible drive coupling.",
                hypothesis="Shaft centerlines between the primary motor and driven gearbox exhibit angular deviation, producing characteristic 2x rotational speed harmonic vibration.",
                confidence=0.62,
                confidence_category=ConfidenceStatus.MODERATE,
                supporting_evidence_ids=ev_ids[:1] if ev_ids else [],
                contradicting_evidence_ids=[],
                maintenance_history_references=[],
                citation_ids=cit_ids[1:3] if len(cit_ids) >= 3 else cit_ids,
                verification_status=VerificationStatus.UNVERIFIED,
                proposed_by_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                category=RootCauseCategory.MISALIGNMENT,
                subsystem="Motor-Spindle Flexible Coupling",
                identified_at=now,
            )
            h3 = CandidateRootCause(
                cause_id=f"RC-{machine_id}-03",
                description="Mechanical looseness and preload loss in machine foundation mounting bolts.",
                hypothesis="Foundation anchoring bolts exhibit reduced clamp torque, reducing structural damping and elevating measured 1x vibration amplitudes.",
                confidence=0.45,
                confidence_category=ConfidenceStatus.LOW,
                supporting_evidence_ids=ev_ids[:1] if ev_ids else [],
                contradicting_evidence_ids=[],
                maintenance_history_references=[],
                citation_ids=[],
                verification_status=VerificationStatus.UNVERIFIED,
                proposed_by_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                category=RootCauseCategory.MECHANICAL_WEAR,
                subsystem="Foundation Anchor Assembly",
                identified_at=now,
            )
            return [h1, h2, h3]

        elif anomaly_type == AnomalyType.OVERHEATING:
            h1 = CandidateRootCause(
                cause_id=f"RC-{machine_id}-01",
                description="Coolant flow restriction or heat exchanger fouling in spindle cooling jacket.",
                hypothesis="Particulate contamination in the closed-loop cooling system has restricted fluid flow, causing rapid thermal buildup under normal machine operating load.",
                confidence=0.82,
                confidence_category=ConfidenceStatus.HIGH,
                supporting_evidence_ids=ev_ids,
                contradicting_evidence_ids=[],
                maintenance_history_references=maint_refs[:1] if maint_refs else [],
                citation_ids=cit_ids[:2] if cit_ids else [],
                verification_status=VerificationStatus.UNVERIFIED,
                proposed_by_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                category=RootCauseCategory.COOLING_FAILURE,
                subsystem="Spindle Closed-Loop Cooling Jacket",
                identified_at=now,
            )
            h2 = CandidateRootCause(
                cause_id=f"RC-{machine_id}-02",
                description="Lubricant thermal breakdown and viscosity degradation.",
                hypothesis="High-speed synthetic grease has undergone thermal oxidation and oil bleed, increasing frictional heating between rolling elements and raceways.",
                confidence=0.68,
                confidence_category=ConfidenceStatus.MODERATE,
                supporting_evidence_ids=ev_ids[:1] if ev_ids else [],
                contradicting_evidence_ids=[],
                maintenance_history_references=[],
                citation_ids=cit_ids[1:3] if len(cit_ids) >= 3 else cit_ids,
                verification_status=VerificationStatus.UNVERIFIED,
                proposed_by_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                category=RootCauseCategory.LUBRICATION_FAILURE,
                subsystem="Bearing Lubrication Circuit",
                identified_at=now,
            )
            return [h1, h2]

        elif anomaly_type == AnomalyType.PRESSURE_DROP:
            h1 = CandidateRootCause(
                cause_id=f"RC-{machine_id}-01",
                description="Pneumatic/hydraulic pressure relief valve seat leakage or regulator failure.",
                hypothesis="Main pressure relief valve cartridge seal has sustained particulate wear, allowing internal pressure bypass back to reservoir.",
                confidence=0.85,
                confidence_category=ConfidenceStatus.HIGH,
                supporting_evidence_ids=ev_ids,
                contradicting_evidence_ids=[],
                maintenance_history_references=maint_refs[:1] if maint_refs else [],
                citation_ids=cit_ids[:2] if cit_ids else [],
                verification_status=VerificationStatus.UNVERIFIED,
                proposed_by_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                category=RootCauseCategory.PRESSURE_SYSTEM_FAULT,
                subsystem="Main Pressure Regulation Block",
                identified_at=now,
            )
            h2 = CandidateRootCause(
                cause_id=f"RC-{machine_id}-02",
                description="Actuator cylinder piston seal degradation and blow-by leakage.",
                hypothesis="Elastomer quad-ring seal on primary hydraulic cylinder piston has degraded, permitting fluid slip between working chambers.",
                confidence=0.60,
                confidence_category=ConfidenceStatus.MODERATE,
                supporting_evidence_ids=ev_ids[:1] if ev_ids else [],
                contradicting_evidence_ids=[],
                maintenance_history_references=[],
                citation_ids=[],
                verification_status=VerificationStatus.UNVERIFIED,
                proposed_by_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                category=RootCauseCategory.PRESSURE_SYSTEM_FAULT,
                subsystem="Primary Hydraulic Actuator",
                identified_at=now,
            )
            return [h1, h2]

        elif anomaly_type == AnomalyType.ELECTRICAL_FAULT:
            h1 = CandidateRootCause(
                cause_id=f"RC-{machine_id}-01",
                description="Stator winding insulation thermal breakdown and inter-turn short.",
                hypothesis="Drive motor phase current spikes indicate localized dielectric insulation breakdown across the stator winding turns.",
                confidence=0.80,
                confidence_category=ConfidenceStatus.HIGH,
                supporting_evidence_ids=ev_ids,
                contradicting_evidence_ids=[],
                maintenance_history_references=maint_refs[:1] if maint_refs else [],
                citation_ids=cit_ids[:2] if cit_ids else [],
                verification_status=VerificationStatus.UNVERIFIED,
                proposed_by_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                category=RootCauseCategory.ELECTRICAL_FAULT,
                subsystem="Main Drive Motor Stator Assembly",
                identified_at=now,
            )
            return [h1]

        # Default fallback for UNKNOWN or unspecified anomaly types
        return [
            CandidateRootCause(
                cause_id=f"RC-{machine_id}-UNK",
                description="Unresolved machine anomaly with insufficient causal telemetry signature.",
                hypothesis="Observed telemetry divergence cannot be mapped with confidence to a known mechanical failure mode without physical field inspection.",
                confidence=0.35,
                confidence_category=ConfidenceStatus.LOW,
                supporting_evidence_ids=ev_ids,
                contradicting_evidence_ids=[],
                maintenance_history_references=[],
                citation_ids=cit_ids[:1] if cit_ids else [],
                verification_status=VerificationStatus.UNVERIFIED,
                proposed_by_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                category=RootCauseCategory.UNKNOWN,
                subsystem="Unspecified Subsystem",
                identified_at=now,
            )
        ]


def get_llm_client() -> ManuMindLLMClient:
    """
    Factory creating configured LLM client based on MANUMIND_LLM_PROVIDER environment variable.
    Defaults to DeterministicMockLLMClient if unconfigured or set to 'mock'.
    """
    provider = os.getenv("MANUMIND_LLM_PROVIDER", "mock").lower().strip()
    if provider == "mock":
        return DeterministicMockLLMClient()
    # In offline or non-live test environments, always default safely to DeterministicMockLLMClient
    return DeterministicMockLLMClient()
