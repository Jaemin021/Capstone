# llm/prompts.py

from typing import Any, Dict, List
from config import INCLUDE_AUXILIARY_LLM_SCORES


CATEGORY_EXPLANATIONS = {
    "clarity": (
        "Clarity means the wording is specific, concrete, and easy to interpret. "
        "Low scores indicate vague, ambiguous, or hard-to-interpret wording."
    ),
    "single_concept": (
        "Single concept means the item asks one thing at a time. "
        "Low scores indicate multiple ideas combined in one question."
    ),
    "answerability": (
        "Answerability means respondents can answer realistically based on normal memory, experience, and judgment. "
        "Low scores indicate excessive memory burden, unrealistic demands, or unclear response conditions."
    ),
    "neutrality": (
        "Neutrality means the wording does not lead respondents toward a particular answer. "
        "Low scores indicate leading, suggestive, emotionally loaded, or biased wording."
    ),
}


def build_rule_context(rule_analysis: Dict[str, Any], feature_counts: Dict[str, Any]) -> Dict[str, Any]:
    """
    규칙 기반 분석 결과를 LLM 참고용 컨텍스트로 정리한다.
    """
    context: Dict[str, Any] = {}

    for category, matches in rule_analysis.items():
        if not matches:
            continue

        context[category] = {
            "matched_details": matches,
            "feature_counts": feature_counts.get(category, {}),
            "issue_explanation": CATEGORY_EXPLANATIONS.get(category, ""),
        }

    return context


def build_evaluation_prompt(
    question: str,
    option_type: str,
    options: List[str],
    rule_analysis: Dict[str, Any],
    feature_counts: Dict[str, Any],
) -> List[Dict[str, str]]:
    """
    척도별 LLM 평가(score + reason)를 위한 프롬프트를 생성한다.
    """
    rule_context = build_rule_context(rule_analysis, feature_counts)
    evaluate_neutrality = "yes" if INCLUDE_AUXILIARY_LLM_SCORES else "no"

    system_prompt = """
You are a survey item quality evaluator.

Your task is to evaluate a survey item on the following quality dimensions:
- clarity
- single_concept
- answerability
- neutrality (only if requested)

You are part of a hybrid evaluation system:
1. A rule-based detector identifies possible wording issues.
2. You provide a secondary judgment by assigning a score from 1 to 10 for each dimension and a short reason.

Important principles:
- The rule-based output is only supporting context, not absolute truth.
- You may agree or disagree with the rule-based signals.
- You must evaluate the actual survey item as a whole.
- Be conservative and consistent.
- Do not assign perfect scores unless the quality is clearly very strong.
- Reasons must be short, concrete, and directly tied to the wording or response structure.

Scoring guide:
- 9-10: very strong quality, little or no meaningful issue
- 7-8: generally good but with minor weakness
- 5-6: moderate issue that may affect quality
- 3-4: clear problem
- 1-2: severe problem

Dimension definitions:
- clarity:
  wording is specific, concrete, and easy to interpret
- single_concept:
  the item asks one thing rather than combining multiple ideas
- answerability:
  respondents can answer realistically based on normal memory, experience, and judgment
- neutrality:
  wording is not leading, suggestive, emotionally loaded, or biased

Output requirements:
1. Return scores from 1 to 10.
2. Return a short reason for each scored category.
3. If neutrality is not requested, return null for neutrality.
4. Follow the schema exactly.
5. Do not produce an overall score.
"""

    user_prompt = f"""
Please evaluate the following survey item.

[Question]
{question}

[Option Type]
{option_type}

[Options]
{options}

[Rule-based reference]
{rule_context}

[Instruction]
Evaluate clarity, single_concept, and answerability.
Evaluate neutrality as well: {evaluate_neutrality}

Return score + reason for each category.
"""

    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_prompt.strip()},
    ]


def build_rewrite_prompt(
    question: str,
    option_type: str,
    options: List[str],
    rule_analysis: Dict[str, Any],
    final_scores: Dict[str, Any],
    overall_pre_score: float,
) -> List[Dict[str, str]]:
    """
    낮은 품질 문항의 rewrite suggestion 생성을 위한 프롬프트를 생성한다.
    """
    flagged = {
        category: details
        for category, details in rule_analysis.items()
        if details
    }

    system_prompt = """
You are a survey question rewriting assistant.

Your job is to improve a low-quality survey question while preserving its original intent as much as possible.

You must:
1. Rewrite the question into a better survey item.
2. Preserve the original meaning as much as possible.
3. Reduce problems related to:
   - clarity
   - single_concept
   - neutrality
   - answerability
4. Make the rewritten item natural and suitable for survey use.
5. Keep the rewritten sentence concise.
6. Return only:
   - recommended_question
   - reason

Important:
- Do not change the topic unnecessarily.
- Do not make the sentence too long.
- The rewritten question should fit the given option structure if possible.
- Write the recommended_question in Korean if the original question is in Korean.
- reason should be short and practical.
"""

    user_prompt = f"""
Please rewrite the following survey question.

[Original Question]
{question}

[Option Type]
{option_type}

[Options]
{options}

[Rule-based Issues]
{flagged}

[Category Scores]
{final_scores}

[Overall Pre Score]
{overall_pre_score}

Requirements:
- Preserve the original intent.
- Improve the weak dimensions if possible.
- Make the question more appropriate for a survey.
"""

    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_prompt.strip()},
    ]