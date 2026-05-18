# backend/services/item_construct_evaluation_service.py

from datetime import datetime
import models

from services.item_construct_embedding_service import evaluate_embedding_construct_features
from services.item_construct_llm_service import (
    evaluate_llm_construct_features,
    calculate_llm_construct_score
)


def sanitize_construct_llm_features(llm_features):
    if not isinstance(llm_features, dict):
        return None

    allowed_keys = [
        "construct_fit",
        "semantic_consistency",
        "redundancy_risk",
        "off_construct_risk",
        "expected_citc_direction",
    ]

    return {
        key: llm_features.get(key)
        for key in allowed_keys
    }


def evaluate_construct_for_survey(db, survey_id: str, overwrite: bool = True):
    survey = db.query(models.Survey).filter_by(survey_id=survey_id).first()

    if survey is None:
        return {"error": "survey not found"}

    normal_items = db.query(models.SurveyItem).filter_by(
        survey_id=survey_id,
        item_role="normal"
    ).order_by(models.SurveyItem.item_order).all()

    results = []
    debug_errors = []

    for item in normal_items:
        if overwrite:
            old_eval = db.query(models.ConstructEvaluation).filter_by(
                survey_id=survey_id,
                item_id=item.item_id
            ).first()

            if old_eval is not None:
                db.delete(old_eval)
                db.commit()

        item_errors = []
        embedding_result = {
            "embedding_features": None,
            "embedding_score": None
        }
        llm_features = None
        llm_score = None

        try:
            embedding_result = evaluate_embedding_construct_features(
                target_item=item,
                survey=survey,
                normal_items=normal_items
            )
        except Exception as e:
            item_errors.append(f"embedding failed: {repr(e)}")

        try:
            llm_features = evaluate_llm_construct_features(
                target_item=item,
                survey=survey,
                normal_items=normal_items
            )
            llm_features = sanitize_construct_llm_features(llm_features)
            llm_score = calculate_llm_construct_score(llm_features)
        except Exception as e:
            item_errors.append(f"llm failed: {repr(e)}")

        if item_errors:
            debug_errors.append({
                "item_id": item.item_id,
                "item_order": item.item_order,
                "errors": item_errors
            })

        db_eval = models.ConstructEvaluation(
            survey_id=survey_id,
            item_id=item.item_id,
            embedding_features=embedding_result["embedding_features"],
            embedding_score=embedding_result["embedding_score"],
            llm_features=llm_features,
            llm_score=llm_score,
            predicted_citc=None,
            predicted_alpha_impact=None,
            created_at=datetime.now().isoformat()
        )

        db.add(db_eval)
        db.commit()
        db.refresh(db_eval)

        results.append({
            "construct_eval_id": db_eval.construct_eval_id,
            "item_id": item.item_id,
            "item_order": item.item_order,
            "question_text": item.question_text,
            "embedding_features": embedding_result["embedding_features"],
            "embedding_score": embedding_result["embedding_score"],
            "llm_features": sanitize_construct_llm_features(llm_features),
            "llm_score": llm_score,
            "predicted_citc": None,
            "errors": item_errors if item_errors else None
        })

    response = {
        "survey_id": survey_id,
        "item_count": len(results),
        "results": results,
        "message": "construct evaluation created"
    }

    if debug_errors:
        response["debug"] = {
            "errors": debug_errors
        }

    return response
