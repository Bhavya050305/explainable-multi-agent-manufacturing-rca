"""
ManuMind AI — Grounded Answer Generation Service Orchestrator
Phase 3 Step 6: Grounded Generation Pipeline

Department of AI & Data Science — RMK Engineering College
"""

import time
from typing import Optional

from backend.app.rag.context_builder import EvidenceContextBuilder, context_builder
from backend.app.rag.generation_config import GenerationConfig, generation_config
from backend.app.rag.generation_schemas import (
    AbstentionReason,
    ConfidenceLabel,
    GroundedAnswer,
)
from backend.app.rag.grounding_validator import GroundingValidator, grounding_validator
from backend.app.rag.prompt_templates import (
    check_operational_command,
    check_prompt_injection,
    classify_safety_intent,
)
from backend.app.rag.providers.base import BaseLLMProvider
from backend.app.rag.providers.factory import provider_factory
from backend.app.rag.query_processor import QueryProcessor, query_processor
from backend.app.rag.retrieval_config import retrieval_config
from backend.app.rag.retrieval_schemas import RetrievalFilter, RetrievalMode
from backend.app.rag.retrieval_service import RetrievalService, retrieval_service


class GroundedGenerationService:
    """
    Orchestrates evidence retrieval, context bounding, prompt construction,
    provider inference, citation validation, and manufacturing governance enforcement.
    """

    def __init__(
        self,
        retrieval_svc: Optional[RetrievalService] = None,
        ctx_builder: Optional[EvidenceContextBuilder] = None,
        validator: Optional[GroundingValidator] = None,
        query_proc: Optional[QueryProcessor] = None,
        config: GenerationConfig = generation_config,
    ):
        self.retrieval_service = retrieval_svc or retrieval_service
        self.context_builder = ctx_builder or context_builder
        self.validator = validator or grounding_validator
        self.query_processor = query_proc or query_processor
        self.config = config

    def generate_grounded_answer(
        self,
        query_text: str,
        machine_id: Optional[str] = None,
        filter_spec: Optional[RetrievalFilter] = None,
        provider_name: Optional[str] = None,
        top_k: int = 5,
    ) -> GroundedAnswer:
        """
        End-to-end grounded generation workflow.
        Args:
            query_text: Natural-language manufacturing question.
            machine_id: Optional target machine asset (e.g., 'M104').
            filter_spec: Optional high-level metadata filter.
            provider_name: Optional LLM provider override ('mock', 'gemini', etc.).
            top_k: Number of retrieved segments to consider.
        Returns:
            Validated GroundedAnswer model instance.
        """
        start_overall = time.perf_counter()

        # 1. Query Processing & Normalization
        processed_query = self.query_processor.process_query(query_text)
        effective_machine = machine_id or processed_query.extracted_machine_id

        # 2. Select Provider
        provider: BaseLLMProvider = provider_factory.get_provider(provider_name)

        # Pre-Retrieval Intent Safety Gate
        safety_intent = classify_safety_intent(query_text)
        if safety_intent == AbstentionReason.PROMPT_INJECTION_DETECTED:
            latency = (time.perf_counter() - start_overall) * 1000
            return GroundedAnswer(
                query=query_text,
                answer="ABSTAINED: Adversarial prompt injection or security policy override detected. Request rejected.",
                summary="Security policy violation: prompt injection attempt blocked.",
                observed_evidence=[],
                possible_explanations=[],
                recommended_investigations=["Verify user input source and integrity."],
                uncertainties=["Request violates system safety boundary."],
                citations=[],
                confidence_label=ConfidenceLabel.ABSTAINED,
                abstained=True,
                abstention_reason=AbstentionReason.PROMPT_INJECTION_DETECTED,
                is_synthetic=True,
                provider=provider.provider_name,
                model_identifier=provider.model_identifier,
                generation_latency_ms=round(latency, 2),
                total_latency_ms=round(latency, 2),
                validation_passed=True,
            )

        if safety_intent == AbstentionReason.SAFETY_INTERLOCK_VIOLATION:
            latency = (time.perf_counter() - start_overall) * 1000
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
                provider=provider.provider_name,
                model_identifier=provider.model_identifier,
                generation_latency_ms=round(latency, 2),
                total_latency_ms=round(latency, 2),
                validation_passed=True,
            )

        if safety_intent == AbstentionReason.UNAUTHORIZED_OPERATIONAL_COMMAND:
            latency = (time.perf_counter() - start_overall) * 1000
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
                provider=provider.provider_name,
                model_identifier=provider.model_identifier,
                generation_latency_ms=round(latency, 2),
                total_latency_ms=round(latency, 2),
                validation_passed=True,
            )

        # Pre-Retrieval Safety Gate: Fleet Asset Boundary (Unknown / Invalid Machine ID)
        if effective_machine and effective_machine.upper() not in retrieval_config.VALID_MACHINES:
            latency = (time.perf_counter() - start_overall) * 1000
            return GroundedAnswer(
                query=query_text,
                answer=(
                    f"ABSTAINED: Asset boundary mismatch. Machine identifier '{effective_machine}' is not a recognized "
                    f"asset in the manufacturing plant fleet (valid assets: M101–M110). To prevent dangerous machine "
                    f"cross-contamination, diagnostic generation is withheld."
                ),
                summary=f"Asset mismatch: machine '{effective_machine}' does not exist in plant registry.",
                observed_evidence=[],
                possible_explanations=[],
                recommended_investigations=[
                    f"Confirm operating logs and maintenance manual for target asset {effective_machine}.",
                    "Verify target asset tag against active plant fleet (M101–M110)."
                ],
                uncertainties=[f"Asset {effective_machine} is not present in plant registry."],
                citations=[],
                confidence_label=ConfidenceLabel.ABSTAINED,
                abstained=True,
                abstention_reason=AbstentionReason.MACHINE_MISMATCH,
                is_synthetic=True,
                provider=provider.provider_name,
                model_identifier=provider.model_identifier,
                generation_latency_ms=round(latency, 2),
                total_latency_ms=round(latency, 2),
                validation_passed=True,
            )

        # 3. Step 5 Semantic Retrieval
        start_ret = time.perf_counter()
        if filter_spec is None and effective_machine:
            filter_spec = RetrievalFilter(
                machine_id=effective_machine,
                include_global=True,
                cross_machine=False,
            )

        retrieval_resp = self.retrieval_service.retrieve(
            query=processed_query.original_query,
            filter=filter_spec,
            top_k=top_k,
        )
        ret_latency_ms = (time.perf_counter() - start_ret) * 1000

        # 4. Evidence Context Assembly & Bounding
        context = self.context_builder.build_context(
            retrieval_response=retrieval_resp,
            target_machine_id=effective_machine,
        )

        # 5. LLM Inference / Synthesis
        start_gen = time.perf_counter()
        answer = provider.generate(
            query_text=processed_query.original_query,
            context=context,
            target_machine_id=effective_machine,
        )
        gen_latency_ms = (time.perf_counter() - start_gen) * 1000

        # 6. Independent Grounding & Citation Validation
        val_result = self.validator.validate(answer=answer, context=context)

        # 7. Post-Validation Adjustment if necessary
        answer.validation_passed = val_result.is_valid
        answer.validation_notes = val_result.errors + [f"WARNING: {w}" for w in val_result.warnings]

        total_latency_ms = (time.perf_counter() - start_overall) * 1000
        answer.retrieval_latency_ms = round(ret_latency_ms, 2)
        answer.generation_latency_ms = round(gen_latency_ms, 2)
        answer.total_latency_ms = round(total_latency_ms, 2)

        return answer

    def generate_answer(
        self,
        query_text: str,
        target_machine_id: Optional[str] = None,
        category: Optional[str] = None,
        provider_name: Optional[str] = None,
        top_k: int = 5,
    ) -> GroundedAnswer:
        """Alias for generate_grounded_answer accepting target_machine_id and category."""
        filter_spec = None
        if category:
            filter_spec = RetrievalFilter(
                category=category,
                machine_id=target_machine_id,
                cross_machine=(target_machine_id is None),
            )
        return self.generate_grounded_answer(
            query_text=query_text,
            machine_id=target_machine_id,
            filter_spec=filter_spec,
            provider_name=provider_name,
            top_k=top_k,
        )

    def investigate_machine_anomaly(
        self,
        query_text: str,
        machine_id: str,
        anomaly_type: Optional[str] = None,
    ) -> GroundedAnswer:
        """Convenience method for asset-specific anomaly investigation."""
        filter_spec = RetrievalFilter(
            machine_id=machine_id,
            include_global=True,
            cross_machine=False,
        )
        return self.generate_grounded_answer(
            query_text=query_text,
            machine_id=machine_id,
            filter_spec=filter_spec,
        )

    def investigate_safety_protocol(self, query_text: str) -> GroundedAnswer:
        """Convenience method for safety-critical protocol inquiries."""
        filter_spec = RetrievalFilter(
            is_safety_related=True,
            cross_machine=True,
        )
        return self.generate_grounded_answer(
            query_text=query_text,
            filter_spec=filter_spec,
        )

    def investigate_historical_incident(
        self,
        query_text: str,
        machine_id: Optional[str] = None,
    ) -> GroundedAnswer:
        """Convenience method for historical incident synthesis."""
        filter_spec = RetrievalFilter(
            category="INCIDENT",
            machine_id=machine_id,
            cross_machine=(machine_id is None),
        )
        return self.generate_grounded_answer(
            query_text=query_text,
            machine_id=machine_id,
            filter_spec=filter_spec,
        )


generation_service = GroundedGenerationService()
