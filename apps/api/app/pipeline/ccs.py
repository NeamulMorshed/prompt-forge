from app.pipeline.crs_loader import Slot


def compute_ccs(slots: list[Slot], filled: dict[str, str]) -> float:
    total = sum(s.weight for s in slots)
    if total == 0.0:
        return 0.0
    filled_w = sum(s.weight for s in slots if filled.get(s.id))
    return round(filled_w / total, 4)


def needs_discovery(slots: list[Slot], filled: dict[str, str], threshold: float = 0.70) -> bool:
    if compute_ccs(slots, filled) < threshold:
        return True
    return any(s.required and not filled.get(s.id) for s in slots)
