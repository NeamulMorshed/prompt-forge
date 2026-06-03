import pytest
from app.pipeline.crs_loader import Slot, load_crs, load_domain_defaults


def test_load_marketing_content_returns_slots():
    slots = load_crs("marketing_content")
    assert len(slots) == 8
    ids = [s.id for s in slots]
    assert "goal" in ids
    assert "audience" in ids
    assert "channel" in ids


def test_slots_have_correct_types():
    slots = load_crs("marketing_content")
    for s in slots:
        assert isinstance(s.id, str)
        assert 0.0 < s.weight <= 1.0
        assert isinstance(s.required, bool)
        assert isinstance(s.hint, str)


def test_load_writing_academic_returns_slots():
    slots = load_crs("writing_academic")
    ids = [s.id for s in slots]
    assert "goal" in ids
    assert "topic" in ids


def test_domain_defaults_marketing():
    defaults = load_domain_defaults("marketing_content")
    assert defaults.get("tone") == "professional and engaging"


def test_unknown_domain_raises():
    with pytest.raises(FileNotFoundError):
        load_crs("nonexistent_domain")
