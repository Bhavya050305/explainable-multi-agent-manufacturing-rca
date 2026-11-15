"""
ManuMind AI — Grounded Answer Generation Configuration
Phase 3 Step 6: Grounded Generation Pipeline

Department of AI & Data Science — RMK Engineering College
"""

import os
from typing import List, Set


class GenerationConfig:
    """Configuration parameters for manufacturing evidence-grounded answer generation."""

    def __init__(self):
        # Provider selection
        self.DEFAULT_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock").lower()
        self.MOCK_MODEL_NAME: str = "manumind-grounded-mock-v1"

        # Context limits
        self.MAX_CONTEXT_TOKENS: int = 2000
        self.MAX_SEGMENTS_IN_CONTEXT: int = 5
        self.MIN_SIMILARITY_FOR_GROUNDING: float = 0.60
        self.HIGH_CONFIDENCE_SIMILARITY: float = 0.75

        # Validation & Retries
        self.MAX_VALIDATION_RETRIES: int = 2
        self.STRICT_CITATION_ENFORCEMENT: bool = True

        # Safety & Governance
        self.DISCLOSE_SYNTHETIC_EVIDENCE: bool = True
        self.DISALLOW_OPERATIONAL_EXECUTION: bool = True
        self.PLACEHOLDER_TOKEN: str = "[SPEC_REQUIRED:"

        # Prompt Injection & Operational Keywords
        self.PROMPT_INJECTION_KEYWORDS: Set[str] = {
            "ignore previous instructions",
            "ignore all instructions",
            "ignore all previous instructions",
            "ignore the evidence",
            "invent the torque specification",
            "invent the rpm limit",
            "system prompt override",
            "print system prompt",
            "show internal instructions",
            "disclose the system prompt",
            "disable safety checks",
            "reveal secret key",
            "api key",
        }

        self.OPERATIONAL_COMMAND_KEYWORDS: Set[str] = {
            "start machine",
            "tell the controller to run",
            "run the machine now",
            "stop production line",
            "execute emergency stop override",
            "set spindle speed to",
            "run automated cycle",
            "release brake without lockout",
        }

        self.INTERLOCK_VIOLATION_KEYWORDS: Set[str] = {
            "disable the safety interlock",
            "make the interlock stop blocking",
            "bypass lockout/tagout",
            "bypass lockout tagout",
            "bypass safety interlock",
            "override interlock",
            "override protective shutdown",
        }


generation_config = GenerationConfig()
