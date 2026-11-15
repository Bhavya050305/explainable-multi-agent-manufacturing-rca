"""
ManuMind AI — LLM Provider Factory
Phase 3 Step 6: Grounded Generation Pipeline

Department of AI & Data Science — RMK Engineering College
"""

import os
from typing import Optional

from backend.app.rag.generation_config import generation_config
from backend.app.rag.providers.base import BaseLLMProvider
from backend.app.rag.providers.mock_provider import MockGroundedProvider, mock_grounded_provider


class ProviderFactory:
    """Factory creating configured LLM provider instances with strict credential validation."""

    @staticmethod
    def get_provider(provider_name: Optional[str] = None) -> BaseLLMProvider:
        """
        Instantiate or return the selected LLM provider.
        Args:
            provider_name: Explicit provider override (e.g., 'mock', 'gemini', 'openai').
        Returns:
            Configured BaseLLMProvider.
        Raises:
            ValueError: If credentials for external providers are missing or unknown provider requested.
        """
        selected = (provider_name or generation_config.DEFAULT_PROVIDER).lower()

        if selected == "mock":
            return mock_grounded_provider

        elif selected == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError(
                    "Missing credentials: GEMINI_API_KEY environment variable is not configured. "
                    "Configure a valid key or set LLM_PROVIDER=mock for deterministic offline execution."
                )
            raise NotImplementedError("Live Gemini provider adapter requires manual activation. Use 'mock'.")

        elif selected == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "Missing credentials: OPENAI_API_KEY environment variable is not configured. "
                    "Configure a valid key or set LLM_PROVIDER=mock for deterministic offline execution."
                )
            raise NotImplementedError("Live OpenAI provider adapter requires manual activation. Use 'mock'.")

        elif selected == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "Missing credentials: ANTHROPIC_API_KEY environment variable is not configured. "
                    "Configure a valid key or set LLM_PROVIDER=mock for deterministic offline execution."
                )
            raise NotImplementedError("Live Anthropic provider adapter requires manual activation. Use 'mock'.")

        else:
            raise ValueError(
                f"Unknown LLM provider '{selected}'. Supported providers are: 'mock', 'gemini', 'openai', 'anthropic'"
            )


provider_factory = ProviderFactory()
