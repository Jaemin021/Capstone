# backend/services/feature_service.py

import math

TOO_FAST_ABSOLUTE_THRESHOLD_MS = 1500


def safe_avg(values, default=0):
    valid_values = [
        v for v in values
        if v is not None
    ]

    if not valid_values:
        return default

    return sum(valid_values) / len(valid_values)


def safe_max(values, default=0):
    valid_values = [
        v for v in values
        if v is not None
    ]

    if not valid_values:
        return default

    return max(valid_values)


def calculate_log_features(response_log, item_logs, connection_events):
    item_times = [
        item_log.item_time_ms
        for item_log in item_logs
        if item_log.item_time_ms is not None and item_log.item_time_ms >= 0
    ]

    item_count = len(item_times)

    total_time_ms = response_log.total_time_ms or 0

    if total_time_ms <= 0 and item_times:
        total_time_ms = sum(item_times)

    avg_item_time_ms = total_time_ms / item_count if item_count > 0 else 0

    too_fast_threshold = TOO_FAST_ABSOLUTE_THRESHOLD_MS

    too_fast_count = sum(
        1 for t in item_times
        if t < too_fast_threshold
    )

    too_fast_ratio = too_fast_count / item_count if item_count > 0 else 0

    avg_touch_per_item = (
        response_log.total_touch_count / item_count
        if item_count > 0 else 0
    )

    offline_ratio = (
        response_log.offline_total_ms / total_time_ms
        if total_time_ms > 0 else 0
    )

    has_offline_event = any(
        e.event_type == "offline"
        for e in connection_events
    )

    connection_lost = 1 if response_log.connection_lost or has_offline_event else 0

    # -----------------------------
    # 신규 문항 단위 시간 feature
    # -----------------------------
    time_to_first_answer_values = [
        item_log.time_to_first_answer_ms
        for item_log in item_logs
        if item_log.time_to_first_answer_ms is not None
        and item_log.time_to_first_answer_ms >= 0
    ]

    time_after_last_answer_values = [
        item_log.time_after_last_answer_ms
        for item_log in item_logs
        if item_log.time_after_last_answer_ms is not None
        and item_log.time_after_last_answer_ms >= 0
    ]

    initial_visit_time_values = [
        item_log.initial_visit_time_ms
        for item_log in item_logs
        if item_log.initial_visit_time_ms is not None
        and item_log.initial_visit_time_ms >= 0
    ]

    revisit_time_values = [
        item_log.revisit_time_ms
        for item_log in item_logs
        if item_log.revisit_time_ms is not None
        and item_log.revisit_time_ms >= 0
    ]

    change_counts = [
        item_log.change_count or 0
        for item_log in item_logs
    ]

    visit_counts = [
        item_log.visit_count or 0
        for item_log in item_logs
    ]

    back_visit_counts = [
        item_log.back_visit_count or 0
        for item_log in item_logs
    ]

    total_change_count = sum(change_counts)
    total_visit_count = sum(visit_counts)
    total_back_visit_count = sum(back_visit_counts)

    revisited_item_count = sum(
        1 for item_log in item_logs
        if item_log.is_revisited
    )

    answer_changed_count = sum(
        1 for item_log in item_logs
        if item_log.answer_changed
    )

    changed_after_revisit_count = sum(
        1 for item_log in item_logs
        if item_log.changed_after_revisit
    )

    revisit_item_ratio = (
        revisited_item_count / item_count
        if item_count > 0 else 0
    )

    answer_changed_ratio = (
        answer_changed_count / item_count
        if item_count > 0 else 0
    )

    changed_after_revisit_ratio = (
        changed_after_revisit_count / item_count
        if item_count > 0 else 0
    )

    avg_change_count = (
        total_change_count / item_count
        if item_count > 0 else 0
    )

    avg_visit_count = (
        total_visit_count / item_count
        if item_count > 0 else 0
    )

    avg_back_visit_count = (
        total_back_visit_count / item_count
        if item_count > 0 else 0
    )

    return {
        # 기존 feature
        "total_time_ms": total_time_ms,
        "item_count": item_count,
        "avg_item_time_ms": avg_item_time_ms,
        "too_fast_threshold_ms": too_fast_threshold,
        "too_fast_item_ratio": too_fast_ratio,
        "avg_touch_per_item": avg_touch_per_item,
        "offline_ratio": offline_ratio,
        "connection_lost": connection_lost,

        # 신규 시간 feature
        "mean_time_to_first_answer_ms": safe_avg(time_to_first_answer_values),
        "min_time_to_first_answer_ms": min(time_to_first_answer_values) if time_to_first_answer_values else 0,
        "max_time_to_first_answer_ms": safe_max(time_to_first_answer_values),

        "mean_time_after_last_answer_ms": safe_avg(time_after_last_answer_values),
        "max_time_after_last_answer_ms": safe_max(time_after_last_answer_values),

        "mean_initial_visit_time_ms": safe_avg(initial_visit_time_values),
        "mean_revisit_time_ms": safe_avg(revisit_time_values),
        "max_revisit_time_ms": safe_max(revisit_time_values),

        # 신규 변경/재방문 feature
        "total_change_count": total_change_count,
        "mean_change_count": avg_change_count,

        "total_visit_count": total_visit_count,
        "mean_visit_count": avg_visit_count,

        "total_back_visit_count": total_back_visit_count,
        "mean_back_visit_count": avg_back_visit_count,

        "revisited_item_count": revisited_item_count,
        "revisit_item_ratio": revisit_item_ratio,

        "answer_changed_count": answer_changed_count,
        "answer_changed_ratio": answer_changed_ratio,

        "changed_after_revisit_count": changed_after_revisit_count,
        "changed_after_revisit_ratio": changed_after_revisit_ratio
    }


