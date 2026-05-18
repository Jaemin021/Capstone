import os
import re
import json
from dotenv import load_dotenv

from services.openai_http_client import create_chat_completion
from services.item_quality_dictionary import (
    AMBIGUOUS_TERMS,
    NEGATIVE_TERMS,
    LEADING_TERMS,
    DOUBLE_BARRELED_HINTS,
)

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


def build_quality_dictionary_payload():
    return {
        "ambiguous_terms": AMBIGUOUS_TERMS,
        "negative_terms": NEGATIVE_TERMS,
        "leading_terms": LEADING_TERMS,
        "double_barreled_hints": DOUBLE_BARRELED_HINTS,
    }


def _to_string_list(value):
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_llm_quality_result(parsed):
    if not isinstance(parsed, dict):
        raise ValueError(f"LLM quality result must be dict. parsed={parsed!r}")

    normalized = dict(parsed)

    normalized["problem_categories"] = _to_string_list(parsed.get("problem_categories"))
    normalized["detected_terms"] = _to_string_list(parsed.get("detected_terms"))

    comment = parsed.get("llm_comment")
    normalized["llm_comment"] = comment if isinstance(comment, str) else ""

    rewrite = parsed.get("suggested_rewrite")
    normalized["suggested_rewrite"] = rewrite if isinstance(rewrite, str) else ""

    return normalized


def evaluate_item_with_llm(question_text, options):
    quality_dictionary = build_quality_dictionary_payload()

    prompt = f"""
You are a conservative survey item wording evaluator focused on measurement quality.

Primary objective:
- Flag only wording issues that can materially degrade survey quality
  (misinterpretation, response bias, non-answerability, double meaning).
- Do NOT suggest edits for minor style preferences that do not harm measurement.

Task:
1) Evaluate wording quality for the item.
2) Use the term dictionary below as a diagnostic aid, not as an automatic penalty list.
3) Judge risks in the full context of question + options.

Critical calibration:
- Start from "acceptable by default" unless clear evidence shows quality harm.
- A flagged term is not a problem by itself.
- If options anchor meaning (e.g., concrete frequency/timeframe), ambiguity penalty should be small or none.
- Mark a problem only when there is concrete risk of distorted responses.
- Keep problem_categories high precision (0~2 entries).

Rewrite policy:
- suggested_rewrite should appear only when there is a meaningful quality-harming issue.
- If no meaningful issue:
  problem_categories must be [],
  detected_terms must be [],
  suggested_rewrite must be "".
- If rewrite is needed:
  suggested_rewrite must be exactly one Korean sentence that directly fixes the main quality risk.
  Preserve original construct intent and response format.
  Do not prepend labels such as "수정 제안:", "제안:", "원문:", and do not add explanations.

Evaluation scope:
- Only wording quality (clarity/single concept/answerability/neutrality).
- Ignore construct-level consistency with other items.

Language policy:
- All natural-language outputs must be in Korean:
  term_assessments.reason, llm_comment, suggested_rewrite.
- Do not write English sentences in those fields.

Scoring policy:
- 9~10: excellent wording, no practical risk.
- 7~8: generally good, only minor concerns.
- 6: borderline; monitor but not clearly harmful.
- <6: clear quality-harming wording issues that need revision.
- Very low scores (<4) require explicit severe flaws.
- For scores <6, llm_comment must state the concrete harm mechanism.

Input:
Question:
{question_text}

Options:
{json.dumps(options, ensure_ascii=False)}

Term dictionary:
{json.dumps(quality_dictionary, ensure_ascii=False)}

Return ONLY JSON with this schema:
{{
  "clarity": 0-10,
  "single_concept": 0-10,
  "answerability": 0-10,
  "neutrality": 0-10,
  "overall_quality_score": 0-10,
  "problem_categories": ["clarity_issue|single_concept_issue|answerability_issue|neutrality_issue|leading|double_barreled|ambiguous_time|negative_wording"],
  "detected_terms": ["terms or variants that mattered"],
  "term_assessments": [
    {{
      "term": "matched term or variant",
      "category": "ambiguous|negative|leading|double_barreled",
      "context_effect": "problem|acceptable",
      "reason": "짧은 한국어 근거 1문장"
    }}
  ],
  "llm_comment": "한국어 2~3문장 진단 요약",
  "suggested_rewrite": "필요할 때만 한국어 제안본 문장 1개, 문제 없으면 빈 문자열"
}}
"""

    content = create_chat_completion(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Return ONLY valid JSON. "
                    "Be conservative and context-aware. "
                    "Prioritize measurement-quality harms over stylistic preferences. "
                    "Do not auto-penalize dictionary terms without contextual evidence. "
                    "Use Korean for all free-text output fields."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )

    parsed = extract_json_from_text(content)
    if not isinstance(parsed, dict):
        raise ValueError(f"LLM item quality JSON parse failed. raw={content!r}")

    return normalize_llm_quality_result(parsed)
