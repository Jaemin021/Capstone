# backend/services/llm_validation_item_service.py

import json
import os
import random
import re

from dotenv import load_dotenv

from services.openai_http_client import create_chat_completion


load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

if not API_KEY:
    raise ValueError("OPENAI_API_KEY is not configured. Check your .env file.")


def default_validation_plan():
    return {
        "validation_level": 0,
        "reverse_items": [],
        "trap_items": [],
    }


def get_validation_limits(item_count: int):
    if item_count <= 5:
        return 1, 0
    if item_count <= 10:
        return 1, 1
    return 2, 1


def build_prompt(survey):
    return f"""
너는 설문 설계 전문가다.

아래 설문을 보고 다음 작업을 수행해라.
1) 역문항 생성
2) 함정문항 생성
3) 삽입 위치 결정

규칙:
- 역문항은 원문과 의미가 반대가 되도록 자연스럽게 작성한다.
- 역문항은 "다음 진술은 ..." 같은 메타 문장을 붙이지 말고, 질문 문장 자체만 작성한다.
- 함정문항은 특정 선택지를 고르게 하는 확인 문항이다.
- 문항 수 기준:
  1~5: reverse 1
  6~10: reverse 1 + trap 1
  11+: reverse 2 + trap 1

인덱스 규칙:
- source_index는 0부터 시작
- insert_after_index는 원본 문항 기준

출력 규칙:
- 반드시 JSON만 출력

출력 형식:
{{
  "validation_level": int,
  "reverse_items": [
    {{
      "source_index": int,
      "insert_after_index": int,
      "question_text": str
    }}
  ],
  "trap_items": [
    {{
      "insert_after_index": int,
      "correct_option_order": int
    }}
  ]
}}

설문:
{json.dumps(survey, ensure_ascii=False)}
"""


def extract_json_from_text(text: str):
    if not text:
        return None

    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


REVERSE_PREFIX_PATTERNS = [
    r"^\s*다음\s*진술(?:은)?\s*나에게\s*해당하지\s*않(?:는다|습니다)\s*[:：]?\s*",
    r"^\s*다음\s*문장(?:은)?\s*나에게\s*해당하지\s*않(?:는다|습니다)\s*[:：]?\s*",
    r"^\s*this\s+statement\s+does\s+not\s+apply\s+to\s+me\s*[:：]?\s*",
]


def strip_reverse_prefix(text: str) -> str:
    cleaned = str(text or "").strip()
    for pattern in REVERSE_PREFIX_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def build_natural_reverse_text(original_text: str) -> str:
    """Build a readable reverse item sentence from an original item."""
    text = strip_reverse_prefix(original_text)
    if not text:
        return ""

    end = ""
    if text[-1] in ".!?":
        end = text[-1]
        text = text[:-1].rstrip()

    rules = [
        (r"라고 생각한다$", "라고 생각하지 않는다"),
        (r"라고 느낀다$", "라고 느끼지 않는다"),
        (r"라고 본다$", "라고 보지 않는다"),
        (r"도움이 된다$", "도움이 되지 않는다"),
        (r"만족스럽다$", "만족스럽지 않다"),
        (r"충분하다$", "충분하지 않다"),
        (r"적절하다$", "적절하지 않다"),
        (r"맞는다$", "맞지 않는다"),
        (r"좋다$", "좋지 않다"),
        (r"편이다$", "편이 아니다"),
        (r"이다$", "이 아니다"),
        (r"있다$", "없다"),
        (r"한다$", "하지 않는다"),
        (r"된다$", "되지 않는다"),
    ]

    for pattern, replacement in rules:
        if re.search(pattern, text):
            return re.sub(pattern, replacement, text) + end

    if text.endswith("다") and len(text) > 1:
        return f"{text[:-1]}지 않다{end}"

    return f"{text} (그렇지 않다){end}"


