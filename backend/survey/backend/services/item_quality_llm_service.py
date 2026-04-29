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
You are a strict but conservative survey item wording evaluator.

Task:
1) Evaluate wording quality for the item.
2) Use the term dictionary below as a diagnostic aid.
3) Always judge term risk in context of both question and options.

Important policy:
- Do NOT penalize a term just because it appears.
- If options provide concrete anchors (example: "once every 3 days", fixed frequency, explicit timeframe),
  ambiguous adverbs like "often/frequently" may be acceptable and should receive little or no penalty.
- Penalize only when context is actually unclear, biased, double-barreled, or hard to answer.
- Score conservatively: avoid extreme 0-2 or 9-10 unless there is very strong evidence.
- Typical well-written item should be around 6.0~8.5.

Evaluation scope:
- Only wording quality (clarity/single concept/answerability/neutrality).
- Ignore construct-level consistency with other items.

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
      "reason": "one short reason"
    }}
  ],
  "llm_comment": "2-4 sentence conservative diagnostic summary",
  "suggested_rewrite": "rewrite only when needed; otherwise empty string"
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
                    "Do not auto-penalize dictionary terms without contextual evidence."
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
