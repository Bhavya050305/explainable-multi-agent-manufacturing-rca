"""
ManuMind AI — RAG Subprocess Bridge Runner
Phase 4 Step 3: Read-Only RAG Retrieval MCP Tool Implementation

Department of AI & Data Science — RMK Engineering College

Executed strictly in the .venv-rag Python environment to isolate ChromaDB,
PyTorch, Transformers, and tokenizers from the Base Python MCP server environment.
Communication protocol:
- Input: JSON-serialized request on sys.stdin.
- Output: JSON-serialized response on sys.stdout.
- Diagnostics: Strictly routed to sys.stderr.
"""

import sys
import os
import json
import logging
import traceback

# Disable ChromaDB and huggingface telemetry/noise
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Configure logging strictly to stderr to prevent stdout protocol frame pollution
logger = logging.getLogger("rag-bridge-runner")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [RAG-Bridge] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def run_retrieval() -> int:
    """Reads JSON request from stdin, executes RetrievalService, writes JSON response to stdout."""
    try:
        raw_input = sys.stdin.read().strip()
        if not raw_input:
            err_resp = {
                "status": "ERROR",
                "error_type": "EmptyInputError",
                "message": "Empty or missing request payload on stdin.",
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            return 1

        request_data = json.loads(raw_input)
        query = request_data.get("query")
        k = request_data.get("k", 5)

        if not query or not isinstance(query, str) or not query.strip():
            err_resp = {
                "status": "ERROR",
                "error_type": "ValidationError",
                "message": "Query must be a non-empty string.",
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            return 1

        try:
            k = int(k)
        except (ValueError, TypeError):
            err_resp = {
                "status": "ERROR",
                "error_type": "ValidationError",
                "message": f"Parameter 'k' must be an integer, got: {k}",
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            return 1

        logger.info(f"Executing retrieval for query='{query[:60]}...' (k={k})")

        from backend.app.rag.retrieval_service import RetrievalService

        service = RetrievalService()
        response = service.retrieve(query=query, top_k=k)

        results = [
            {
                "rank": item.rank,
                "segment_id": item.segment_id,
                "parent_chunk_id": item.parent_chunk_id,
                "document_id": item.document_id,
                "category": item.category,
                "source_type": item.source_type,
                "is_synthetic": bool(item.is_synthetic),
                "is_safety_related": bool(item.is_safety_related),
                "source_path": item.source_path,
                "section_heading": item.section_heading,
                "parent_heading": item.parent_heading,
                "similarity_score": round(float(item.similarity_score), 6),
                "content": item.content,
                "content_hash": item.content_hash,
                "provenance_validated": bool(item.provenance_validated),
            }
            for item in response.results
        ]

        output = {
            "status": "SUCCESS",
            "query": response.query,
            "requested_top_k": response.requested_top_k,
            "returned_count": response.returned_count,
            "results": results,
            "collection_name": response.collection_name,
            "embedding_model": response.embedding_model,
        }

        sys.stdout.write(json.dumps(output) + "\n")
        sys.stdout.flush()
        return 0

    except Exception as exc:
        logger.error(f"RAG retrieval bridge exception: {exc}", exc_info=True)
        err_resp = {
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
        sys.stdout.write(json.dumps(err_resp) + "\n")
        sys.stdout.flush()
        return 1


if __name__ == "__main__":
    exit_code = run_retrieval()
    sys.exit(exit_code)
