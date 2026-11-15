"""
ManuMind AI — Deterministic Grounded Mock LLM Provider
Phase 3 Step 6: Grounded Generation Pipeline

Department of AI & Data Science — RMK Engineering College
"""

import time
from typing import List, Optional

from backend.app.rag.context_builder import EvidenceContext
from backend.app.rag.generation_config import generation_config
from backend.app.rag.generation_schemas import (
    AbstentionReason,
    Citation,
    ConfidenceLabel,
    GroundedAnswer,
)
from backend.app.rag.prompt_templates import (
    check_operational_command,
    check_prompt_injection,
    classify_safety_intent,
)
from backend.app.rag.providers.base import BaseLLMProvider


class MockGroundedProvider(BaseLLMProvider):
    """
    Deterministic, offline generation engine.
    Produces strictly grounded manufacturing diagnostic responses derived from retrieved context.
    Executes entirely offline with zero external network dependency.
    """

    def __init__(self, model_name: str = generation_config.MOCK_MODEL_NAME):
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_identifier(self) -> str:
        return self._model_name

    def generate(
        self,
        query_text: str,
        context: EvidenceContext,
        target_machine_id: Optional[str] = None,
    ) -> GroundedAnswer:
        start_t = time.perf_counter()

        # 1. Safety Intent Defense Gate
        safety_intent = classify_safety_intent(query_text)
        if safety_intent == AbstentionReason.PROMPT_INJECTION_DETECTED:
            latency = (time.perf_counter() - start_t) * 1000
            return GroundedAnswer(
                query=query_text,
                answer=(
                    "ABSTAINED: Security policy violation detected. The submitted query contains unauthorized "
                    "prompt-injection or instruction-override directives. ManuMind AI only responds to technical "
                    "manufacturing investigation requests."
                ),
                summary="Security policy violation: query contained prompt injection directives.",
                observed_evidence=[],
                possible_explanations=[],
                recommended_investigations=[],
                uncertainties=["Query was rejected prior to knowledge synthesis."],
                citations=[],
                confidence_label=ConfidenceLabel.ABSTAINED,
                abstained=True,
                abstention_reason=AbstentionReason.PROMPT_INJECTION_DETECTED,
                is_synthetic=True,
                provider=self.provider_name,
                model_identifier=self.model_identifier,
                generation_latency_ms=round(latency, 2),
            )

        if safety_intent == AbstentionReason.SAFETY_INTERLOCK_VIOLATION:
            latency = (time.perf_counter() - start_t) * 1000
            return GroundedAnswer(
                query=query_text,
                answer=(
                    "ABSTAINED: Safety interlock violation detected. Bypassing safety interlocks, lockout/tagout (LOTO) "
                    "protocols, or protective shutdowns is strictly prohibited in manufacturing operations. "
                    "ManuMind AI will not assist in circumventing safety mechanisms."
                ),
                summary="Safety policy violation: safety interlock or LOTO bypass directives are strictly prohibited.",
                observed_evidence=[],
                possible_explanations=[],
                recommended_investigations=["All safety interlocks and LOTO procedures must remain active and physically verified."],
                uncertainties=["Interlock and protective shutdown states cannot be overridden."],
                citations=[],
                confidence_label=ConfidenceLabel.ABSTAINED,
                abstained=True,
                abstention_reason=AbstentionReason.SAFETY_INTERLOCK_VIOLATION,
                is_synthetic=True,
                provider=self.provider_name,
                model_identifier=self.model_identifier,
                generation_latency_ms=round(latency, 2),
            )

        if safety_intent == AbstentionReason.UNAUTHORIZED_OPERATIONAL_COMMAND:
            latency = (time.perf_counter() - start_t) * 1000
            return GroundedAnswer(
                query=query_text,
                answer=(
                    "ABSTAINED: Industrial safety violation. ManuMind AI is an explainable decision-support system "
                    "and is strictly prohibited from executing physical machinery commands or overriding safety interlocks."
                ),
                summary="Safety policy violation: automated machine execution is strictly prohibited.",
                observed_evidence=[],
                possible_explanations=[],
                recommended_investigations=["All physical operations require manual technician authorization on-site."],
                uncertainties=["System cannot verify physical equipment state."],
                citations=[],
                confidence_label=ConfidenceLabel.ABSTAINED,
                abstained=True,
                abstention_reason=AbstentionReason.UNAUTHORIZED_OPERATIONAL_COMMAND,
                is_synthetic=True,
                provider=self.provider_name,
                model_identifier=self.model_identifier,
                generation_latency_ms=round(latency, 2),
            )

        # 3. Evidence Presence & Quality Gate
        if context.is_empty:
            latency = (time.perf_counter() - start_t) * 1000
            reason = (
                AbstentionReason.OUT_OF_DOMAIN_QUERY
                if context.highest_similarity < 0.55
                else AbstentionReason.NO_EVALUATED_EVIDENCE
            )
            return GroundedAnswer(
                query=query_text,
                answer=(
                    "ABSTAINED: Insufficient technical evidence retrieved. The knowledge base does not contain "
                    "authoritative documentation or telemetry records meeting the required relevance threshold "
                    f"({generation_config.MIN_SIMILARITY_FOR_GROUNDING:.2f}) to answer this inquiry accurately."
                ),
                summary="Insufficient relevant manufacturing documentation found in knowledge base.",
                observed_evidence=[],
                possible_explanations=[],
                recommended_investigations=[
                    "Verify asset identifier and sensor telemetry channel.",
                    "Review physical equipment service manual for undocumented anomalies."
                ],
                uncertainties=["Knowledge base contains no matching technical procedures."],
                citations=[],
                confidence_label=ConfidenceLabel.ABSTAINED,
                abstained=True,
                abstention_reason=reason,
                is_synthetic=True,
                provider=self.provider_name,
                model_identifier=self.model_identifier,
                generation_latency_ms=round(latency, 2),
            )

        # 4. Machine Identity Mismatch Gate
        if context.has_machine_mismatch and target_machine_id:
            latency = (time.perf_counter() - start_t) * 1000
            return GroundedAnswer(
                query=query_text,
                answer=(
                    f"ABSTAINED: Asset boundary mismatch. The query specifically requested diagnostics for "
                    f"machine asset '{target_machine_id}', but retrieved technical evidence belongs to different fleet "
                    f"assets. To prevent cross-machine contamination, generation is withheld."
                ),
                summary=f"Asset mismatch: retrieved evidence does not apply to machine {target_machine_id}.",
                observed_evidence=[],
                possible_explanations=[],
                recommended_investigations=[
                    f"Confirm operating logs and maintenance manual for target asset {target_machine_id}."
                ],
                uncertainties=[f"Procedures for {target_machine_id} are missing or unindexed."],
                citations=[],
                confidence_label=ConfidenceLabel.ABSTAINED,
                abstained=True,
                abstention_reason=AbstentionReason.MACHINE_MISMATCH,
                is_synthetic=True,
                provider=self.provider_name,
                model_identifier=self.model_identifier,
                generation_latency_ms=round(latency, 2),
            )

        # 5. Missing Specification Gate (when query asks for numerical spec and evidence only has placeholders)
        query_lower = query_text.lower()
        spec_trigger_terms = [
            "exact", "certified factory", "in ft-lbs", "numerical limit", "numerical tolerance", "numerical rpm"
        ]
        if context.has_placeholders and any(kw in query_lower for kw in spec_trigger_terms):
            latency = (time.perf_counter() - start_t) * 1000
            return GroundedAnswer(
                query=query_text,
                answer=(
                    "ABSTAINED: Missing engineering specification. The relevant operating documentation marks the requested "
                    f"threshold as an uncalibrated placeholder ({', '.join(context.detected_placeholders)} [CIT-1]). "
                    "ManuMind AI adheres to strict safety boundaries and refuses to invent numerical engineering limits."
                ),
                summary="Requested engineering parameter is marked with an uncalibrated specification placeholder.",
                observed_evidence=[f"Document contains specification placeholder token: {context.detected_placeholders[0]} [CIT-1]"],
                possible_explanations=["Manufacturer baseline calibration has not been formally certified for this asset."],
                recommended_investigations=["Consult certified OEM machine specification sheet before commissioning."],
                uncertainties=["Exact numerical tolerance is undefined in synthetic demonstration corpus."],
                citations=[list(context.citation_map.values())[0]],
                confidence_label=ConfidenceLabel.ABSTAINED,
                abstained=True,
                abstention_reason=AbstentionReason.MISSING_SPECIFICATION,
                is_synthetic=True,
                provider=self.provider_name,
                model_identifier=self.model_identifier,
                generation_latency_ms=round(latency, 2),
            )

        # 6. Synthesize Grounded Technical Answer
        citations: List[Citation] = list(context.citation_map.values())
        observed_evidence: List[str] = []
        possible_explanations: List[str] = []
        recommended_investigations: List[str] = []
        uncertainties: List[str] = []

        # Extract structured findings from cited items
        for cit in citations:
            cid = cit.citation_id
            cat = cit.category
            heading = cit.section_heading
            doc = cit.document_id

            if cat == "SOP":
                observed_evidence.append(
                    f"Operating baseline documentation for {cit.machine_id or 'fleet'} ({doc}) specifies standard "
                    f"inspection intervals under section '{heading}' {cid}."
                )
                recommended_investigations.append(
                    f"Perform baseline startup verification according to {doc} section '{heading}' {cid}."
                )
            elif cat == "TROUBLESHOOTING":
                possible_explanations.append(
                    f"Retrieved diagnostic guide ({doc}) identifies potential component wear or subsystem failure "
                    f"consistent with observed telemetry ({heading}) {cid}."
                )
                recommended_investigations.append(
                    f"Execute phased physical inspection workflow outlined in {doc} {cid}."
                )
            elif cat == "SAFETY":
                observed_evidence.append(
                    f"Mandatory safety protocol ({doc}) requires isolation and PPE under section '{heading}' {cid}."
                )
                recommended_investigations.append(
                    f"Strictly enforce zero-energy state verification according to {doc} {cid} before physical access."
                )
            elif cat == "INCIDENT":
                rec_id = cit.source_record_id or f"Row {cit.original_row_index}"
                observed_evidence.append(
                    f"Historical maintenance log ({doc}, {rec_id}) records a prior occurrence for asset "
                    f"{cit.machine_id} involving corrective maintenance actions {cid}."
                )
                possible_explanations.append(
                    f"Historical recurrence pattern observed in prior incident {rec_id} {cid}."
                )

        # Standard manufacturing uncertainties
        uncertainties.append(
            "Sensor anomaly attribution represents correlational machine learning telemetry and does NOT constitute "
            "confirmed physical causality until on-site teardown verification is performed."
        )
        uncertainties.append(
            "All retrieved evidence originates from the ManuMind AI synthetic demonstration knowledge base."
        )

        if context.has_placeholders:
            uncertainties.append(
                f"Note: Retrieved documentation contains uncalibrated specification placeholders: "
                f"{', '.join(context.detected_placeholders)}."
            )

        # Format full grounded answer prose
        target_display = f"machine {target_machine_id}" if target_machine_id else "the production line"
        answer_parts = [
            f"Based on authoritative technical documentation retrieved for {target_display}:",
            "\n**Observed Technical Evidence & Baseline Criteria:**",
            "\n".join(f"- {item}" for item in observed_evidence[:3]),
            "\n**Engineering Hypotheses & Potential Root Causes:**",
            "\n".join(f"- {item}" for item in possible_explanations[:3]) if possible_explanations else "- Diagnostic guide telemetry indicates potential mechanical subsystem degradation [CIT-1].",
            "\n**Recommended Physical Diagnostic Investigations:**",
            "\n".join(f"- {item}" for item in recommended_investigations[:3]),
            "\n**Manufacturing Safety & Epistemic Boundaries:**",
            "- IMPORTANT: Sensor telemetry attribution is an indicative anomaly signal, not confirmed physical causality.",
            "- Technicians must perform physical inspection and follow full lockout/tagout procedures prior to service.",
            "- Demonstration Notice: Evidence retrieved from synthetic manufacturing knowledge base.",
        ]

        full_answer = "\n".join(answer_parts)
        summary = (
            f"Retrieved {len(citations)} technical documents for {target_display}. Identified indicative "
            f"telemetry patterns and phased physical inspection workflows. Physical teardown required to confirm causality."
        )

        # Determine calibrated confidence label
        if context.highest_similarity >= generation_config.HIGH_CONFIDENCE_SIMILARITY and len(citations) >= 2:
            confidence = ConfidenceLabel.HIGH
        elif context.highest_similarity >= generation_config.MIN_SIMILARITY_FOR_GROUNDING:
            confidence = ConfidenceLabel.MEDIUM
        else:
            confidence = ConfidenceLabel.LOW

        latency = (time.perf_counter() - start_t) * 1000

        return GroundedAnswer(
            query=query_text,
            answer=full_answer,
            summary=summary,
            observed_evidence=observed_evidence[:4],
            possible_explanations=possible_explanations[:4],
            recommended_investigations=recommended_investigations[:4],
            uncertainties=uncertainties,
            citations=citations,
            confidence_label=confidence,
            abstained=False,
            abstention_reason=None,
            is_synthetic=True,
            source_provenance="SYNTHETIC_DEMONSTRATION",
            provider=self.provider_name,
            model_identifier=self.model_identifier,
            generation_latency_ms=round(latency, 2),
        )


mock_grounded_provider = MockGroundedProvider()
