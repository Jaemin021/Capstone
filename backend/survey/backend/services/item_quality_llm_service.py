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
REWRITE_MODEL = os.getenv("OPENAI_REWRITE_MODEL", MODEL)


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


def _to_optional_score(value):
    if value is None:
        return None

    try:
        parsed = float(value)
    except Exception:
        if isinstance(value, str):
            match = re.search(r"-?\d+(?:\.\d+)?", value)
            if not match:
                return None
            try:
                parsed = float(match.group(0))
            except Exception:
                return None
        else:
            return None

    if parsed < 0:
        return 0.0
    if parsed > 10:
        return 10.0
    return parsed


def _normalize_term_assessments(value):
    rows = []
    if not isinstance(value, list):
        return rows

    for raw in value:
        if not isinstance(raw, dict):
            continue

        term = str(raw.get("term", "")).strip()
        if not term:
            continue

        category = str(raw.get("category", "")).strip().lower()
        context_effect = str(raw.get("context_effect", "")).strip().lower()
        reason = raw.get("reason")
        severity = raw.get("severity")

        normalized = {
            "term": term,
            "category": category if category else "ambiguous",
            "context_effect": context_effect if context_effect in {"problem", "acceptable"} else "problem",
            "reason": reason if isinstance(reason, str) else "",
            "severity": _to_optional_score(severity) if severity is not None else 1.0,
        }

        if normalized["severity"] is None:
            normalized["severity"] = 1.0

        rows.append(normalized)

    return rows


def _normalize_option_recovery(value):
    if not isinstance(value, dict):
        return None

    applied = bool(value.get("applied"))
    reason = value.get("reason")

    return {
        "applied": applied,
        "reason": reason if isinstance(reason, str) else "",
    }


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

    normalized["term_assessments"] = _normalize_term_assessments(parsed.get("term_assessments"))
    normalized["option_clarity_score"] = _to_optional_score(parsed.get("option_clarity_score"))
    normalized["option_recovery"] = _normalize_option_recovery(parsed.get("option_recovery"))

    return normalized


def _clean_rewrite_text(text):
    if not isinstance(text, str):
        return ""

    cleaned = text.strip()
    if not cleaned:
        return ""

    cleaned = cleaned.replace("```", "")
    cleaned = cleaned.replace("\r", "\n")
    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
    if lines:
        cleaned = lines[0]

    for prefix in ["수정 제안:", "제안:", "원문:"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()

    cleaned = cleaned.strip('"').strip("'").strip()
    if cleaned and cleaned[-1] not in {"?", "."}:
        cleaned += "?"

    return cleaned


def evaluate_item_with_llm(question_text, options):
    quality_dictionary = build_quality_dictionary_payload()

    prompt = f"""
You are a strict survey wording evaluator for measurement quality.

Primary objective:
- Detect wording risks that can distort responses.
- Treat dictionary-matched terms as high-priority risk signals.
- Penalize risky term usage clearly, unless options make the meaning explicit.

Task:
1) Evaluate wording quality for the item.
2) Use the term dictionary as a risk detector.
3) Judge risks in full context of question + options.

Scoring calibration:
- 9~10: no practical wording risk.
- 7~8: generally acceptable but with minor risk.
- 6: borderline.
- <6: clear quality-harming wording issue.
- If risky dictionary terms remain unresolved, score should drop meaningfully.

Option recovery rule (important):
- If options provide concrete anchors (frequency/timeframe/intensity), ambiguity risk may recover.
- Explicitly reflect this in option_clarity_score and option_recovery.

Rewrite policy:
- If overall_quality_score < 6 or any context_effect="problem" term remains unresolved,
  suggested_rewrite must be one Korean sentence.
- suggested_rewrite must directly resolve dictionary-based risk terms.
- Keep construct intent and response format.
- Do not prepend labels such as "수정 제안:".

Language policy:
- All free-text fields must be Korean.

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
  "detected_terms": ["matched terms or variants that mattered"],
  "term_assessments": [
    {{
      "term": "matched term or variant",
      "category": "ambiguous|negative|leading|double_barreled",
      "context_effect": "problem|acceptable",
      "severity": 0|1|2,
      "reason": "짧은 한국어 근거 1문장"
    }}
  ],
  "option_clarity_score": 0-10,
  "option_recovery": {{
    "applied": true|false,
    "reason": "한국어 1문장"
  }},
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
                    "Use Korean for all free-text fields. "
                    "Apply meaningful score drops for unresolved dictionary-risk terms. "
                    "If risk is resolved by options, reflect it explicitly in option_recovery."
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


def generate_rewrite_with_llm(question_text, options, problem_categories=None, detected_terms=None, llm_comment=None):
    prompt = f"""
당신은 설문 문항 수정 전문가입니다.
아래 문항을 한국어 한 문장으로 수정하세요.

수정 목적:
- 문제 원인은 단어사전(모호어/부정어/유도어/이중질문 단서) 기반입니다.
- 감점된 개념을 직접 해소해야 합니다.
- 모호한 빈도/시간 표현은 구체 기준(예: 지난 2주, 주 n회)을 넣어 명확히 하세요.
- 이중질문이면 한 문항 한 개념으로 줄이세요.
- 부정표현이면 가능한 긍정형으로 바꾸세요.

제약:
- 출력은 문항 1문장만.
- 설명, 라벨, 따옴표, JSON 금지.
- 원래 측정 의도와 응답 형식은 유지.

원문 문항:
{question_text}

보기:
{json.dumps(options or [], ensure_ascii=False)}

문제 카테고리:
{json.dumps(problem_categories or [], ensure_ascii=False)}

탐지 용어:
{json.dumps(detected_terms or [], ensure_ascii=False)}

진단 코멘트:
{llm_comment or ""}
"""

    content = create_chat_completion(
        model=REWRITE_MODEL,
        messages=[
            {
                "role": "system",
                "content": "한국어 한 문장만 출력하세요. 설명 없이 문항 문장만 출력하세요.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )

    return _clean_rewrite_text(content)
