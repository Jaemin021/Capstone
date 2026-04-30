import json
import os
import re

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
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def default_llm_construct_result():
    return {
        "construct_fit": 0,
        "semantic_consistency": 0,
        "redundancy_risk": 0,
        "off_construct_risk": 0,
        "expected_citc_direction": "unknown",
    }


def _sanitize_expected_citc_direction(value):
    if not isinstance(value, str):
        return "unknown"

    lowered = value.strip().lower()
    if lowered in {"high", "medium", "low", "unknown"}:
        return lowered

    return "unknown"


def _sanitize_score(value):
    try:
        number = float(value)
    except Exception:
        number = 0.0

    return max(0.0, min(10.0, number))


def normalize_llm_construct_result(parsed):
    if not isinstance(parsed, dict):
        raise ValueError(f"LLM construct result must be dict. parsed={parsed!r}")

    return {
        "construct_fit": _sanitize_score(parsed.get("construct_fit")),
        "semantic_consistency": _sanitize_score(parsed.get("semantic_consistency")),
        "redundancy_risk": _sanitize_score(parsed.get("redundancy_risk")),
        "off_construct_risk": _sanitize_score(parsed.get("off_construct_risk")),
        "expected_citc_direction": _sanitize_expected_citc_direction(
            parsed.get("expected_citc_direction")
        ),
    }


def evaluate_llm_construct_features(target_item, survey, normal_items):
    other_items = [
        {
            "item_order": item.item_order,
            "question_text": item.question_text,
        }
        for item in normal_items
        if item.item_id != target_item.item_id
    ]

    prompt = f"""
You evaluate how well a target survey item aligns with the survey construct.

Important:
- Focus ONLY on construct alignment.
- Do NOT evaluate wording quality here.
- Be conservative: do not over-penalize unless there is clear evidence of mismatch.
- Return JSON only.

Survey context:
title: {survey.title}
construct_name: {survey.construct_name}
construct_description: {survey.construct_description}

Target item:
{target_item.question_text}

Other normal items:
{json.dumps(other_items, ensure_ascii=False)}

Return ONLY JSON:
{{
  "construct_fit": float,           // 0~10, higher is better
  "semantic_consistency": float,    // 0~10, higher is better
  "redundancy_risk": float,         // 0~10, higher means more redundant
  "off_construct_risk": float,      // 0~10, higher means more off-construct
  "expected_citc_direction": "high|medium|low|unknown"
}}
"""

    content = create_chat_completion(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Return ONLY valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )

    parsed = extract_json_from_text(content)
    if not isinstance(parsed, dict):
        raise ValueError(f"LLM construct JSON parse failed. raw={content!r}")

    base = default_llm_construct_result()
    base.update(normalize_llm_construct_result(parsed))
    return base


def calculate_llm_construct_score(llm_features):
    construct_fit = float(llm_features.get("construct_fit", 0) or 0)
    semantic_consistency = float(llm_features.get("semantic_consistency", 0) or 0)
    redundancy_risk = float(llm_features.get("redundancy_risk", 0) or 0)
    off_construct_risk = float(llm_features.get("off_construct_risk", 0) or 0)

    score = (
        construct_fit * 0.45
        + semantic_consistency * 0.35
        - redundancy_risk * 0.10
        - off_construct_risk * 0.25
    )

    return round(max(0, min(10, score)), 3)
