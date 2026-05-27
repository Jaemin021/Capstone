import re


TERM_CATEGORY_WEIGHTS = {
    "ambiguous": 1.1,
    "negative": 0.8,
    "leading": 1.0,
    "double_barreled": 1.5,
}

PROBLEM_CATEGORY_WEIGHTS = {
    "clarity_issue": 0.6,
    "single_concept_issue": 0.9,
    "answerability_issue": 0.7,
    "neutrality_issue": 0.6,
    "leading": 0.7,
    "double_barreled": 1.0,
    "ambiguous_time": 1.0,
    "negative_wording": 0.8,
}

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


def safe_float(value, default=0.0):
    if value is None:
        return default

    if isinstance(value, str):
        text = value.strip()

        # Handles values like "8/10", "8.5점", "score: 7"
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


def _calculate_dictionary_penalty(llm):
    if not isinstance(llm, dict):
        return 0.0

    penalty = 0.0
    problem_assessment_count = 0

    for row in _to_list(llm.get("term_assessments")):
        if not isinstance(row, dict):
            continue

        context_effect = str(row.get("context_effect", "")).strip().lower()
        if context_effect != "problem":
            continue

        category = str(row.get("category", "")).strip().lower()
        severity = safe_float(row.get("severity"), default=1.0)
        severity = clamp(severity, 0.5, 2.0)
        weight = TERM_CATEGORY_WEIGHTS.get(category, 0.9)

        penalty += weight * severity
        problem_assessment_count += 1

    categories = _to_lower_set(llm.get("problem_categories"))
    for category in categories:
        penalty += PROBLEM_CATEGORY_WEIGHTS.get(category, 0.5)

    detected_terms_count = len(_to_list(llm.get("detected_terms")))
    if detected_terms_count > 0 and (problem_assessment_count > 0 or len(categories) > 0):
        penalty += min(detected_terms_count, 5) * 0.35

    return min(penalty, 6.0)


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


def _needs_option_recovery(llm):
    if not isinstance(llm, dict):
        return False

    categories = _to_lower_set(llm.get("problem_categories"))
    if categories.intersection({"ambiguous_time", "answerability_issue", "clarity_issue"}):
        return True

    for row in _to_list(llm.get("term_assessments")):
        if not isinstance(row, dict):
            continue

        category = str(row.get("category", "")).strip().lower()
        context_effect = str(row.get("context_effect", "")).strip().lower()
        if category == "ambiguous" and context_effect == "problem":
            return True

    return False


def _calculate_option_adjustment(llm, options):
    llm_option_clarity_score = None
    if isinstance(llm, dict):
        parsed = safe_float(llm.get("option_clarity_score"), default=None)
        if parsed is not None:
            llm_option_clarity_score = clamp(parsed, 0.0, 10.0)

    clarity = _estimate_option_clarity(options, llm_option_clarity_score=llm_option_clarity_score)
    if not _needs_option_recovery(llm):
        return 0.0

    recovery_bonus = max(0.0, clarity - 0.55) * 2.8
    unresolved_ambiguity_penalty = max(0.0, 0.45 - clarity) * 2.2
    return recovery_bonus - unresolved_ambiguity_penalty


def calculate_quality_score(llm, options=None):
    if llm is None:
        return None

    clarity = safe_float(llm.get("clarity", llm.get("clarity_score")))
    single_concept = safe_float(llm.get("single_concept", llm.get("single_concept_score")))
    answerability = safe_float(llm.get("answerability", llm.get("answerability_score")))
    neutrality = safe_float(llm.get("neutrality", llm.get("neutrality_score")))
    llm_overall = safe_float(llm.get("overall_quality_score"), default=None)

    subscores = [clarity, single_concept, answerability, neutrality]
    if all(score <= 1.5 for score in subscores):
        clarity *= 10
        single_concept *= 10
        answerability *= 10
        neutrality *= 10

    clarity = clamp(clarity, 0.0, 10.0)
    single_concept = clamp(single_concept, 0.0, 10.0)
    answerability = clamp(answerability, 0.0, 10.0)
    neutrality = clamp(neutrality, 0.0, 10.0)

    # Guard against invalid parsed responses becoming all-zero silently.
    if all(score == 0 for score in [clarity, single_concept, answerability, neutrality]):
        return None

    weighted_subscore = (
        clarity * 0.40 +
        single_concept * 0.30 +
        answerability * 0.20 +
        neutrality * 0.10
    )

    if llm_overall is None:
        score = weighted_subscore
    else:
        llm_overall = clamp(llm_overall, 0.0, 10.0)
        score = weighted_subscore * 0.75 + llm_overall * 0.25

    dictionary_penalty = _calculate_dictionary_penalty(llm)
    option_adjustment = _calculate_option_adjustment(llm, options)

    score = score - dictionary_penalty + option_adjustment
    # Keep final score bounded for downstream status and UI handling.
    return round(clamp(score, 0.0, 10.0), 3)
