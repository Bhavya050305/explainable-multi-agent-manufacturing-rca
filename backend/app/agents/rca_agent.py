"""
ManuMind AI — Root Cause Analysis (RCA) Agent Implementation
Investigates manufacturing anomalies using multi-source evidence:
1. Anomaly Detection Agent assessments and sensor feature attributions.
2. Historical maintenance logs from SQLite asset registry.
3. Manufacturing SOPs and technical manuals via RAG retrieval bridge.
4. Domain-specific diagnostic reasoning via provider-independent LLM client.

Architectural Governance & Security Invariants:
- Generates multiple competing candidate root-cause hypotheses with explicit confidence scoring.
- Distinguishes strictly between hypothesis formulation and authoritative verification.
- The RCA Agent CANNOT mark a candidate root cause as VERIFIED.
- Strictly forbidden from modifying human_approval, verification_decisions, or workflow_status.
- Enforces source-diversity corroboration and preserves citation provenance ([CIT-X]).
- Transparently discloses synthetic data, evidence limitations, and operational uncertainty.
"""

from copy import deepcopy
from datetime import datetime, timezone
import logging
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from pydantic import ValidationError

from backend.app.agents.enums import (
    AgentExecutionStatus,
    AgentName,
    AnomalyExecutionStatus,
    AnomalySeverity,
    AnomalyType,
    ConfidenceStatus,
    EvidenceSourceAvailability,
    EvidenceSourceType,
    ExecutionMode,
    RCAExecutionStatus,
    RootCauseCategory,
    VerificationStatus,
)
from backend.app.agents.llm_client import (
    DeterministicMockLLMClient,
    ManuMindLLMClient,
    get_llm_client,
)
from backend.app.agents.reducers import validate_agent_state_update
from backend.app.agents.schemas import (
    AgentExecutionRecord,
    AnomalyAssessment,
    AnomalyDetectionResult,
    CandidateRootCause,
    EvidenceItem,
    RootCauseAnalysisResult,
    _sanitize_string,
)
from backend.app.agents.state import (
    ManuMindState,
    ManuMindStateModel,
    validate_state,
)

logger = logging.getLogger("RootCauseAnalysisAgent")


