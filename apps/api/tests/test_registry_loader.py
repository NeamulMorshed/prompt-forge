from app.registry.loader import load_patterns, get_top_patterns, Pattern


def test_load_patterns_marketing_content():
    patterns = load_patterns("marketing_content")
    assert len(patterns) == 10
    assert all(p.domain == "marketing_content" for p in patterns)


def test_patterns_have_required_fields():
    patterns = load_patterns("marketing_content")
    for p in patterns:
        assert isinstance(p.id, str)
        assert isinstance(p.domain, str)
        assert isinstance(p.structure, str)
        assert isinstance(p.abstraction, str)
        assert isinstance(p.quality_score, float)
        assert isinstance(p.sources, list)


def test_patterns_sorted_by_id():
    patterns = load_patterns("marketing_content")
    assert patterns[0].id == "pattern_001"
    assert patterns[1].id == "pattern_002"


def test_quality_scores_reasonable():
    patterns = load_patterns("marketing_content")
    for p in patterns:
        assert 0.0 <= p.quality_score <= 10.0


def test_get_top_patterns_returns_highest_scores():
    patterns = get_top_patterns("marketing_content", limit=3)
    assert len(patterns) <= 3
    # Check they're sorted descending by score
    for i in range(len(patterns) - 1):
        assert patterns[i].quality_score >= patterns[i + 1].quality_score


def test_get_top_patterns_respects_limit():
    patterns = get_top_patterns("marketing_content", limit=5)
    assert len(patterns) == 5

    patterns = get_top_patterns("marketing_content", limit=2)
    assert len(patterns) == 2


def test_load_nonexistent_domain_returns_empty():
    patterns = load_patterns("nonexistent_domain")
    assert patterns == []


def test_pattern_from_dict():
    data = {
        "id": "test_001",
        "domain": "test_domain",
        "structure": "test structure",
        "abstraction": "test abstraction",
        "quality_score": 8.5,
        "sources": ["source1", "source2"],
    }
    pattern = Pattern.from_dict(data)
    assert pattern.id == "test_001"
    assert pattern.domain == "test_domain"
    assert pattern.quality_score == 8.5
    assert len(pattern.sources) == 2
