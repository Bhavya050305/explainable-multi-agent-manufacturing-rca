"""
ManuMind AI — RAG Official Tokenizer Service
Phase 3 Step 4: Embedding Generation and Vector Database Indexing

Department of AI & Data Science — RMK Engineering College
"""

from typing import List, Optional
from transformers import AutoTokenizer, PreTrainedTokenizerFast


class TokenizerService:
    """
    Official tokenizer service wrapping BAAI/bge-small-en-v1.5 (BertTokenizerFast).
    Provides exact token counting, special token accounting, and budget enforcement.
    """

    MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    REVISION_COMMIT_HASH: str = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
    NOMINAL_MAX_LENGTH: int = 512
    SPECIAL_TOKENS_COUNT: int = 2  # [CLS] and [SEP]
    DEFAULT_EFFECTIVE_BUDGET: int = 500  # Conservative budget below 512

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        effective_budget: int = DEFAULT_EFFECTIVE_BUDGET,
        local_files_only: bool = True,
    ):
        self.model_name = model_name
        self.effective_budget = effective_budget
        self._tokenizer: PreTrainedTokenizerFast = AutoTokenizer.from_pretrained(
            self.model_name,
            local_files_only=local_files_only,
        )

    @property
    def tokenizer(self) -> PreTrainedTokenizerFast:
        """Direct access to underlying fast tokenizer."""
        return self._tokenizer

    @property
    def model_max_length(self) -> int:
        """Maximum context length supported by model architecture (512)."""
        return getattr(self._tokenizer, "model_max_length", self.NOMINAL_MAX_LENGTH)

    @property
    def vocab_size(self) -> int:
        """Vocabulary size of tokenizer."""
        return self._tokenizer.vocab_size

    def get_effective_input_limit(self) -> int:
        """
        Effective content token limit leaving headroom for special tokens ([CLS], [SEP]).
        """
        return min(self.effective_budget, self.NOMINAL_MAX_LENGTH - self.SPECIAL_TOKENS_COUNT)

    def count_tokens(self, text: str, add_special_tokens: bool = False) -> int:
        """
        Count actual tokens using the official BGE BertTokenizerFast.
        If add_special_tokens=True, includes [CLS] and [SEP] (+2 tokens).
        """
        if not text:
            return self.SPECIAL_TOKENS_COUNT if add_special_tokens else 0
        token_ids = self._tokenizer.encode(
            text,
            add_special_tokens=add_special_tokens,
            truncation=False,
        )
        return len(token_ids)

    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        """Encode text into token IDs."""
        if not text:
            return [101, 102] if add_special_tokens else []
        return self._tokenizer.encode(
            text,
            add_special_tokens=add_special_tokens,
            truncation=False,
        )

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into subword tokens."""
        if not text:
            return []
        return self._tokenizer.tokenize(text)

    def decode(self, token_ids: List[int], skip_special_tokens: bool = True) -> str:
        """Decode token IDs back to text."""
        return self._tokenizer.decode(token_ids, skip_special_tokens=skip_special_tokens)


# Singleton instance
tokenizer_service = TokenizerService()
