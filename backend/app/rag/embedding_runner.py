"""
ManuMind AI — Embedding and Vector Indexing Runner
Phase 3 Step 4: Embedding Generation and Vector Database Indexing

Department of AI & Data Science — RMK Engineering College
"""

import json
import sys
from pathlib import Path

# Add project root to path
repo_root = Path(__file__).resolve().parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.app.rag.embedding_service import embedding_service


def main():
    print("=" * 70)
    print("ManuMind AI — Phase 3 Step 4: Embedding & Vector Index Pipeline")
    print("=" * 70)

    results = embedding_service.run_pipeline()

    print("\n--- Pipeline Execution Summary ---")
    summary_to_print = {k: v for k, v in results.items() if k != "segmentation_summary"}
    print(json.dumps(summary_to_print, indent=2))

    print("\nPersistence verification:", results.get("persistence_verified"))
    print("Total segments:", results.get("total_segments_generated"))
    print("Vector dimensions:", results.get("embedding_dimension"))
    print("Status:", results.get("status"))


if __name__ == "__main__":
    main()
