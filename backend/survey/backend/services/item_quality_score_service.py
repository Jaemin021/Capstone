import re


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


def calculate_quality_score(llm):
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
        clarity * 0.35 +
        single_concept * 0.25 +
        answerability * 0.25 +
        neutrality * 0.15
    )

    # Optional LLM overall score is blended conservatively to reduce variance.
    if llm_overall is None:
        score = weighted_subscore
    else:
        llm_overall = clamp(llm_overall, 0.0, 10.0)
        score = weighted_subscore * 0.8 + llm_overall * 0.2

    return round(clamp(score, 0.0, 10.0), 3)
