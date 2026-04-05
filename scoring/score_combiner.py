from config import (
    PRIMARY_CATEGORIES,
    CATEGORY_SCORE_WEIGHTS,
    SCORE_MIN,
    SCORE_MAX,
    ROUND_DIGITS,
)


def clamp_score(value: float, min_value: float = SCORE_MIN, max_value: float = SCORE_MAX) -> float:
    return max(min_value, min(max_value, value))


def round_score(value: float) -> float:
    return round(value, ROUND_DIGITS)


def combine_rule_and_llm_scores(rule_scores: dict, llm_scores: dict, categories: list[str] | None = None) -> dict:
    target_categories = PRIMARY_CATEGORIES if categories is None else categories
    final_scores = {}

    for category in target_categories:
        if category not in rule_scores or rule_scores.get(category) is None:
            raise ValueError(f"Missing rule score for category: {category}")

        rule_score = float(rule_scores[category])

        llm_entry = llm_scores.get(category)
        llm_score = None

        if isinstance(llm_entry, dict):
            raw_llm_score = llm_entry.get("score")
            if raw_llm_score is not None:
                llm_score = float(raw_llm_score)

        if llm_score is None:
            llm_score = rule_score

        weights = CATEGORY_SCORE_WEIGHTS.get(category, {"rule": 0.7, "llm": 0.3})
        rule_weight = weights.get("rule", 0.7)
        llm_weight = weights.get("llm", 0.3)

        final_score = (rule_score * rule_weight) + (llm_score * llm_weight)
        final_scores[category] = round_score(clamp_score(final_score))

    return final_scores


def compute_overall_pre_score(final_scores: dict, categories: list[str] | None = None) -> tuple[float, float]:
    target_categories = PRIMARY_CATEGORIES if categories is None else categories
    values = [float(final_scores[category]) for category in target_categories if category in final_scores]

    if not values:
        return SCORE_MIN, 0.0

    overall_pre_score = round_score(sum(values) / len(values))
    overall_pre_score_100 = round_score(overall_pre_score * 10)

    return overall_pre_score, overall_pre_score_100