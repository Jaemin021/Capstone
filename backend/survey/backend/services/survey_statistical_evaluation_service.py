# backend/services/survey_statistical_evaluation_service.py

from datetime import datetime
import models
from services.feature_service import should_exclude_from_statistics


def now_str():
    return datetime.now().isoformat()


def variance(values):
    if len(values) < 2:
        return 0.0

    mean = sum(values) / len(values)

    return sum((x - mean) ** 2 for x in values) / (len(values) - 1)


def covariance(xs, ys):
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0

    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)

    return sum(
        (x - mean_x) * (y - mean_y)
        for x, y in zip(xs, ys)
    ) / (len(xs) - 1)


def correlation(xs, ys):
    var_x = variance(xs)
    var_y = variance(ys)

    if var_x == 0 or var_y == 0:
        return None

    return covariance(xs, ys) / ((var_x ** 0.5) * (var_y ** 0.5))


def calculate_cronbach_alpha(matrix):
    n = len(matrix)

    if n < 2:
        return None

    k = len(matrix[0])

    if k < 2:
        return None

    item_columns = list(zip(*matrix))

    item_variances = [
        variance(list(col))
        for col in item_columns
    ]

    total_scores = [
        sum(row)
        for row in matrix
    ]

    total_variance = variance(total_scores)

    if total_variance == 0:
        return None

    alpha = (k / (k - 1)) * (
        1 - (sum(item_variances) / total_variance)
    )

    return round(alpha, 4)


def calculate_citc(matrix, item_ids):
    results = {}

    if len(matrix) < 2:
        return {item_id: None for item_id in item_ids}

    for idx, item_id in enumerate(item_ids):
        item_scores = [
            row[idx]
            for row in matrix
        ]

        corrected_total_scores = [
            sum(row) - row[idx]
            for row in matrix
        ]

        citc = correlation(item_scores, corrected_total_scores)

        results[item_id] = None if citc is None else round(citc, 4)

    return results


def calculate_alpha_if_item_deleted(matrix, item_ids):
    results = {}

    if len(item_ids) <= 2:
        return {item_id: None for item_id in item_ids}

    for idx, item_id in enumerate(item_ids):
        reduced_matrix = [
            row[:idx] + row[idx + 1:]
            for row in matrix
        ]

        alpha = calculate_cronbach_alpha(reduced_matrix)

        results[item_id] = alpha

    return results


def build_response_score_matrix(db, survey_id):
    items = db.query(models.SurveyItem).filter_by(
        survey_id=survey_id,
        item_role="normal"
    ).order_by(models.SurveyItem.item_order).all()

    item_ids = [item.item_id for item in items]

    responses = db.query(models.Response).filter_by(
        survey_id=survey_id,
        is_completed=True
    ).all()

    response_feature_rows = db.query(models.ResponseFeature).filter_by(
        survey_id=survey_id
    ).all()

    compact_feature_by_response = {
        row.response_id: (row.compact_features or {})
        for row in response_feature_rows
    }

    matrix = []
    excluded_response_ids = []
    included_response_ids = []

    for response in responses:
        compact_features = compact_feature_by_response.get(response.response_id) or {}
        excluded, _ = should_exclude_from_statistics(compact_features)

        if excluded:
            excluded_response_ids.append(response.response_id)
            continue

        answers = db.query(models.ResponseAnswer).filter_by(
            survey_id=survey_id,
            response_id=response.response_id
        ).all()

        answer_map = {
            ans.item_id: ans.selected_score
            for ans in answers
            if ans.selected_score is not None
        }

        row = []
        valid = True

        for item_id in item_ids:
            if item_id not in answer_map:
                valid = False
                break

            row.append(float(answer_map[item_id]))

        if valid:
            matrix.append(row)
            included_response_ids.append(response.response_id)

    metadata = {
        "raw_response_count": len(responses),
        "excluded_response_count": len(excluded_response_ids),
        "included_response_count": len(included_response_ids),
        "excluded_response_ids": excluded_response_ids,
        "included_response_ids": included_response_ids,
    }

    return matrix, item_ids, metadata


def evaluate_survey_statistics(db, survey_id: str, overwrite: bool = True):
    matrix, item_ids, metadata = build_response_score_matrix(db, survey_id)

    if len(matrix) < 2:
        return {
            "survey_id": survey_id,
            "response_count": len(matrix),
            "raw_response_count": metadata.get("raw_response_count", 0),
            "excluded_response_count": metadata.get("excluded_response_count", 0),
            "item_count": len(item_ids),
            "error": "Cronbach alpha/CITC 계산에는 최소 2개 이상의 완성 응답이 필요합니다."
        }

    if len(item_ids) < 2:
        return {
            "survey_id": survey_id,
            "response_count": len(matrix),
            "item_count": len(item_ids),
            "error": "Cronbach alpha/CITC 계산에는 최소 2개 이상의 normal 문항이 필요합니다."
        }

    cronbach_alpha = calculate_cronbach_alpha(matrix)
    item_citc_results = calculate_citc(matrix, item_ids)
    alpha_if_item_deleted = calculate_alpha_if_item_deleted(matrix, item_ids)

    if overwrite:
        db.query(models.SurveyStatisticalEvaluation).filter_by(
            survey_id=survey_id
        ).delete()
        db.commit()

    db_eval = models.SurveyStatisticalEvaluation(
        survey_id=survey_id,
        response_count=len(matrix),
        cronbach_alpha=cronbach_alpha,
        item_citc_results=item_citc_results,
        alpha_if_item_deleted=alpha_if_item_deleted,
        created_at=now_str()
    )

    db.add(db_eval)
    db.commit()
    db.refresh(db_eval)

    return {
        "stat_eval_id": db_eval.stat_eval_id,
        "survey_id": survey_id,
        "response_count": len(matrix),
        "raw_response_count": metadata.get("raw_response_count", 0),
        "excluded_response_count": metadata.get("excluded_response_count", 0),
        "item_count": len(item_ids),
        "cronbach_alpha": cronbach_alpha,
        "item_citc_results": item_citc_results,
        "alpha_if_item_deleted": alpha_if_item_deleted,
        "message": "survey statistical evaluation created"
    }
