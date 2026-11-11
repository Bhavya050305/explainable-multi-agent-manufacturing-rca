"""
ManuMind AI — RAG Structural Text Splitter
Phase 3 Step 3: Document Chunking and Metadata-Aware Chunk Generation

Department of AI & Data Science — RMK Engineering College
"""

import math
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass

from backend.app.rag.chunking_config import ChunkingConfig, chunking_config


@dataclass
class RawSection:
    """Represents a structural section extracted from a Markdown document."""
    parent_heading: Optional[str]
    section_heading: str
    body_text: str
    is_safety_section: bool = False


@dataclass
class SplitChunkResult:
    """Represents the raw content and heading metadata of a generated chunk."""
    content: str
    section_heading: str
    parent_heading: Optional[str]
    token_count: int
    is_safety_related: bool


class TextSplitter:
    """
    Structure-aware Markdown splitter with deterministic subword token estimation.
    Preserves heading hierarchies, tables, safety procedures, and specification placeholders.
    """

    def __init__(self, config: ChunkingConfig = chunking_config):
        self.config = config
        self._token_pattern = re.compile(r"\w+|[^\w\s]", re.UNICODE)
        self._heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
        self._placeholder_pattern = re.compile(r"\[SPEC_REQUIRED:[^\]]+\]")

    def count_tokens(self, text: str) -> int:
        """
        Deterministic provisional token estimation strategy (deterministic_subword_heuristic_v1).
        - Matches unicode words and individual punctuation marks.
        - Words with len <= 4 count as 1 token.
        - Words with len > 4 count as ceil(len / 4) tokens.
        - Punctuation marks count as 1 token.
        """
        if not text:
            return 0

        matches = self._token_pattern.findall(text)
        tokens = 0
        for m in matches:
            if m.isalnum():
                tokens += max(1, math.ceil(len(m) / 4))
            else:
                tokens += 1
        return tokens

    def parse_structural_sections(self, body_text: str, doc_title: str) -> List[RawSection]:
        """
        Parse Markdown text into structural sections keyed by headings.
        Preserves hierarchy: parent_heading (H1/H2) and section_heading (H2/H3/H4).
        """
        lines = body_text.splitlines()
        sections: List[RawSection] = []

        current_h1: Optional[str] = doc_title
        current_h2: Optional[str] = None
        current_heading: str = doc_title or "Overview"
        current_lines: List[str] = []

        for line in lines:
            m = re.match(r"^(#{1,4})\s+(.+)$", line)
            if m:
                level = len(m.group(1))
                heading_text = m.group(2).strip()

                # Flush existing buffer if non-empty
                if any(l.strip() for l in current_lines):
                    sec_text = "\n".join(current_lines).strip()
                    parent = current_h2 if (current_h2 and current_h2 != current_heading) else current_h1
                    sections.append(
                        RawSection(
                            parent_heading=parent,
                            section_heading=current_heading,
                            body_text=sec_text,
                            is_safety_section=self._is_safety_text(current_heading + " " + sec_text),
                        )
                    )
                    current_lines = []

                if level == 1:
                    current_h1 = heading_text
                    current_h2 = None
                    current_heading = heading_text
                elif level == 2:
                    current_h2 = heading_text
                    current_heading = heading_text
                else:  # level 3 or 4
                    current_heading = heading_text
            else:
                current_lines.append(line)

        # Flush final section
        if any(l.strip() for l in current_lines):
            sec_text = "\n".join(current_lines).strip()
            parent = current_h2 if (current_h2 and current_h2 != current_heading) else current_h1
            sections.append(
                RawSection(
                    parent_heading=parent,
                    section_heading=current_heading,
                    body_text=sec_text,
                    is_safety_section=self._is_safety_text(current_heading + " " + sec_text),
                )
            )

        return sections

    def _is_safety_text(self, text: str) -> bool:
        """Check if text contains safety-critical keywords, excluding synthetic disclaimer banner."""
        cleaned = re.sub(
            r">\s*\*\*SAFETY NOTICE:\s*SYNTHETIC DEMONSTRATION MATERIAL[^\n]*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        upper = cleaned.upper()
        return any(kw in upper for kw in self.config.SAFETY_KEYWORDS)

    def split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs, preserving Markdown tables intact."""
        raw_paras = text.split("\n\n")
        paragraphs: List[str] = []

        inside_table = False
        table_buffer: List[str] = []

        for p in raw_paras:
            p_strip = p.strip()
            if not p_strip:
                continue

            # Check if paragraph contains table lines
            lines = p_strip.splitlines()
            is_table_block = all(l.strip().startswith("|") for l in lines if l.strip())

            if is_table_block:
                paragraphs.append(p_strip)
            else:
                paragraphs.append(p_strip)

        return paragraphs

    def split_document(
        self, body_text: str, category: str, doc_title: str
    ) -> List[SplitChunkResult]:
        """
        Split a document into deterministic chunks matching target token size.
        - INCIDENT documents remain complete in 1 chunk.
        - SOP, TROUBLESHOOTING, and SAFETY documents split by structure.
        """
        # 1. Incident handling: 1 atomic chunk
        if category == "INCIDENT":
            content = body_text.strip()
            return [
                SplitChunkResult(
                    content=content,
                    section_heading="Full Incident Record",
                    parent_heading=None,
                    token_count=self.count_tokens(content),
                    is_safety_related=False,
                )
            ]

        # 2. Structural section parsing
        sections = self.parse_structural_sections(body_text, doc_title)
        chunks: List[SplitChunkResult] = []

        # Buffer for packing adjacent small sections under the same parent heading
        buffered_sections: List[RawSection] = []
        buffered_tokens = 0

        def flush_buffer():
            nonlocal buffered_sections, buffered_tokens
            if not buffered_sections:
                return

            if len(buffered_sections) == 1:
                sec = buffered_sections[0]
                self._process_single_section(sec, doc_title, chunks)
            else:
                # Combined chunk
                combined_texts = []
                parent = buffered_sections[0].parent_heading
                sec_headings = [s.section_heading for s in buffered_sections]
                primary_heading = " & ".join(sec_headings[:2])
                if len(sec_headings) > 2:
                    primary_heading += f" (+{len(sec_headings)-2} subsections)"

                for s in buffered_sections:
                    combined_texts.append(f"### {s.section_heading}\n{s.body_text}")

                full_text = "\n\n".join(combined_texts).strip()
                t_count = self.count_tokens(full_text)

                if t_count <= self.config.MAX_CHUNK_SIZE_TOKENS:
                    is_safety = any(s.is_safety_section for s in buffered_sections)
                    chunks.append(
                        SplitChunkResult(
                            content=full_text,
                            section_heading=primary_heading,
                            parent_heading=parent,
                            token_count=t_count,
                            is_safety_related=is_safety,
                        )
                    )
                else:
                    # If combined exceeded max, process each individually
                    for s in buffered_sections:
                        self._process_single_section(s, doc_title, chunks)

            buffered_sections = []
            buffered_tokens = 0

        for sec in sections:
            sec_tokens = self.count_tokens(sec.body_text)

            # If section alone is medium-to-large, flush buffer first and process
            if sec_tokens >= self.config.MIN_PREFERRED_CHUNK_SIZE_TOKENS:
                flush_buffer()
                self._process_single_section(sec, doc_title, chunks)
            else:
                # Small section: check if we can pack it with previous buffered sections
                if (
                    buffered_sections
                    and buffered_sections[0].parent_heading == sec.parent_heading
                    and (buffered_tokens + sec_tokens) <= self.config.TARGET_CHUNK_SIZE_TOKENS
                ):
                    buffered_sections.append(sec)
                    buffered_tokens += sec_tokens
                else:
                    flush_buffer()
                    buffered_sections.append(sec)
                    buffered_tokens = sec_tokens

        flush_buffer()

        return chunks

    def _process_single_section(
        self, sec: RawSection, doc_title: str, output: List[SplitChunkResult]
    ) -> None:
        """Process a single section, keeping it intact or splitting if oversized."""
        sec_tokens = self.count_tokens(sec.body_text)

        # Context prefix to guarantee standalone understanding
        prefix_parts = []
        if sec.parent_heading and sec.parent_heading != sec.section_heading:
            prefix_parts.append(sec.parent_heading)
        prefix_parts.append(sec.section_heading)
        heading_prefix = " > ".join(prefix_parts)

        # Content with heading context
        annotated_content = f"## {heading_prefix}\n\n{sec.body_text}".strip()
        annotated_tokens = self.count_tokens(annotated_content)

        if annotated_tokens <= self.config.MAX_CHUNK_SIZE_TOKENS:
            output.append(
                SplitChunkResult(
                    content=annotated_content,
                    section_heading=sec.section_heading,
                    parent_heading=sec.parent_heading,
                    token_count=annotated_tokens,
                    is_safety_related=sec.is_safety_section,
                )
            )
        else:
            # Section exceeds target size: split along paragraphs/sentences
            sub_chunks = self._split_oversized_text(
                sec.body_text, heading_prefix, sec.is_safety_section
            )
            for sc in sub_chunks:
                output.append(
                    SplitChunkResult(
                        content=sc,
                        section_heading=sec.section_heading,
                        parent_heading=sec.parent_heading,
                        token_count=self.count_tokens(sc),
                        is_safety_related=sec.is_safety_section,
                    )
                )

    def _split_oversized_text(
        self, text: str, heading_prefix: str, is_safety: bool
    ) -> List[str]:
        """
        Split oversized text across paragraph and sentence boundaries with overlap.
        Repeats the heading context at the top of each generated sub-chunk.
        """
        paragraphs = self.split_paragraphs(text)
        sub_chunks: List[str] = []

        current_paras: List[str] = []
        current_tokens = 0
        header_intro = f"## {heading_prefix}\n\n"
        header_tokens = self.count_tokens(header_intro)

        for p in paragraphs:
            p_tokens = self.count_tokens(p)

            # If a single paragraph itself is enormous, split by sentences
            if p_tokens > (self.config.MAX_CHUNK_SIZE_TOKENS - header_tokens):
                sentences = re.split(r"(?<=[.!?])\s+", p)
                for s in sentences:
                    s_tokens = self.count_tokens(s)
                    if (header_tokens + current_tokens + s_tokens) > self.config.MAX_CHUNK_SIZE_TOKENS and current_paras:
                        chunk_body = "\n\n".join(current_paras).strip()
                        sub_chunks.append(f"{header_intro}{chunk_body}")
                        # Maintain overlap: keep last sentence
                        current_paras = [current_paras[-1], s]
                        current_tokens = self.count_tokens("\n\n".join(current_paras))
                    else:
                        current_paras.append(s)
                        current_tokens += s_tokens
            else:
                if (header_tokens + current_tokens + p_tokens) > self.config.MAX_CHUNK_SIZE_TOKENS and current_paras:
                    chunk_body = "\n\n".join(current_paras).strip()
                    sub_chunks.append(f"{header_intro}{chunk_body}")
                    # Overlap: retain last paragraph if reasonable size
                    if self.count_tokens(current_paras[-1]) <= self.config.CHUNK_OVERLAP_TOKENS * 2:
                        current_paras = [current_paras[-1], p]
                    else:
                        current_paras = [p]
                    current_tokens = self.count_tokens("\n\n".join(current_paras))
                else:
                    current_paras.append(p)
                    current_tokens += p_tokens

        if current_paras:
            chunk_body = "\n\n".join(current_paras).strip()
            sub_chunks.append(f"{header_intro}{chunk_body}")

        return sub_chunks
