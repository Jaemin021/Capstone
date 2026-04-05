from typing import Dict, List
from pydantic import BaseModel, Field
from openai import OpenAI
import openai

from config import LLM_MODEL
from llm.eval_prompts import build_rewrite_prompt

client = OpenAI()


class RewriteSuggestion(BaseModel):
    recommended_question: str = Field(description="Improved survey question")
    reason: str = Field(description="Short explanation of why this rewrite is better")


def empty_suggestion() -> Dict:
    return {
        "needed": False,
        "recommended_question": None,
        "reason": None,
    }


def suggest_question_rewrite(
    question: str,
    option_type: str,
    options: List[str],
    rule_analysis: Dict,
    final_scores: Dict,
    overall_pre_score: float,
) -> Dict:
    messages = build_rewrite_prompt(
        question=question,
        option_type=option_type,
        options=options,
        rule_analysis=rule_analysis,
        final_scores=final_scores,
        overall_pre_score=overall_pre_score,
    )

    try:
        response = client.responses.parse(
            model=LLM_MODEL,
            input=messages,
            text_format=RewriteSuggestion
        )

        parsed = response.output_parsed.model_dump()
        return {
            "needed": True,
            "recommended_question": parsed["recommended_question"],
            "reason": parsed["reason"],
        }

    except openai.AuthenticationError:
        raise RuntimeError("API 키 오류")
    except openai.RateLimitError:
        raise RuntimeError("사용량 제한")
    except openai.APIConnectionError:
        raise RuntimeError("네트워크 연결 오류")
    except Exception as e:
        raise RuntimeError(f"Rewrite LLM 오류: {e}")