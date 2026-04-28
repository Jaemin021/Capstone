# backend/services/item_quality_score_service.py

def safe_float(value, default=0.0):
    try:
        return float(value)
    except:
        return default


def calculate_quality_score(rule, llm):
    if llm is None:
        return 0.0

    clarity = safe_float(llm.get("clarity"))
    single_concept = safe_float(llm.get("single_concept"))
    answerability = safe_float(llm.get("answerability"))
    neutrality = safe_float(llm.get("neutrality"))

    base = (
        clarity * 0.35 +
        single_concept * 0.25 +
        answerability * 0.25 +
        neutrality * 0.15
    )

    penalty = (
        rule.get("ambiguous", 0) * 0.3 +
        rule.get("negative", 0) * 0.5 +
        rule.get("leading", 0) * 0.4 +
        rule.get("double", 0) * 0.4
    )

    score = base - penalty
    return round(max(0.0, min(10.0, score)), 3)