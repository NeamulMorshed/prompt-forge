from app.pipeline.ccs import compute_ccs, needs_discovery
from app.pipeline.crs_loader import Slot

_SLOTS = [
    Slot(id="goal",     weight=0.20, required=True,  hint=""),
    Slot(id="audience", weight=0.18, required=True,  hint=""),
    Slot(id="channel",  weight=0.15, required=True,  hint=""),
    Slot(id="tone",     weight=0.12, required=False, hint=""),
]
_TOTAL_WEIGHT = 0.65


def test_empty_slots_gives_zero():
    assert compute_ccs(_SLOTS, {}) == 0.0


def test_all_filled_gives_one():
    filled = {"goal": "x", "audience": "x", "channel": "x", "tone": "x"}
    assert compute_ccs(_SLOTS, filled) == 1.0


def test_partial_fill():
    filled = {"goal": "x", "audience": "x"}
    ccs = compute_ccs(_SLOTS, filled)
    expected = round((0.20 + 0.18) / _TOTAL_WEIGHT, 4)
    assert abs(ccs - expected) < 0.0001


def test_needs_discovery_when_ccs_below_threshold():
    assert needs_discovery(_SLOTS, {}, threshold=0.70) is True


def test_no_discovery_when_all_required_filled_and_ccs_high():
    filled = {"goal": "x", "audience": "x", "channel": "x", "tone": "x"}
    assert needs_discovery(_SLOTS, filled, threshold=0.70) is False


def test_needs_discovery_when_required_slot_empty_even_if_ccs_ok():
    # tone is optional, so filling goal+audience+tone gives high CCS but channel (required) missing
    filled = {"goal": "x", "audience": "x", "tone": "x"}
    # CCS = (0.20+0.18+0.12)/0.65 = 0.769, above threshold, but "channel" required+empty
    assert needs_discovery(_SLOTS, filled, threshold=0.70) is True
