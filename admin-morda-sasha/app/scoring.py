RISK_THRESHOLDS = (
    (10, "LOW"),
    (40, "MEDIUM"),
    (80, "HIGH"),
    (100, "CRITICAL"),
)


def risk_from_score(score: int) -> str:
    if not 0 <= score <= 100:
        raise ValueError("score must be 0..100")

    for upper, level in RISK_THRESHOLDS:
        if score <= upper:
            return level

    return "CRITICAL"
