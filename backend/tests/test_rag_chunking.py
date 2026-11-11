"""
ManuMind AI — Phase 3 Step 3: RAG Document Chunking and Metadata-Aware Chunk Generation Tests
Comprehensive Test Suite covering all 24 mandatory audit requirements.

Department of AI & Data Science — RMK Engineering College
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.chunking_config import ChunkingConfig, chunking_config
from backend.app.rag.chunk_schemas import (
    ChunkMetadata,
    ChunkRecord,
    ChunkingQualityMetrics,
    ChunkingSummary,
)
from backend.app.rag.text_splitter import TextSplitter, RawSection, SplitChunkResult
from backend.app.rag.metadata_enricher import MetadataEnricher
from backend.app.rag.chunking_service import ChunkingService
from backend.app.rag.chunking_report import ChunkingReportGenerator
from backend.app.rag.config import RAGConfig, rag_config
from backend.app.rag.ingestion_service import IngestionService
from backend.app.rag.schemas import (
    ExecutionMode,
    IngestionRecord,
    DocumentMetadata,
)


class TestRAGDocumentChunking(unittest.TestCase):
    """Authoritative test suite for Phase 3 Step 3 document chunking pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.rag_cfg = rag_config
        cls.chunk_cfg = chunking_config
        cls.ingestion_service = IngestionService(cls.rag_cfg)
        # Pre-ingest corpus in memory for tests requiring full documents
        cls.ingest_summary = cls.ingestion_service.ingest(
            execution_mode=ExecutionMode.IN_MEMORY_INGESTION
        )
        cls.ingested_docs = list(cls.ingestion_service.registry.values())
        cls.splitter = TextSplitter(cls.chunk_cfg)
        cls.enricher = MetadataEnricher(cls.chunk_cfg)
        cls.service = ChunkingService(cls.chunk_cfg, cls.ingestion_service)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="manumind_chunk_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. Markdown Heading Detection
    # -------------------------------------------------------------------------
    def test_01_markdown_heading_detection(self):
        """Verify structural Markdown splitter accurately identifies #, ##, ### headings."""
        doc_text = (
            "# Main Title\n\nIntroductory text paragraph.\n\n"
            "## Section 1: Overview\n\nOverview content paragraph.\n\n"
            "### Subsection 1.1: Scope\n\nScope details paragraph.\n\n"
            "## Section 2: Requirements\n\nRequirements text paragraph."
        )
        sections = self.splitter.parse_structural_sections(doc_text, doc_title="Main Title")

        # Must detect 4 distinct structural sections
        self.assertEqual(len(sections), 4)
        headings = [s.section_heading for s in sections]
        self.assertEqual(headings, ["Main Title", "Section 1: Overview", "Subsection 1.1: Scope", "Section 2: Requirements"])

    # -------------------------------------------------------------------------
    # 2. Parent and Child Heading Propagation
    # -------------------------------------------------------------------------
    def test_02_parent_and_child_heading_propagation(self):
        """Verify nested subsections propagate parent heading hierarchy."""
        doc_text = (
            "# SOP-M101 Hydraulic Maintenance\n\n"
            "## Section 3: Pressure Check\n\nIntro to pressure check.\n\n"
            "### Step 3.1: Gauge Verification\n\nInspect 0-250 bar pressure gauge calibration."
        )
        sections = self.splitter.parse_structural_sections(doc_text, doc_title="SOP-M101")
        step_section = [s for s in sections if s.section_heading == "Step 3.1: Gauge Verification"][0]

        self.assertEqual(step_section.parent_heading, "Section 3: Pressure Check")

        # Verify heading context is prepended in split chunk content
        chunks = self.splitter.split_document(doc_text, category="SOP", doc_title="SOP-M101")
        step_chunk = [c for c in chunks if "Step 3.1: Gauge Verification" in c.section_heading or "Step 3.1: Gauge Verification" in c.content][0]
        self.assertIn("Section 3: Pressure Check > Step 3.1: Gauge Verification", step_chunk.content)

    # -------------------------------------------------------------------------
    # 3. Paragraph Boundary Preservation
    # -------------------------------------------------------------------------
    def test_03_paragraph_boundary_preservation(self):
        """Verify paragraphs separated by blank lines are preserved as discrete semantic blocks."""
        p1 = "First cohesive paragraph describing hydraulic power unit activation."
        p2 = "Second cohesive paragraph covering fluid temperature stabilization at 45°C."
        p3 = "Third cohesive paragraph detailing pressure relief valve calibration."
        text = f"{p1}\n\n{p2}\n\n{p3}"

        paragraphs = self.splitter.split_paragraphs(text)
        self.assertEqual(len(paragraphs), 3)
        self.assertEqual(paragraphs[0], p1)
        self.assertEqual(paragraphs[1], p2)
        self.assertEqual(paragraphs[2], p3)

    # -------------------------------------------------------------------------
    # 4. Sentence-Aware Splitting
    # -------------------------------------------------------------------------
    def test_04_sentence_aware_splitting(self):
        """Verify oversized paragraphs split strictly along sentence terminations (. ? !)."""
        sentences = [
            "Operating pressure must not exceed the maximum certified limit under full load.",
            "Inspect all hydraulic fittings for evidence of micro-seepage before energizing the pump.",
            "Verify that accumulator pre-charge pressure meets factory specifications at 20°C.",
            "Record differential pressure across the high-pressure filter element after 15 minutes of run time.",
            "Ensure the emergency depressurization valve operates smoothly without mechanical binding.",
            "Any fluid leakage exceeding 2 drops per minute requires immediate work stoppage and supervisor notification.",
        ]
        # Repeat sentences to form an oversized text block
        long_para = " ".join(sentences * 4)
        sub_chunks = self.splitter._split_oversized_text(
            text=long_para,
            heading_prefix="Hydraulic Inspection > Pressure Test",
            is_safety=True,
        )

        self.assertGreater(len(sub_chunks), 1)
        for sc in sub_chunks:
            # Must retain heading prefix
            self.assertTrue(sc.startswith("## Hydraulic Inspection > Pressure Test\n\n"))
            body = sc.replace("## Hydraulic Inspection > Pressure Test\n\n", "")
            # Body must end with a sentence terminator
            self.assertTrue(body.endswith((".", "!", "?")), f"Sub-chunk body does not end with sentence terminator: {body[-20:]}")

    # -------------------------------------------------------------------------
    # 5. Token Count Enforcement
    # -------------------------------------------------------------------------
    def test_05_token_count_enforcement(self):
        """Verify deterministic subword heuristic token counting behaves accurately."""
        # Empty string
        self.assertEqual(self.splitter.count_tokens(""), 0)

        # Short words <= 4 chars count as 1 token
        self.assertEqual(self.splitter.count_tokens("The pump runs well"), 4)

        # Longer words > 4 chars count as ceil(len / 4)
        # "calibration" = 11 chars -> ceil(11/4) = 3 tokens
        self.assertEqual(self.splitter.count_tokens("calibration"), 3)

        # Punctuation counts as 1 token each
        self.assertEqual(self.splitter.count_tokens("stop!"), 1 + 1)

        # Token counting on realistic text is deterministic and positive
        sample = "Execute lockout/tagout procedure according to standard safety requirements."
        t1 = self.splitter.count_tokens(sample)
        t2 = self.splitter.count_tokens(sample)
        self.assertEqual(t1, t2)
        self.assertGreater(t1, 10)

    # -------------------------------------------------------------------------
    # 6. Overlap Behavior
    # -------------------------------------------------------------------------
    def test_06_overlap_behavior(self):
        """Verify sequential chunks from an oversized section share sliding window overlap."""
        paras = [
            f"Detailed diagnostic paragraph number {i} covering spindle thermal displacement analysis." * 3
            for i in range(1, 8)
        ]
        text = "\n\n".join(paras)

        sub_chunks = self.splitter._split_oversized_text(
            text=text,
            heading_prefix="Thermal Analysis",
            is_safety=False,
        )
        self.assertGreater(len(sub_chunks), 1)

        # Verify that content from chunk 0 tail is included in chunk 1 body
        body0 = sub_chunks[0].replace("## Thermal Analysis\n\n", "")
        body1 = sub_chunks[1].replace("## Thermal Analysis\n\n", "")

        last_para_chunk0 = body0.split("\n\n")[-1]
        self.assertIn(last_para_chunk0[:40], body1)

    # -------------------------------------------------------------------------
    # 7. Deterministic Chunk IDs
    # -------------------------------------------------------------------------
    def test_07_deterministic_chunk_ids(self):
        """Verify chunk IDs follow {document_id}_chk{index:03d} and remain deterministic."""
        sample_doc = [d for d in self.ingested_docs if d.document_type == "SOP"][0]

        chunks_run1 = self.service.chunk_document(sample_doc)
        chunks_run2 = self.service.chunk_document(sample_doc)

        self.assertEqual(len(chunks_run1), len(chunks_run2))
        for c1, c2 in zip(chunks_run1, chunks_run2):
            self.assertEqual(c1.chunk_id, c2.chunk_id)
            self.assertEqual(c1.chunk_id, f"{sample_doc.document_id}_chk{c1.chunk_index:03d}")
            self.assertEqual(c1.content_hash, c2.content_hash)

    # -------------------------------------------------------------------------
    # 8. Stable Ordering
    # -------------------------------------------------------------------------
    def test_08_stable_ordering(self):
        """Verify chunk indices strictly start at 0 and increment sequentially with zero gaps."""
        sample_doc = [d for d in self.ingested_docs if d.document_type == "TROUBLESHOOTING"][0]
        chunks = self.service.chunk_document(sample_doc)

        self.assertGreater(len(chunks), 1)
        for expected_idx, chunk in enumerate(chunks):
            self.assertEqual(chunk.chunk_index, expected_idx)
            self.assertEqual(chunk.metadata.chunk_index, expected_idx)

    # -------------------------------------------------------------------------
    # 9. Empty Content Rejection
    # -------------------------------------------------------------------------
    def test_09_empty_content_rejection(self):
        """Verify that zero empty or whitespace-only chunks are generated."""
        summary = self.service.chunk_corpus(
            execution_mode=ExecutionMode.VALIDATION_ONLY,
            documents=self.ingested_docs,
        )
        self.assertEqual(summary.metrics.empty_chunks_count, 0)
        self.assertNotIn("Empty chunk content generated", "\n".join(summary.errors))

    # -------------------------------------------------------------------------
    # 10. Metadata Schema Validation
    # -------------------------------------------------------------------------
    def test_10_metadata_schema_validation(self):
        """Verify ChunkRecord and ChunkMetadata strictly satisfy Pydantic v2 schemas."""
        sample_doc = [d for d in self.ingested_docs if d.document_type == "SAFETY"][0]
        chunks = self.service.chunk_document(sample_doc)

        for chk in chunks:
            # Re-validate via Pydantic model_validate
            validated_record = ChunkRecord.model_validate(chk.model_dump())
            validated_meta = ChunkMetadata.model_validate(chk.metadata.model_dump())
            self.assertEqual(validated_record.chunk_id, chk.chunk_id)
            self.assertEqual(validated_meta.document_id, sample_doc.document_id)
            self.assertIsInstance(validated_meta.is_safety_related, bool)
            self.assertIsInstance(validated_meta.token_count, int)

    # -------------------------------------------------------------------------
    # 11. Machine ID Preservation
    # -------------------------------------------------------------------------
    def test_11_machine_id_preservation(self):
        """Verify machine IDs (M101-M110) propagate into chunk metadata."""
        machine_ids_found = set()
        summary = self.service.chunk_corpus(
            execution_mode=ExecutionMode.VALIDATION_ONLY,
            documents=self.ingested_docs,
        )

        for m_id, count in summary.metrics.chunks_per_machine.items():
            machine_ids_found.add(m_id)
            self.assertGreater(count, 0)

        # Expected machine IDs across corpus: M101 through M110
        expected_machines = {f"M1{i:02d}" for i in range(1, 11)}
        self.assertEqual(machine_ids_found, expected_machines)

    # -------------------------------------------------------------------------
    # 12. Incident Source Row Mapping Preservation
    # -------------------------------------------------------------------------
    def test_12_incident_source_row_mapping_preservation(self):
        """Verify maintenance incident chunks preserve source record ID and row index."""
        inc_docs = [d for d in self.ingested_docs if d.document_type == "INCIDENT"]
        self.assertEqual(len(inc_docs), 400)

        sample_inc = inc_docs[0]
        chunks = self.service.chunk_document(sample_inc)
        self.assertEqual(len(chunks), 1)
        chk = chunks[0]

        self.assertIsNotNone(chk.metadata.source_record_id)
        self.assertTrue(chk.metadata.source_record_id.startswith("ROW-"))
        self.assertIsNotNone(chk.metadata.original_row_index)
        self.assertEqual(chk.metadata.category, "INCIDENT")
        self.assertIn(chk.metadata.machine_id, [f"M1{i:02d}" for i in range(1, 11)])

    # -------------------------------------------------------------------------
    # 13. Incident Isolation (1:1 Atomic Mapping)
    # -------------------------------------------------------------------------
    def test_13_incident_isolation(self):
        """Verify all 400 maintenance incidents produce exactly 1 chunk each without merging or splitting."""
        inc_docs = [d for d in self.ingested_docs if d.document_type == "INCIDENT"]
        self.assertEqual(len(inc_docs), 400)

        for inc in inc_docs:
            chunks = self.service.chunk_document(inc)
            self.assertEqual(
                len(chunks),
                1,
                f"Incident {inc.document_id} was split into {len(chunks)} chunks instead of 1 atomic chunk",
            )
            self.assertEqual(chunks[0].chunk_index, 0)
            self.assertEqual(chunks[0].metadata.source_record_id, inc.metadata.source_record_id)

    # -------------------------------------------------------------------------
    # 14. Synthetic Provenance Preservation
    # -------------------------------------------------------------------------
    def test_14_synthetic_provenance_preservation(self):
        """Verify is_synthetic flag and synthetic disclaimer banners are preserved."""
        summary = self.service.chunk_corpus(
            execution_mode=ExecutionMode.VALIDATION_ONLY,
            documents=self.ingested_docs,
        )
        self.assertGreater(summary.metrics.chunks_with_synthetic_disclaimers, 400)
        self.assertEqual(summary.metrics.total_chunks_generated, 564)

        # All chunks must have is_synthetic = True
        for doc in self.ingested_docs:
            chunks = self.service.chunk_document(doc)
            for c in chunks:
                self.assertTrue(c.metadata.is_synthetic)

    # -------------------------------------------------------------------------
    # 15. Specification Placeholder Preservation
    # -------------------------------------------------------------------------
    def test_15_specification_placeholder_preservation(self):
        """Verify all 123 [SPEC_REQUIRED:...] placeholders are preserved verbatim across chunks."""
        total_placeholders = 0
        chunks_with_placeholders = 0

        for doc in self.ingested_docs:
            chunks = self.service.chunk_document(doc)
            for c in chunks:
                count = c.content.count("[SPEC_REQUIRED:")
                if count > 0:
                    total_placeholders += count
                    chunks_with_placeholders += 1
                    self.assertTrue(c.metadata.contains_spec_placeholder)

        # Reconciled in Step 2.1.1: exactly 123 placeholders across 18 demonstration documents
        self.assertEqual(total_placeholders, 123)
        self.assertEqual(chunks_with_placeholders, 41)

    # -------------------------------------------------------------------------
    # 16. Safety Warning and Procedure Context Preservation
    # -------------------------------------------------------------------------
    def test_16_safety_warning_and_procedure_context_preservation(self):
        """Verify safety warnings (LOTO, PPE, Hazard) retain heading context and are tagged."""
        safety_docs = [d for d in self.ingested_docs if d.document_type == "SAFETY"]
        self.assertEqual(len(safety_docs), 3)

        for sdoc in safety_docs:
            chunks = self.service.chunk_document(sdoc)
            for c in chunks:
                self.assertTrue(c.metadata.is_safety_related)
                self.assertIn("## ", c.content)  # Must include heading context

    # -------------------------------------------------------------------------
    # 17. Oversized Safety Section Handling
    # -------------------------------------------------------------------------
    def test_17_oversized_safety_section_handling(self):
        """Verify oversized safety procedures repeat warning and heading context across splits."""
        safety_text = (
            "WARNING: Hazardous high voltage (400V 3-phase) and hydraulic pressure present.\n\n"
            + "\n\n".join(
                [
                    f"Step {i}: Isolate switchgear panel {i}, verify zero energy state with calibrated multimeter, apply lockout padlock and danger tag."
                    for i in range(1, 25)
                ]
            )
        )
        sec = RawSection(
            parent_heading="Electrical Isolation",
            section_heading="Lockout / Tagout Procedures",
            body_text=safety_text,
            is_safety_section=True,
        )

        results: List[SplitChunkResult] = []
        self.splitter._process_single_section(sec, doc_title="Safety Standard", output=results)

        self.assertGreater(len(results), 1)
        for r in results:
            self.assertTrue(r.is_safety_related)
            self.assertIn("Electrical Isolation > Lockout / Tagout Procedures", r.content)

    # -------------------------------------------------------------------------
    # 18. Table Preservation
    # -------------------------------------------------------------------------
    def test_18_table_preservation(self):
        """Verify Markdown telemetry and parameter tables remain cohesive without row fragmentation."""
        table_text = (
            "| Parameter | Normal Range | Alert Threshold | Critical Stop |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| Vibration (mm/s) | 0.5 - 2.5 | > 3.8 | > 5.5 |\n"
            "| Temperature (°C) | 40 - 65 | > 75 | > 85 |\n"
            "| Pressure (bar) | 140 - 160 | < 130 or > 170 | < 110 or > 185 |"
        )
        paras = self.splitter.split_paragraphs(table_text)
        self.assertEqual(len(paras), 1)
        self.assertEqual(paras[0], table_text)

    # -------------------------------------------------------------------------
    # 19. Duplicate Source Content with Separate Document Identities
    # -------------------------------------------------------------------------
    def test_19_duplicate_source_content_with_separate_document_identities(self):
        """Verify documents with similar or identical procedure text produce distinct chunk identities."""
        sop_docs = [d for d in self.ingested_docs if d.document_type == "SOP"]
        m101_sop = [d for d in sop_docs if d.machine_id == "M101"][0]
        m102_sop = [d for d in sop_docs if d.machine_id == "M102"][0]

        chunks_m101 = self.service.chunk_document(m101_sop)
        chunks_m102 = self.service.chunk_document(m102_sop)

        ids_m101 = {c.chunk_id for c in chunks_m101}
        ids_m102 = {c.chunk_id for c in chunks_m102}

        # Zero ID overlap
        self.assertEqual(len(ids_m101.intersection(ids_m102)), 0)

        # Machine ID in metadata correctly reflects individual document
        for c in chunks_m101:
            self.assertEqual(c.metadata.machine_id, "M101")
            self.assertEqual(c.metadata.document_id, m101_sop.document_id)
        for c in chunks_m102:
            self.assertEqual(c.metadata.machine_id, "M102")
            self.assertEqual(c.metadata.document_id, m102_sop.document_id)

    # -------------------------------------------------------------------------
    # 20. Repeated Run Idempotency
    # -------------------------------------------------------------------------
    def test_20_repeated_run_idempotency(self):
        """Verify running chunking twice produces identical chunk counts, IDs, hashes, and contents."""
        self.service.clear_registry()

        # Run 1
        summary1 = self.service.chunk_corpus(
            execution_mode=ExecutionMode.IN_MEMORY_INGESTION,
            documents=self.ingested_docs,
        )
        reg1 = dict(self.service.registry)

        # Run 2 (without clearing - tests in-memory registry idempotency)
        summary2 = self.service.chunk_corpus(
            execution_mode=ExecutionMode.IN_MEMORY_INGESTION,
            documents=self.ingested_docs,
        )
        reg2 = dict(self.service.registry)

        self.assertEqual(summary1.metrics.total_chunks_generated, summary2.metrics.total_chunks_generated)
        self.assertEqual(len(reg1), len(reg2))
        self.assertEqual(len(summary2.errors), 0)

        for cid, chunk1 in reg1.items():
            self.assertIn(cid, reg2)
            chunk2 = reg2[cid]
            self.assertEqual(chunk1.content_hash, chunk2.content_hash)
            self.assertEqual(chunk1.content, chunk2.content)

    # -------------------------------------------------------------------------
    # 21. Full Corpus Chunk Generation
    # -------------------------------------------------------------------------
    def test_21_full_corpus_chunk_generation(self):
        """Verify chunking across all 418 documents produces expected distribution."""
        summary = self.service.chunk_corpus(
            execution_mode=ExecutionMode.VALIDATION_ONLY,
            documents=self.ingested_docs,
        )
        m = summary.metrics

        self.assertEqual(m.total_source_documents, 418)
        self.assertEqual(m.total_chunks_generated, 564)
        self.assertEqual(m.chunks_per_category["INCIDENT"], 400)
        self.assertEqual(m.chunks_per_category["SOP"], 110)
        self.assertEqual(m.chunks_per_category["TROUBLESHOOTING"], 39)
        self.assertEqual(m.chunks_per_category["SAFETY"], 15)
        self.assertEqual(m.duplicate_chunk_ids_count, 0)
        self.assertEqual(m.empty_chunks_count, 0)
        self.assertEqual(len(summary.errors), 0)

    # -------------------------------------------------------------------------
    # 22. Source Text Coverage and No Silent Content Loss
    # -------------------------------------------------------------------------
    def test_22_source_text_coverage_and_no_silent_content_loss(self):
        """Verify key technical terms and operational procedures are preserved across chunks."""
        summary = self.service.chunk_corpus(
            execution_mode=ExecutionMode.VALIDATION_ONLY,
            documents=self.ingested_docs,
        )
        self.assertEqual(summary.metrics.source_text_coverage_percentage, 100.0)

        # Test specific known strings across technical demonstration documents
        all_chunk_contents = " ".join(
            [c.content for doc in self.ingested_docs for c in self.service.chunk_document(doc)]
        )

        critical_terms = [
            "Lockout/Tagout",
            "spindle vibration",
            "hydraulic fluid",
            "coolant concentration",
            "[SPEC_REQUIRED: Certified OEM electrical isolation procedure]",
        ]
        for term in critical_terms:
            self.assertIn(term, all_chunk_contents)

    # -------------------------------------------------------------------------
    # 23. Invalid Metadata Handling
    # -------------------------------------------------------------------------
    def test_23_invalid_metadata_handling(self):
        """Verify enricher gracefully handles documents with minimal or edge-case metadata."""
        minimal_doc = IngestionRecord(
            document_id="DOC-EDGE-001",
            source_path="knowledge_base/edge.md",
            document_type="GENERAL",
            source_type="SYNTHETIC_MANUAL",
            is_synthetic=True,
            title="Edge Case Document",
            content="Simple text body without special sections.",
            version="1.0",
            content_hash=hashlib.sha256(b"Simple text body without special sections.").hexdigest(),
            raw_file_hash="abc123def456",
            metadata=DocumentMetadata(
                document_id="DOC-EDGE-001",
                document_type="GENERAL",
                source_type="SYNTHETIC_MANUAL",
                is_synthetic=True,
                title="Edge Case Document",
                author="Test Harness",
                version="1.0",
                last_updated="2026-11-10",
                machine_id=None,
            ),
        )
        chunks = self.service.chunk_document(minimal_doc)
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0].chunk_id, "DOC-EDGE-001_chk000")
        self.assertIsNone(chunks[0].metadata.machine_id)
        self.assertFalse(chunks[0].metadata.is_safety_related)

    # -------------------------------------------------------------------------
    # 24. Unsupported Document Handling
    # -------------------------------------------------------------------------
    def test_24_unsupported_document_handling(self):
        """Verify empty body text and documents without headings are handled safely."""
        empty_body_doc = IngestionRecord(
            document_id="DOC-EMPTY-001",
            source_path="knowledge_base/empty.md",
            document_type="GENERAL",
            source_type="SYNTHETIC_MANUAL",
            is_synthetic=True,
            title="Empty Doc",
            content="",
            version="1.0",
            content_hash=hashlib.sha256(b"").hexdigest(),
            raw_file_hash="emptyhash123",
            metadata=DocumentMetadata(
                document_id="DOC-EMPTY-001",
                document_type="GENERAL",
                source_type="SYNTHETIC_MANUAL",
                is_synthetic=True,
                title="Empty Doc",
                author="Test Harness",
                version="1.0",
                last_updated="2026-11-10",
            ),
        )
        # Empty body should produce 0 chunks without crashing
        chunks = self.service.chunk_document(empty_body_doc)
        self.assertEqual(len(chunks), 0)


if __name__ == "__main__":
    unittest.main()
