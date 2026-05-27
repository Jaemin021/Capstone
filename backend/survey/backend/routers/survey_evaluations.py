# backend/routers/survey_evaluations.py

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import re
from fastapi import APIRouter
from database import SessionLocal
import models

from services.survey_statistical_evaluation_service import (
    evaluate_survey_statistics,
    build_response_score_matrix,
)
from services.item_construct_evaluation_service import (
    evaluate_construct_for_survey,
    sanitize_construct_llm_features,
)

from services.item_quality_llm_service import (
    evaluate_item_with_llm,
    generate_rewrite_with_llm,
)
from services.item_quality_score_service import calculate_quality_score

router = APIRouter(prefix="/survey-evaluations")
SUGGESTED_REWRITE_THRESHOLD = 6.0
RISK_STATUS_FOR_REWRITE = {"warning", "bad"}
TERM_REPLACEMENTS = {
    "자주": "지난 2주 동안 주 3회 이상",
    "가끔": "지난 2주 동안 주 1~2회",
    "보통": "중간 수준(주 2~3회)",
    "대체로": "대부분의 경우",
    "적당히": "명확한 기준에 맞게",
    "충분히": "기준을 충족할 만큼",
    "조금": "낮은 수준으로",
    "많이": "높은 수준으로",
}


def now_str():
    return datetime.now().isoformat()


def score_status(score, good=8.0, warning=6.0):
    if score is None:
        return "unknown"
    if score >= good:
        return "good"
    if score >= warning:
        return "warning"
    return "bad"


def _has_text(value):
    return isinstance(value, str) and value.strip() != ""


def _needs_suggested_rewrite(score, status):
    return (
        isinstance(score, (int, float))
        and score < SUGGESTED_REWRITE_THRESHOLD
    ) or status in RISK_STATUS_FOR_REWRITE


def _replace_detected_terms(text, detected_terms):
    rewritten = text
    for term in (detected_terms or []):
        key = str(term).strip()
        if not key:
            continue
        replacement = TERM_REPLACEMENTS.get(key)
        if replacement and key in rewritten:
            rewritten = rewritten.replace(key, replacement, 1)
    return rewritten


def build_fallback_rewrite(question_text, problem_categories, detected_terms):
    base_question = (question_text or "").strip()
    if not base_question:
        return ""

    categories = set(problem_categories or [])
    normalized = re.sub(r"\s+", " ", base_question).strip()
    normalized = re.sub(r"[.?!]+$", "", normalized).strip()
    normalized = _replace_detected_terms(normalized, detected_terms)

    if "double_barreled" in categories or "single_concept_issue" in categories:
        normalized = re.split(r"(그리고|및|또는|거나)", normalized, maxsplit=1)[0].strip()

    prefix = ""
    if "ambiguous_time" in categories or "answerability_issue" in categories:
        prefix = "지난 2주 동안, "

    proposal = f"{prefix}{normalized}".strip()
    if proposal and proposal[-1] not in ["?", "."]:
        proposal = proposal + "?"

    return proposal


def _parse_quality_worker_count():
    raw = os.getenv("QUALITY_LLM_MAX_WORKERS", "6").strip()
    try:
        parsed = int(raw)
    except Exception:
        return 6
    return max(1, min(parsed, 12))


