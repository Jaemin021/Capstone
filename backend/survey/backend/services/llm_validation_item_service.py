# backend/services/llm_validation_item_service.py

import os
import re
import json
import random
from dotenv import load_dotenv
from openai import OpenAI

# -----------------------------
# 환경변수 로드
# -----------------------------
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

if not API_KEY:
    raise ValueError("❌ OPENAI_API_KEY가 설정되지 않았습니다. .env 파일 확인하세요.")

client = OpenAI(api_key=API_KEY)


# -----------------------------
# 기본 fallback plan
# -----------------------------
def default_validation_plan():
    return {
        "validation_level": 0,
        "reverse_items": [],
        "trap_items": []
    }


# -----------------------------
# 생성 개수 제한
# -----------------------------
def get_validation_limits(item_count: int):
    if item_count <= 5:
        return 1, 0
    if item_count <= 10:
        return 1, 1
    return 2, 1


# -----------------------------
# 프롬프트
# -----------------------------
def build_prompt(survey):
    return f"""
너는 설문 설계 전문가다.

아래 설문을 보고:
1. 역문항 생성
2. 함정문항 생성
3. 삽입 위치 결정

규칙:
- 역문항은 의미가 반대가 되도록 자연스럽게 생성
- 함정문항은 특정 선택지를 고르게 해야 함
- 문항 수에 따라 level 결정:
  1~5: reverse 1
  6~10: reverse 1 + trap 1
  11+: reverse 2 + trap 1

인덱스 규칙:
- source_index는 0부터 시작
- insert_after_index는 원본문항 기준

⚠️ 중요:
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


# -----------------------------
# JSON 추출
# -----------------------------
def extract_json_from_text(text: str):
    if not text:
        return None

    text = text.strip()

    try:
        return json.loads(text)
    except:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except:
        return None


# -----------------------------
# 🔥 위치 보정 함수 (핵심)
# -----------------------------
def adjust_validation_positions(plan, item_count):
    if item_count < 3:
        return plan

    used_positions = set()

    # 허용 위치: 첫/마지막 제외
    valid_positions = list(range(1, item_count - 1))

    # -----------------------------
    # reverse 먼저 배치
    # -----------------------------
    for rev in plan["reverse_items"]:
        source_index = rev["source_index"]

        candidates = [
            i for i in valid_positions
            if i != source_index              # 원본 바로 뒤 금지
            and i not in used_positions       # 겹침 방지
        ]

        if not candidates:
            continue

        chosen = random.choice(candidates)
        rev["insert_after_index"] = chosen
        used_positions.add(chosen)

    # -----------------------------
    # trap 배치 (reverse와도 안 붙게)
    # -----------------------------
    for trap in plan["trap_items"]:
        candidates = [
            i for i in valid_positions
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


# -----------------------------
# 정규화
# -----------------------------
def normalize_validation_plan(raw_plan, item_count: int):
    if item_count <= 0:
        return default_validation_plan()

    if not isinstance(raw_plan, dict):
        return default_validation_plan()

    normalized = default_validation_plan()

    # level
    validation_level = raw_plan.get("validation_level", 0)
    if isinstance(validation_level, int):
        normalized["validation_level"] = max(0, validation_level)

    # reverse
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

        normalized["reverse_items"].append({
            "source_index": source_index,
            "insert_after_index": source_index,  # 일단 기본값
            "question_text": question_text.strip()
        })

    # trap
    for trap in raw_plan.get("trap_items", []):
        if not isinstance(trap, dict):
            continue

        correct_option_order = trap.get("correct_option_order", 2)

        if not isinstance(correct_option_order, int):
            correct_option_order = 2

        if correct_option_order < 1 or correct_option_order > 5:
            correct_option_order = 2

        normalized["trap_items"].append({
            "insert_after_index": item_count - 1,
            "correct_option_order": correct_option_order
        })

    # 개수 제한
    max_reverse, max_trap = get_validation_limits(item_count)
    normalized["reverse_items"] = normalized["reverse_items"][:max_reverse]
    normalized["trap_items"] = normalized["trap_items"][:max_trap]

    # 🔥 여기서 위치 보정
    normalized = adjust_validation_positions(normalized, item_count)

    return normalized


# -----------------------------
# LLM 호출
# -----------------------------
def generate_validation_plan_with_llm(survey_data):
    item_count = len(survey_data.get("items", []))

    if item_count <= 0:
        return default_validation_plan()

    prompt = build_prompt(survey_data)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Return ONLY JSON"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content
        raw_plan = extract_json_from_text(content)

        return normalize_validation_plan(raw_plan, item_count)

    except Exception as e:
        print("❌ LLM 실패:", e)
        return default_validation_plan()