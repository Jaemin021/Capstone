from config import (
    RESPONSE_CATEGORIES,
    RESPONSE_SCORE_WEIGHTS,
    SCORE_MIN,
    SCORE_MAX,
    ROUND_DIGITS,
)


def clamp_score(value: float, min_value: float = SCORE_MIN, max_value: float = SCORE_MAX) -> float:
    return max(min_value, min(max_value, value))


def round_score(value: float) -> float:
    return round(value, ROUND_DIGITS)


def compute_overall_response_score(rule_scores: dict, categories: list[str] | None = None) -> tuple[float, float]:
    """
    category별 응답 rule score를 받아
    최종 overall_response_score(1~10),
    overall_response_score_100(0~100) 계산
    """
    target_categories = RESPONSE_CATEGORIES if categories is None else categories

    weighted_sum = 0.0
    total_weight = 0.0

    for category in target_categories:
        if category not in rule_scores or rule_scores.get(category) is None:
            raise ValueError(f"Missing response rule score for category: {category}")

        score = float(rule_scores[category])
        weight = float(RESPONSE_SCORE_WEIGHTS.get(category, 0.0))

        weighted_sum += score * weight
        total_weight += weight

    if total_weight <= 0:
        overall_score = SCORE_MIN
    else:
        overall_score = weighted_sum / total_weight

    overall_score = round_score(clamp_score(overall_score))
    overall_score_100 = round_score(overall_score * 10)

    return overall_score, overall_score_100