def _evaluate_single_quality_item(survey_id: str, item_snapshot: dict):
    question_text = item_snapshot["question_text"]
    llm_result = None
    llm_error = None

    try:
        llm_result = evaluate_item_with_llm(
            question_text,
            item_snapshot["option_texts"]
        )
    except Exception as error:
        llm_error = repr(error)

    score = calculate_quality_score(llm_result, options=item_snapshot.get("option_texts"))
    problem_categories = llm_result.get("problem_categories") if isinstance(llm_result, dict) else None
    detected_terms = llm_result.get("detected_terms") if isinstance(llm_result, dict) else None
    llm_comment = llm_result.get("llm_comment") if isinstance(llm_result, dict) else None
    suggested_rewrite = llm_result.get("suggested_rewrite") if isinstance(llm_result, dict) else None
    status = score_status(score)

    if _needs_suggested_rewrite(score, status) and not _has_text(suggested_rewrite):
        try:
            suggested_rewrite = generate_rewrite_with_llm(
                question_text=question_text,
                options=item_snapshot.get("option_texts"),
                problem_categories=problem_categories,
                detected_terms=detected_terms,
                llm_comment=llm_comment,
            )
        except Exception:
            suggested_rewrite = ""

    if _needs_suggested_rewrite(score, status) and not _has_text(suggested_rewrite):
        suggested_rewrite = build_fallback_rewrite(
            question_text=question_text,
            problem_categories=problem_categories,
            detected_terms=detected_terms,
        )

    if not _needs_suggested_rewrite(score, status):
        suggested_rewrite = ""

    eval_row = {
        "survey_id": survey_id,
        "item_id": item_snapshot["item_id"],
        "quality_score": score,
        "problem_categories": problem_categories,
        "detected_terms": detected_terms,
        "llm_comment": llm_comment,
        "suggested_rewrite": suggested_rewrite,
        "created_at": now_str(),
    }
    result_row = {
        "item_id": item_snapshot["item_id"],
        "item_order": item_snapshot["item_order"],
        "question_text": question_text,
        "quality_score": score,
        "status": status,
        "problem_categories": problem_categories,
        "detected_terms": detected_terms,
        "llm_comment": llm_comment,
        "suggested_rewrite": suggested_rewrite,
        "llm_error": llm_error
    }
    debug_error = None
    if llm_error:
        debug_error = {
            "item_id": item_snapshot["item_id"],
            "item_order": item_snapshot["item_order"],
            "error": llm_error
        }

    return {
        "item_order": item_snapshot["item_order"],
        "result_row": result_row,
        "eval_row": eval_row,
        "debug_error": debug_error,
    }


def _evaluate_quality_without_long_db_lock(survey_id: str):
    db = SessionLocal()

    try:
        items = db.query(models.SurveyItem).filter_by(
            survey_id=survey_id,
            item_role="normal"
        ).order_by(models.SurveyItem.item_order).all()

        item_snapshots = []

        for item in items:
            options = db.query(models.SurveyItemOption).filter_by(
                item_id=item.item_id
            ).order_by(models.SurveyItemOption.option_order).all()

            item_snapshots.append({
                "item_id": item.item_id,
                "item_order": item.item_order,
                "question_text": item.question_text,
                "option_texts": [opt.option_label for opt in options],
            })

    finally:
        db.close()

    results = []
    eval_rows = []
    debug_errors = []

    max_workers = _parse_quality_worker_count()
    worker_results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_evaluate_single_quality_item, survey_id, item_snapshot)
            for item_snapshot in item_snapshots
        ]

        for future in futures:
            worker_results.append(future.result())

    worker_results.sort(key=lambda row: row["item_order"])

    for worker_row in worker_results:
        results.append(worker_row["result_row"])
        eval_rows.append(worker_row["eval_row"])
        if worker_row["debug_error"] is not None:
            debug_errors.append(worker_row["debug_error"])

    db = SessionLocal()

    try:
        db.query(models.ItemQualityEvaluation).filter_by(
            survey_id=survey_id
        ).delete(synchronize_session=False)

        for eval_row in eval_rows:
            db.add(models.ItemQualityEvaluation(**eval_row))

        db.commit()

        response = {
            "survey_id": survey_id,
            "results": results
        }
        if debug_errors:
            response["debug"] = {
                "errors": debug_errors
            }
        return response

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@router.post("/{survey_id}/quality")
def evaluate_quality(survey_id: str):
    return _evaluate_quality_without_long_db_lock(survey_id)


@router.get("/{survey_id}/quality")
def get_quality_results(survey_id: str):
    db = SessionLocal()

    try:
        rows = db.query(
            models.SurveyItem,
            models.ItemQualityEvaluation
        ).join(
            models.ItemQualityEvaluation,
            models.SurveyItem.item_id == models.ItemQualityEvaluation.item_id
        ).filter(
            models.SurveyItem.survey_id == survey_id,
            models.SurveyItem.item_role == "normal"
        ).order_by(
            models.SurveyItem.item_order
        ).all()

        results = []

        for item, eval_row in rows:
            score = eval_row.quality_score
            status = score_status(score)
            results.append({
                "item_id": item.item_id,
                "item_order": item.item_order,
                "question_text": item.question_text,
                "quality_score": score,
                "status": status,
                "problem_categories": eval_row.problem_categories,
                "detected_terms": eval_row.detected_terms,
                "llm_comment": eval_row.llm_comment,
                "suggested_rewrite": (
                    eval_row.suggested_rewrite
                    if _needs_suggested_rewrite(score, status)
                    else ""
                ),
                "created_at": eval_row.created_at
            })

        return {
            "survey_id": survey_id,
            "results": results
        }

    finally:
        db.close()


