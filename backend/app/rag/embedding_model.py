"""
ManuMind AI — RAG BGE Embedding Model
Phase 3 Step 4: Embedding Generation and Vector Database Indexing

Department of AI & Data Science — RMK Engineering College
"""

import math
from typing import List, Union
import numpy as np
import torch
from transformers import AutoModel, PreTrainedModel

from backend.app.rag.tokenizer_service import TokenizerService, tokenizer_service


class BGEEmbeddingModel:
    """
    Wrapper for official BAAI/bge-small-en-v1.5 embedding model executing on CPU.
    Produces deterministic 384-dimensional L2-normalized dense vector representations.
    """

    MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 384
    REVISION_COMMIT_HASH: str = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        tokenizer_svc: TokenizerService | None = None,
        local_files_only: bool = True,
    ):
        self.model_name = model_name
        self.tokenizer_svc = tokenizer_svc or tokenizer_service
        self.device = torch.device("cpu")

        # Load official model weights on CPU
        self._model: PreTrainedModel = AutoModel.from_pretrained(
            self.model_name,
            local_files_only=local_files_only,
        )
        self._model.to(self.device)
        self._model.eval()

    @property
    def model(self) -> PreTrainedModel:
        """Direct access to underlying PyTorch BertModel."""
        return self._model

    @property
    def embedding_dim(self) -> int:
        """Output embedding vector dimensionality (384)."""
        return self.EMBEDDING_DIM

    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Generate dense embeddings for a list of text strings in deterministic batches.
        Returns:
            np.ndarray of shape (len(texts), 384), dtype=np.float32.
        """
        if not texts:
            return np.empty((0, self.EMBEDDING_DIM), dtype=np.float32)

        all_embeddings: List[np.ndarray] = []
        tokenizer = self.tokenizer_svc.tokenizer

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]

            # Tokenize batch with truncation at max model length
            encoded = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self.tokenizer_svc.NOMINAL_MAX_LENGTH,
                return_tensors="pt",
            ).to(self.device)

            with torch.no_grad():
                outputs = self._model(**encoded)
                # BGE standard: take [CLS] token representation (index 0)
                cls_embeddings = outputs.last_hidden_state[:, 0]

                if normalize:
                    cls_embeddings = torch.nn.functional.normalize(
                        cls_embeddings, p=2, dim=1
                    )

            batch_np = cls_embeddings.cpu().numpy().astype(np.float32)

            # Verification: check for finite values (no NaN, no Inf)
            if not np.all(np.isfinite(batch_np)):
                raise ValueError(
                    f"Non-finite values (NaN/Inf) detected in generated embeddings for batch starting at index {i}"
                )

            # Verify dimension
            if batch_np.shape[1] != self.EMBEDDING_DIM:
                raise ValueError(
                    f"Unexpected embedding dimension: expected {self.EMBEDDING_DIM}, got {batch_np.shape[1]}"
                )

            all_embeddings.append(batch_np)

        return np.vstack(all_embeddings)

    def embed_single(self, text: str, normalize: bool = True) -> np.ndarray:
        """Generate embedding for a single text string."""
        return self.embed_texts([text], batch_size=1, normalize=normalize)[0]


# Singleton instance
bge_embedding_model = BGEEmbeddingModel()
