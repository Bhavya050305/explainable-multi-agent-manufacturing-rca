"""
ManuMind AI — RAG Ingestion Pipeline Configuration
Phase 3 Step 2: Document Ingestion Pipeline

Department of AI & Data Science — RMK Engineering College
"""

from pathlib import Path
from typing import List, Set, Dict


def find_project_root() -> Path:
    """Locate repository root deterministically."""
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / "knowledge_base").exists() and (current / "backend").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return Path.cwd().resolve()


class RAGConfig:
    """Configuration settings for document ingestion pipeline."""

    def __init__(self, base_dir: Path | None = None):
        self.BASE_DIR: Path = (base_dir or find_project_root()).resolve()
        self.KNOWLEDGE_BASE_DIR: Path = self.BASE_DIR / "knowledge_base"
        self.CORPUS_MANIFEST_PATH: Path = self.KNOWLEDGE_BASE_DIR / "corpus_manifest.json"
        self.MAINTENANCE_CSV_PATH: Path = self.BASE_DIR / "data" / "raw" / "maintenance_history.csv"
        self.REPORTS_DIR: Path = self.BASE_DIR / "reports" / "phase3"

        # Supported formats and discovery
        self.SUPPORTED_EXTENSIONS: Set[str] = {".md"}
        self.EXCLUDED_PREFIXES: Set[str] = {".", "~"}
        self.EXCLUDED_SUFFIXES: Set[str] = {".tmp", ".swp", ".bak", ".old"}
        self.EXCLUDED_DIRS: Set[str] = {"index", "__pycache__"}

        # Document categories
        self.VALID_DOCUMENT_TYPES: Set[str] = {
            "SOP",
            "TROUBLESHOOTING",
            "SAFETY",
            "INCIDENT",
        }

        # Provenance policies
        self.PROVENANCE_POLICY: Dict[str, Dict[str, str | bool]] = {
            "SOP": {
                "source_type": "SYNTHETIC_DEMONSTRATION",
                "is_synthetic": True,
            },
            "TROUBLESHOOTING": {
                "source_type": "SYNTHETIC_DEMONSTRATION",
                "is_synthetic": True,
            },
            "SAFETY": {
                "source_type": "SYNTHETIC_DEMONSTRATION",
                "is_synthetic": True,
            },
            "INCIDENT": {
                "source_type": "DERIVED_SYNTHETIC",
                "is_synthetic": True,
            },
        }

        # Expected corpus distribution
        self.EXPECTED_COUNTS = {
            "SOP": 10,
            "TROUBLESHOOTING": 5,
            "SAFETY": 3,
            "INCIDENT": 400,
            "TOTAL": 418,
        }

        # Mandatory front matter keys
        self.MANDATORY_COMMON_KEYS: Set[str] = {
            "document_id",
            "document_type",
            "source_type",
            "is_synthetic",
        }

        # Content normalization settings
        self.STRIP_TRAILING_WHITESPACE: bool = True
        self.NORMALIZE_NEWLINES: bool = True  # Standardize CRLF to LF
        self.ENCODING: str = "utf-8"


rag_config = RAGConfig()
