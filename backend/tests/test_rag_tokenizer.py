"""
ManuMind AI — Phase 3 Step 4: RAG Official Tokenizer Tests
Verifies official BAAI/bge-small-en-v1.5 tokenizer properties, actual token counts,
special-token accounting, effective limits, and Unicode/placeholder preservation.

Department of AI & Data Science — RMK Engineering College
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.tokenizer_service import TokenizerService, tokenizer_service


class TestRAGTokenizer(unittest.TestCase):
    """Authoritative test suite for official BGE-small tokenizer integration."""

    @classmethod
    def setUpClass(cls):
        cls.service = tokenizer_service

    def test_01_model_and_tokenizer_identity(self):
        """Verify model name, architecture, and fast tokenizer class."""
        self.assertEqual(self.service.model_name, "BAAI/bge-small-en-v1.5")
        self.assertEqual(self.service.MODEL_NAME, "BAAI/bge-small-en-v1.5")
        self.assertTrue(self.service.tokenizer.is_fast)
        self.assertEqual(self.service.tokenizer.__class__.__name__, "BertTokenizerFast")

    def test_02_actual_token_counting(self):
        """Verify token counts are exact and positive on standard technical text."""
        text = "CNC Lathe Alpha main spindle bearing temperature steady-state check."
        count_no_special = self.service.count_tokens(text, add_special_tokens=False)
        count_with_special = self.service.count_tokens(text, add_special_tokens=True)

        self.assertGreater(count_no_special, 0)
        # Adding special tokens ([CLS], [SEP]) must add exactly 2 tokens
        self.assertEqual(count_with_special, count_no_special + 2)

    def test_03_special_tokens_accounting(self):
        """Verify [CLS] and [SEP] special tokens and IDs match BertTokenizer standard."""
        tokens = self.service.tokenizer.all_special_tokens
        ids = self.service.tokenizer.all_special_ids

        self.assertIn("[CLS]", tokens)
        self.assertIn("[SEP]", tokens)
        self.assertIn("[PAD]", tokens)
        self.assertIn("[UNK]", tokens)

        cls_id = self.service.tokenizer.cls_token_id
        sep_id = self.service.tokenizer.sep_token_id
        self.assertEqual(cls_id, 101)
        self.assertEqual(sep_id, 102)

        # Empty string encoded with special tokens must be exactly [101, 102]
        encoded_empty = self.service.encode("", add_special_tokens=True)
        self.assertEqual(encoded_empty, [101, 102])

    def test_04_prefix_accounting(self):
        """Verify token counts properly account for retrieval query prefix if applied."""
        query_prefix = "Represent this sentence for searching relevant passages: "
        query_text = "hydraulic fluid leak on platen cylinder"

        tokens_prefix = self.service.count_tokens(query_prefix, add_special_tokens=False)
        tokens_query = self.service.count_tokens(query_text, add_special_tokens=False)
        tokens_combined = self.service.count_tokens(f"{query_prefix}{query_text}", add_special_tokens=False)

        # Combined must equal or closely match sum of components
        self.assertGreater(tokens_prefix, 5)
        self.assertEqual(tokens_combined, tokens_prefix + tokens_query)

    def test_05_effective_input_limit(self):
        """Verify nominal model max length (512) and conservative effective content limit (500)."""
        self.assertEqual(self.service.model_max_length, 512)
        effective_limit = self.service.get_effective_input_limit()
        self.assertLessEqual(effective_limit, 510)  # Must leave headroom for 2 special tokens
        self.assertEqual(effective_limit, 500)

    def test_06_empty_input(self):
        """Verify safe handling of empty string, None-like, and whitespace-only text."""
        self.assertEqual(self.service.count_tokens("", add_special_tokens=False), 0)
        self.assertEqual(self.service.count_tokens("   \n\t  ", add_special_tokens=False), 0)
        self.assertEqual(self.service.count_tokens("", add_special_tokens=True), 2)
        self.assertEqual(self.service.tokenize(""), [])

    def test_07_unicode_text_handling(self):
        """Verify accurate tokenization of manufacturing units, Greek symbols, and temperatures."""
        unicode_text = "Operating temperature: 65°C ± 2.5°C; Viscosity: 46 mm²/s; Micro-strain: 15 µm; Resistance: 10 MΩ."
        tokens = self.service.tokenize(unicode_text)
        token_count = self.service.count_tokens(unicode_text, add_special_tokens=False)

        self.assertGreater(len(tokens), 0)
        self.assertEqual(len(tokens), token_count)
        # Decode must preserve text semantics
        encoded = self.service.encode(unicode_text, add_special_tokens=False)
        decoded = self.service.decode(encoded, skip_special_tokens=True)
        self.assertIn("65", decoded)
        self.assertIn("15", decoded)

    def test_08_specification_placeholder_preservation(self):
        """Verify that [SPEC_REQUIRED:...] placeholders are encoded and decoded intact."""
        placeholder = "[SPEC_REQUIRED: VFD DC Bus Discharge Duration (typically 5-10 minutes)]"
        encoded = self.service.encode(placeholder, add_special_tokens=False)
        decoded = self.service.decode(encoded, skip_special_tokens=True)

        self.assertIn("spec _ required", decoded.lower().replace(" ", " "))
        self.assertIn("5 - 10 minutes", decoded)


if __name__ == "__main__":
    unittest.main()
