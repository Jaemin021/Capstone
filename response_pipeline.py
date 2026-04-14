from scoring.response_rule_scoring import (
    analyze_response_features,
    compute_response_penalty_details,
    compute_response_raw_penalties,
    compute_response_rule_scores,
    build_response_flags,
    count_response_issues,
)
from scoring.response_score_combiner import (
    compute_overall_response_score,
)
from config import RESPONSE_CATEGORIES


def analyze_response_reliability(survey: dict, response: dict) -> dict:
    """
    survey JSON + response JSON을 함께 사용하여
    응답 신뢰도 결과를 계산
    """
    feature_analysis, feature_counts = analyze_response_features(survey, response)

    penalty_details = compute_response_penalty_details(
        feature_counts,
        categories=RESPONSE_CATEGORIES,
    )

    raw_penalties = compute_response_raw_penalties(
        feature_counts,
        categories=RESPONSE_CATEGORIES,
    )

    rule_scores = compute_response_rule_scores(
        raw_penalties,
        categories=RESPONSE_CATEGORIES,
    )

    overall_response_score, overall_response_score_100 = compute_overall_response_score(
        rule_scores,
        categories=RESPONSE_CATEGORIES,
    )

    flags = build_response_flags(feature_counts)
    issue_count = count_response_issues(feature_counts, categories=RESPONSE_CATEGORIES)

    result = {
        "survey_id": response.get("survey_id", survey.get("survey_id")),
        "response_id": response.get("response_id"),
        "participant_id": response.get("participant_id"),

        "feature_analysis": feature_analysis,
        "feature_counts": feature_counts,

        "penalty_details": penalty_details,
        "raw_penalties": raw_penalties,
        "rule_scores": rule_scores,

        "overall_response_score": overall_response_score,
        "overall_response_score_100": overall_response_score_100,

        "flags": flags,
        "issue_count": issue_count,
        "has_issue": issue_count > 0,
    }

    return result