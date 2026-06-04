import hashlib
import logging

from app.ingestion.crawler import fetch_page_markdown, fetch_urls_for_domain
from app.ingestion.extractor import extract_patterns
from app.ingestion.scorer import score_pattern
from app.llm.router import LLMRouter
from app.registry.qdrant_store import PatternPoint, QdrantPatternStore

logger = logging.getLogger("app.ingestion.pipeline")

_MIN_QUALITY_SCORE = 6.5


def embed_text(text: str) -> list[float]:
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(text).tolist()
    except ImportError:
        import random
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        return [rng.gauss(0, 1) for _ in range(384)]


def run_ingestion_pipeline(
    domain: str,
    store: QdrantPatternStore,
    router: LLMRouter,
    brave_api_key: str,
    max_urls: int = 10,
    min_quality: float = _MIN_QUALITY_SCORE,
) -> int:
    urls = fetch_urls_for_domain(domain, api_key=brave_api_key, max_results=max_urls)
    logger.info("Found %d URLs for domain %s", len(urls), domain)

    ingested = 0
    points: list[PatternPoint] = []

    for url in urls:
        markdown = fetch_page_markdown(url)
        if not markdown:
            continue

        raw_patterns = extract_patterns(markdown, domain=domain, source_url=url, router=router)

        for raw in raw_patterns:
            quality = score_pattern(raw)
            if quality < min_quality:
                logger.debug("Skipping low-quality pattern (%.1f) from %s", quality, url)
                continue

            pattern_text = f"{raw['structure']}: {raw['abstraction']}"
            vector = embed_text(pattern_text)
            pattern_id = hashlib.md5(pattern_text.encode()).hexdigest()[:16]

            points.append(PatternPoint(
                id=f"{domain}_{pattern_id}",
                domain=domain,
                structure=raw["structure"],
                abstraction=raw["abstraction"],
                quality_score=quality,
                vector=vector,
            ))
            ingested += 1

    if points:
        store.upsert(points)
        logger.info("Ingested %d patterns for domain %s", ingested, domain)

    return ingested
