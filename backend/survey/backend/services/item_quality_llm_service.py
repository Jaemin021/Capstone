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
- Detect wording risks using the provided term dictionary.
- Focus on unresolved wording problems only (dictionary-context based).

Task:
1) Use the term dictionary as the primary risk detector.
2) Judge in full context of question + options.
3) If options provide concrete timeframe/frequency anchors (e.g., "지난 2주", "주 1~2회"),
   treat ambiguous-frequency wording as acceptable in context.

Option recovery rule (important):
- If options provide concrete anchors (frequency/timeframe/intensity), ambiguity risk may recover.
- If recovered, do not include that term in unresolved problem categories.

Rewrite policy:
- If any context_effect="problem" term remains unresolved, suggested_rewrite must be one Korean sentence.
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
                    "Focus on dictionary-based unresolved wording problems only. "
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
- 단, 보기에 이미 구체적인 시간/기간/빈도 기준이 충분하면 불필요한 수정을 피하세요.

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


def _normalize_text(text):
    return re.sub(r"\s+", " ", str(text or "").strip())


def _is_time_or_frequency_anchor(text):
    lowered = str(text or "").strip().lower()
    if not lowered:
        return False

    if re.search(r"\d+\s*(회|번|일|주|개월|달|월|년|시간|분)", lowered):
        return True

    anchor_hints = (
        "지난",
        "최근",
        "주당",
        "매일",
        "거의 매일",
        "전혀",
        "항상",
        "주 1회",
        "주 2",
        "주 3",
        "2주",
        "4주",
    )
    return any(hint in lowered for hint in anchor_hints)


def _is_concrete_time_frequency_anchor(text):
    lowered = str(text or "").strip().lower()
    if not lowered:
        return False

    if re.search(r"\d+\s*(회|번|일|주|개월|달|월|년|시간|분)", lowered):
        return True

    concrete_hints = (
        "지난",
        "최근",
        "주당",
        "매일",
        "주 1",
        "주 2",
        "주 3",
        "2주",
        "4주",
        "한 달",
        "1달",
        "두 달",
    )
    return any(hint in lowered for hint in concrete_hints)


def _estimate_dictionary_option_clarity_score(options):
    option_texts = [str(option).strip() for option in (options or []) if str(option).strip()]
    if not option_texts:
        return 5.0

    anchor_count = sum(1 for option in option_texts if _is_time_or_frequency_anchor(option))
    anchor_ratio = anchor_count / len(option_texts)

    has_extreme_low = any("전혀" in option or "없음" in option or "아니다" in option for option in option_texts)
    has_extreme_high = any("항상" in option or "매우" in option or "거의 매일" in option for option in option_texts)
    extreme_bonus = 0.15 if has_extreme_low and has_extreme_high else 0.0

    score = (anchor_ratio + extreme_bonus) * 10.0
    return max(0.0, min(10.0, round(score, 3)))


