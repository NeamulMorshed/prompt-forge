import pytest
from unittest.mock import MagicMock, patch
from app.registry.qdrant_store import QdrantPatternStore, PatternPoint


def test_upsert_calls_qdrant_client():
    mock_client = MagicMock()
    store = QdrantPatternStore(client=mock_client, collection="test_patterns")
    point = PatternPoint(
        id="test_001",
        domain="marketing_content",
        structure="hook + body + cta",
        abstraction="Lead with benefit, explain mechanism, end with CTA.",
        quality_score=8.5,
        vector=[0.1] * 384,
    )
    store.upsert([point])
    mock_client.upsert.assert_called_once()


def test_search_returns_patterns():
    mock_client = MagicMock()
    mock_client.search.return_value = [
        MagicMock(
            payload={
                "domain": "marketing_content",
                "structure": "hook + body + cta",
                "abstraction": "Lead with benefit.",
                "quality_score": 9.0,
            },
            score=0.92,
        )
    ]
    store = QdrantPatternStore(client=mock_client, collection="test_patterns")
    results = store.search(query_vector=[0.1] * 384, domain="marketing_content", limit=3)
    assert len(results) == 1
    assert results[0]["structure"] == "hook + body + cta"
    assert results[0]["score"] == 0.92


def test_ensure_collection_creates_if_missing():
    mock_client = MagicMock()
    mock_client.get_collection.side_effect = Exception("not found")
    store = QdrantPatternStore(client=mock_client, collection="patterns")
    store.ensure_collection(vector_size=384)
    mock_client.create_collection.assert_called_once()


# --- Crawler ---

from app.ingestion.crawler import fetch_urls_for_domain, fetch_page_markdown


def test_fetch_urls_returns_list():
    with patch("app.ingestion.crawler.httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "web": {
                    "results": [
                        {"url": "https://example.com/copywriting-tips"},
                        {"url": "https://example.com/ad-patterns"},
                    ]
                }
            },
        )
        mock_get.return_value.raise_for_status = lambda: None
        urls = fetch_urls_for_domain("d2c_ad_creative", api_key="fake-key", max_results=2)
    assert len(urls) == 2
    assert "https://example.com/copywriting-tips" in urls


def test_fetch_page_markdown_converts_html():
    with patch("app.ingestion.crawler.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body><h1>Great Ad Tips</h1><p>Hook your reader.</p></body></html>"
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.raise_for_status = lambda: None
        mock_get.return_value = mock_resp
        md = fetch_page_markdown("https://example.com/ad-tips")
    assert md is not None
    assert "Great Ad Tips" in md
    assert "Hook your reader" in md


def test_fetch_page_skips_non_html():
    with patch("app.ingestion.crawler.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/pdf"}
        mock_resp.raise_for_status = lambda: None
        mock_get.return_value = mock_resp
        md = fetch_page_markdown("https://example.com/doc.pdf")
    assert md is None


# --- Extractor ---

from app.ingestion.extractor import extract_patterns


def test_extract_patterns_returns_list():
    mock_router = MagicMock()
    mock_router.complete.return_value = MagicMock(
        text='[{"structure": "hook + body + cta", "abstraction": "Lead with benefit, close with action.", "confidence": 0.9}]',
        model="mock/gemini",
        prompt_tokens=100,
        completion_tokens=50,
    )
    patterns = extract_patterns(
        markdown="Some article about copywriting with hook body CTA structure.",
        domain="marketing_content",
        source_url="https://example.com/tips",
        router=mock_router,
    )
    assert len(patterns) == 1
    assert patterns[0]["structure"] == "hook + body + cta"
    assert "abstraction" in patterns[0]


def test_extract_patterns_handles_invalid_json():
    mock_router = MagicMock()
    mock_router.complete.return_value = MagicMock(
        text="not valid json",
        model="mock/gemini",
        prompt_tokens=100,
        completion_tokens=10,
    )
    patterns = extract_patterns(
        markdown="Some content",
        domain="marketing_content",
        source_url="https://example.com",
        router=mock_router,
    )
    assert patterns == []


# --- Scorer ---

from app.ingestion.scorer import score_pattern


def test_score_pattern_high_confidence_abstraction():
    pattern = {
        "structure": "hook + body + cta",
        "abstraction": "Lead with a compelling benefit statement that speaks to the reader's pain, explain the mechanism clearly in the body, end with a specific call-to-action.",
        "confidence": 0.95,
    }
    score = score_pattern(pattern)
    assert score >= 7.0
    assert score <= 10.0


def test_score_pattern_low_confidence():
    pattern = {
        "structure": "x",
        "abstraction": "short",
        "confidence": 0.2,
    }
    score = score_pattern(pattern)
    assert score < 6.0


# --- Pipeline ---

from app.ingestion.pipeline import run_ingestion_pipeline


def test_run_pipeline_end_to_end():
    mock_router = MagicMock()
    mock_router.complete.return_value = MagicMock(
        text='[{"structure": "hook + cta", "abstraction": "Hook reader, immediate CTA — no fluff between intent and action.", "confidence": 0.9}]',
        model="mock/gemini",
        prompt_tokens=50,
        completion_tokens=20,
    )
    mock_store = MagicMock()

    with patch("app.ingestion.pipeline.fetch_urls_for_domain", return_value=["https://example.com/tips"]), \
         patch("app.ingestion.pipeline.fetch_page_markdown", return_value="Great copywriting tips here."), \
         patch("app.ingestion.pipeline.embed_text", return_value=[0.1] * 384):
        count = run_ingestion_pipeline(
            domain="marketing_content",
            store=mock_store,
            router=mock_router,
            brave_api_key="fake",
            max_urls=1,
        )

    assert count >= 1
    mock_store.upsert.assert_called_once()


# --- Semantic loader ---

from app.registry.loader import get_top_patterns_semantic


def test_get_top_patterns_semantic_returns_patterns():
    mock_store = MagicMock()
    mock_store.search.return_value = [
        {
            "pattern_id": "mc_001",
            "structure": "hook + body + cta",
            "abstraction": "Lead with benefit.",
            "quality_score": 9.0,
            "score": 0.91,
        }
    ]
    with patch("app.registry.loader._qdrant_store", mock_store):
        results = get_top_patterns_semantic(
            domain="marketing_content",
            context_text="drive conversions for email campaign targeting B2B SaaS",
            limit=3,
        )
    assert len(results) == 1
    assert results[0].structure == "hook + body + cta"