def adjust_validation_positions(plan, item_count):
    if item_count < 3:
        return plan

    used_positions = set()

    # exclude first and last item positions
    valid_positions = list(range(1, item_count - 1))

    # place reverse items first
    for rev in plan["reverse_items"]:
        source_index = rev["source_index"]

        candidates = [
            i
            for i in valid_positions
            if i != source_index and i not in used_positions
        ]

        if not candidates:
            continue

        chosen = random.choice(candidates)
        rev["insert_after_index"] = chosen
        used_positions.add(chosen)

    # place trap items not adjacent to existing validation items
    for trap in plan["trap_items"]:
        candidates = [
            i
            for i in valid_positions
            if i not in used_positions
            and (i - 1) not in used_positions
            and (i + 1) not in used_positions
        ]

        if not candidates:
            continue

        chosen = random.choice(candidates)
        trap["insert_after_index"] = chosen
        used_positions.add(chosen)

    return plan


def normalize_validation_plan(raw_plan, item_count: int):
    if item_count <= 0:
        return default_validation_plan()

    if not isinstance(raw_plan, dict):
        return default_validation_plan()

    normalized = default_validation_plan()

    validation_level = raw_plan.get("validation_level", 0)
    if isinstance(validation_level, int):
        normalized["validation_level"] = max(0, validation_level)

    for rev in raw_plan.get("reverse_items", []):
        if not isinstance(rev, dict):
            continue

        source_index = rev.get("source_index")
        question_text = rev.get("question_text")

        if not isinstance(source_index, int):
            continue

        if source_index < 0 or source_index >= item_count:
            continue

        if not isinstance(question_text, str) or not question_text.strip():
            continue

        cleaned_question = build_natural_reverse_text(question_text)
        if not cleaned_question:
            continue

        normalized["reverse_items"].append(
            {
                "source_index": source_index,
                "insert_after_index": source_index,
                "question_text": cleaned_question,
            }
        )

    for trap in raw_plan.get("trap_items", []):
        if not isinstance(trap, dict):
            continue

        correct_option_order = trap.get("correct_option_order", 2)

        if not isinstance(correct_option_order, int):
            correct_option_order = 2

        if correct_option_order < 1 or correct_option_order > 5:
            correct_option_order = 2

        normalized["trap_items"].append(
            {
                "insert_after_index": item_count - 1,
                "correct_option_order": correct_option_order,
            }
        )

    max_reverse, max_trap = get_validation_limits(item_count)
    normalized["reverse_items"] = normalized["reverse_items"][:max_reverse]
    normalized["trap_items"] = normalized["trap_items"][:max_trap]

    normalized = adjust_validation_positions(normalized, item_count)

    return normalized


def build_fallback_validation_plan(survey_data):
    item_count = len(survey_data.get("items", []))

    if item_count <= 0:
        return default_validation_plan()

    reverse_count, trap_count = get_validation_limits(item_count)

    reverse_items = []
    for idx in range(min(reverse_count, item_count)):
        source = survey_data["items"][idx]
        original_text = str(source.get("question_text", "")).strip()
        if not original_text:
            continue

        reverse_text = build_natural_reverse_text(original_text)
        if not reverse_text:
            continue

        reverse_items.append(
            {
                "source_index": idx,
                "insert_after_index": idx,
                "question_text": reverse_text,
            }
        )

    trap_items = []
    if trap_count > 0:
        trap_items.append(
            {
                "insert_after_index": max(0, item_count - 2),
                "correct_option_order": 3,
            }
        )

    return adjust_validation_positions(
        {
            "validation_level": 1 if (reverse_items or trap_items) else 0,
            "reverse_items": reverse_items,
            "trap_items": trap_items,
        },
        item_count,
    )


def generate_validation_plan_with_llm(survey_data):
    item_count = len(survey_data.get("items", []))

    if item_count <= 0:
        return default_validation_plan()

    prompt = build_prompt(survey_data)

    try:
        content = create_chat_completion(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Return ONLY JSON"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        raw_plan = extract_json_from_text(content)
        normalized = normalize_validation_plan(raw_plan, item_count)

        if not normalized["reverse_items"] and not normalized["trap_items"]:
            return build_fallback_validation_plan(survey_data)

        return normalized

    except Exception as e:
        print("LLM validation plan failed:", repr(e))
        return build_fallback_validation_plan(survey_data)
