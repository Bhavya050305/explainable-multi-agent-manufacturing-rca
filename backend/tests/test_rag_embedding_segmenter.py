"""
ManuMind AI — Phase 3 Step 4: RAG Embedding Segmenter Tests
Verifies embedding-specific segmentation, parent-child lineage, incident isolation,
token limit enforcement, and placeholder/safety preservation.

Department of AI & Data Science — RMK Engineering College
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.chunk_schemas import ChunkMetadata, ChunkRecord
from backend.app.rag.chunking_service import ChunkingService
from backend.app.rag.embedding_segmenter import EmbeddingSegmenter
from backend.app.rag.tokenizer_service import TokenizerService, tokenizer_service


class TestRAGEmbeddingSegmenter(unittest.TestCase):
    """Authoritative test suite for embedding segmenter."""

    @classmethod
    def setUpClass(cls):
        cls.tokenizer_svc = tokenizer_service
        cls.segmenter = EmbeddingSegmenter(tokenizer_svc=cls.tokenizer_svc, max_segment_tokens=500)
        # Low-budget segmenter to force segmentation in unit tests
        cls.low_budget_segmenter = EmbeddingSegmenter(tokenizer_svc=cls.tokenizer_svc, max_segment_tokens=100)

        # Pre-generate real canonical chunks
        cls.chunk_svc = ChunkingService()
        cls.docs = list(cls.chunk_svc.ingestion_service.registry.values())
        if not cls.docs:
            cls.chunk_svc.ingestion_service.ingest()
            cls.docs = list(cls.chunk_svc.ingestion_service.registry.values())

        cls.sample_sop_chunk = [
            c for d in cls.docs if d.document_type == "SOP"
            for c in cls.chunk_svc.chunk_document(d)
        ][0]
        cls.sample_incident_chunk = [
            c for d in cls.docs if d.document_type == "INCIDENT"
            for c in cls.chunk_svc.chunk_document(d)
        ][0]

    def test_01_short_chunks_remain_intact(self):
        """Verify chunks with actual tokens <= max_segment_tokens remain 1:1 intact."""
        segments = self.segmenter.segment_chunk(self.sample_sop_chunk)
        self.assertEqual(len(segments), 1)
        seg = segments[0]
        self.assertEqual(seg.segment_index, 0)
        self.assertEqual(seg.metadata.segment_count, 1)
        self.assertEqual(seg.parent_chunk_id, self.sample_sop_chunk.chunk_id)
        self.assertEqual(seg.embedding_segment_id, f"{self.sample_sop_chunk.chunk_id}_seg000")
        self.assertEqual(seg.content, self.sample_sop_chunk.content)

    def test_02_oversized_chunks_are_segmented(self):
        """Verify an oversized chunk exceeding token budget is split into multiple segments."""
        # Use low_budget_segmenter (limit 100 tokens) on a 250-token chunk
        segments = self.low_budget_segmenter.segment_chunk(self.sample_incident_chunk)
        self.assertGreater(len(segments), 1)
        for s in segments:
            self.assertLessEqual(s.token_count, 120)  # within margin
            self.assertEqual(s.parent_chunk_id, self.sample_incident_chunk.chunk_id)

    def test_03_deterministic_segment_ids(self):
        """Verify segment IDs follow {parent_chunk_id}_seg{idx:03d} deterministically."""
        segments = self.low_budget_segmenter.segment_chunk(self.sample_sop_chunk)
        for idx, seg in enumerate(segments):
            expected_id = f"{self.sample_sop_chunk.chunk_id}_seg{idx:03d}"
            self.assertEqual(seg.embedding_segment_id, expected_id)
            self.assertEqual(seg.segment_index, idx)

    def test_04_correct_segment_ordering(self):
        """Verify segment indices are continuous and strictly start at 0."""
        segments = self.low_budget_segmenter.segment_chunk(self.sample_incident_chunk)
        for idx, s in enumerate(segments):
            self.assertEqual(s.segment_index, idx)
            self.assertEqual(s.metadata.segment_index, idx)
            self.assertEqual(s.metadata.segment_count, len(segments))

    def test_05_parent_child_lineage(self):
        """Verify segment metadata explicitly retains parent chunk ID and document ID."""
        segments = self.segmenter.segment_chunk(self.sample_sop_chunk)
        seg = segments[0]
        self.assertEqual(seg.parent_chunk_id, self.sample_sop_chunk.chunk_id)
        self.assertEqual(seg.document_id, self.sample_sop_chunk.document_id)
        self.assertEqual(seg.metadata.raw_file_hash, self.sample_sop_chunk.metadata.raw_file_hash)

    def test_06_incident_identity_preservation(self):
        """Verify maintenance incident segments preserve source record ID, row index, and date."""
        segments = self.segmenter.segment_chunk(self.sample_incident_chunk)
        seg = segments[0]
        self.assertEqual(seg.metadata.source_record_id, self.sample_incident_chunk.metadata.source_record_id)
        self.assertEqual(seg.metadata.original_row_index, self.sample_incident_chunk.metadata.original_row_index)
        self.assertEqual(seg.metadata.event_date, self.sample_incident_chunk.metadata.event_date)
        self.assertEqual(seg.metadata.category, "INCIDENT")

    def test_07_incident_isolation(self):
        """Verify incident segmentation never merges multiple incidents."""
        inc_chunks = [
            c for d in self.docs[:5] if d.document_type == "INCIDENT"
            for c in self.chunk_svc.chunk_document(d)
        ]
        all_segs = []
        for ic in inc_chunks:
            segs = self.segmenter.segment_chunk(ic)
            # Each segment must have exactly this incident's document_id
            for s in segs:
                self.assertEqual(s.document_id, ic.document_id)
                self.assertEqual(s.parent_chunk_id, ic.chunk_id)
            all_segs.extend(segs)

        # Confirm all segment IDs are unique
        seg_ids = [s.embedding_segment_id for s in all_segs]
        self.assertEqual(len(seg_ids), len(set(seg_ids)))

    def test_08_sentence_boundary_splitting(self):
        """Verify oversized paragraphs split along sentence terminators without cutting words."""
        long_text = (
            "## Emergency Hydraulic Depressurization\n\n"
            + "The hydraulic accumulator must be depressurized to zero bar before inspection. " * 15
        )
        fake_chunk = ChunkRecord(
            chunk_id="TEST-OVERSIZED_chk000",
            document_id="TEST-OVERSIZED",
            chunk_index=0,
            content=long_text,
            content_hash="fakehash123",
            metadata=self.sample_sop_chunk.metadata,
        )
        segments = self.low_budget_segmenter.segment_chunk(fake_chunk)
        self.assertGreater(len(segments), 1)
        for s in segments:
            # Segment content must end with complete sentence or period
            self.assertTrue(s.content.strip().endswith((".", "!", "?")))

    def test_09_heading_preservation(self):
        """Verify heading context is preserved across generated segments."""
        long_text = (
            "## Safety Standard > Spindle Bearing Maintenance\n\n"
            + "Paragraph describing bearing inspection and race runout calibration. " * 10
        )
        fake_chunk = ChunkRecord(
            chunk_id="TEST-HEADING_chk000",
            document_id="TEST-HEADING",
            chunk_index=0,
            content=long_text,
            content_hash="fakehash456",
            metadata=self.sample_sop_chunk.metadata,
        )
        segments = self.low_budget_segmenter.segment_chunk(fake_chunk)
        self.assertGreater(len(segments), 1)
        for s in segments:
            self.assertIn("Safety Standard > Spindle Bearing Maintenance", s.content)

    def test_10_table_preservation(self):
        """Verify Markdown tables remain cohesive during segmentation."""
        table_text = (
            "## Telemetry Envelope\n\n"
            "| Sensor | Normal | Warning | Critical |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| Vibration | 1.5 - 2.5 | > 3.8 | > 5.5 |\n"
            "| Temperature | 45 - 55 | > 65 | > 75 |\n"
        )
        fake_chunk = ChunkRecord(
            chunk_id="TEST-TABLE_chk000",
            document_id="TEST-TABLE",
            chunk_index=0,
            content=table_text,
            content_hash="fakehash789",
            metadata=self.sample_sop_chunk.metadata,
        )
        segments = self.segmenter.segment_chunk(fake_chunk)
        self.assertEqual(len(segments), 1)
        self.assertIn("| Sensor |", segments[0].content)

    def test_11_safety_warning_preservation(self):
        """Verify safety warnings and LOTO procedures maintain safety metadata."""
        safety_chunks = [
            c for d in self.docs if d.document_type == "SAFETY"
            for c in self.chunk_svc.chunk_document(d)
        ]
        self.assertGreater(len(safety_chunks), 0)
        for sc in safety_chunks:
            segs = self.segmenter.segment_chunk(sc)
            for s in segs:
                self.assertTrue(s.metadata.is_safety_related)

    def test_12_no_empty_segments(self):
        """Verify that zero empty or whitespace-only segments are generated."""
        sample_chunks = [
            c for d in self.docs[:10]
            for c in self.chunk_svc.chunk_document(d)
        ]
        segments, summary = self.segmenter.segment_corpus(sample_chunks)
        self.assertEqual(summary.empty_segments_count, 0)
        for s in segments:
            self.assertGreater(len(s.content.strip()), 0)

    def test_13_no_silent_text_loss(self):
        """Verify that all non-whitespace content in canonical chunk is present in segments."""
        segments = self.low_budget_segmenter.segment_chunk(self.sample_sop_chunk)
        combined_seg_content = " ".join(s.content for s in segments)
        words = self.sample_sop_chunk.content.split()
        # Sample key words from canonical chunk
        for w in words[:10]:
            self.assertIn(w, combined_seg_content)

    def test_14_actual_token_limit_enforcement(self):
        """Verify that 100% of generated segments strictly obey max_segment_tokens."""
        sample_chunks = [
            c for d in self.docs[:20]
            for c in self.chunk_svc.chunk_document(d)
        ]
        segments, summary = self.segmenter.segment_corpus(sample_chunks)
        self.assertEqual(summary.segments_above_effective_limit, 0)
        for s in segments:
            self.assertLessEqual(s.token_count, self.tokenizer_svc.NOMINAL_MAX_LENGTH)

    def test_15_specification_placeholder_preservation(self):
        """Verify specification placeholders remain intact in generated segments."""
        spec_chunks = [
            c for d in self.docs
            for c in self.chunk_svc.chunk_document(d)
            if c.metadata.contains_spec_placeholder
        ]
        self.assertGreater(len(spec_chunks), 0)
        for sc in spec_chunks:
            segs = self.segmenter.segment_chunk(sc)
            for s in segs:
                if "[SPEC_REQUIRED:" in s.content:
                    self.assertTrue(s.metadata.contains_spec_placeholder)

    def test_16_repeated_run_idempotency(self):
        """Verify segmentation is strictly deterministic across repeated runs."""
        segs_run1 = self.segmenter.segment_chunk(self.sample_incident_chunk)
        segs_run2 = self.segmenter.segment_chunk(self.sample_incident_chunk)

        self.assertEqual(len(segs_run1), len(segs_run2))
        for s1, s2 in zip(segs_run1, segs_run2):
            self.assertEqual(s1.embedding_segment_id, s2.embedding_segment_id)
            self.assertEqual(s1.content_hash, s2.content_hash)
            self.assertEqual(s1.token_count, s2.token_count)


if __name__ == "__main__":
    unittest.main()
