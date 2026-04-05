from copy import deepcopy

from rules.matcher import analyze_item_rules
from scoring.rule_scoring import (
    compute_penalty_details,
    compute_raw_penalties,
    compute_rule_scores,
    compute_auxiliary_raw_penalties,
    compute_auxiliary_rule_scores,
)
from scoring.score_combiner import (
    combine_rule_and_llm_scores,
    compute_overall_pre_score,
)
from llm.eval_evaluator import get_llm_evaluation
from llm.rule_assist_evaluator import get_rule_assist_analysis
from llm.rewrite import suggest_question_rewrite, empty_suggestion
from config import (
    PRIMARY_CATEGORIES,
    AUXILIARY_CATEGORIES,
    INCLUDE_AUXILIARY_LLM_SCORES,
    ENABLE_REWRITE_SUGGESTION,
    REWRITE_THRESHOLD,
    ENABLE_RULE_ASSIST_LLM,
    RULE_ASSIST_CATEGORIES,
)


ALL_CATEGORIES = PRIMARY_CATEGORIES + AUXILIARY_CATEGORIES


def merge_rule_analysis(
    base_rule_analysis: dict,
    assist_rule_analysis: dict,
    categories: list[str],
) -> dict:
    """
    exact matcher 결과와 rule-assist LLM 결과를 병합한다.

    중복 완화 기준:
    - 우선 (feature, dictionary_term) 기준으로 같은 계열 문제를 1개로 본다.
    - exact가 먼저 들어오므로, exact가 있으면 assist는 같은 key에서 제외된다.
    - dictionary_term이 없으면 보조적으로 match를 사용한다.
    """
    merged = {}

    for category in categories:
        base_matches = base_rule_analysis.get(category, []) or []
        assist_matches = assist_rule_analysis.get(category, []) or []

        seen = set()
        merged_matches = []

        for item in base_matches + assist_matches:
            feature = str(item.get("feature", "")).strip()
            dictionary_term = str(item.get("dictionary_term", "")).strip()
            match = str(item.get("match", "")).strip()
            source = str(item.get("source", "")).strip()

            if not feature or not match:
                continue

            canonical_term = dictionary_term if dictionary_term else match
            key = (feature, canonical_term)

            if key in seen:
                continue

            if not source:
                source = "exact"

            seen.add(key)
            merged_matches.append({
                "feature": feature,
                "dictionary_term": canonical_term,
                "match": match,
                "source": source,
            })

        merged[category] = merged_matches

    return merged


def rebuild_feature_counts_from_rule_analysis(
    rule_analysis: dict,
    base_feature_counts: dict,
    categories: list[str],
) -> dict:
    """
    병합된 rule_analysis를 기준으로 feature_counts를 다시 계산한다.
    feature key 구조는 base_feature_counts를 기준으로 유지한다.
    """
    rebuilt = deepcopy(base_feature_counts)

    for category in categories:
        category_counts = rebuilt.get(category, {})

        for feature_name in category_counts.keys():
            category_counts[feature_name] = 0

        for item in rule_analysis.get(category, []):
            feature = item.get("feature")
            if feature in category_counts:
                category_counts[feature] += 1

        rebuilt[category] = category_counts

    return rebuilt


