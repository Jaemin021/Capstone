# backend/routers/survey_evaluations.py

from datetime import datetime
from fastapi import APIRouter
from database import SessionLocal
import models

from services.survey_statistical_evaluation_service import evaluate_survey_statistics
from services.item_construct_evaluation_service import evaluate_construct_for_survey

from services.item_quality_dictionary import (
    AMBIGUOUS_TERMS,
    NEGATIVE_TERMS,
    LEADING_TERMS,
    DOUBLE_BARRELED_HINTS
)

from services.item_quality_llm_service import evaluate_item_with_llm
from services.item_quality_score_service import calculate_quality_score

router = APIRouter(prefix="/survey-evaluations")


def now_str():
    return datetime.now().isoformat()


def count_terms(text, dictionary):
    return sum(1 for w in dictionary if w in text)


def score_status(score, good=8.0, warning=6.0):
    if score is None:
        return "unknown"
    if score >= good:
        return "good"
    if score >= warning:
        return "warning"
    return "bad"


@router.post("/{survey_id}/quality")
def evaluate_quality(survey_id: str):
    db = SessionLocal()

    try:
        # 재평가 시 기존 품질 평가 결과 삭제
        db.query(models.ItemQualityEvaluation).filter_by(
            survey_id=survey_id
        ).delete()

        items = db.query(models.SurveyItem).filter_by(
            survey_id=survey_id,
            item_role="normal"
        ).order_by(models.SurveyItem.item_order).all()

        results = []

        for item in items:
            options = db.query(models.SurveyItemOption).filter_by(
                item_id=item.item_id
            ).order_by(models.SurveyItemOption.option_order).all()

            option_texts = [opt.option_label for opt in options]

            rule = {
                "ambiguous": count_terms(item.question_text, AMBIGUOUS_TERMS),
                "negative": count_terms(item.question_text, NEGATIVE_TERMS),
                "leading": count_terms(item.question_text, LEADING_TERMS),
                "double": count_terms(item.question_text, DOUBLE_BARRELED_HINTS),
            }

            llm_result = evaluate_item_with_llm(
                item.question_text,
                option_texts
            )

            score = calculate_quality_score(rule, llm_result)

            db_eval = models.ItemQualityEvaluation(
                survey_id=survey_id,
                item_id=item.item_id,
                quality_score=score,
                problem_categories=llm_result.get("problem_categories") if llm_result else None,
                detected_terms=llm_result.get("detected_terms") if llm_result else None,
                llm_comment=llm_result.get("llm_comment") if llm_result else None,
                suggested_rewrite=llm_result.get("suggested_rewrite") if llm_result else None,
                created_at=now_str()
            )

            db.add(db_eval)

            results.append({
                "item_id": item.item_id,
                "item_order": item.item_order,
                "question_text": item.question_text,
                "quality_score": score,
                "status": score_status(score),
                "problem_categories": db_eval.problem_categories,
                "detected_terms": db_eval.detected_terms,
                "llm_comment": db_eval.llm_comment,
                "suggested_rewrite": db_eval.suggested_rewrite
            })

        db.commit()

        return {
            "survey_id": survey_id,
            "results": results
        }

    finally:
        db.close()


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
            results.append({
                "item_id": item.item_id,
                "item_order": item.item_order,
                "question_text": item.question_text,
                "quality_score": eval_row.quality_score,
                "status": score_status(eval_row.quality_score),
                "problem_categories": eval_row.problem_categories,
                "detected_terms": eval_row.detected_terms,
                "llm_comment": eval_row.llm_comment,
                "suggested_rewrite": eval_row.suggested_rewrite,
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
        ).join(
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
            if eval_row.embedding_score is not None and eval_row.llm_score is not None:
                combined_score = round(
                    eval_row.embedding_score * 0.4 + eval_row.llm_score * 0.6,
                    3
                )

            results.append({
                "item_id": item.item_id,
                "item_order": item.item_order,
                "question_text": item.question_text,
                "embedding_features": eval_row.embedding_features,
                "embedding_score": eval_row.embedding_score,
                "llm_features": eval_row.llm_features,
                "llm_score": eval_row.llm_score,
                "combined_score": combined_score,
                "status": score_status(combined_score),
                "predicted_citc": eval_row.predicted_citc,
                "predicted_alpha_impact": eval_row.predicted_alpha_impact,
                "created_at": eval_row.created_at
            })

        return {
            "survey_id": survey_id,
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
            "cronbach_alpha": stat.cronbach_alpha,
            "alpha_status": score_status(stat.cronbach_alpha, good=0.7, warning=0.6),
            "items": item_results,
            "created_at": stat.created_at
        }

    finally:
        db.close()