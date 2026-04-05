from config import (
    PRIMARY_CATEGORIES,
    AUXILIARY_CATEGORIES,
    RULE_PENALTY_WEIGHTS,
    MAX_RAW_PENALTY,
    SCORE_MIN,
    SCORE_MAX,
    ROUND_DIGITS,
)


def clamp_score(value: float, min_value: float = SCORE_MIN, max_value: float = SCORE_MAX) -> float:
    return max(min_value, min(max_value, value))


def round_score(value: float) -> float:
    return round(value, ROUND_DIGITS)


def compute_penalty_details(feature_counts: dict, categories: list[str] | None = None) -> dict:
    target_categories = categories or PRIMARY_CATEGORIES
    penalty_details = {}

    for category in target_categories:
        category_counts = feature_counts.get(category, {})
        category_weights = RULE_PENALTY_WEIGHTS.get(category, {})
        category_detail = {}

        for feature_name, count in category_counts.items():
            weight = category_weights.get(feature_name, 0.0)
            category_detail[feature_name] = round_score(count * weight)

        penalty_details[category] = category_detail

    return penalty_details


def compute_raw_penalties(feature_counts: dict, categories: list[str] | None = None) -> dict:
    target_categories = categories or PRIMARY_CATEGORIES
    raw_penalties = {}

    for category in target_categories:
        category_counts = feature_counts.get(category, {})
        category_weights = RULE_PENALTY_WEIGHTS.get(category, {})

        total_penalty = 0.0
        for feature_name, count in category_counts.items():
            weight = category_weights.get(feature_name, 0.0)
            total_penalty += count * weight

        raw_penalties[category] = round_score(total_penalty)

    return raw_penalties


def convert_penalty_to_rule_score(raw_penalty: float, category: str) -> float:
    max_penalty = MAX_RAW_PENALTY.get(category, 5.0)

    if max_penalty <= 0:
        return SCORE_MAX

    normalized_penalty = min(raw_penalty / max_penalty, 1.0)
    score = SCORE_MAX - normalized_penalty * (SCORE_MAX - SCORE_MIN)
    return round_score(clamp_score(score))


def compute_rule_scores(raw_penalties: dict, categories: list[str] | None = None) -> dict:
    target_categories = categories or PRIMARY_CATEGORIES
    rule_scores = {}

    for category in target_categories:
        raw_penalty = raw_penalties.get(category, 0.0)
        rule_scores[category] = convert_penalty_to_rule_score(raw_penalty, category)

    return rule_scores


def compute_auxiliary_raw_penalties(feature_counts: dict) -> dict:
    return compute_raw_penalties(feature_counts, categories=AUXILIARY_CATEGORIES)


def compute_auxiliary_rule_scores(raw_penalties: dict) -> dict:
    return compute_rule_scores(raw_penalties, categories=AUXILIARY_CATEGORIES)