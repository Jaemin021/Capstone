# llm/eval_evaluator.py

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from openai import OpenAI
import openai

from config import PRIMARY_CATEGORIES, LLM_MODEL, INCLUDE_AUXILIARY_LLM_SCORES
from llm.eval_prompts import build_evaluation_prompt

client = OpenAI()


class CategoryEvaluation(BaseModel):
    score: float = Field(description="Quality score from 1 to 10")
    reason: str = Field(description="Short and concrete reason")


class LLMEvaluationResponse(BaseModel):
    clarity: Optional[CategoryEvaluation] = None
    single_concept: Optional[CategoryEvaluation] = None
    answerability: Optional[CategoryEvaluation] = None
    neutrality: Optional[CategoryEvaluation] = None


def _normalize_category_value(value: Any) -> dict:
    """
    LLM category 결과를 안전하게 정규화한다.
    score가 없거나 잘못된 경우 None으로 둔다.
    """
    if not value or not isinstance(value, dict):
        return {
            "score": None,
            "reason": "Missing LLM evaluation"
        }

    raw_score = value.get("score")
    reason = str(value.get("reason", "")).strip()

    try:
        score = float(raw_score) if raw_score is not None else None
    except (TypeError, ValueError):
        score = None

    return {
        "score": score,
        "reason": reason if reason else "Missing LLM evaluation"
    }


def normalize_llm_scores(llm_raw_result: Dict) -> Dict:
    normalized = {}

    for category in PRIMARY_CATEGORIES:
        value = llm_raw_result.get(category)
        normalized[category] = _normalize_category_value(value)

    if INCLUDE_AUXILIARY_LLM_SCORES:
        value = llm_raw_result.get("neutrality")
        normalized["neutrality"] = _normalize_category_value(value)
    else:
        normalized["neutrality"] = None

    return normalized


def get_llm_evaluation(
    question: str,
    option_type: str,
    options: List[str],
    rule_analysis: Dict,
    feature_counts: Dict,
) -> Dict:
    messages = build_evaluation_prompt(
        question=question,
        option_type=option_type,
        options=options,
        rule_analysis=rule_analysis,
        feature_counts=feature_counts,
    )

    try:
        response = client.responses.parse(
            model=LLM_MODEL,
            input=messages,
            text_format=LLMEvaluationResponse
        )
        parsed = response.output_parsed.model_dump()
        return normalize_llm_scores(parsed)

    except openai.AuthenticationError:
        raise RuntimeError("API 키 오류")
    except openai.RateLimitError:
        raise RuntimeError("사용량 제한")
    except openai.APIConnectionError:
        raise RuntimeError("네트워크 연결 오류")
    except Exception as e:
        raise RuntimeError(f"LLM 오류: {e}")