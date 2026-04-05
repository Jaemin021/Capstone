from config import PRIMARY_CATEGORIES, AUXILIARY_CATEGORIES
from dictionaries.terms import TERM_DICTIONARY


ALL_CATEGORIES = PRIMARY_CATEGORIES + AUXILIARY_CATEGORIES


def find_term_matches(text: str, terms: list[str]) -> list[str]:
    """
    주어진 text 안에 terms의 항목이 포함되어 있는지 검사하여
    중복 없이 매칭된 용어 목록을 반환한다.
    """
    if not text:
        return []

    found = []
    for term in terms:
        if term in text and term not in found:
            found.append(term)
    return found


def analyze_text_by_dictionary(text: str, category_filter: list[str] | None = None) -> dict:
    """
    TERM_DICTIONARY를 기준으로 text를 분석한다.

    반환 구조:
    {
        "rule_analysis": {
            "clarity": [
                {
                    "feature": "vague_degree",
                    "dictionary_term": "적절한",
                    "match": "적절한",
                    "source": "exact"
                }
            ],
            ...
        },
        "feature_counts": {
            "clarity": {
                "vague_degree": 1,
                "vague_frequency": 1,
                "subjective_evaluation": 0
            },
            ...
        }
    }
    """
    categories = category_filter or ALL_CATEGORIES

    rule_analysis = {}
    feature_counts = {}

    for category in categories:
        category_rules = TERM_DICTIONARY.get(category, {})
        category_matches = []
        category_feature_counts = {}

        for feature_name, term_list in category_rules.items():
            matched_terms = find_term_matches(text, term_list)
            category_feature_counts[feature_name] = len(matched_terms)

            for term in matched_terms:
                category_matches.append({
                    "feature": feature_name,
                    "dictionary_term": term,
                    "match": term,
                    "source": "exact",
                })

        rule_analysis[category] = category_matches
        feature_counts[category] = category_feature_counts

    return {
        "rule_analysis": rule_analysis,
        "feature_counts": feature_counts
    }


def count_total_issues(rule_analysis: dict, categories: list[str] | None = None) -> int:
    """
    rule_analysis에서 전체 매칭 개수를 계산한다.
    """
    target_categories = categories or ALL_CATEGORIES
    return sum(len(rule_analysis.get(category, [])) for category in target_categories)


def has_any_issue(rule_analysis: dict, categories: list[str] | None = None) -> bool:
    """
    rule_analysis에 하나라도 매칭 이슈가 있는지 반환한다.
    """
    target_categories = categories or ALL_CATEGORIES
    return any(len(rule_analysis.get(category, [])) > 0 for category in target_categories)


def analyze_question(question: str) -> dict:
    """
    질문 텍스트 기준 규칙 분석.
    """
    analysis_result = analyze_text_by_dictionary(question)

    return {
        "question": question,
        "rule_analysis": analysis_result["rule_analysis"],
        "feature_counts": analysis_result["feature_counts"],
        "issue_count": count_total_issues(analysis_result["rule_analysis"]),
        "has_issue": has_any_issue(analysis_result["rule_analysis"]),
    }


def analyze_item_rules(item: dict) -> dict:
    """
    문항 단위 규칙 분석 함수.
    현재는 question 중심으로 분석하며,
    이후 option_type / options 기반 규칙을 확장할 수 있다.
    """
    question = item.get("question", "") or ""
    option_type = item.get("option_type", "") or ""
    options = item.get("options", []) or []

    analysis_result = analyze_text_by_dictionary(question)

    rule_analysis = analysis_result["rule_analysis"]
    feature_counts = analysis_result["feature_counts"]

    primary_issue_count = count_total_issues(rule_analysis, PRIMARY_CATEGORIES)
    auxiliary_issue_count = count_total_issues(rule_analysis, AUXILIARY_CATEGORIES)
    total_issue_count = primary_issue_count + auxiliary_issue_count

    return {
        "item_id": item.get("item_id"),
        "question": question,
        "option_type": option_type,
        "options": options,
        "rule_analysis": rule_analysis,
        "feature_counts": feature_counts,
        "primary_issue_count": primary_issue_count,
        "auxiliary_issue_count": auxiliary_issue_count,
        "issue_count": total_issue_count,
        "has_issue": total_issue_count > 0,
    }