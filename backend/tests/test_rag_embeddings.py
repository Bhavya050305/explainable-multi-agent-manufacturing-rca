"""
ManuMind AI — Phase 3 Step 4: RAG Embedding Model Tests
Verifies official BAAI/bge-small-en-v1.5 CPU embedding generation, 384-dimensional output,
finite numerical checks, L2 normalization, deterministic repeatability, and batch processing.

Department of AI & Data Science — RMK Engineering College
"""

import sys
import unittest
import numpy as np
import torch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.embedding_model import BGEEmbeddingModel, bge_embedding_model


class TestRAGEmbeddings(unittest.TestCase):
    """Authoritative test suite for BGE-small dense embedding model."""

    @classmethod
    def setUpClass(cls):
        cls.embedder = bge_embedding_model

    def test_01_output_dimension_equals_384(self):
        """Verify model output shape is exactly (N, 384) for single and multiple inputs."""
        single_vec = self.embedder.embed_single("CNC Lathe Alpha vibration telemetry")
        self.assertEqual(single_vec.shape, (384,))

        batch_vecs = self.embedder.embed_texts([
            "Hydraulic stamping press oil temperature alert",
            "5-Axis milling center rotary trunnion backlash",
        ])
        self.assertEqual(batch_vecs.shape, (2, 384))

    def test_02_finite_numerical_values(self):
        """Verify generated embeddings contain only finite values (zero NaN, zero Inf)."""
        texts = [
            "Normal baseline operation",
            "Progressive bearing wear fault mode",
            "Emergency stop lockout tagout checklist",
        ]
        vecs = self.embedder.embed_texts(texts)
        self.assertTrue(np.all(np.isfinite(vecs)))
        self.assertFalse(np.any(np.isnan(vecs)))
        self.assertFalse(np.any(np.isinf(vecs)))

    def test_03_deterministic_input_to_output_mapping(self):
        """Verify identical input text produces identical embedding vectors across repeated runs."""
        text = "M104 ceramic hybrid spindle bearing replacement work order."
        vec1 = self.embedder.embed_single(text)
        vec2 = self.embedder.embed_single(text)

        np.testing.assert_array_almost_equal(vec1, vec2, decimal=6)

    def test_04_l2_normalization_for_cosine_distance(self):
        """Verify output vectors are unit L2 normalized (Euclidean norm == 1.0)."""
        texts = [
            "Thermal excursion above 65°C on hydraulic reservoir.",
            "Spindle vibration RMS elevated to 6.2 mm/s.",
        ]
        vecs = self.embedder.embed_texts(texts, normalize=True)
        norms = np.linalg.norm(vecs, axis=1)
        for n in norms:
            self.assertAlmostEqual(float(n), 1.0, places=5)

    def test_05_batch_handling_invariance(self):
        """Verify batching produces identical results regardless of batch_size."""
        texts = [
            f"Manufacturing diagnostic sentence number {i} for fleet health monitoring."
            for i in range(10)
        ]
        vecs_batch_2 = self.embedder.embed_texts(texts, batch_size=2)
        vecs_batch_5 = self.embedder.embed_texts(texts, batch_size=5)

        np.testing.assert_array_almost_equal(vecs_batch_2, vecs_batch_5, decimal=5)

    def test_06_empty_batch_handling(self):
        """Verify passing empty list returns empty array of shape (0, 384)."""
        vecs = self.embedder.embed_texts([])
        self.assertEqual(vecs.shape, (0, 384))
        self.assertEqual(vecs.dtype, np.float32)

    def test_07_cpu_only_execution_verification(self):
        """Verify execution device is strictly CPU and CUDA is not required or utilized."""
        self.assertEqual(self.embedder.device.type, "cpu")
        # Ensure model parameters are on CPU
        for param in self.embedder.model.parameters():
            self.assertEqual(param.device.type, "cpu")
            break

    def test_08_model_identity_verification(self):
        """Verify model name, architecture, and revision commit hash."""
        self.assertEqual(self.embedder.model_name, "BAAI/bge-small-en-v1.5")
        self.assertEqual(self.embedder.MODEL_NAME, "BAAI/bge-small-en-v1.5")
        self.assertEqual(self.embedder.REVISION_COMMIT_HASH, "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a")
        self.assertEqual(self.embedder.embedding_dim, 384)

    def test_09_semantic_similarity_sanity(self):
        """Verify semantically related texts have higher cosine similarity than unrelated texts."""
        emb_bearing1 = self.embedder.embed_single("High vibration and acoustic noise on spindle bearing inner raceway.")
        emb_bearing2 = self.embedder.embed_single("Spindle bearing race micro-spalling and ball pass frequency defect.")
        emb_unrelated = self.embedder.embed_single("Invoice approval workflow for administrative procurement office.")

        sim_related = np.dot(emb_bearing1, emb_bearing2)
        sim_unrelated = np.dot(emb_bearing1, emb_unrelated)

        self.assertGreater(sim_related, sim_unrelated)
        self.assertGreater(sim_related, 0.6)


if __name__ == "__main__":
    unittest.main()
