#!/usr/bin/env python3
"""CLI: uv run python scripts/run_ingestion.py --domain marketing_content"""
import argparse
import os
import sys

sys.path.insert(0, ".")

from app.config import settings
from app.ingestion.pipeline import run_ingestion_pipeline
from app.llm.factory import build_router
from app.registry.qdrant_store import build_store


def main():
    parser = argparse.ArgumentParser(description="Run pattern ingestion pipeline")
    parser.add_argument("--domain", required=True, help="Domain to ingest patterns for")
    parser.add_argument("--max-urls", type=int, default=10)
    parser.add_argument("--min-quality", type=float, default=6.5)
    args = parser.parse_args()

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    brave_api_key = os.getenv("BRAVE_API_KEY", "")
    if not brave_api_key:
        print("ERROR: BRAVE_API_KEY env var required")
        sys.exit(1)

    store = build_store(url=qdrant_url)
    store.ensure_collection(vector_size=384)

    router = build_router(
        groq_api_key=settings.groq_api_key,
        gemini_api_key=settings.gemini_api_key,
    )

    count = run_ingestion_pipeline(
        domain=args.domain,
        store=store,
        router=router,
        brave_api_key=brave_api_key,
        max_urls=args.max_urls,
        min_quality=args.min_quality,
    )
    print(f"Ingested {count} patterns for domain '{args.domain}'")


if __name__ == "__main__":
    main()