@router.post("/{survey_id}/construct")
def evaluate_construct(survey_id: str):
    db = SessionLocal()

    try:
        result = evaluate_construct_for_survey(
            db=db,
            survey_id=survey_id,
            overwrite=True
        )
        return result

    finally:
        db.close()


@router.get("/{survey_id}/construct")
def get_construct_results(survey_id: str):
    db = SessionLocal()

    try:
        rows = db.query(
            models.SurveyItem,
            models.ConstructEvaluation
        ).outerjoin(
            models.ConstructEvaluation,
            models.SurveyItem.item_id == models.ConstructEvaluation.item_id
        ).filter(
            models.SurveyItem.survey_id == survey_id,
            models.SurveyItem.item_role == "normal"
        ).order_by(
            models.SurveyItem.item_order
        ).all()

        results = []

        for item, eval_row in rows:
            combined_score = None
            if (
                eval_row is not None
                and eval_row.embedding_score is not None
                and eval_row.llm_score is not None
            ):
                combined_score = round(
                    eval_row.embedding_score * 0.4 + eval_row.llm_score * 0.6,
                    3
                )

            results.append({
                "item_id": item.item_id,
                "item_order": item.item_order,
                "question_text": item.question_text,
                "embedding_features": eval_row.embedding_features if eval_row else None,
                "embedding_score": eval_row.embedding_score if eval_row else None,
                "llm_features": sanitize_construct_llm_features(eval_row.llm_features) if eval_row else None,
                "llm_score": eval_row.llm_score if eval_row else None,
                "combined_score": combined_score,
                "status": score_status(combined_score),
                "predicted_citc": eval_row.predicted_citc if eval_row else None,
                "predicted_alpha_impact": eval_row.predicted_alpha_impact if eval_row else None,
                "created_at": eval_row.created_at if eval_row else None
            })

        return {
            "survey_id": survey_id,
            "item_count": len(results),
            "results": results
        }

    finally:
        db.close()


@router.post("/{survey_id}/statistics")
def evaluate_statistics(survey_id: str):
    db = SessionLocal()

    try:
        result = evaluate_survey_statistics(
            db=db,
            survey_id=survey_id,
            overwrite=True
        )
        return result

    finally:
        db.close()


@router.get("/{survey_id}/statistics")
def get_statistics_results(survey_id: str):
    db = SessionLocal()

    try:
        stat = db.query(models.SurveyStatisticalEvaluation).filter_by(
            survey_id=survey_id
        ).order_by(
            models.SurveyStatisticalEvaluation.created_at.desc()
        ).first()

        if not stat:
            return {
                "survey_id": survey_id,
                "result": None,
                "message": "No statistical evaluation found."
            }

        _, _, sample_metadata = build_response_score_matrix(db, survey_id)

        normal_items = db.query(models.SurveyItem).filter_by(
            survey_id=survey_id,
            item_role="normal"
        ).order_by(models.SurveyItem.item_order).all()

        item_map = {
            item.item_id: {
                "item_id": item.item_id,
                "item_order": item.item_order,
                "question_text": item.question_text
            }
            for item in normal_items
        }

        item_results = []

        citc_results = stat.item_citc_results or {}
        alpha_deleted = stat.alpha_if_item_deleted or {}

        for item_id, item_info in item_map.items():
            citc = citc_results.get(item_id)
            alpha_if_deleted = alpha_deleted.get(item_id)

            item_results.append({
                **item_info,
                "citc": citc,
                "citc_status": score_status(citc, good=0.4, warning=0.2),
                "alpha_if_item_deleted": alpha_if_deleted
            })

        return {
            "survey_id": survey_id,
            "response_count": stat.response_count,
            "raw_response_count": sample_metadata.get("raw_response_count", stat.response_count),
            "excluded_response_count": sample_metadata.get("excluded_response_count", 0),
            "cronbach_alpha": stat.cronbach_alpha,
            "alpha_status": score_status(stat.cronbach_alpha, good=0.7, warning=0.6),
            "items": item_results,
            "created_at": stat.created_at
        }

    finally:
        db.close()
