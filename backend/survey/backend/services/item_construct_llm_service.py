import os
import re
import json
from dotenv import load_dotenv

from services.openai_http_client import create_chat_completion

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


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


def default_llm_construct_result():
    return {
        "construct_fit": 0,
        "semantic_consistency": 0,
        "redundancy_risk": 0,
        "off_construct_risk": 0,
        "expected_citc_direction": "unknown",
        "reason": "",
        "suggestion": ""
    }


def evaluate_llm_construct_features(target_item, survey, normal_items):
    other_items = [
        {
            "item_order": item.item_order,
            "question_text": item.question_text
        }
        for item in normal_items
        if item.item_id != target_item.item_id
    ]

    prompt = f"""
너는 설문 문항의 구성개념 타당도와 CITC 가능성을 사전에 평가하는 전문가다.

목표:
아래 target_item이 설문 전체가 측정하려는 개념과 얼마나 잘 맞는지 평가하라.

주의:
- 문항 표현 품질을 평가하지 말 것.
- 문항이 같은 construct를 측정하는지에만 집중할 것.
- 실제 응답 데이터가 없으므로 CITC를 계산하지 말고, CITC가 높게 나올 가능성을 feature로 추정할 것.
- JSON만 출력할 것.

[설문 정보]
title: {survey.title}
construct_name: {survey.construct_name}
construct_description: {survey.construct_description}

[target_item]
{target_item.question_text}

[다른 원본문항]
{json.dumps(other_items, ensure_ascii=False)}

출력 형식:
{{
  "construct_fit": float, 
  "semantic_consistency": float,
  "redundancy_risk": float,
  "off_construct_risk": float,
  "expected_citc_direction": "high|medium|low|unknown",
  "reason": str,
  "suggestion": str
}}

점수 기준:
- construct_fit: target_item이 설문 construct와 맞는 정도, 0~10
- semantic_consistency: 다른 문항들과 같은 개념군에 속하는 정도, 0~10
- redundancy_risk: 다른 문항과 너무 중복되는 위험, 0~10. 높을수록 중복 위험 큼
- off_construct_risk: 다른 개념을 묻는 위험, 0~10. 높을수록 위험 큼
"""

    content = create_chat_completion(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Return ONLY JSON"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    parsed = extract_json_from_text(content)

    if not isinstance(parsed, dict):
        raise ValueError(f"LLM construct JSON parse failed. raw={content!r}")

    base = default_llm_construct_result()
    base.update(parsed)
    return base


def calculate_llm_construct_score(llm_features):
    """
    지금은 임시 참고 score.
    나중에 실제 CITC 데이터가 생기면 이 식은 학습으로 대체.
    """

    construct_fit = float(llm_features.get("construct_fit", 0) or 0)
    semantic_consistency = float(llm_features.get("semantic_consistency", 0) or 0)
    redundancy_risk = float(llm_features.get("redundancy_risk", 0) or 0)
    off_construct_risk = float(llm_features.get("off_construct_risk", 0) or 0)

    score = (
        construct_fit * 0.45 +
        semantic_consistency * 0.35 -
        redundancy_risk * 0.10 -
        off_construct_risk * 0.25
    )

    return round(max(0, min(10, score)), 3)
