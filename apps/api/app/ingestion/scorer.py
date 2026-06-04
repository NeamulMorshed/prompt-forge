def score_pattern(pattern: dict) -> float:
    score = 5.0

    confidence = float(pattern.get("confidence", 0.5))
    score += confidence * 2.0

    abstraction = pattern.get("abstraction", "")
    word_count = len(abstraction.split())
    if word_count >= 20:
        score += 1.5
    elif word_count >= 10:
        score += 0.5

    structure = pattern.get("structure", "")
    parts = len(structure.split("+"))
    if 2 <= parts <= 5:
        score += 1.0

    has_copy_signals = any(word in abstraction.lower() for word in ["click", "buy now", "brand", "product name"])
    if has_copy_signals:
        score -= 2.0

    return round(min(10.0, max(1.0, score)), 1)
