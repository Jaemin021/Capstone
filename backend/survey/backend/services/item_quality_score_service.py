import re

from services.item_quality_dictionary import (
    AMBIGUOUS_TERMS,
    NEGATIVE_TERMS,
    LEADING_TERMS,
    DOUBLE_BARRELED_HINTS,
)


CLEAR_OPTION_HINTS = (
    "전혀",
    "거의",
    "가끔",
    "때때로",
    "자주",
    "항상",
    "매우",
    "동의하지 않는다",
    "동의한다",
)

VAGUE_OPTION_HINTS = (
    "보통",
    "적당",
    "어느 정도",
    "대체로",
    "일반적으로",
    "조금",
    "많이",
    "약간",
)

LOW_EXTREME_HINTS = ("전혀", "아니다", "없다", "거의 없다", "동의하지 않는다")
HIGH_EXTREME_HINTS = ("매우", "항상", "확실히", "동의한다", "그렇다")

AMBIGUOUS_TERM_SET = {term.strip().lower() for term in AMBIGUOUS_TERMS if str(term).strip()}
NEGATIVE_TERM_SET = {term.strip().lower() for term in NEGATIVE_TERMS if str(term).strip()}
LEADING_TERM_SET = {term.strip().lower() for term in LEADING_TERMS if str(term).strip()}
DOUBLE_BARRELED_HINT_SET = {term.strip().lower() for term in DOUBLE_BARRELED_HINTS if str(term).strip()}


def safe_float(value, default=0.0):
    if value is None:
        return default

    if isinstance(value, str):
        text = value.strip()
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if match:
            try:
                return float(match.group(0))
            except Exception:
                return default

    try:
        return float(value)
    except Exception:
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def _to_list(value):
    if isinstance(value, list):
        return value
    return []


def _to_lower_set(value):
    return {
        str(item).strip().lower()
        for item in _to_list(value)
        if str(item).strip()
    }


def _categorize_dictionary_term(term):
    lowered = str(term).strip().lower()
    if not lowered:
        return None
    if lowered in AMBIGUOUS_TERM_SET:
        return "ambiguous_time"
    if lowered in NEGATIVE_TERM_SET:
        return "negative_wording"
    if lowered in LEADING_TERM_SET:
        return "leading"
    if lowered in DOUBLE_BARRELED_HINT_SET:
        return "double_barreled"
    return None


def _extract_question_term_categories(question_text):
    categories = set()
    lowered_question = str(question_text or "").strip().lower()
    if not lowered_question:
        return categories

    if any(term in lowered_question for term in AMBIGUOUS_TERM_SET):
        categories.add("ambiguous_time")
    if any(term in lowered_question for term in NEGATIVE_TERM_SET):
        categories.add("negative_wording")
    if any(term in lowered_question for term in LEADING_TERM_SET):
        categories.add("leading")
    if any(term in lowered_question for term in DOUBLE_BARRELED_HINT_SET):
        categories.add("double_barreled")

    return categories


def _is_clear_option(text):
    if not text:
        return False

    lowered = text.lower()
    if re.search(r"\d+\s*(회|번|일|주|개월|달|월|년|시간|분)", lowered):
        return True

    return any(hint in lowered for hint in CLEAR_OPTION_HINTS)


def _is_vague_option(text):
    if not text:
        return False

    lowered = text.lower()
    return any(hint in lowered for hint in VAGUE_OPTION_HINTS)


def _has_scale_extremes(option_texts):
    has_low = any(any(hint in text for hint in LOW_EXTREME_HINTS) for text in option_texts)
    has_high = any(any(hint in text for hint in HIGH_EXTREME_HINTS) for text in option_texts)
    return has_low and has_high


def _estimate_option_clarity(options, llm_option_clarity_score=None):
    option_texts = [
        str(option).strip().lower()
        for option in _to_list(options)
        if str(option).strip()
    ]

    if not option_texts:
        local_clarity = 0.5
    else:
        count = len(option_texts)
        clear_count = sum(1 for text in option_texts if _is_clear_option(text))
        vague_count = sum(1 for text in option_texts if _is_vague_option(text))

        ratio_clear = clear_count / count
        ratio_vague = vague_count / count
        monotonic_bonus = 0.15 if _has_scale_extremes(option_texts) and ratio_clear >= 0.5 else 0.0
        local_clarity = clamp((ratio_clear * 0.55) + ((1 - ratio_vague) * 0.45) + monotonic_bonus, 0.0, 1.0)

    if llm_option_clarity_score is None:
        return local_clarity

    llm_clarity = clamp(llm_option_clarity_score / 10.0, 0.0, 1.0)
    return clamp((local_clarity * 0.6) + (llm_clarity * 0.4), 0.0, 1.0)


def _extract_issue_categories(llm, question_text):
    categories = _to_lower_set(llm.get("problem_categories")) if isinstance(llm, dict) else set()
    has_term_assessments = False

    if isinstance(llm, dict):
        term_assessments = _to_list(llm.get("term_assessments"))
        has_term_assessments = len(term_assessments) > 0

        for row in term_assessments:
            if not isinstance(row, dict):
                continue
            context_effect = str(row.get("context_effect", "")).strip().lower()
            if context_effect != "problem":
                continue
            term_category = str(row.get("category", "")).strip().lower()
            if term_category == "ambiguous":
                categories.add("ambiguous_time")
            elif term_category == "negative":
                categories.add("negative_wording")
            elif term_category == "leading":
                categories.add("leading")
            elif term_category == "double_barreled":
                categories.add("double_barreled")

        # term_assessments가 있으면 resolved/acceptable 여부를 이미 담고 있으므로
        # detected_terms만으로는 추가 감점 카테고리를 붙이지 않는다.
        if not has_term_assessments:
            for term in _to_list(llm.get("detected_terms")):
                mapped = _categorize_dictionary_term(term)
                if mapped:
                    categories.add(mapped)

    # 평가 결과가 충분치 않을 때만 질문 텍스트 기반 보수적 감지를 사용한다.
    if not has_term_assessments and len(categories) == 0:
        categories.update(_extract_question_term_categories(question_text))
    return categories


def calculate_quality_score(llm, options=None, question_text=""):
    if llm is None:
        return None

    option_clarity = _estimate_option_clarity(
        options=options,
        llm_option_clarity_score=safe_float(llm.get("option_clarity_score"), default=None),
    )

    issue_categories = _extract_issue_categories(llm, question_text)
    has_issue = len(issue_categories) > 0

    # Rule-first scoring:
    # - no issue expression: good
    # - issue expression exists: warning/bad based on severity
    # - ambiguous-time issue can recover partially when options are explicit
    if not has_issue:
        return 9.2

    severe_issue_categories = {
        "double_barreled",
        "single_concept_issue",
        "leading",
        "negative_wording",
    }

    ambiguous_issue_categories = {
        "ambiguous_time",
        "answerability_issue",
        "clarity_issue",
    }

    has_severe_issue = len(issue_categories.intersection(severe_issue_categories)) > 0
    is_ambiguous_family_only = issue_categories.issubset(ambiguous_issue_categories)

    if has_severe_issue:
        return 5.9

    if is_ambiguous_family_only:
        if option_clarity >= 0.80:
            return 6.9
        if option_clarity >= 0.65:
            return 6.4
        return 5.9

    if option_clarity >= 0.80:
        return 6.6

    return 6.1
