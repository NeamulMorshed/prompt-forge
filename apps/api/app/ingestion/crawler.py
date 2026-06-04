import logging

import httpx
import markdownify

logger = logging.getLogger("app.ingestion.crawler")

_DOMAIN_QUERIES: dict[str, str] = {
    "marketing_content": "best copywriting frameworks email marketing structural patterns site:copyhackers.com OR site:conversionxl.com",
    "d2c_ad_creative": "Facebook ad copy frameworks D2C advertising patterns structure",
    "real_estate_listing": "real estate listing copywriting frameworks property description patterns",
    "writing_academic": "academic writing structure patterns thesis argument frameworks",
}

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


def fetch_urls_for_domain(domain: str, api_key: str, max_results: int = 10) -> list[str]:
    query = _DOMAIN_QUERIES.get(domain, f"{domain} copywriting frameworks structural patterns")
    try:
        resp = httpx.get(
            _BRAVE_SEARCH_URL,
            params={"q": query, "count": max_results},
            headers={"Accept": "application/json", "X-Subscription-Token": api_key},
            timeout=10.0,
        )
        resp.raise_for_status()
        results = resp.json().get("web", {}).get("results", [])
        return [r["url"] for r in results if "url" in r]
    except Exception as exc:
        logger.warning("Brave search failed for %s: %s", domain, exc)
        return []


def fetch_page_markdown(url: str) -> str | None:
    try:
        resp = httpx.get(url, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type:
            return None
        md = markdownify.markdownify(resp.text, heading_style="ATX")
        return md[:8000]
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None
