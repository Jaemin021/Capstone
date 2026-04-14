from collections import Counter, defaultdict

from config import (
    RESPONSE_CATEGORIES,
    RESPONSE_PENALTY_WEIGHTS,
    MAX_RESPONSE_RAW_PENALTY,
    SCORE_MIN,
    SCORE_MAX,
    ROUND_DIGITS,
)


def clamp_score(value: float, min_value: float = SCORE_MIN, max_value: float = SCORE_MAX) -> float:
    return max(min_value, min(max_value, value))


def round_score(value: float) -> float:
    return round(value, ROUND_DIGITS)


def build_empty_feature_counts() -> dict:
    """
    응답 신뢰도 feature count 기본 틀 생성
    """
    return {
        "instruction": {
            "instruction_fail": 0,
        },
        "consistency": {
            "reverse_inconsistency": 0,
            "similar_item_inconsistency": 0,
        },
        "pattern": {
            "straightlining": 0,
            "low_variance": 0,
            "extreme_repetition": 0,
        },
        "behavior": {
            "excessive_tab_switch": 0,
            "high_focus_loss": 0,
            "excessive_revisit": 0,
        },
    }


def _build_item_map(survey: dict) -> dict:
    """
    item_id -> survey item 매핑
    """
    items = survey.get("items", []) or []
    return {
        item.get("item_id"): item
        for item in items
        if item.get("item_id")
    }


def _build_answer_map(response: dict) -> dict:
    """
    item_id -> answer 매핑
    """
    answers = response.get("answers", []) or []
    return {
        answer.get("item_id"): answer
        for answer in answers
        if answer.get("item_id")
    }


def _extract_numeric_answer(answer: dict):
    """
    단일 선택 / 척도형 응답의 숫자값 추출
    """
    if not answer:
        return None

    value = answer.get("answer_value")

    if isinstance(value, (int, float)):
        return float(value)

    return None


def _get_question_log(answer: dict) -> dict:
    """
    문항별 로그 추출
    """
    if not answer:
        return {}
    return answer.get("question_log", {}) or {}


def _safe_len_options(item: dict) -> int:
    """
    선택지 개수 반환
    """
    options = item.get("options", []) or []
    return len(options)


def _normalize_reverse_value(value: float, option_count: int):
    """
    역문항 값을 원문항 방향으로 뒤집어서 비교하기 위한 보정값
    예: 1~5 척도에서 1 <-> 5, 2 <-> 4
    """
    if value is None or option_count <= 1:
        return value

    return (option_count + 1) - value


def _is_extreme_value(value: float, option_count: int) -> bool:
    """
    극단값 응답인지 판별
    """
    if value is None or option_count <= 1:
        return False

    return value == 1 or value == option_count


def _max_same_run(values: list[float]) -> int:
    """
    연속 동일 응답 최대 길이 계산
    """
    if not values:
        return 0

    max_run = 1
    current_run = 1

    for i in range(1, len(values)):
        if values[i] == values[i - 1]:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1

    return max_run


def _variance(values: list[float]) -> float:
    """
    매우 간단한 분산 계산 (모분산 방식)
    """
    if not values:
        return 0.0

    mean_value = sum(values) / len(values)
    return sum((v - mean_value) ** 2 for v in values) / len(values)


