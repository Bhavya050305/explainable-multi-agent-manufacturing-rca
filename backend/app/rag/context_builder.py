"""
ManuMind AI — Grounded Answer Context Builder
Phase 3 Step 6: Grounded Generation Pipeline

Department of AI & Data Science — RMK Engineering College
"""

import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.rag.generation_config import GenerationConfig, generation_config
from backend.app.rag.generation_schemas import Citation
from backend.app.rag.retrieval_schemas import RetrievalResponse, RetrievalResultItem
from backend.app.rag.tokenizer_service import tokenizer_service


class EvidenceContext(BaseModel):
    """Container for assembled, bounded evidence context with citation mappings."""
    formatted_context: str
    citation_map: Dict[str, Citation] = Field(default_factory=dict)
    evidence_text_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Full text of each cited segment mapped by citation ID [CIT-X]",
    )
    retrieved_items: List[RetrievalResultItem] = Field(default_factory=list)
    has_placeholders: bool = False
    detected_placeholders: List[str] = Field(default_factory=list)
    has_machine_mismatch: bool = False
    target_machine_id: Optional[str] = None
    is_empty: bool = True
    mean_similarity: float = 0.0
    highest_similarity: float = 0.0
    total_tokens: int = Field(
        default=0,
        description="Exact context token count measured with official BGE tokenizer",
    )


class EvidenceContextBuilder:
    """
    Builds a bounded, deterministic evidence context from Step 5 retrieval results.
    Enforces token caps, prevents cross-contamination, preserves engineering symbols,
    and indexes every segment with an auditable citation token [CIT-X].
    """

    PLACEHOLDER_REGEX = re.compile(r"\[SPEC_REQUIRED:[^\]]+\]")

    def __init__(self, config: GenerationConfig = generation_config):
        self.config = config

    def build_context(
        self,
        retrieval_response: RetrievalResponse,
        target_machine_id: Optional[str] = None,
    ) -> EvidenceContext:
        """
        Assemble bounded evidence blocks from retrieval response.
        Args:
            retrieval_response: Output from Step 5 retrieval pipeline.
            target_machine_id: Fleet machine identifier if query is machine-specific.
        Returns:
            EvidenceContext model.
        """
        raw_items = retrieval_response.results
        if not raw_items:
            return EvidenceContext(
                formatted_context="[NO RELEVANT EVIDENCE RETRIEVED]",
                is_empty=True,
                target_machine_id=target_machine_id,
                total_tokens=0,
            )

        # Filter items meeting minimum grounding similarity threshold
        filtered_items = [
            item for item in raw_items
            if item.similarity_score >= self.config.MIN_SIMILARITY_FOR_GROUNDING
        ]

        if not filtered_items:
            return EvidenceContext(
                formatted_context="[NO EVIDENCE MET MINIMUM SIMILARITY THRESHOLD]",
                is_empty=True,
                target_machine_id=target_machine_id,
                highest_similarity=(raw_items[0].similarity_score if raw_items else 0.0),
                total_tokens=0,
            )

        # Candidate items up to MAX_SEGMENTS_IN_CONTEXT
        candidate_items = filtered_items[:self.config.MAX_SEGMENTS_IN_CONTEXT]

        # Iteratively assemble context blocks while strictly enforcing MAX_CONTEXT_TOKENS (2000)
        retained_items: List[RetrievalResultItem] = []
        retained_blocks: List[str] = []

        for item in candidate_items:
            tentative_cit_id = f"[CIT-{len(retained_items) + 1}]"
            mach_str = item.machine_id if item.machine_id else "PLANT-WIDE GLOBAL"
            prov_str = "SYNTHETIC_DEMONSTRATION" if item.is_synthetic else "REAL"

            candidate_block = (
                f"<evidence citation_id=\"{tentative_cit_id}\" doc_id=\"{item.document_id}\" "
                f"machine=\"{mach_str}\" category=\"{item.category}\" "
                f"section=\"{item.section_heading}\" similarity=\"{item.similarity_score:.4f}\" "
                f"provenance=\"{prov_str}\">\n"
                f"{item.content.strip()}\n"
                f"</evidence>"
            )

            tentative_context = (
                "\n\n".join(retained_blocks + [candidate_block])
                if retained_blocks
                else candidate_block
            )
            token_count = tokenizer_service.count_tokens(tentative_context)

            # Drop excess segment if adding it exceeds context budget (no partial truncation)
            if token_count > self.config.MAX_CONTEXT_TOKENS:
                break

            retained_blocks.append(candidate_block)
            retained_items.append(item)

        if not retained_items:
            return EvidenceContext(
                formatted_context="[NO EVIDENCE MET CONTEXT TOKEN BUDGET]",
                is_empty=True,
                target_machine_id=target_machine_id,
                total_tokens=0,
            )

        # Assemble final context, citations, and metadata mapping
        citation_map: Dict[str, Citation] = {}
        evidence_text_map: Dict[str, str] = {}
        all_placeholders: List[str] = []
        machine_mismatch = False

        if target_machine_id:
            target_upper = target_machine_id.upper()
            non_global_items = [it for it in retained_items if it.machine_id and it.machine_id != "NONE"]
            if non_global_items and all(it.machine_id != target_upper for it in non_global_items):
                machine_mismatch = True

        for idx, item in enumerate(retained_items, 1):
            cit_id = f"[CIT-{idx}]"

            # Detect specification placeholders
            placeholders = self.PLACEHOLDER_REGEX.findall(item.content)
            all_placeholders.extend(placeholders)

            # Extract representative snippet (first 300 chars)
            snippet = item.content.strip()
            if len(snippet) > 300:
                snippet = snippet[:297] + "..."

            citation = Citation(
                citation_id=cit_id,
                document_id=item.document_id,
                segment_id=item.segment_id,
                parent_chunk_id=item.parent_chunk_id,
                source_path=item.source_path,
                section_heading=item.section_heading,
                category=item.category,
                machine_id=item.machine_id,
                original_row_index=item.original_row_index,
                source_record_id=item.source_record_id,
                snippet=snippet,
                similarity_score=item.similarity_score,
                is_synthetic=item.is_synthetic,
            )
            citation_map[cit_id] = citation
            evidence_text_map[cit_id] = item.content.strip()

        formatted_context = "\n\n".join(retained_blocks)
        total_tokens = tokenizer_service.count_tokens(formatted_context)

        sims = [it.similarity_score for it in retained_items]
        mean_sim = sum(sims) / len(sims) if sims else 0.0
        high_sim = max(sims) if sims else 0.0

        return EvidenceContext(
            formatted_context=formatted_context,
            citation_map=citation_map,
            evidence_text_map=evidence_text_map,
            retrieved_items=retained_items,
            has_placeholders=bool(all_placeholders),
            detected_placeholders=list(set(all_placeholders)),
            has_machine_mismatch=machine_mismatch,
            target_machine_id=target_machine_id,
            is_empty=False,
            mean_similarity=round(mean_sim, 4),
            highest_similarity=round(high_sim, 4),
            total_tokens=total_tokens,
        )


context_builder = EvidenceContextBuilder()
