"""
ManuMind AI — RAG Metadata Filter Compiler
Phase 3 Step 5: Retrieval and Search Pipeline

Department of AI & Data Science — RMK Engineering College
"""

from typing import Any, Dict, List, Optional, Tuple

from backend.app.rag.retrieval_config import RetrievalConfig, retrieval_config
from backend.app.rag.retrieval_schemas import RetrievalFilter, RetrievalMode


class MetadataFilterCompiler:
    """
    Compiles validated high-level retrieval filters into ChromaDB $and / $in query dicts.
    Enforces machine isolation, cross-machine policies, and category boundaries.
    """

    def __init__(self, config: RetrievalConfig = retrieval_config):
        self.config = config

    def compile_filter(
        self,
        filter_spec: Optional[RetrievalFilter] = None,
        extracted_machine_id: Optional[str] = None,
        mode_override: Optional[RetrievalMode] = None,
    ) -> Tuple[Optional[Dict[str, Any]], RetrievalMode]:
        """
        Compile retrieval filters into ChromaDB `where` syntax.
        Args:
            filter_spec: Optional high-level RetrievalFilter.
            extracted_machine_id: Machine ID extracted from query text if any.
            mode_override: Optional explicit retrieval mode override.
        Returns:
            Tuple of (chroma_where_dict, effective_retrieval_mode).
        Raises:
            ValueError: If unknown machine ID or invalid category is requested.
        """
        conditions: List[Dict[str, Any]] = []

        # Determine target machine ID
        specified_machine = filter_spec.machine_id if filter_spec else None
        target_machine = specified_machine or extracted_machine_id

        # Validate machine ID if provided
        if target_machine:
            target_machine = target_machine.upper()
            if target_machine not in self.config.VALID_MACHINES:
                raise ValueError(
                    f"Invalid machine identifier '{target_machine}'. "
                    f"Valid fleet assets are: {sorted(self.config.VALID_MACHINES)}"
                )

        # Determine effective retrieval mode
        is_cross_machine = (
            (filter_spec and filter_spec.cross_machine)
            or mode_override == RetrievalMode.CROSS_MACHINE
        )

        if is_cross_machine:
            effective_mode = RetrievalMode.CROSS_MACHINE
        elif target_machine:
            effective_mode = RetrievalMode.MACHINE_SPECIFIC
        elif mode_override == RetrievalMode.GLOBAL_ONLY:
            effective_mode = RetrievalMode.GLOBAL_ONLY
        else:
            effective_mode = RetrievalMode.CROSS_MACHINE

        # 1. Machine Filtering
        if effective_mode == RetrievalMode.MACHINE_SPECIFIC and target_machine:
            include_global = filter_spec.include_global if filter_spec else True
            if include_global:
                # Include target machine OR plant-wide global documents ("NONE")
                conditions.append({"machine_id": {"$in": [target_machine, "NONE"]}})
            else:
                conditions.append({"machine_id": target_machine})
        elif effective_mode == RetrievalMode.GLOBAL_ONLY:
            conditions.append({"machine_id": "NONE"})

        # If cross-machine mode and user explicitly requested machine filter in filter_spec
        # but cross_machine is True, we allow matching across machines unless strictly constrained.

        if filter_spec:
            # 2. Category Filtering
            if filter_spec.category:
                cat = filter_spec.category.upper()
                if cat not in self.config.VALID_CATEGORIES:
                    raise ValueError(
                        f"Invalid category '{filter_spec.category}'. "
                        f"Valid categories: {sorted(self.config.VALID_CATEGORIES)}"
                    )
                conditions.append({"category": cat})

            # 3. Safety Filtering
            if filter_spec.is_safety_related is not None:
                conditions.append({"is_safety_related": filter_spec.is_safety_related})

            # 4. Synthetic Status Filtering
            if filter_spec.is_synthetic is not None:
                conditions.append({"is_synthetic": filter_spec.is_synthetic})

            # 5. Provenance Source Type
            if filter_spec.source_type:
                conditions.append({"source_type": filter_spec.source_type})

            # 6. Specific Document ID
            if filter_spec.document_id:
                conditions.append({"document_id": filter_spec.document_id})

            # 7. Specific Incident Record ID
            if filter_spec.source_record_id:
                conditions.append({"source_record_id": filter_spec.source_record_id})

        # Assemble ChromaDB where clause
        if not conditions:
            return None, effective_mode
        if len(conditions) == 1:
            return conditions[0], effective_mode

        return {"$and": conditions}, effective_mode


metadata_filter_compiler = MetadataFilterCompiler()