def analyze_response_features(survey: dict, response: dict) -> tuple[dict, dict]:
    """
    survey + response를 이용해
    feature_analysis, feature_counts를 생성
    """
    feature_analysis = {
        "instruction": [],
        "consistency": [],
        "pattern": [],
        "behavior": [],
    }
    feature_counts = build_empty_feature_counts()

    item_map = _build_item_map(survey)
    answer_map = _build_answer_map(response)
    survey_items = survey.get("items", []) or []
    survey_log = response.get("survey_log", {}) or {}

    # --------------------------------------------------
    # 1) instruction
    # --------------------------------------------------
    for item in survey_items:
        if not item.get("is_trap", False):
            continue

        if item.get("trap_type") != "instruction":
            continue

        item_id = item.get("item_id")
        expected_answer = item.get("trap_expected_answer")
        answer = answer_map.get(item_id)

        if not answer:
            continue

        answer_value = answer.get("answer_value")
        selected_options = answer.get("selected_options")

        fail = False

        if answer_value is not None:
            fail = answer_value != expected_answer
        elif selected_options is not None:
            fail = expected_answer not in selected_options

        if fail:
            feature_counts["instruction"]["instruction_fail"] += 1
            feature_analysis["instruction"].append({
                "feature": "instruction_fail",
                "item_id": item_id,
                "expected_answer": expected_answer,
                "actual_answer": answer_value if answer_value is not None else selected_options,
                "reason": "지시형 함정문항의 기대 응답과 실제 응답이 일치하지 않음",
            })

    # --------------------------------------------------
    # 2) consistency
    # --------------------------------------------------
    group_to_items = defaultdict(list)
    for item in survey_items:
        group_id = item.get("consistency_group")
        if group_id:
            group_to_items[group_id].append(item)

    for group_id, grouped_items in group_to_items.items():
        # 역문항 비교
        reverse_items = [item for item in grouped_items if item.get("is_reverse") is True]
        non_reverse_items = [item for item in grouped_items if item.get("is_reverse") is not True]

        for reverse_item in reverse_items:
            reverse_item_id = reverse_item.get("item_id")
            reverse_answer = answer_map.get(reverse_item_id)
            reverse_value = _extract_numeric_answer(reverse_answer)

            if reverse_value is None:
                continue

            reverse_option_count = _safe_len_options(reverse_item)
            normalized_reverse = _normalize_reverse_value(reverse_value, reverse_option_count)

            for source_item in non_reverse_items:
                source_item_id = source_item.get("item_id")
                source_answer = answer_map.get(source_item_id)
                source_value = _extract_numeric_answer(source_answer)

                if source_value is None:
                    continue

                # 차이가 2 이상이면 baseline에서 불일치로 판단
                if abs(source_value - normalized_reverse) >= 2:
                    feature_counts["consistency"]["reverse_inconsistency"] += 1
                    feature_analysis["consistency"].append({
                        "feature": "reverse_inconsistency",
                        "group_id": group_id,
                        "source_item_id": source_item_id,
                        "reverse_item_id": reverse_item_id,
                        "source_answer": source_value,
                        "reverse_answer": reverse_value,
                        "normalized_reverse_answer": normalized_reverse,
                        "reason": "원문항과 역문항의 응답 방향이 일관되지 않음",
                    })

        # 유사 문항 비교
        numeric_group_answers = []
        for item in grouped_items:
            item_id = item.get("item_id")
            answer = answer_map.get(item_id)
            value = _extract_numeric_answer(answer)

            if value is None:
                continue

            numeric_group_answers.append((item, value))

        for i in range(len(numeric_group_answers)):
            for j in range(i + 1, len(numeric_group_answers)):
                item_a, value_a = numeric_group_answers[i]
                item_b, value_b = numeric_group_answers[j]

                # 역문항 비교는 위에서 따로 봤으므로 여기서는 둘 다 일반 문항인 경우만
                if item_a.get("is_reverse") or item_b.get("is_reverse"):
                    continue

                if abs(value_a - value_b) >= 2:
                    feature_counts["consistency"]["similar_item_inconsistency"] += 1
                    feature_analysis["consistency"].append({
                        "feature": "similar_item_inconsistency",
                        "group_id": group_id,
                        "item_id_a": item_a.get("item_id"),
                        "item_id_b": item_b.get("item_id"),
                        "answer_a": value_a,
                        "answer_b": value_b,
                        "reason": "같은 일관성 그룹 내 유사 문항 간 응답 차이가 큼",
                    })

    # --------------------------------------------------
    # 3) pattern
    # --------------------------------------------------
    numeric_answers = []
    extreme_count = 0

    for item in survey_items:
        item_id = item.get("item_id")
        answer = answer_map.get(item_id)
        value = _extract_numeric_answer(answer)

        if value is None:
            continue

        numeric_answers.append(value)

        option_count = _safe_len_options(item)
        if _is_extreme_value(value, option_count):
            extreme_count += 1

    # straightlining
    max_run = _max_same_run(numeric_answers)
    if max_run >= 4:
        feature_counts["pattern"]["straightlining"] = 1
        feature_analysis["pattern"].append({
            "feature": "straightlining",
            "max_same_run": max_run,
            "reason": "같은 응답값이 연속해서 반복됨",
        })

    # low_variance
    if len(numeric_answers) >= 3:
        variance_value = _variance(numeric_answers)
        if variance_value <= 0.30:
            feature_counts["pattern"]["low_variance"] = 1
            feature_analysis["pattern"].append({
                "feature": "low_variance",
                "variance": round_score(variance_value),
                "reason": "전체 응답 분산이 매우 낮음",
            })

    # extreme_repetition
    if len(numeric_answers) >= 3:
        extreme_ratio = extreme_count / len(numeric_answers)
        if extreme_ratio >= 0.80:
            feature_counts["pattern"]["extreme_repetition"] = 1
            feature_analysis["pattern"].append({
                "feature": "extreme_repetition",
                "extreme_count": extreme_count,
                "answer_count": len(numeric_answers),
                "extreme_ratio": round_score(extreme_ratio),
                "reason": "극단값 응답 비율이 매우 높음",
            })

    # --------------------------------------------------
    # 4) behavior
    # --------------------------------------------------
    tab_switch_count = survey_log.get("tab_switch_count", 0) or 0
    total_focus_loss_count = survey_log.get("focus_loss_count", 0) or 0

    total_revisit_count = 0
    for answer in response.get("answers", []) or []:
        qlog = _get_question_log(answer)
        total_revisit_count += qlog.get("revisit_count", 0) or 0

    if tab_switch_count >= 3:
        feature_counts["behavior"]["excessive_tab_switch"] = 1
        feature_analysis["behavior"].append({
            "feature": "excessive_tab_switch",
            "tab_switch_count": tab_switch_count,
            "reason": "설문 중 탭 전환 횟수가 많음",
        })

    if total_focus_loss_count >= 3:
        feature_counts["behavior"]["high_focus_loss"] = 1
        feature_analysis["behavior"].append({
            "feature": "high_focus_loss",
            "focus_loss_count": total_focus_loss_count,
            "reason": "설문 중 포커스 이탈 횟수가 많음",
        })

    if total_revisit_count >= 3:
        feature_counts["behavior"]["excessive_revisit"] = 1
        feature_analysis["behavior"].append({
            "feature": "excessive_revisit",
            "revisit_count": total_revisit_count,
            "reason": "문항 revisit 횟수가 많음",
        })

    return feature_analysis, feature_counts


