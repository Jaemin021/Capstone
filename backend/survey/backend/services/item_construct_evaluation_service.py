# backend/services/item_construct_evaluation_service.py

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from types import SimpleNamespace
import models

from services.embedding_service import get_embedding
from services.item_construct_embedding_service import (
    build_construct_text,
    calculate_embedding_construct_features_from_vectors,
)
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


def _parse_construct_llm_worker_count():
    raw = os.getenv("CONSTRUCT_LLM_MAX_WORKERS", "4").strip()
    try:
        parsed = int(raw)
    except Exception:
        return 4
    return max(1, min(parsed, 8))


def _evaluate_single_construct_llm(target_item_snapshot, survey_snapshot, all_item_snapshots):
    target_item = SimpleNamespace(**target_item_snapshot)
    survey = SimpleNamespace(**survey_snapshot)
    normal_items = [SimpleNamespace(**row) for row in all_item_snapshots]

    try:
        llm_features = evaluate_llm_construct_features(
            target_item=target_item,
            survey=survey,
            normal_items=normal_items
        )
        llm_features = sanitize_construct_llm_features(llm_features)
        llm_score = calculate_llm_construct_score(llm_features)
        return {
            "item_id": target_item.item_id,
            "llm_features": llm_features,
            "llm_score": llm_score,
            "error": None,
        }
    except Exception as e:
        return {
            "item_id": target_item.item_id,
            "llm_features": None,
            "llm_score": None,
            "error": f"llm failed: {repr(e)}",
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

    item_snapshots = [
        {
            "item_id": item.item_id,
            "item_order": item.item_order,
            "question_text": item.question_text,
        }
        for item in normal_items
    ]
    survey_snapshot = {
        "title": survey.title,
        "construct_name": survey.construct_name,
        "construct_description": survey.construct_description,
    }

    item_vectors = {}
    construct_vec = None
    embedding_global_error = None

    try:
        for row in item_snapshots:
            item_vectors[row["item_id"]] = get_embedding(row["question_text"])
        construct_text = build_construct_text(survey, normal_items)
        construct_vec = get_embedding(construct_text)
    except Exception as e:
        embedding_global_error = f"embedding precompute failed: {repr(e)}"

    llm_result_map = {}
    max_workers = _parse_construct_llm_worker_count()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _evaluate_single_construct_llm,
                item_snapshot,
                survey_snapshot,
                item_snapshots,
            )
            for item_snapshot in item_snapshots
        ]
        for future in futures:
            row = future.result()
            llm_result_map[row["item_id"]] = row

    now = datetime.now().isoformat()

    if overwrite:
        db.query(models.ConstructEvaluation).filter_by(
            survey_id=survey_id,
        ).delete(synchronize_session=False)

    for item in normal_items:
        item_errors = []
        embedding_result = {
            "embedding_features": None,
            "embedding_score": None
        }

        if embedding_global_error is not None:
            item_errors.append(embedding_global_error)
        else:
            try:
                embedding_result = calculate_embedding_construct_features_from_vectors(
                    target_item_id=item.item_id,
                    item_vectors=item_vectors,
                    construct_vec=construct_vec,
                )
            except Exception as e:
                item_errors.append(f"embedding failed: {repr(e)}")

        llm_row = llm_result_map.get(item.item_id)
        llm_features = llm_row.get("llm_features") if llm_row else None
        llm_score = llm_row.get("llm_score") if llm_row else None
        if llm_row and llm_row.get("error"):
            item_errors.append(llm_row["error"])

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
            created_at=now
        )

        db.add(db_eval)
        db.flush()

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

    db.commit()

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
