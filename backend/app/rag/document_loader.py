"""
ManuMind AI — RAG Document Loader
Phase 3 Step 2: Document Ingestion Pipeline

Department of AI & Data Science — RMK Engineering College
"""

import hashlib
import os
from pathlib import Path
from typing import List, Tuple

from backend.app.rag.config import RAGConfig, rag_config
from backend.app.rag.exceptions import (
    DocumentLoadError,
    EmptyDocumentError,
    UnsupportedFileError,
)
from backend.app.rag.schemas import RawDocument, RejectedDocument


class DocumentLoader:
    """Discovers and loads Markdown documents deterministically and safely."""

    def __init__(self, config: RAGConfig = rag_config):
        self.config = config

    def discover_files(self, base_dir: Path | None = None) -> List[Path]:
        """Recursively discover all file paths under base_dir in sorted order."""
        root = (base_dir or self.config.KNOWLEDGE_BASE_DIR).resolve()
        if not root.exists():
            return []

        all_paths: List[Path] = []
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune excluded directories (e.g. vector index directories, hidden directories)
            excluded_dirs = getattr(self.config, "EXCLUDED_DIRS", {"index", "__pycache__"})
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in excluded_dirs]
            for fname in filenames:
                # Exclude hidden files (e.g. .gitkeep, .gitignore) and manifest file
                if fname.startswith(".") or fname == "corpus_manifest.json":
                    continue
                all_paths.append(Path(dirpath) / fname)

        # Return strictly deterministic sorted order
        return sorted(all_paths, key=lambda p: str(p.relative_to(root)).replace("\\", "/"))

    def load_document(self, file_path: Path, root_dir: Path) -> RawDocument:
        """Read and validate a single document file."""
        rel_path = str(file_path.relative_to(root_dir)).replace("\\", "/")

        # 1. Check filename exclusions (hidden or temporary)
        fname = file_path.name
        if any(fname.startswith(prefix) for prefix in self.config.EXCLUDED_PREFIXES):
            raise UnsupportedFileError(
                f"File '{fname}' is hidden or temporary",
                source_path=rel_path,
            )

        if any(fname.endswith(suffix) for suffix in self.config.EXCLUDED_SUFFIXES):
            raise UnsupportedFileError(
                f"File '{fname}' matches excluded temporary suffix",
                source_path=rel_path,
            )

        # 2. Check supported extension
        if file_path.suffix.lower() not in self.config.SUPPORTED_EXTENSIONS:
            raise UnsupportedFileError(
                f"Unsupported file extension '{file_path.suffix}' for '{fname}'",
                source_path=rel_path,
            )

        # 3. Read raw bytes and verify non-empty
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
        except OSError as e:
            raise DocumentLoadError(
                f"Failed to read file from disk: {e}",
                source_path=rel_path,
            )

        size_bytes = len(raw_bytes)
        if size_bytes == 0:
            raise EmptyDocumentError(
                f"Document is empty (0 bytes): {fname}",
                source_path=rel_path,
            )

        raw_hash = hashlib.sha256(raw_bytes).hexdigest()

        # 4. Decode UTF-8 safely
        try:
            raw_content = raw_bytes.decode(self.config.ENCODING)
        except UnicodeDecodeError as e:
            raise DocumentLoadError(
                f"UTF-8 decode failure at byte {e.start}: {e.reason}",
                source_path=rel_path,
            )

        # 5. Check if content is whitespace only
        if not raw_content.strip():
            raise EmptyDocumentError(
                f"Document contains only whitespace: {fname}",
                source_path=rel_path,
            )

        return RawDocument(
            source_path=rel_path,
            file_name=fname,
            raw_content=raw_content,
            size_bytes=size_bytes,
            raw_file_hash=raw_hash,
        )

    def load_all(
        self, base_dir: Path | None = None
    ) -> Tuple[List[RawDocument], List[RejectedDocument]]:
        """
        Discover and load all supported documents under base_dir.
        Returns a tuple of (loaded_raw_documents, rejected_documents).
        """
        root = (base_dir or self.config.KNOWLEDGE_BASE_DIR).resolve()
        discovered_paths = self.discover_files(root)

        loaded: List[RawDocument] = []
        rejected: List[RejectedDocument] = []

        for p in discovered_paths:
            rel_str = str(p.relative_to(root)).replace("\\", "/")
            # Filter out known non-corpus root files such as corpus_manifest.json
            if p.name == "corpus_manifest.json":
                continue

            try:
                raw_doc = self.load_document(p, root)
                loaded.append(raw_doc)
            except (DocumentLoadError, UnsupportedFileError, EmptyDocumentError) as err:
                rejected.append(
                    RejectedDocument(
                        source_path=rel_str,
                        document_id=None,
                        rejection_reason=err.__class__.__name__,
                        error_details=str(err),
                        phase="loading",
                    )
                )

        # Deterministic sorting
        loaded.sort(key=lambda d: d.source_path)
        rejected.sort(key=lambda r: r.source_path)

        return loaded, rejected