def compute_response_penalty_details(feature_counts: dict, categories: list[str] | None = None) -> dict:
    target_categories = categories or RESPONSE_CATEGORIES
    penalty_details = {}

    for category in target_categories:
        category_counts = feature_counts.get(category, {})
        category_weights = RESPONSE_PENALTY_WEIGHTS.get(category, {})
        category_detail = {}

        for feature_name, count in category_counts.items():
            weight = category_weights.get(feature_name, 0.0)
            category_detail[feature_name] = round_score(count * weight)

        penalty_details[category] = category_detail

    return penalty_details


def compute_response_raw_penalties(feature_counts: dict, categories: list[str] | None = None) -> dict:
    target_categories = categories or RESPONSE_CATEGORIES
    raw_penalties = {}

    for category in target_categories:
        category_counts = feature_counts.get(category, {})
        category_weights = RESPONSE_PENALTY_WEIGHTS.get(category, {})

        total_penalty = 0.0
        for feature_name, count in category_counts.items():
            weight = category_weights.get(feature_name, 0.0)
            total_penalty += count * weight

        raw_penalties[category] = round_score(total_penalty)

    return raw_penalties


def convert_response_penalty_to_rule_score(raw_penalty: float, category: str) -> float:
    max_penalty = MAX_RESPONSE_RAW_PENALTY.get(category, 5.0)

    if max_penalty <= 0:
        return SCORE_MAX

    normalized_penalty = min(raw_penalty / max_penalty, 1.0)
    score = SCORE_MAX - normalized_penalty * (SCORE_MAX - SCORE_MIN)
    return round_score(clamp_score(score))


def compute_response_rule_scores(raw_penalties: dict, categories: list[str] | None = None) -> dict:
    target_categories = categories or RESPONSE_CATEGORIES
    rule_scores = {}

    for category in target_categories:
        raw_penalty = raw_penalties.get(category, 0.0)
        rule_scores[category] = convert_response_penalty_to_rule_score(raw_penalty, category)

    return rule_scores


def build_response_flags(feature_counts: dict) -> dict:
    """
    프론트용 주요 경고 플래그
    """
    return {
        "instruction_fail": feature_counts.get("instruction", {}).get("instruction_fail", 0) > 0,
        "inconsistency": (
            feature_counts.get("consistency", {}).get("reverse_inconsistency", 0) > 0
            or feature_counts.get("consistency", {}).get("similar_item_inconsistency", 0) > 0
        ),
        "straightlining": (
            feature_counts.get("pattern", {}).get("straightlining", 0) > 0
        ),
        "suspicious_behavior": (
            feature_counts.get("behavior", {}).get("excessive_tab_switch", 0) > 0
            or feature_counts.get("behavior", {}).get("high_focus_loss", 0) > 0
            or feature_counts.get("behavior", {}).get("excessive_revisit", 0) > 0
        ),
    }


def count_response_issues(feature_counts: dict, categories: list[str] | None = None) -> int:
    target_categories = categories or RESPONSE_CATEGORIES
    total = 0

    for category in target_categories:
        total += sum(feature_counts.get(category, {}).values())

    return total