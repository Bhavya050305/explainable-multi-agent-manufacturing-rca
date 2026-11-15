"""
ManuMind AI — Base LLM Provider Interface
Phase 3 Step 6: Grounded Generation Pipeline

Department of AI & Data Science — RMK Engineering College
"""

from abc import ABC, abstractmethod
from typing import Optional

from backend.app.rag.context_builder import EvidenceContext
from backend.app.rag.generation_schemas import GroundedAnswer


class BaseLLMProvider(ABC):
    """Abstract interface for grounded manufacturing LLM generation providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'mock', 'gemini', 'openai')."""
        pass

    @property
    @abstractmethod
    def model_identifier(self) -> str:
        """Model identifier or version string."""
        pass

    @abstractmethod
    def generate(
        self,
        query_text: str,
        context: EvidenceContext,
        target_machine_id: Optional[str] = None,
    ) -> GroundedAnswer:
        """
        Generate a structured, evidence-grounded manufacturing answer.
        Args:
            query_text: User investigation question.
            context: Formatted and indexed evidence context blocks.
            target_machine_id: Fleet machine identifier if machine-specific.
        Returns:
            GroundedAnswer model instance.
        """
        pass