def _has_concrete_time_frequency_options(options):
    option_texts = [str(option).strip() for option in (options or []) if str(option).strip()]
    if not option_texts:
        return False

    anchor_count = sum(1 for option in option_texts if _is_concrete_time_frequency_anchor(option))
    required_count = max(2, (len(option_texts) + 1) // 2)
    return anchor_count >= required_count


def _rewrite_by_dictionary_rules(question_text, unresolved_terms, unresolved_categories):
    rewritten = _normalize_text(question_text)
    rewritten = re.sub(r"[.?!]+$", "", rewritten).strip()

    leading_terms = ["당연히", "반드시", "꼭", "확실히"]
    for term in leading_terms:
        rewritten = rewritten.replace(term, "")

    negative_map = {
        "불편하지 않다": "편리하다",
        "만족하지 않는다": "만족한다",
        "없다": "있다",
        "못하다": "할 수 있다",
    }
    for before, after in negative_map.items():
        if before in rewritten:
            rewritten = rewritten.replace(before, after)

    ambiguous_map = {
        "자주": "지난 2주 동안 주 3회 이상",
        "가끔": "지난 2주 동안 주 1~2회",
        "보통": "중간 수준(주 2~3회)",
        "대체로": "대부분의 경우",
        "적당히": "명확한 기준에 따라",
        "충분히": "기준을 충족할 만큼",
        "조금": "낮은 수준으로",
        "많이": "높은 수준으로",
    }
    for term in unresolved_terms:
        replacement = ambiguous_map.get(term)
        if replacement and term in rewritten:
            rewritten = rewritten.replace(term, replacement, 1)

    if "double_barreled" in unresolved_categories or "single_concept_issue" in unresolved_categories:
        rewritten = re.split(r"(그리고|및|또는|거나)", rewritten, maxsplit=1)[0].strip()

    rewritten = re.sub(r"\s+", " ", rewritten).strip()
    if not rewritten:
        rewritten = _normalize_text(question_text)

    if rewritten and rewritten[-1] not in {"?", "."}:
        rewritten += "?"

    return rewritten


def evaluate_item_with_dictionary_rules(question_text, options):
    question = _normalize_text(question_text)
    lowered_question = question.lower()
    option_clarity_score = _estimate_dictionary_option_clarity_score(options)
    ambiguity_resolved_by_options = _has_concrete_time_frequency_options(options)

    detected_terms = []
    term_assessments = []
    unresolved_categories = set()
    unresolved_terms = []

    def record_term(term, category, resolved):
        nonlocal detected_terms, term_assessments, unresolved_categories, unresolved_terms

        detected_terms.append(term)
        context_effect = "acceptable" if resolved else "problem"
        term_assessments.append({
            "term": term,
            "category": category,
            "context_effect": context_effect,
            "severity": 0 if resolved else 2,
            "reason": (
                "보기에 구체 기준이 있어 해석 위험이 완화되었습니다."
                if resolved
                else "문항 단독 해석 시 응답자마다 의미 기준이 달라질 수 있습니다."
            ),
        })
        if not resolved:
            unresolved_terms.append(term)

    for term in AMBIGUOUS_TERMS:
        t = str(term).strip()
        if t and t in lowered_question:
            resolved = ambiguity_resolved_by_options
            record_term(t, "ambiguous", resolved)
            if not resolved:
                unresolved_categories.add("ambiguous_time")
                unresolved_categories.add("answerability_issue")

    for term in NEGATIVE_TERMS:
        t = str(term).strip()
        if t and t in lowered_question:
            record_term(t, "negative", False)
            unresolved_categories.add("negative_wording")
            unresolved_categories.add("clarity_issue")

    for term in LEADING_TERMS:
        t = str(term).strip()
        if t and t in lowered_question:
            record_term(t, "leading", False)
            unresolved_categories.add("leading")
            unresolved_categories.add("neutrality_issue")

    for term in DOUBLE_BARRELED_HINTS:
        t = str(term).strip()
        if t and t in lowered_question:
            record_term(t, "double_barreled", False)
            unresolved_categories.add("double_barreled")
            unresolved_categories.add("single_concept_issue")

    # 중복 제거하면서 순서 유지
    dedup_detected_terms = []
    seen_terms = set()
    for term in detected_terms:
        if term in seen_terms:
            continue
        seen_terms.add(term)
        dedup_detected_terms.append(term)

    if unresolved_categories:
        llm_comment = (
            "사전 기반 문제표현이 확인되어 문항 해석 위험이 있습니다. "
            "해당 표현을 제거하거나 구체 기준으로 바꾼 수정 문장을 제안합니다."
        )
        suggested_rewrite = _rewrite_by_dictionary_rules(
            question_text=question,
            unresolved_terms=unresolved_terms,
            unresolved_categories=unresolved_categories,
        )
    else:
        if dedup_detected_terms:
            llm_comment = "사전 표현은 포함되어 있으나 보기가 의미 기준을 충분히 고정해 해석 위험이 완화되었습니다."
        else:
            llm_comment = "사전에 정의한 문제표현이 문항에서 확인되지 않았습니다."
        suggested_rewrite = ""

    return {
        "problem_categories": sorted(unresolved_categories),
        "detected_terms": dedup_detected_terms,
        "term_assessments": term_assessments,
        "option_clarity_score": option_clarity_score,
        "option_recovery": {
            "applied": bool(ambiguity_resolved_by_options and "ambiguous_time" not in unresolved_categories),
            "reason": (
                "보기의 빈도/시간 기준이 구체적이라 모호어 위험이 완화되었습니다."
                if ambiguity_resolved_by_options
                else "보기에 구체 빈도/시간 기준이 부족해 모호어 위험이 남아 있습니다."
            ),
        },
        "llm_comment": llm_comment,
        "suggested_rewrite": suggested_rewrite,
    }
