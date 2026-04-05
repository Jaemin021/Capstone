# config.py

LLM_MODEL = "gpt-5.4-mini"

# -------------------------
# Core evaluation settings
# -------------------------

PRIMARY_CATEGORIES = [
    "clarity",
    "single_concept",
    "answerability",
]

AUXILIARY_CATEGORIES = [
    "neutrality",
]

CATEGORY_LABELS = {
    "clarity": "명확성",
    "single_concept": "단일성",
    "neutrality": "중립성",
    "answerability": "응답 가능성",
}

# -------------------------
# Score scale
# -------------------------

SCORE_MIN = 1.0
SCORE_MAX = 10.0
ROUND_DIGITS = 2

# -------------------------
# Rule / LLM combination
# -------------------------

CATEGORY_SCORE_WEIGHTS = {
    "clarity": {"rule": 0.7, "llm": 0.3},
    "single_concept": {"rule": 0.7, "llm": 0.3},
    "answerability": {"rule": 0.7, "llm": 0.3},
}

# -------------------------
# Rule penalty weights
# -------------------------

RULE_PENALTY_WEIGHTS = {
    "clarity": {
        "vague_degree": 1.0,
        "vague_frequency": 1.0,
        "subjective_evaluation": 1.0,
    },
    "single_concept": {
        "double_barreled_connector": 1.5,
    },
    "answerability": {
        "broad_recall": 1.2,
        "absolute_expression": 1.2,
        "excessive_precision": 1.5,
    },
    "neutrality": {
        "leading_assertion": 1.2,
        "positive_bias": 1.0,
    },
}

# penalty가 이 값을 넘으면 rule_score가 거의 최저점에 가까워지도록 설정
MAX_RAW_PENALTY = {
    "clarity": 5.0,
    "single_concept": 5.0,
    "answerability": 5.0,
    "neutrality": 5.0,
}

# -------------------------
# Option / item settings
# -------------------------

ALLOWED_OPTION_TYPES = {
    "single_choice",
    "multiple_choice",
    "scale",
    "text",
    "number",
}

# -------------------------
# Rule-assist LLM settings
# -------------------------

ENABLE_RULE_ASSIST_LLM = True

RULE_ASSIST_CATEGORIES = [
    "clarity",
    "single_concept",
    "answerability",
    "neutrality",
]

# -------------------------
# Auxiliary LLM settings
# -------------------------

INCLUDE_AUXILIARY_LLM_SCORES = True

# -------------------------
# Rewrite suggestion settings
# -------------------------

ENABLE_REWRITE_SUGGESTION = True
REWRITE_THRESHOLD = 70.0

# -------------------------
# Post-hoc comparison mapping
# -------------------------

POST_METRIC_MAPPING = {
    "clarity": "variance_score",
    "single_concept": "citc_score",
    "answerability": "missing_score",
}