def calculate_content_features(answers, survey_items):
    answer_map = {a.item_id: a for a in answers}

    trap_total = 0
    trap_fail = 0

    for item in survey_items:
        if item.item_role == "trap":
            trap_total += 1
            ans = answer_map.get(item.item_id)

            if ans is None:
                trap_fail += 1
            elif ans.selected_option_order != item.trap_correct_option_order:
                trap_fail += 1

    trap_fail_ratio = trap_fail / trap_total if trap_total > 0 else 0

    return {
        "trap_total_count": trap_total,
        "trap_fail_count": trap_fail,
        "trap_fail_ratio": trap_fail_ratio
    }


def build_compact_features(log_f, content_f, relation_f, population_f):
    return {
        # 기존 log feature
        "avg_item_time_ms": log_f.get("avg_item_time_ms", 0),
        "too_fast_item_ratio": log_f.get("too_fast_item_ratio", 0),
        "avg_touch_per_item": log_f.get("avg_touch_per_item", 0),
        "offline_ratio": log_f.get("offline_ratio", 0),
        "connection_lost": log_f.get("connection_lost", 0),

        # 신규 log feature
        "mean_time_to_first_answer_ms": log_f.get("mean_time_to_first_answer_ms", 0),
        "min_time_to_first_answer_ms": log_f.get("min_time_to_first_answer_ms", 0),
        "mean_time_after_last_answer_ms": log_f.get("mean_time_after_last_answer_ms", 0),

        "mean_change_count": log_f.get("mean_change_count", 0),
        "total_change_count": log_f.get("total_change_count", 0),

        "mean_visit_count": log_f.get("mean_visit_count", 0),
        "mean_back_visit_count": log_f.get("mean_back_visit_count", 0),
        "total_back_visit_count": log_f.get("total_back_visit_count", 0),

        "revisit_item_ratio": log_f.get("revisit_item_ratio", 0),
        "answer_changed_ratio": log_f.get("answer_changed_ratio", 0),
        "changed_after_revisit_ratio": log_f.get("changed_after_revisit_ratio", 0),

        "mean_revisit_time_ms": log_f.get("mean_revisit_time_ms", 0),
        "max_revisit_time_ms": log_f.get("max_revisit_time_ms", 0),

        # content feature
        "trap_fail_ratio": (
            content_f.get("trap_fail_ratio", 0)
            if content_f is not None
            else 0
        ),

        # relation feature
        "reverse_avg_diff": (
            relation_f.get("reverse_avg_diff")
            if relation_f is not None
            else None
        ),
        "reverse_consistency_score": (
            relation_f.get("reverse_consistency_score")
            if relation_f is not None
            else None
        ),

        # population feature
        "time_curve_deviation": (
            population_f.get("time_curve_deviation")
            if population_f is not None
            else None
        ),
        "population_sample_count": (
            population_f.get("population_sample_count")
            if population_f is not None
            else 0
        ),

        "item_count": log_f.get("item_count", 0)
    }


def calculate_relation_features(answers, survey_items):
    answer_map = {a.item_id: a for a in answers}

    reverse_pair_count = 0
    reverse_total_diff = 0

    for item in survey_items:
        if item.item_role != "reverse":
            continue

        if item.source_item_id is None:
            continue

        source_answer = answer_map.get(item.source_item_id)
        reverse_answer = answer_map.get(item.item_id)

        if source_answer is None or reverse_answer is None:
            continue

        if (
            source_answer.selected_option_order is None
            or reverse_answer.selected_option_order is None
        ):
            continue

        expected_reverse_order = 6 - source_answer.selected_option_order
        diff = abs(reverse_answer.selected_option_order - expected_reverse_order)

        reverse_pair_count += 1
        reverse_total_diff += diff

    reverse_avg_diff = (
        reverse_total_diff / reverse_pair_count
        if reverse_pair_count > 0
        else None
    )

    reverse_consistency_score = (
        1 - (reverse_avg_diff / 4)
        if reverse_avg_diff is not None
        else None
    )

    return {
        "reverse_pair_count": reverse_pair_count,
        "reverse_total_diff": reverse_total_diff,
        "reverse_avg_diff": reverse_avg_diff,
        "reverse_consistency_score": reverse_consistency_score
    }