def analyze_item(item: dict) -> dict:
    question = item.get("question", "") or ""
    option_type = item.get("option_type", "") or ""
    options = item.get("options", []) or []

    # 1) Exact rule-based analysis
    rule_result = analyze_item_rules(item)
    exact_rule_analysis = rule_result["rule_analysis"]
    exact_feature_counts = rule_result["feature_counts"]

    # 2) Optional rule-assist LLM analysis
    assist_rule_analysis = {category: [] for category in ALL_CATEGORIES}

    if ENABLE_RULE_ASSIST_LLM:
        assist_result = get_rule_assist_analysis(
            question=question,
            categories=RULE_ASSIST_CATEGORIES,
            exact_rule_analysis=exact_rule_analysis,
        )
        raw_assist_rule_analysis = assist_result.get("rule_analysis", {})

        for category in ALL_CATEGORIES:
            assist_rule_analysis[category] = raw_assist_rule_analysis.get(category, [])

    # 3) Merge exact rule + assist rule
    rule_analysis = merge_rule_analysis(
        base_rule_analysis=exact_rule_analysis,
        assist_rule_analysis=assist_rule_analysis,
        categories=ALL_CATEGORIES,
    )

    feature_counts = rebuild_feature_counts_from_rule_analysis(
        rule_analysis=rule_analysis,
        base_feature_counts=exact_feature_counts,
        categories=ALL_CATEGORIES,
    )

    primary_issue_count = sum(len(rule_analysis.get(category, [])) for category in PRIMARY_CATEGORIES)
    auxiliary_issue_count = sum(len(rule_analysis.get(category, [])) for category in AUXILIARY_CATEGORIES)
    total_issue_count = primary_issue_count + auxiliary_issue_count

    # 4) Rule-based scoring (primary categories)
    penalty_details = compute_penalty_details(feature_counts, categories=PRIMARY_CATEGORIES)
    raw_penalties = compute_raw_penalties(feature_counts, categories=PRIMARY_CATEGORIES)
    rule_scores = compute_rule_scores(raw_penalties, categories=PRIMARY_CATEGORIES)

    # 5) Auxiliary category scoring
    auxiliary_penalty_details = {}
    auxiliary_raw_penalties = {}
    auxiliary_rule_scores = {}

    if AUXILIARY_CATEGORIES:
        auxiliary_penalty_details = compute_penalty_details(
            feature_counts, categories=AUXILIARY_CATEGORIES
        )
        auxiliary_raw_penalties = compute_auxiliary_raw_penalties(feature_counts)
        auxiliary_rule_scores = compute_auxiliary_rule_scores(auxiliary_raw_penalties)

    # 6) LLM evaluation (existing free evaluation)
    llm_scores = get_llm_evaluation(
        question=question,
        option_type=option_type,
        options=options,
        rule_analysis=rule_analysis,
        feature_counts=feature_counts,
    )

    # 7) Combine rule + llm
    final_scores = combine_rule_and_llm_scores(
        rule_scores=rule_scores,
        llm_scores=llm_scores,
        categories=PRIMARY_CATEGORIES,
    )

    # 8) Overall pre score
    overall_pre_score, overall_pre_score_100 = compute_overall_pre_score(
        final_scores,
        categories=PRIMARY_CATEGORIES,
    )

    # 9) Optional rewrite suggestion
    suggestion = empty_suggestion()
    if ENABLE_REWRITE_SUGGESTION and overall_pre_score_100 < REWRITE_THRESHOLD:
        suggestion = suggest_question_rewrite(
            question=question,
            option_type=option_type,
            options=options,
            rule_analysis=rule_analysis,
            final_scores=final_scores,
            overall_pre_score=overall_pre_score,
        )

    result = {
        "item_id": item.get("item_id"),
        "question": question,
        "option_type": option_type,
        "options": options,

        "rule_analysis": rule_analysis,
        "feature_counts": feature_counts,

        "penalty_details": penalty_details,
        "raw_penalties": raw_penalties,
        "rule_scores": rule_scores,

        "llm_scores": {
            category: llm_scores.get(category)
            for category in PRIMARY_CATEGORIES
        },

        "final_scores": final_scores,
        "overall_pre_score": overall_pre_score,
        "overall_pre_score_100": overall_pre_score_100,

        "primary_issue_count": primary_issue_count,
        "auxiliary_issue_count": auxiliary_issue_count,
        "issue_count": total_issue_count,
        "has_issue": total_issue_count > 0,

        "suggestion": suggestion,
    }

    result["exact_rule_analysis"] = exact_rule_analysis
    result["assist_rule_analysis"] = assist_rule_analysis

    if AUXILIARY_CATEGORIES:
        result["auxiliary_rule_analysis"] = {
            category: rule_analysis.get(category, [])
            for category in AUXILIARY_CATEGORIES
        }
        result["auxiliary_feature_counts"] = {
            category: feature_counts.get(category, {})
            for category in AUXILIARY_CATEGORIES
        }
        result["auxiliary_penalty_details"] = auxiliary_penalty_details
        result["auxiliary_raw_penalties"] = auxiliary_raw_penalties
        result["auxiliary_rule_scores"] = auxiliary_rule_scores

        if INCLUDE_AUXILIARY_LLM_SCORES:
            result["auxiliary_llm_scores"] = {
                category: llm_scores.get(category)
                for category in AUXILIARY_CATEGORIES
            }

    return result


def analyze_survey(survey: dict) -> dict:
    items = survey.get("items", []) or []
    results = [analyze_item(item) for item in items]

    if not results:
        return {
            "survey_id": survey.get("survey_id"),
            "title": survey.get("title", ""),
            "item_count": 0,
            "summary": {
                "avg_overall_pre_score": 0.0,
                "avg_overall_pre_score_100": 0.0,
                "avg_final_scores": {category: 0.0 for category in PRIMARY_CATEGORIES},
            },
            "items": [],
        }

    avg_overall_pre_score = round(
        sum(item["overall_pre_score"] for item in results) / len(results), 2
    )
    avg_overall_pre_score_100 = round(
        sum(item["overall_pre_score_100"] for item in results) / len(results), 2
    )

    avg_final_scores = {}
    for category in PRIMARY_CATEGORIES:
        values = [item["final_scores"].get(category, 0.0) for item in results]
        avg_final_scores[category] = round(sum(values) / len(values), 2)

    summary = {
        "avg_overall_pre_score": avg_overall_pre_score,
        "avg_overall_pre_score_100": avg_overall_pre_score_100,
        "avg_final_scores": avg_final_scores,
    }

    if AUXILIARY_CATEGORIES and INCLUDE_AUXILIARY_LLM_SCORES:
        avg_auxiliary_llm_scores = {}
        for category in AUXILIARY_CATEGORIES:
            values = []
            for item in results:
                aux_scores = item.get("auxiliary_llm_scores", {})
                category_score = aux_scores.get(category, {}).get("score") if aux_scores.get(category) else None
                if category_score is not None:
                    values.append(float(category_score))

            avg_auxiliary_llm_scores[category] = round(sum(values) / len(values), 2) if values else 0.0

        summary["avg_auxiliary_llm_scores"] = avg_auxiliary_llm_scores

    return {
        "survey_id": survey.get("survey_id"),
        "title": survey.get("title", ""),
        "item_count": len(results),
        "summary": summary,
        "items": results,
    }