class RootCauseAnalysisAgent:
    """
    Root Cause Analysis (RCA) Agent for manufacturing systems.
    Coordinates evidence aggregation across sensor telemetry, maintenance logs,
    and technical documentation to formulate explainable, ranked root-cause hypotheses.
    """

    def __init__(
        self,
        llm_client: Optional[ManuMindLLMClient] = None,
        maintenance_service: Optional[Any] = None,
        rag_service: Optional[Any] = None,
    ):
        """
        Initializes RCA Agent with optional dependency injection for testing.
        Defaults to configured singleton services if not explicitly provided.
        """
        self.llm_client = llm_client or get_llm_client()
        self._maintenance_service = maintenance_service
        self._rag_service = rag_service

    def _get_maintenance_service(self) -> Any:
        """Resolves maintenance history retrieval service."""
        if self._maintenance_service is not None:
            return self._maintenance_service
        try:
            from backend.app.mcp_server.tools import handle_get_maintenance_history
            return handle_get_maintenance_history
        except Exception as exc:
            logger.warning(f"Could not import handle_get_maintenance_history: {exc}")
            return None

    def _get_rag_service(self) -> Any:
        """Resolves RAG manual search service."""
        if self._rag_service is not None:
            return self._rag_service
        try:
            from backend.app.mcp_server.tools import handle_search_manuals
            return handle_search_manuals
        except Exception as exc:
            logger.warning(f"Could not import handle_search_manuals: {exc}")
            return None

    def _validate_input_state(
        self, state: Union[ManuMindState, Dict[str, Any]]
    ) -> Tuple[str, AnomalyAssessment, AnomalyDetectionResult, bool]:
        """
        Validates that input state contains a valid machine ID and a successful anomaly detection.
        Raises ValueError if prerequisites are missing, malformed, or indicate a failed anomaly run.
        """
        machine_id = state.get("machine_id")
        if not machine_id or not isinstance(machine_id, str) or not machine_id.strip():
            raise ValueError("Input state missing valid machine_id.")

        # Check anomaly assessment
        assessment = state.get("anomaly_assessment")
        if assessment is None:
            raise ValueError("Input state missing anomaly_assessment: cannot run RCA without anomaly evaluation.")

        if isinstance(assessment, dict):
            try:
                assessment = AnomalyAssessment.model_validate(assessment)
            except ValidationError as err:
                raise ValueError(f"Malformed anomaly_assessment in state: {err}") from err

        # Verify execution status of anomaly detection
        if assessment.execution_status != AnomalyExecutionStatus.SUCCESS:
            raise ValueError(
                f"RCA investigation aborted: Anomaly assessment reported non-successful status "
                f"({assessment.execution_status.value}). RCA requires successful anomaly detection."
            )

        if not assessment.anomaly_detected:
            raise ValueError(
                "RCA investigation aborted: Anomaly assessment indicates healthy equipment (anomaly_detected=False). "
                "RCA is only triggered for confirmed anomalous conditions."
            )

        # Check anomaly detection result
        detection_result = state.get("anomaly_detection_result")
        if detection_result is None:
            raise ValueError("Input state missing anomaly_detection_result.")

        if isinstance(detection_result, dict):
            try:
                detection_result = AnomalyDetectionResult.model_validate(detection_result)
            except ValidationError as err:
                raise ValueError(f"Malformed anomaly_detection_result in state: {err}") from err

        if detection_result.execution_status != AnomalyExecutionStatus.SUCCESS:
            raise ValueError(
                f"RCA investigation aborted: Anomaly detection result status is {detection_result.execution_status.value}."
            )

        is_synthetic = bool(
            getattr(assessment, "is_synthetic", False)
            or (state.get("sensor_measurements") and getattr(state.get("sensor_measurements"), "is_synthetic", False))
        )

        return machine_id.strip(), assessment, detection_result, is_synthetic

    def _fetch_maintenance_history(
        self, machine_id: str
    ) -> Tuple[List[Dict[str, Any]], EvidenceSourceAvailability, Optional[str]]:
        """
        Retrieves historical maintenance records for the machine via MCP tool or injected service.
        Returns records list, availability status, and error message if any.
        """
        service = self._get_maintenance_service()
        if service is None:
            return [], EvidenceSourceAvailability.UNAVAILABLE, "Maintenance history service unconfigured"

        try:
            res = service(machine_id=machine_id, limit=50)
            if not isinstance(res, dict):
                return [], EvidenceSourceAvailability.FAILED, f"Unexpected response type from maintenance service: {type(res).__name__}"

            status = res.get("status", "SUCCESS")
            records = res.get("records", [])

            if status == "NO_DATA" or not records:
                return [], EvidenceSourceAvailability.EMPTY, None

            return records, EvidenceSourceAvailability.AVAILABLE, None
        except Exception as exc:
            logger.warning(f"Maintenance history retrieval failed for {machine_id}: {exc}")
            return [], EvidenceSourceAvailability.FAILED, str(exc)

    def _fetch_rag_manuals(
        self, query: str, k: int = 5
    ) -> Tuple[List[Dict[str, Any]], EvidenceSourceAvailability, Optional[str]]:
        """
        Queries manufacturing manuals and SOPs via RAG bridge subprocess.
        Returns validated result items, availability status, and error message if any.
        """
        service = self._get_rag_service()
        if service is None:
            return [], EvidenceSourceAvailability.UNAVAILABLE, "RAG search service unconfigured"

        try:
            res = service(query=query, k=k)
            if not isinstance(res, dict):
                return [], EvidenceSourceAvailability.FAILED, f"Unexpected response type from RAG service: {type(res).__name__}"

            results = res.get("results", [])
            status = res.get("status", "SUCCESS")

            if status == "NO_RESULTS" or not results:
                return [], EvidenceSourceAvailability.EMPTY, None

            # Sanitize content in retrieved documents to prevent prompt injection
            sanitized_results: List[Dict[str, Any]] = []
            for r in results:
                if isinstance(r, dict):
                    clean_r = dict(r)
                    if "content" in clean_r and isinstance(clean_r["content"], str):
                        clean_r["content"] = _sanitize_string(clean_r["content"]) or ""
                    sanitized_results.append(clean_r)

            return sanitized_results, EvidenceSourceAvailability.AVAILABLE, None
        except Exception as exc:
            logger.warning(f"RAG manual retrieval failed for query '{query}': {exc}")
            return [], EvidenceSourceAvailability.FAILED, str(exc)

    def _calculate_corroboration_score(
        self,
        hypothesis: CandidateRootCause,
        assessment: AnomalyAssessment,
        maintenance_records: List[Dict[str, Any]],
        rag_results: List[Dict[str, Any]],
        source_availability: Dict[str, EvidenceSourceAvailability],
        is_synthetic: bool,
    ) -> Tuple[float, ConfidenceStatus, int, List[str], List[str]]:
        """
        Computes transparent, evidence-based corroboration support score in [0.05, 0.95].
        Note: The score is an evidence-corroboration index, NOT a calibrated probability.

        Rules:
        - Baseline prior: 0.50
        - Telemetry consistency: +0.15 if observed anomaly matches expected signature.
        - SHAP attribution confirmation: +0.10 if top SHAP feature matches hypothesis subsystem.
        - Technical manual corroboration: +0.15 if RAG manual excerpt matches mechanism.
        - Historical maintenance pattern: +0.10 if prior work orders match symptom.
        - Contradicting evidence penalty: -0.15 per contradicting item (e.g. recent brand-new replacement: -0.20).
        - Missing source penalty: -0.05 per unavailable or failed evidence source.
        - Same-source citations DO NOT count as multiple independent source types.
        - Synthetic evidence cap: maximum support score capped at 0.70.
        """
        score = 0.50
        supporting_ev_ids: List[str] = list(hypothesis.supporting_evidence_ids)
        contradicting_ev_ids: List[str] = list(hypothesis.contradicting_evidence_ids)
        distinct_source_types: Set[EvidenceSourceType] = set()

        # 1. Telemetry Evidence Evaluation
        if assessment.affected_sensors:
            distinct_source_types.add(EvidenceSourceType.TELEMETRY)
            # Check if affected sensors align with hypothesis category
            category = getattr(hypothesis, "category", None)
            if category == RootCauseCategory.BEARING_DEGRADATION and "vibration" in assessment.affected_sensors:
                score += 0.15
            elif category == RootCauseCategory.COOLING_FAILURE and "temperature" in assessment.affected_sensors:
                score += 0.15
            elif category == RootCauseCategory.PRESSURE_SYSTEM_FAULT and "pressure" in assessment.affected_sensors:
                score += 0.15
            elif category == RootCauseCategory.ELECTRICAL_FAULT and "current" in assessment.affected_sensors:
                score += 0.15
            elif category == RootCauseCategory.MISALIGNMENT and "vibration" in assessment.affected_sensors:
                score += 0.12
            else:
                score += 0.05

            # SHAP feature importance contribution
            if assessment.attribution_details and isinstance(assessment.attribution_details, dict):
                distinct_source_types.add(EvidenceSourceType.SHAP_ANALYSIS)
                importances = assessment.attribution_details.get("feature_importance", {})
                if importances:
                    top_feature = max(importances.items(), key=lambda kv: kv[1])[0] if importances else None
                    if top_feature in assessment.affected_sensors:
                        score += 0.10

        # 2. RAG Technical Manual Evaluation
        if rag_results and source_availability.get("RAG_DOCUMENT") == EvidenceSourceAvailability.AVAILABLE:
            # Check for matches between manual content and hypothesis description
            manual_match = False
            unique_doc_ids: Set[str] = set()
            for r in rag_results:
                doc_id = r.get("document_id") or r.get("segment_id") or "RAG_DOC"
                unique_doc_ids.add(doc_id)
                content = (r.get("content") or "").lower()
                desc_words = [w.lower() for w in hypothesis.description.split() if len(w) > 4]
                if any(w in content for w in desc_words):
                    manual_match = True

            if manual_match:
                score += 0.15
                distinct_source_types.add(EvidenceSourceType.RAG_DOCUMENT)
            else:
                score += 0.05
                if unique_doc_ids:
                    distinct_source_types.add(EvidenceSourceType.RAG_DOCUMENT)

        # 3. Maintenance History Evaluation
        if maintenance_records and source_availability.get("MAINTENANCE_LOG") == EvidenceSourceAvailability.AVAILABLE:
            distinct_source_types.add(EvidenceSourceType.MAINTENANCE_LOG)
            # Check for recurring issues vs recent replacements
            desc_lower = hypothesis.description.lower()
            recent_replacement = False
            recurrent_symptom = False

            for rec in maintenance_records:
                action_text = (rec.get("action") or "").lower()
                issue_text = (rec.get("issue") or "").lower()

                # Contradiction: recent component replacement with identical part
                if "replace" in action_text and any(term in action_text for term in ["bearing", "seal", "motor", "coupling"]):
                    if any(term in desc_lower for term in ["bearing", "seal", "motor", "coupling"]):
                        recent_replacement = True

                # Corroboration: recurring historical issue
                if any(term in issue_text for term in ["vibration", "leak", "hot", "noise", "pressure"]):
                    recurrent_symptom = True

            if recent_replacement:
                score -= 0.20
                contra_id = f"EV-CONTRA-MAINT-{hypothesis.cause_id}"
                if contra_id not in contradicting_ev_ids:
                    contradicting_ev_ids.append(contra_id)
            elif recurrent_symptom:
                score += 0.10

        # 4. Missing Source Penalties
        if source_availability.get("RAG_DOCUMENT") in (EvidenceSourceAvailability.FAILED, EvidenceSourceAvailability.UNAVAILABLE):
            score -= 0.05
        if source_availability.get("MAINTENANCE_LOG") in (EvidenceSourceAvailability.FAILED, EvidenceSourceAvailability.UNAVAILABLE):
            score -= 0.05

        # 5. Contradicting Evidence Penalty
        score -= len(contradicting_ev_ids) * 0.15

        # 6. Synthetic Data Constraint
        if is_synthetic:
            score = min(score, 0.70)

        # 7. Bound and Categorize
        bounded_score = round(max(0.05, min(0.95, score)), 4)
        if bounded_score >= 0.80:
            category_status = ConfidenceStatus.HIGH
        elif bounded_score >= 0.60:
            category_status = ConfidenceStatus.MODERATE
        else:
            category_status = ConfidenceStatus.LOW

        source_diversity_count = len(distinct_source_types)

        return bounded_score, category_status, source_diversity_count, supporting_ev_ids, contradicting_ev_ids

    def analyze(self, state: Union[ManuMindState, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes root cause analysis investigation over shared state:
        1. Validates input state, telemetry evidence, and prerequisite anomaly assessment.
        2. Queries maintenance logs and RAG technical documentation with error isolation.
        3. Formulates multiple candidate root-cause hypotheses via LLM client.
        4. Evaluates evidence corroboration and scores hypotheses transparently.
        5. Packages structured RootCauseAnalysisResult and partial state updates.
        6. Enforces write boundary via validate_agent_state_update(AgentName.ROOT_CAUSE_ANALYSIS, update).
        """
        start_time = time.perf_counter()
        now = datetime.now(timezone.utc)

        # 1. Input State Validation
        try:
            machine_id, assessment, detection_res, is_synthetic = self._validate_input_state(state)
        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            rec_fail = AgentExecutionRecord(
                record_id=f"EXEC-RCA-{uuid.uuid4().hex[:8].upper()}",
                agent_name=AgentName.ROOT_CAUSE_ANALYSIS,
                execution_status=AgentExecutionStatus.FAILED,
                started_at=now,
                completed_at=datetime.now(timezone.utc),
                execution_duration=round(elapsed, 4),
                error_summary=f"Input state validation failure: {str(exc)}",
            )
            update_err: Dict[str, Any] = {
                "rca_execution_status": RCAExecutionStatus.FAILED,
                "agent_executions": [rec_fail],
            }
            return validate_agent_state_update(AgentName.ROOT_CAUSE_ANALYSIS, update_err)

        # 2. Gather Evidence Sources with Explicit Availability Status
        source_availability: Dict[str, EvidenceSourceAvailability] = {
            "TELEMETRY": EvidenceSourceAvailability.AVAILABLE,
        }

        # A. Maintenance History
        maint_records, maint_avail, maint_err = self._fetch_maintenance_history(machine_id)
        source_availability["MAINTENANCE_LOG"] = maint_avail

        # B. RAG Technical Documentation
        affected_str = ", ".join(assessment.affected_sensors) if assessment.affected_sensors else "sensors"
        rag_query = f"{assessment.anomaly_type.value} failure causes and troubleshooting on machine {machine_id} affecting {affected_str}"
        rag_results, rag_avail, rag_err = self._fetch_rag_manuals(rag_query, k=5)
        source_availability["RAG_DOCUMENT"] = rag_avail

        # 3. Assemble Evidence Items and Provenance References
        evidence_items: List[EvidenceItem] = []
        supporting_evidence_ids: List[str] = list(assessment.evidence_ids)
        maint_refs: List[str] = []
        rag_citation_ids: List[str] = []

        # Add maintenance evidence items
        if maint_records and maint_avail == EvidenceSourceAvailability.AVAILABLE:
            for idx, rec in enumerate(maint_records[:3]):
                rec_id = f"EV-MAINT-{machine_id}-{rec.get('id', idx)}"
                maint_refs.append(f"WORK-ORDER-{rec.get('id', idx)}")
                supporting_evidence_ids.append(rec_id)
                evidence_items.append(
                    EvidenceItem(
                        evidence_id=rec_id,
                        source_type=EvidenceSourceType.MAINTENANCE_LOG,
                        source_reference=f"maintenance_db_record_{rec.get('id', idx)}",
                        description=f"Maintenance log on {rec.get('date')}: Issue='{rec.get('issue')}', Action='{rec.get('action')}', Outcome='{rec.get('outcome')}'",
                        observed_at=now,
                        source_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                        synthetic_data_indicator=is_synthetic,
                        relevance_score=0.75,
                        relevance_explanation="Historical maintenance intervention for identical asset",
                    )
                )

        # Add RAG documentation evidence items
        if rag_results and rag_avail == EvidenceSourceAvailability.AVAILABLE:
            for idx, r in enumerate(rag_results[:3]):
                cit_id = f"[CIT-{idx + 1}]"
                rag_citation_ids.append(cit_id)
                doc_ev_id = f"EV-RAG-{machine_id}-{idx + 1}"
                supporting_evidence_ids.append(doc_ev_id)
                evidence_items.append(
                    EvidenceItem(
                        evidence_id=doc_ev_id,
                        source_type=EvidenceSourceType.RAG_DOCUMENT,
                        source_reference=r.get("source_path") or f"manual_doc_{r.get('document_id', idx)}",
                        description=f"{cit_id} Section '{r.get('section_heading')}': {r.get('content')[:180]}...",
                        observed_at=now,
                        source_agent=AgentName.ROOT_CAUSE_ANALYSIS,
                        synthetic_data_indicator=bool(r.get("is_synthetic", is_synthetic)),
                        citation_ids=[cit_id],
                        relevance_score=round(float(r.get("similarity_score", 0.70)), 4),
                        relevance_explanation="Technical troubleshooting manual retrieval",
                    )
                )

        # 4. Formulate Root-Cause Hypotheses via LLM Client
        llm_context: Dict[str, Any] = {
            "machine_id": machine_id,
            "anomaly_type": assessment.anomaly_type.value,
            "severity": assessment.severity.value,
            "affected_sensors": assessment.affected_sensors,
            "observed_values": assessment.observed_values,
            "attribution_details": assessment.attribution_details,
            "supporting_evidence_ids": supporting_evidence_ids,
            "maintenance_history_references": maint_refs,
            "citation_ids": rag_citation_ids,
            "is_synthetic": is_synthetic,
        }

        hypotheses: List[CandidateRootCause] = []
        llm_error: Optional[str] = None

        try:
            prompt = (
                f"Analyze root cause for anomaly '{assessment.anomaly_type.value}' on machine '{machine_id}'. "
                f"Affected sensors: {assessment.affected_sensors}. Formulate ranked competing diagnostic hypotheses."
            )
            raw_hypotheses = self.llm_client.generate_root_cause_hypotheses(
                prompt=prompt,
                system_instruction="You are the ManuMind AI Root Cause Analysis Agent. Propose evidence-backed candidate root causes.",
                context=llm_context,
            )

            # Enforce that LLM hypotheses cannot assert VERIFIED status
            for hyp in raw_hypotheses:
                if hyp.verification_status == VerificationStatus.VERIFIED:
                    # Downgrade to UNVERIFIED to enforce security boundary
                    hyp = hyp.model_copy(update={"verification_status": VerificationStatus.UNVERIFIED})
                hypotheses.append(hyp)

        except Exception as exc:
            logger.warning(f"LLM root cause hypothesis generation failed: {exc}")
            llm_error = str(exc)

        # 5. Handle LLM Failure vs Corroboration
        if llm_error is not None:
            elapsed = time.perf_counter() - start_time
            rec_err = AgentExecutionRecord(
                record_id=f"EXEC-RCA-{uuid.uuid4().hex[:8].upper()}",
                agent_name=AgentName.ROOT_CAUSE_ANALYSIS,
                execution_status=AgentExecutionStatus.FAILED,
                started_at=now,
                completed_at=datetime.now(timezone.utc),
                execution_duration=round(elapsed, 4),
                error_summary=f"LLM hypothesis generation failure: {llm_error}",
            )
            result_err = RootCauseAnalysisResult(
                machine_id=machine_id,
                execution_status=RCAExecutionStatus.FAILED,
                anomaly_reference=assessment.explanation[:100],
                anomaly_type=assessment.anomaly_type,
                hypotheses=[],
                primary_hypothesis_id=None,
                supporting_evidence_ids=supporting_evidence_ids,
                contradicting_evidence_ids=[],
                rag_citations=rag_citation_ids,
                maintenance_history_findings=maint_refs,
                evidence_source_availability=source_availability,
                corroboration_summary="Root cause analysis aborted due to upstream LLM client failure.",
                uncertainty_and_limitations=f"LLM provider error: {llm_error}. No diagnostic hypotheses were fabricated.",
                recommended_diagnostic_actions=["Inspect machine physical telemetry manually", "Review LLM provider connectivity"],
                human_review_recommended=True,
                is_synthetic=is_synthetic,
                analysis_timestamp=now,
            )
            update_err = {
                "rca_execution_status": RCAExecutionStatus.FAILED,
                "root_cause_analysis_result": result_err,
                "agent_executions": [rec_err],
                "evidence_collection": evidence_items,
            }
            return validate_agent_state_update(AgentName.ROOT_CAUSE_ANALYSIS, update_err)

        # 6. Score & Corroborate Each Hypothesis
        scored_hypotheses: List[CandidateRootCause] = []
        all_contra_ids: List[str] = []

        for hyp in hypotheses:
            score, cat_status, diversity_count, supp_ids, contra_ids = self._calculate_corroboration_score(
                hypothesis=hyp,
                assessment=assessment,
                maintenance_records=maint_records,
                rag_results=rag_results,
                source_availability=source_availability,
                is_synthetic=is_synthetic,
            )
            all_contra_ids.extend(contra_ids)

            # Update hypothesis with calibrated support score and verified provenance
            updated_hyp = hyp.model_copy(
                update={
                    "confidence": score,
                    "confidence_category": cat_status,
                    "supporting_evidence_ids": list(set(supp_ids + hyp.supporting_evidence_ids)),
                    "contradicting_evidence_ids": list(set(contra_ids + hyp.contradicting_evidence_ids)),
                    "maintenance_history_references": list(set(maint_refs + hyp.maintenance_history_references)),
                    "citation_ids": list(set(rag_citation_ids + hyp.citation_ids)),
                    "verification_status": VerificationStatus.UNVERIFIED,
                }
            )
            scored_hypotheses.append(updated_hyp)

        # Sort hypotheses by confidence descending
        scored_hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        primary_id = scored_hypotheses[0].cause_id if scored_hypotheses else None
        primary_hyp_text = scored_hypotheses[0].description if scored_hypotheses else None

        # 7. Formulate Corroboration Summary and Limitations
        if len(scored_hypotheses) > 1:
            competing_summary = (
                f"Identified {len(scored_hypotheses)} competing hypotheses. "
                f"Primary candidate '{scored_hypotheses[0].cause_id}' ({scored_hypotheses[0].confidence:.2f} support) "
                f"is favored over '{scored_hypotheses[1].cause_id}' ({scored_hypotheses[1].confidence:.2f} support) "
                f"due to closer alignment with {assessment.affected_sensors} signatures."
            )
        elif scored_hypotheses:
            competing_summary = f"Single candidate hypothesis '{scored_hypotheses[0].cause_id}' supported by available evidence."
        else:
            competing_summary = "No candidate root-cause hypotheses could be formulated from available evidence."

        uncertainty_notes = (
            "Hypothesis support scores represent evidence-corroboration indices and are NOT calibrated physical failure probabilities. "
            "RCA hypotheses represent unverified technical propositions awaiting authoritative Supervisor/Human verification."
        )
        if maint_avail in (EvidenceSourceAvailability.FAILED, EvidenceSourceAvailability.UNAVAILABLE):
            uncertainty_notes += " Note: Maintenance history retrieval was unavailable."
        if rag_avail in (EvidenceSourceAvailability.FAILED, EvidenceSourceAvailability.UNAVAILABLE):
            uncertainty_notes += " Note: RAG manual retrieval was unavailable."
        if is_synthetic:
            uncertainty_notes += " Synthetic data disclosure: Telemetry or evidence sources contain synthetic observations."

        # Determine execution status
        if all(s == EvidenceSourceAvailability.AVAILABLE for s in source_availability.values()) and scored_hypotheses:
            rca_status = RCAExecutionStatus.SUCCESS
        elif any(s in (EvidenceSourceAvailability.FAILED, EvidenceSourceAvailability.UNAVAILABLE) for s in source_availability.values()):
            rca_status = RCAExecutionStatus.PARTIAL
        elif not scored_hypotheses:
            rca_status = RCAExecutionStatus.INSUFFICIENT_EVIDENCE
        else:
            rca_status = RCAExecutionStatus.SUCCESS

        # 8. Assemble RootCauseAnalysisResult
        elapsed = time.perf_counter() - start_time
        rca_result = RootCauseAnalysisResult(
            machine_id=machine_id,
            execution_status=rca_status,
            anomaly_reference=assessment.explanation[:120],
            anomaly_type=assessment.anomaly_type,
            hypotheses=scored_hypotheses,
            primary_hypothesis_id=primary_id,
            supporting_evidence_ids=list(set(supporting_evidence_ids)),
            contradicting_evidence_ids=list(set(all_contra_ids)),
            rag_citations=list(set(rag_citation_ids)),
            maintenance_history_findings=maint_refs,
            evidence_source_availability=source_availability,
            corroboration_summary=competing_summary,
            uncertainty_and_limitations=uncertainty_notes,
            recommended_diagnostic_actions=[
                f"Perform physical NDT inspection on {scored_hypotheses[0].subsystem or 'affected component'}" if scored_hypotheses else "Inspect machine",
                "Verify sensor calibration and wiring continuity",
                "Submit proposed candidate for Human Maintenance Engineer review",
            ],
            human_review_recommended=True,
            is_synthetic=is_synthetic,
            analysis_timestamp=now,
        )

        # 9. Create Execution Record
        record = AgentExecutionRecord(
            record_id=f"EXEC-RCA-{uuid.uuid4().hex[:8].upper()}",
            agent_name=AgentName.ROOT_CAUSE_ANALYSIS,
            execution_status=AgentExecutionStatus.COMPLETED,
            started_at=now,
            completed_at=datetime.now(timezone.utc),
            execution_duration=round(elapsed, 4),
            evidence_references=list(set(supporting_evidence_ids)),
        )

        # 10. Assemble State Updates (Strictly excluding forbidden worker channels)
        update: Dict[str, Any] = {
            "candidate_root_causes": scored_hypotheses,
            "supporting_evidence": list(set(supporting_evidence_ids)),
            "contradicting_evidence": list(set(all_contra_ids)),
            "maintenance_history_references": list(set(maint_refs)),
            "relevant_rag_citation_ids": list(set(rag_citation_ids)),
            "root_cause_hypothesis": primary_hyp_text,
            "evidence_collection": evidence_items,
            "root_cause_analysis_result": rca_result,
            "rca_execution_status": rca_status,
            "agent_executions": [record],
        }

        # 11. Security Boundary Validation
        validated_update = validate_agent_state_update(AgentName.ROOT_CAUSE_ANALYSIS, update)

        return validated_update


def root_cause_analysis_node(state: ManuMindState) -> Dict[str, Any]:
    """
    LangGraph StateGraph node function for ManuMind Root Cause Analysis Agent.
    Accepts typed shared state and returns validated channel updates.
    """
    agent = RootCauseAnalysisAgent()
    return agent.analyze(state)
