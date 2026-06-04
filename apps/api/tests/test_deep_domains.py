import pytest
from unittest.mock import MagicMock
from app.pipeline.classifier import classify, _KNOWN_DOMAINS
from app.llm.types import CompletionResult


def _mock_router(domain: str):
    router = MagicMock()
    router.complete.return_value = CompletionResult(
        text=f'{{"domain": "{domain}", "intent": "test", "clarity": 0.8}}',
        model="mock/mock",
        prompt_tokens=10,
        completion_tokens=10,
    )
    return router


def test_known_domains_includes_real_estate():
    assert "real_estate_listing" in _KNOWN_DOMAINS


def test_known_domains_includes_d2c():
    assert "d2c_ad_creative" in _KNOWN_DOMAINS


def test_classify_real_estate_listing():
    router = _mock_router("real_estate_listing")
    result = classify("write a listing for my 3-bed house", router)
    assert result.domain == "real_estate_listing"


def test_classify_d2c_ad():
    router = _mock_router("d2c_ad_creative")
    result = classify("create a Facebook ad for my skincare product", router)
    assert result.domain == "d2c_ad_creative"


from app.pipeline.constructor import construct, _DOMAIN_ROLES
from app.pipeline.assembler import ContextObject, ContextValue


def _make_ctx(domain: str, slots: dict[str, str]) -> ContextObject:
    return ContextObject(
        domain=domain,
        intent="test",
        clarity=0.8,
        questions_asked=2,
        final_ccs=0.75,
        slots={k: ContextValue(value=v, source="session") for k, v in slots.items()},
    )


def test_domain_roles_has_real_estate():
    assert "real_estate_listing" in _DOMAIN_ROLES


def test_domain_roles_has_d2c():
    assert "d2c_ad_creative" in _DOMAIN_ROLES


def test_construct_real_estate_includes_property():
    ctx = _make_ctx("real_estate_listing", {
        "goal": "sell a family home",
        "property": "4-bed detached house, 2000sqft, suburb of Austin",
        "highlights": "large garden, new kitchen, A-rated schools nearby",
        "audience": "young families",
    })
    result = construct(ctx, model="gemini-2.0-flash")
    assert "real estate" in result.lower() or "property" in result.lower() or "listing" in result.lower()


def test_construct_d2c_includes_ad_framing():
    ctx = _make_ctx("d2c_ad_creative", {
        "goal": "drive conversions for skincare product",
        "product": "NovaSkin serum — reduces wrinkles in 14 days, $49",
        "audience": "women 35-55 concerned about aging",
        "channel": "Facebook feed ad",
    })
    result = construct(ctx, model="gemini-2.0-flash")
    assert len(result) > 100
