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


# -------------------------
# Response reliability settings 응답 쪽
# -------------------------

# -------------------------
# Response reliability settings
# -------------------------

RESPONSE_CATEGORIES = [
    "instruction",
    "consistency",
    "pattern",
    "behavior",
]

RESPONSE_CATEGORY_LABELS = {
    "instruction": "지시형 함정문항",
    "consistency": "응답 일관성",
    "pattern": "응답 패턴",
    "behavior": "행동 로그",
}

RESPONSE_PENALTY_WEIGHTS = {
    "instruction": {
        "instruction_fail": 3.0,
    },
    "consistency": {
        "reverse_inconsistency": 2.0,
        "similar_item_inconsistency": 1.5,
    },
    "pattern": {
        "straightlining": 1.5,
        "low_variance": 1.2,
        "extreme_repetition": 1.0,
    },
    "behavior": {
        "excessive_tab_switch": 0.8,
        "high_focus_loss": 0.8,
        "excessive_revisit": 0.5,
    },
}

MAX_RESPONSE_RAW_PENALTY = {
    "instruction": 5.0,
    "consistency": 5.0,
    "pattern": 5.0,
    "behavior": 5.0,
}

RESPONSE_SCORE_WEIGHTS = {
    "instruction": 0.40,
    "consistency": 0.30,
    "pattern": 0.15,
    "behavior": 0.15,
}

MIN_RESPONSES_FOR_STAT_SCORING = 30
USE_RESPONSE_STAT_SCORING = True