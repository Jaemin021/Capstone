from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
import openai

from config import LLM_MODEL
from dictionaries.terms import TERM_DICTIONARY
from llm.rule_assist_prompts import build_rule_assist_prompt


client = OpenAI()


class RuleMatch(BaseModel):
    feature: str = Field(description="Feature name from the provided dictionary")
    dictionary_term: str = Field(description="Canonical dictionary term used as the detection basis")
    match: str = Field(description="Actual matched phrase from the question")


class RuleAssistResponse(BaseModel):
    clarity: Optional[List[RuleMatch]] = None
    single_concept: Optional[List[RuleMatch]] = None
    answerability: Optional[List[RuleMatch]] = None
    neutrality: Optional[List[RuleMatch]] = None


def normalize_rule_assist_result(
    llm_raw_result: Dict,
    categories: List[str]
) -> Dict:
    """
    rule_assist LLM 결과를 기존 matcher와 유사한 형태로 정규화한다.
    반환 형식:
    {
        "rule_analysis": {
            "clarity": [...],
            "single_concept": [...],
            "answerability": [...],
            "neutrality": [...]
        }
    }
    """
    normalized = {"rule_analysis": {}}

    for category in categories:
        matches = llm_raw_result.get(category, [])
        normalized_matches = []
        category_rules = TERM_DICTIONARY.get(category, {})
        valid_features = set(category_rules.keys())

        if isinstance(matches, list):
            for item in matches:
                if not isinstance(item, dict):
                    continue

                feature = str(item.get("feature", "")).strip()
                dictionary_term = str(item.get("dictionary_term", "")).strip()
                match = str(item.get("match", "")).strip()

                if not feature or not dictionary_term or not match:
                    continue
                if feature not in valid_features:
                    continue
                if dictionary_term not in category_rules.get(feature, []):
                    continue

                normalized_matches.append({
                    "feature": feature,
                    "dictionary_term": dictionary_term,
                    "match": match,
                    "source": "assist",
                })

        normalized["rule_analysis"][category] = normalized_matches

    return normalized


def get_rule_assist_analysis(
    question: str,
    categories: Optional[List[str]] = None,
    exact_rule_analysis: Optional[Dict] = None,
) -> Dict:
    """
    단어 사전을 기준으로 형태 변형/표현 변형을 LLM이 보조 탐지하도록 요청한다.
    반환 형식은 matcher의 rule_analysis와 호환되도록 맞춘다.

    exact_rule_analysis:
        exact matcher가 이미 잡은 결과. 전달되면 프롬프트에서 중복 탐지를 줄이는 데 사용.
        전달되지 않아도 기존 방식대로 동작한다.
    """
    if categories is None:
        categories = ["clarity", "single_concept", "answerability", "neutrality"]

    messages = build_rule_assist_prompt(
        question=question,
        categories=categories,
        exact_rule_analysis=exact_rule_analysis,
    )

    try:
        response = client.responses.parse(
            model=LLM_MODEL,
            input=messages,
            text_format=RuleAssistResponse
        )

        parsed = response.output_parsed.model_dump()
        return normalize_rule_assist_result(parsed, categories)

    except openai.AuthenticationError:
        raise RuntimeError("API 키 오류")
    except openai.RateLimitError:
        raise RuntimeError("사용량 제한")
    except openai.APIConnectionError:
        raise RuntimeError("네트워크 연결 오류")
    except Exception as e:
        raise RuntimeError(f"Rule-assist LLM 오류: {e}")