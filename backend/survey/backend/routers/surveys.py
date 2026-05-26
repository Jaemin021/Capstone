# backend/routers/surveys.py

import csv
import io
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from database import SessionLocal
import models
import schemas

from services.llm_validation_item_service import generate_validation_plan_with_llm

from services.feature_service import (
    calculate_log_features,
    calculate_content_features,
    calculate_relation_features,
    build_compact_features,
    calculate_reliability_summary,
    resolve_binary_reliability_status,
)
from services.population_feature_service import calculate_population_features


router = APIRouter(prefix="/surveys")
POPULATION_REFRESH_BATCH_SIZE = 10


def generate_access_key():
    return uuid.uuid4().hex


def now_iso():
    return datetime.now().isoformat()


def _safe_float_or_empty(value):
    try:
        if value is None:
            return ""
        return float(value)
    except Exception:
        return ""


def _json_text(value):
    return json.dumps(value, ensure_ascii=False) if value is not None else ""


def _score_status(score, good=8.0, warning=6.0):
    if score is None:
        return "unknown"

    try:
        numeric = float(score)
    except Exception:
        return "unknown"

    if numeric >= good:
        return "good"
    if numeric >= warning:
        return "warning"
    return "bad"


def _refresh_population_features_for_survey(db, survey_id: str):
    responses = db.query(models.Response).filter_by(
        survey_id=survey_id,
        is_completed=True
    ).all()

    updated_count = 0

    for response in responses:
        db_feature = db.query(models.ResponseFeature).filter_by(
            response_id=response.response_id
        ).first()

        if db_feature is None:
            continue

        population_features = calculate_population_features(
            db=db,
            survey_id=survey_id,
            response_id=response.response_id
        )

        compact_features = build_compact_features(
            log_f=db_feature.log_features or {},
            content_f=db_feature.content_features or {},
            relation_f=db_feature.relation_features or {},
            population_f=population_features
        )

        db_feature.population_features = population_features
        db_feature.compact_features = compact_features
        updated_count += 1

    db.commit()
    return updated_count


def normalize_item_category(value):
    if value is None:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    tokens = []
    seen = set()
    for token in raw.split("/"):
        normalized = token.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        tokens.append(normalized)

    if not tokens:
        return None

    return " / ".join(tokens)


def get_survey_by_access_key(db, access_key: str):
    return db.query(models.Survey).filter_by(
        external_survey_key=access_key
    ).first()


def get_public_invite_by_key(db, invite_key: str):
    return db.query(models.PublicSurveyInvite).filter_by(
        invite_key=invite_key
    ).first()


def ensure_public_device_id(device_id: str):
    value = (device_id or "").strip()

    if len(value) < 8:
        raise HTTPException(status_code=400, detail="device_id is too short")

    if len(value) > 128:
        raise HTTPException(status_code=400, detail="device_id is too long")

    return value


def build_survey_response(db, survey):
    items = db.query(models.SurveyItem).filter_by(
        survey_id=survey.survey_id
    ).order_by(models.SurveyItem.item_order).all()

    result = {
        "survey_id": survey.survey_id,
        "title": survey.title,
        "description": survey.description,
        "construct_name": survey.construct_name,
        "construct_description": survey.construct_description,
        "status": survey.status,
        "items": []
    }

    for item in items:
        options = db.query(models.SurveyItemOption).filter_by(
            item_id=item.item_id
        ).order_by(models.SurveyItemOption.option_order).all()

        result["items"].append({
            "item_id": item.item_id,
            "item_order": item.item_order,
            "question_text": item.question_text,
            "item_category": item.item_category,
            "question_type": item.question_type,
            "item_role": item.item_role,
            "is_generated": item.is_generated,
            "source_item_id": item.source_item_id,
            "trap_correct_option_order": item.trap_correct_option_order,
            "reverse_expected_rule": item.reverse_expected_rule,
            "options": [
                {
                    "option_id": opt.option_id,
                    "option_order": opt.option_order,
                    "option_label": opt.option_label,
                    "option_score": opt.option_score
                }
                for opt in options
            ]
        })

    return result


def create_response_and_features(db, survey_id: str, response: schemas.ResponseCreate):
    db_res = models.Response(
        survey_id=survey_id,
        respondent_id=response.respondent_id,
        started_at=response.started_at,
        submitted_at=response.submitted_at,
        is_completed=response.is_completed,
        label=response.label
    )
    db.add(db_res)
    db.commit()
    db.refresh(db_res)

    response_id = db_res.response_id

    for ans in response.answers:
        selected_score = (
            ans.selected_score
            if ans.selected_score is not None
            else ans.selected_option_order
        )

        db_answer = models.ResponseAnswer(
            response_id=response_id,
            survey_id=survey_id,
            item_id=ans.item_id,
            selected_option_id=ans.selected_option_id,
            selected_option_order=ans.selected_option_order,
            selected_score=selected_score,
            answer_text=ans.answer_text,
            answered_at=ans.answered_at
        )
        db.add(db_answer)

    db_log = models.ResponseLog(
        response_id=response_id,
        survey_id=survey_id,
        started_at=response.log.started_at,
        submitted_at=response.log.submitted_at,
        total_time_ms=response.log.total_time_ms,
        total_touch_count=response.log.total_touch_count,
        connection_lost=response.log.connection_lost,
        offline_count=response.log.offline_count,
        offline_total_ms=response.log.offline_total_ms
    )
    db.add(db_log)

    for il in response.log.item_logs:
        db_item_log = models.ResponseItemLog(
            response_id=response_id,
            survey_id=survey_id,
            item_id=il.item_id,
            checked_at=il.checked_at,
            previous_checked_at=il.previous_checked_at,
            entered_at=il.entered_at,
            first_selected_at=il.first_selected_at,
            last_selected_at=il.last_selected_at,
            last_exited_at=il.last_exited_at,
            item_time_ms=il.item_time_ms,
            time_share=il.time_share,
            time_to_first_answer_ms=il.time_to_first_answer_ms,
            time_after_last_answer_ms=il.time_after_last_answer_ms,
            touch_count=il.touch_count,
            change_count=il.change_count,
            visit_count=il.visit_count,
            back_visit_count=il.back_visit_count,
            is_revisited=il.is_revisited,
            initial_visit_time_ms=il.initial_visit_time_ms,
            revisit_time_ms=il.revisit_time_ms,
            answer_changed=il.answer_changed,
            changed_after_revisit=il.changed_after_revisit,
            first_selected_option_order=il.first_selected_option_order,
            final_selected_option_order=il.final_selected_option_order
        )
        db.add(db_item_log)

    for event in response.log.connection_events:
        db_event = models.ConnectionEvent(
            response_id=response_id,
            survey_id=survey_id,
            event_type=event.event_type,
            timestamp=event.timestamp
        )
        db.add(db_event)

    db.commit()

    saved_answers = db.query(models.ResponseAnswer).filter_by(
        response_id=response_id
    ).all()

    survey_items = db.query(models.SurveyItem).filter_by(
        survey_id=survey_id
    ).all()

    saved_item_logs = db.query(models.ResponseItemLog).filter_by(
        response_id=response_id
    ).all()

    saved_connection_events = db.query(models.ConnectionEvent).filter_by(
        response_id=response_id
    ).all()

    log_features = calculate_log_features(
        response_log=db_log,
        item_logs=saved_item_logs,
        connection_events=saved_connection_events
    )

    content_features = calculate_content_features(
        answers=saved_answers,
        survey_items=survey_items
    )

    relation_features = calculate_relation_features(
        answers=saved_answers,
        survey_items=survey_items
    )

    population_features = calculate_population_features(
        db=db,
        survey_id=survey_id,
        response_id=response_id
    )

    compact_features = build_compact_features(
        log_f=log_features,
        content_f=content_features,
        relation_f=relation_features,
        population_f=population_features
    )

    db_feature = models.ResponseFeature(
        response_id=response_id,
        survey_id=survey_id,
        log_features=log_features,
        content_features=content_features,
        population_features=population_features,
        relation_features=relation_features,
        compact_features=compact_features,
        created_at=response.submitted_at
    )

    db.add(db_feature)
    db.commit()
    db.refresh(db_feature)

    population_refresh = {
        "triggered": False,
        "batch_size": POPULATION_REFRESH_BATCH_SIZE,
        "completed_response_count": None,
        "updated_count": 0,
    }

    if bool(response.is_completed):
        completed_response_count = db.query(models.Response).filter_by(
            survey_id=survey_id,
            is_completed=True
        ).count()
        population_refresh["completed_response_count"] = completed_response_count

        if (
            completed_response_count > 0
            and completed_response_count % POPULATION_REFRESH_BATCH_SIZE == 0
        ):
            updated_count = _refresh_population_features_for_survey(
                db=db,
                survey_id=survey_id
            )
            population_refresh["triggered"] = True
            population_refresh["updated_count"] = updated_count

            refreshed_feature = db.query(models.ResponseFeature).filter_by(
                response_id=response_id
            ).first()
            if refreshed_feature is not None:
                compact_features = refreshed_feature.compact_features or compact_features
                population_features = refreshed_feature.population_features or population_features

    return {
        "response_id": response_id,
        "survey_id": survey_id,
        "response_feature_id": db_feature.response_feature_id,
        "log_features": log_features,
        "content_features": content_features,
        "population_features": population_features,
        "relation_features": relation_features,
        "features": compact_features,
        "reliability": calculate_reliability_summary(compact_features),
        "population_refresh": population_refresh,
        "message": "response and features created"
    }


@router.get("/")
def list_surveys():
    db = SessionLocal()

    try:
        surveys = db.query(models.Survey).order_by(models.Survey.title).all()

        results = []

        for survey in surveys:
            item_count = db.query(models.SurveyItem).filter_by(
                survey_id=survey.survey_id
            ).count()

            normal_item_count = db.query(models.SurveyItem).filter_by(
                survey_id=survey.survey_id,
                item_role="normal"
            ).count()

            response_count = db.query(models.Response).filter_by(
                survey_id=survey.survey_id,
                is_completed=True
            ).count()

            last_response = db.query(models.Response).filter_by(
                survey_id=survey.survey_id,
                is_completed=True
            ).order_by(
                models.Response.submitted_at.desc()
            ).first()

            results.append({
                "survey_id": survey.survey_id,
                "title": survey.title,
                "description": survey.description,
                "construct_name": survey.construct_name,
                "construct_description": survey.construct_description,
                "status": survey.status,
                "item_count": item_count,
                "normal_item_count": normal_item_count,
                "response_count": response_count,
                "last_response_at": last_response.submitted_at if last_response else None
            })

        return {
            "surveys": results
        }

    finally:
        db.close()


@router.post("/")
def create_survey(survey: schemas.SurveyCreate):
    db = SessionLocal()

    db_survey = models.Survey(
        title=survey.title,
        description=survey.description,
        construct_name=survey.construct_name,
        construct_description=survey.construct_description
    )
    db.add(db_survey)
    db.commit()
    db.refresh(db_survey)

    survey_id = db_survey.survey_id
    created_items = []

    # -----------------------------
    # 1. 원본 문항 저장
    # -----------------------------
    for item in survey.items:
        db_item = models.SurveyItem(
            survey_id=survey_id,
            item_order=item.item_order,
            question_text=item.question_text,
            item_category=normalize_item_category(item.item_category),
            question_type=item.question_type,
            is_required=item.is_required,
            item_role="normal",
            is_generated=False,
            source_item_id=None,
            trap_correct_option_order=None,
            reverse_expected_rule=None
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)

        created_options = []

        if item.options:
            for opt in item.options:
                db_option = models.SurveyItemOption(
                    item_id=db_item.item_id,
                    option_order=opt.option_order,
                    option_label=opt.option_label,
                    option_score=opt.option_order
                )
                db.add(db_option)
                db.commit()
                db.refresh(db_option)

                created_options.append({
                    "option_id": db_option.option_id,
                    "option_order": db_option.option_order,
                    "option_label": db_option.option_label,
                    "option_score": db_option.option_score
                })

        created_items.append({
            "item_id": db_item.item_id,
            "item_order": db_item.item_order,
            "question_text": db_item.question_text,
            "item_category": db_item.item_category,
            "question_type": db_item.question_type,
            "item_role": "normal",
            "is_generated": False,
            "source_item_id": None,
            "trap_correct_option_order": None,
            "reverse_expected_rule": None,
            "insert_after_index": None,
            "options": created_options
        })

    # -----------------------------
    # 2. LLM 기반 검증문항 생성
    # -----------------------------
    if survey.enable_validation_items:
        original_items = [
            item for item in created_items
            if item["item_role"] == "normal"
        ]

        llm_input = {
            "title": survey.title,
            "items": [
                {
                    "index": i,
                    "question_text": item["question_text"],
                    "options": item["options"]
                }
                for i, item in enumerate(original_items)
            ]
        }

        plan = generate_validation_plan_with_llm(llm_input)

        next_order = len(created_items) + 1

        # -----------------------------
        # 2-1. 역문항 생성
        # -----------------------------
        for rev in plan.get("reverse_items", []):
            source_index = rev.get("source_index")

            if source_index is None or source_index < 0 or source_index >= len(original_items):
                continue

            source = original_items[source_index]

            db_item = models.SurveyItem(
                survey_id=survey_id,
                item_order=next_order,
                question_text=rev["question_text"],
                item_category=source.get("item_category"),
                question_type="likert_5",
                is_required=True,
                item_role="reverse",
                is_generated=True,
                source_item_id=source["item_id"],
                trap_correct_option_order=None,
                reverse_expected_rule="opposite_likert_5"
            )
            db.add(db_item)
            db.commit()
            db.refresh(db_item)

            created_options = []

            for opt in source["options"]:
                db_option = models.SurveyItemOption(
                    item_id=db_item.item_id,
                    option_order=opt["option_order"],
                    option_label=opt["option_label"],
                    option_score=opt["option_order"]
                )
                db.add(db_option)
                db.commit()
                db.refresh(db_option)

                created_options.append({
                    "option_id": db_option.option_id,
                    "option_order": db_option.option_order,
                    "option_label": db_option.option_label,
                    "option_score": db_option.option_score
                })

            created_items.append({
                "item_id": db_item.item_id,
                "item_order": db_item.item_order,
                "question_text": db_item.question_text,
                "item_category": db_item.item_category,
                "question_type": db_item.question_type,
                "item_role": db_item.item_role,
                "is_generated": db_item.is_generated,
                "source_item_id": db_item.source_item_id,
                "trap_correct_option_order": db_item.trap_correct_option_order,
                "reverse_expected_rule": db_item.reverse_expected_rule,
                "insert_after_index": rev.get("insert_after_index"),
                "options": created_options
            })

            next_order += 1

        # -----------------------------
        # 2-2. 함정문항 생성
        # -----------------------------
        for trap in plan.get("trap_items", []):
            base_item = original_items[0]

            correct_option_order = trap.get("correct_option_order", 2)

            correct_opt = next(
                (
                    opt for opt in base_item["options"]
                    if opt["option_order"] == correct_option_order
                ),
                None
            )

            if correct_opt is None:
                correct_option_order = 2
                correct_opt = next(
                    opt for opt in base_item["options"]
                    if opt["option_order"] == correct_option_order
                )

            question_text = f"응답 품질 확인을 위해 '{correct_opt['option_label']}'을 선택해 주세요."

            db_item = models.SurveyItem(
                survey_id=survey_id,
                item_order=next_order,
                question_text=question_text,
                item_category=base_item.get("item_category"),
                question_type="likert_5",
                is_required=True,
                item_role="trap",
                is_generated=True,
                source_item_id=None,
                trap_correct_option_order=correct_option_order,
                reverse_expected_rule=None
            )
            db.add(db_item)
            db.commit()
            db.refresh(db_item)

            created_options = []

            for opt in base_item["options"]:
                db_option = models.SurveyItemOption(
                    item_id=db_item.item_id,
                    option_order=opt["option_order"],
                    option_label=opt["option_label"],
                    option_score=opt["option_order"]
                )
                db.add(db_option)
                db.commit()
                db.refresh(db_option)

                created_options.append({
                    "option_id": db_option.option_id,
                    "option_order": db_option.option_order,
                    "option_label": db_option.option_label,
                    "option_score": db_option.option_score
                })

            created_items.append({
                "item_id": db_item.item_id,
                "item_order": db_item.item_order,
                "question_text": db_item.question_text,
                "item_category": db_item.item_category,
                "question_type": db_item.question_type,
                "item_role": db_item.item_role,
                "is_generated": db_item.is_generated,
                "source_item_id": db_item.source_item_id,
                "trap_correct_option_order": db_item.trap_correct_option_order,
                "reverse_expected_rule": db_item.reverse_expected_rule,
                "insert_after_index": trap.get("insert_after_index"),
                "options": created_options
            })

            next_order += 1

    # -----------------------------
    # 3. insert_after_index 기반 문항 순서 재정렬
    # -----------------------------
    created_items = reorder_validation_items(created_items)

    for order, item in enumerate(created_items, start=1):
        item["item_order"] = order

        db_item = db.query(models.SurveyItem).filter_by(
            item_id=item["item_id"]
        ).first()

        if db_item is not None:
            db_item.item_order = order

    db.commit()

    result = {
        "survey_id": survey_id,
        "title": db_survey.title,
        "description": db_survey.description,
        "construct_name": db_survey.construct_name,
        "construct_description": db_survey.construct_description,
        "status": db_survey.status,
        "items": created_items,
        "message": "survey created"
    }

    db.close()
    return result


@router.post("/{survey_id}/duplicate")
def duplicate_survey(survey_id: str):
    db = SessionLocal()

    try:
        source_survey = db.query(models.Survey).filter_by(survey_id=survey_id).first()
        if source_survey is None:
            raise HTTPException(status_code=404, detail="survey not found")

        copied_title = f"{source_survey.title} (복사본)"
        copied_survey = models.Survey(
            title=copied_title,
            description=source_survey.description,
            construct_name=source_survey.construct_name,
            construct_description=source_survey.construct_description,
            status="draft",
        )
        db.add(copied_survey)
        db.commit()
        db.refresh(copied_survey)

        source_items = db.query(models.SurveyItem).filter_by(
            survey_id=survey_id
        ).order_by(models.SurveyItem.item_order.asc()).all()

        source_options_by_item = {}
        if source_items:
            source_item_ids = [item.item_id for item in source_items]
            source_options = db.query(models.SurveyItemOption).filter(
                models.SurveyItemOption.item_id.in_(source_item_ids)
            ).order_by(
                models.SurveyItemOption.item_id.asc(),
                models.SurveyItemOption.option_order.asc(),
            ).all()

            for option in source_options:
                source_options_by_item.setdefault(option.item_id, []).append(option)

        item_id_map = {}
        copied_items_by_source = {}

        # 1) 문항 자체를 먼저 모두 복사
        for source_item in source_items:
            copied_item = models.SurveyItem(
                survey_id=copied_survey.survey_id,
                item_order=source_item.item_order,
                question_text=source_item.question_text,
                item_category=normalize_item_category(source_item.item_category),
                question_type=source_item.question_type,
                is_required=source_item.is_required,
                item_role=source_item.item_role,
                is_generated=source_item.is_generated,
                source_item_id=None,
                trap_correct_option_order=source_item.trap_correct_option_order,
                reverse_expected_rule=source_item.reverse_expected_rule,
            )
            db.add(copied_item)
            db.flush()

            item_id_map[source_item.item_id] = copied_item.item_id
            copied_items_by_source[source_item.item_id] = copied_item

        # 2) 역문항 source_item_id 참조를 새 item_id로 연결
        for source_item in source_items:
            if source_item.source_item_id is None:
                continue

            copied_item = copied_items_by_source.get(source_item.item_id)
            mapped_source_item_id = item_id_map.get(source_item.source_item_id)

            if copied_item is not None:
                copied_item.source_item_id = mapped_source_item_id

        # 3) 보기 복사
        for source_item in source_items:
            copied_item = copied_items_by_source.get(source_item.item_id)
            if copied_item is None:
                continue

            for source_option in source_options_by_item.get(source_item.item_id, []):
                copied_option = models.SurveyItemOption(
                    item_id=copied_item.item_id,
                    option_order=source_option.option_order,
                    option_label=source_option.option_label,
                    option_score=source_option.option_score,
                )
                db.add(copied_option)

        db.commit()
        db.refresh(copied_survey)

        result = build_survey_response(db, copied_survey)
        result["message"] = "survey duplicated"
        result["source_survey_id"] = source_survey.survey_id
        return result

    finally:
        db.close()


def reorder_validation_items(created_items):
    original_items = [
        item for item in created_items
        if item.get("item_role") == "normal"
    ]

    generated_items = [
        item for item in created_items
        if item.get("item_role") in ["reverse", "trap"]
    ]

    insert_map = {}

    for item in generated_items:
        insert_after_index = item.get("insert_after_index")

        if insert_after_index is None:
            insert_after_index = len(original_items) - 1

        insert_map.setdefault(insert_after_index, []).append(item)

    final_items = []

    for i, item in enumerate(original_items):
        final_items.append(item)

        if i in insert_map:
            final_items.extend(insert_map[i])

    for idx, items in insert_map.items():
        if idx < 0 or idx >= len(original_items):
            final_items.extend(items)

    return final_items


@router.put("/{survey_id}")
@router.patch("/{survey_id}")
def update_survey(survey_id: str, survey: schemas.SurveyCreate):
    db = SessionLocal()

    try:
        db_survey = db.query(models.Survey).filter_by(survey_id=survey_id).first()

        if db_survey is None:
            raise HTTPException(status_code=404, detail="survey not found")

        has_response = db.query(models.Response).filter_by(
            survey_id=survey_id,
            is_completed=True
        ).first()

        if has_response is not None:
            raise HTTPException(
                status_code=409,
                detail="survey already has responses and cannot be edited"
            )

        db_survey.title = survey.title
        db_survey.description = survey.description
        db_survey.construct_name = survey.construct_name
        db_survey.construct_description = survey.construct_description
        db.commit()

        old_item_ids = [
            row.item_id
            for row in db.query(models.SurveyItem.item_id).filter_by(survey_id=survey_id).all()
        ]

        db.query(models.ItemQualityEvaluation).filter_by(
            survey_id=survey_id
        ).delete(synchronize_session=False)
        db.query(models.ConstructEvaluation).filter_by(
            survey_id=survey_id
        ).delete(synchronize_session=False)
        db.query(models.SurveyStatisticalEvaluation).filter_by(
            survey_id=survey_id
        ).delete(synchronize_session=False)
        db.query(models.SurveyLogStatistics).filter_by(
            survey_id=survey_id
        ).delete(synchronize_session=False)

        if old_item_ids:
            db.query(models.SurveyItemOption).filter(
                models.SurveyItemOption.item_id.in_(old_item_ids)
            ).delete(synchronize_session=False)

        db.query(models.SurveyItem).filter_by(survey_id=survey_id).delete(synchronize_session=False)
        db.commit()

        created_items = []

        for item in survey.items:
            db_item = models.SurveyItem(
                survey_id=survey_id,
                item_order=item.item_order,
                question_text=item.question_text,
                item_category=normalize_item_category(item.item_category),
                question_type=item.question_type,
                is_required=item.is_required,
                item_role="normal",
                is_generated=False,
                source_item_id=None,
                trap_correct_option_order=None,
                reverse_expected_rule=None
            )
            db.add(db_item)
            db.commit()
            db.refresh(db_item)

            created_options = []

            if item.options:
                for opt in item.options:
                    db_option = models.SurveyItemOption(
                        item_id=db_item.item_id,
                        option_order=opt.option_order,
                        option_label=opt.option_label,
                        option_score=opt.option_order
                    )
                    db.add(db_option)
                    db.commit()
                    db.refresh(db_option)

                    created_options.append({
                        "option_id": db_option.option_id,
                        "option_order": db_option.option_order,
                        "option_label": db_option.option_label,
                        "option_score": db_option.option_score
                    })

            created_items.append({
                "item_id": db_item.item_id,
                "item_order": db_item.item_order,
                "question_text": db_item.question_text,
                "item_category": db_item.item_category,
                "question_type": db_item.question_type,
                "item_role": "normal",
                "is_generated": False,
                "source_item_id": None,
                "trap_correct_option_order": None,
                "reverse_expected_rule": None,
                "insert_after_index": None,
                "options": created_options
            })

        if survey.enable_validation_items and created_items:
            original_items = [
                item for item in created_items
                if item["item_role"] == "normal"
            ]

            llm_input = {
                "title": survey.title,
                "items": [
                    {
                        "index": i,
                        "question_text": item["question_text"],
                        "options": item["options"]
                    }
                    for i, item in enumerate(original_items)
                ]
            }

            plan = generate_validation_plan_with_llm(llm_input)
            next_order = len(created_items) + 1

            for rev in plan.get("reverse_items", []):
                source_index = rev.get("source_index")

                if source_index is None or source_index < 0 or source_index >= len(original_items):
                    continue

                source = original_items[source_index]

                db_item = models.SurveyItem(
                    survey_id=survey_id,
                    item_order=next_order,
                    question_text=rev["question_text"],
                    item_category=source.get("item_category"),
                    question_type="likert_5",
                    is_required=True,
                    item_role="reverse",
                    is_generated=True,
                    source_item_id=source["item_id"],
                    trap_correct_option_order=None,
                    reverse_expected_rule="opposite_likert_5"
                )
                db.add(db_item)
                db.commit()
                db.refresh(db_item)

                created_options = []

                for opt in source["options"]:
                    db_option = models.SurveyItemOption(
                        item_id=db_item.item_id,
                        option_order=opt["option_order"],
                        option_label=opt["option_label"],
                        option_score=opt["option_order"]
                    )
                    db.add(db_option)
                    db.commit()
                    db.refresh(db_option)

                    created_options.append({
                        "option_id": db_option.option_id,
                        "option_order": db_option.option_order,
                        "option_label": db_option.option_label,
                        "option_score": db_option.option_score
                    })

                created_items.append({
                    "item_id": db_item.item_id,
                    "item_order": db_item.item_order,
                    "question_text": db_item.question_text,
                    "item_category": db_item.item_category,
                    "question_type": db_item.question_type,
                    "item_role": db_item.item_role,
                    "is_generated": db_item.is_generated,
                    "source_item_id": db_item.source_item_id,
                    "trap_correct_option_order": db_item.trap_correct_option_order,
                    "reverse_expected_rule": db_item.reverse_expected_rule,
                    "insert_after_index": rev.get("insert_after_index"),
                    "options": created_options
                })

                next_order += 1

            for trap in plan.get("trap_items", []):
                base_item = original_items[0]
                correct_option_order = trap.get("correct_option_order", 2)

                correct_opt = next(
                    (
                        opt for opt in base_item["options"]
                        if opt["option_order"] == correct_option_order
                    ),
                    None
                )

                if correct_opt is None:
                    correct_option_order = 2
                    correct_opt = next(
                        opt for opt in base_item["options"]
                        if opt["option_order"] == correct_option_order
                    )

                question_text = (
                    f"응답 신뢰도 확인을 위해 '{correct_opt['option_label']}'를 선택해 주세요."
                )

                db_item = models.SurveyItem(
                    survey_id=survey_id,
                    item_order=next_order,
                    question_text=question_text,
                    item_category=base_item.get("item_category"),
                    question_type="likert_5",
                    is_required=True,
                    item_role="trap",
                    is_generated=True,
                    source_item_id=None,
                    trap_correct_option_order=correct_option_order,
                    reverse_expected_rule=None
                )
                db.add(db_item)
                db.commit()
                db.refresh(db_item)

                created_options = []

                for opt in base_item["options"]:
                    db_option = models.SurveyItemOption(
                        item_id=db_item.item_id,
                        option_order=opt["option_order"],
                        option_label=opt["option_label"],
                        option_score=opt["option_order"]
                    )
                    db.add(db_option)
                    db.commit()
                    db.refresh(db_option)

                    created_options.append({
                        "option_id": db_option.option_id,
                        "option_order": db_option.option_order,
                        "option_label": db_option.option_label,
                        "option_score": db_option.option_score
                    })

                created_items.append({
                    "item_id": db_item.item_id,
                    "item_order": db_item.item_order,
                    "question_text": db_item.question_text,
                    "item_category": db_item.item_category,
                    "question_type": db_item.question_type,
                    "item_role": db_item.item_role,
                    "is_generated": db_item.is_generated,
                    "source_item_id": db_item.source_item_id,
                    "trap_correct_option_order": db_item.trap_correct_option_order,
                    "reverse_expected_rule": db_item.reverse_expected_rule,
                    "insert_after_index": trap.get("insert_after_index"),
                    "options": created_options
                })

                next_order += 1

        created_items = reorder_validation_items(created_items)

        for order, item in enumerate(created_items, start=1):
            item["item_order"] = order

            db_item = db.query(models.SurveyItem).filter_by(
                item_id=item["item_id"]
            ).first()

            if db_item is not None:
                db_item.item_order = order

        db.commit()

        return {
            "survey_id": survey_id,
            "title": db_survey.title,
            "description": db_survey.description,
            "construct_name": db_survey.construct_name,
            "construct_description": db_survey.construct_description,
            "status": db_survey.status,
            "items": created_items,
            "message": "survey updated"
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"failed to update survey: {repr(e)}")
    finally:
        db.close()


@router.post("/{survey_id}/public-link")
def create_or_get_public_link(survey_id: str, payload: schemas.SurveyShareLinkCreate):
    db = SessionLocal()

    try:
        survey = db.query(models.Survey).filter_by(survey_id=survey_id).first()
        if survey is None:
            raise HTTPException(status_code=404, detail="survey not found")

        if payload.single_use:
            invite_key = generate_access_key()
            invite = models.PublicSurveyInvite(
                survey_id=survey.survey_id,
                invite_key=invite_key,
                is_consumed=False,
                created_at=now_iso(),
                consumed_at=None,
                consumed_response_id=None,
            )
            db.add(invite)
            db.commit()

            return {
                "survey_id": survey.survey_id,
                "access_key": invite_key,
                "public_path": f"/public/o/{invite_key}",
                "created": True,
                "single_use": True,
                "message": "one-time public link created"
            }

        if payload.rotate or not survey.external_survey_key:
            survey.external_survey_key = generate_access_key()
            db.commit()
            db.refresh(survey)
            created = True
        else:
            created = False

        return {
            "survey_id": survey.survey_id,
            "access_key": survey.external_survey_key,
            "public_path": f"/public/s/{survey.external_survey_key}",
            "created": created,
            "single_use": False,
            "message": "public link ready"
        }

    finally:
        db.close()


@router.get("/public/{access_key}")
def get_public_survey(access_key: str):
    db = SessionLocal()

    try:
        survey = get_survey_by_access_key(db, access_key)
        if survey is None:
            raise HTTPException(status_code=404, detail="public survey not found")

        return build_survey_response(db, survey)

    finally:
        db.close()


@router.get("/public/{access_key}/availability")
def get_public_survey_availability(access_key: str, device_id: str):
    db = SessionLocal()

    try:
        survey = get_survey_by_access_key(db, access_key)
        if survey is None:
            raise HTTPException(status_code=404, detail="public survey not found")

        normalized_device_id = ensure_public_device_id(device_id)
        respondent_id = f"device:{normalized_device_id}"

        existing = db.query(models.Response.response_id).filter_by(
            survey_id=survey.survey_id,
            respondent_id=respondent_id,
            is_completed=True
        ).first()

        if existing is not None:
            return {
                "survey_id": survey.survey_id,
                "available": False,
                "reason": "already_submitted",
                "message": "This device already submitted the survey."
            }

        return {
            "survey_id": survey.survey_id,
            "available": True,
            "reason": None,
            "message": "Survey is available."
        }

    finally:
        db.close()


@router.post("/public/{access_key}/responses")
def create_public_response(access_key: str, response: schemas.PublicResponseCreate):
    db = SessionLocal()

    try:
        survey = get_survey_by_access_key(db, access_key)
        if survey is None:
            raise HTTPException(status_code=404, detail="public survey not found")

        normalized_device_id = ensure_public_device_id(response.device_id)
        respondent_id = f"device:{normalized_device_id}"

        existing = db.query(models.Response.response_id).filter_by(
            survey_id=survey.survey_id,
            respondent_id=respondent_id,
            is_completed=True
        ).first()

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="already submitted from this device"
            )

        response.respondent_id = respondent_id
        return create_response_and_features(db, survey.survey_id, response)

    finally:
        db.close()


@router.get("/public-once/{invite_key}")
def get_public_survey_from_one_time_link(invite_key: str):
    db = SessionLocal()

    try:
        invite = get_public_invite_by_key(db, invite_key)
        if invite is None:
            raise HTTPException(status_code=404, detail="one-time public link not found")

        survey = db.query(models.Survey).filter_by(survey_id=invite.survey_id).first()
        if survey is None:
            raise HTTPException(status_code=404, detail="survey not found")

        return build_survey_response(db, survey)

    finally:
        db.close()


@router.get("/public-once/{invite_key}/availability")
def get_public_survey_availability_from_one_time_link(invite_key: str):
    db = SessionLocal()

    try:
        invite = get_public_invite_by_key(db, invite_key)
        if invite is None:
            raise HTTPException(status_code=404, detail="one-time public link not found")

        if invite.is_consumed:
            return {
                "survey_id": invite.survey_id,
                "available": False,
                "reason": "link_used",
                "message": "This one-time link has already been used."
            }

        return {
            "survey_id": invite.survey_id,
            "available": True,
            "reason": None,
            "message": "Survey is available."
        }

    finally:
        db.close()


@router.post("/public-once/{invite_key}/responses")
def create_public_response_from_one_time_link(invite_key: str, response: schemas.ResponseCreate):
    db = SessionLocal()

    try:
        invite = get_public_invite_by_key(db, invite_key)
        if invite is None:
            raise HTTPException(status_code=404, detail="one-time public link not found")

        if invite.is_consumed:
            raise HTTPException(
                status_code=409,
                detail="one-time link already used"
            )

        respondent_id = f"invite:{invite.invite_id}"
        existing = db.query(models.Response.response_id).filter_by(
            survey_id=invite.survey_id,
            respondent_id=respondent_id,
            is_completed=True
        ).first()
        if existing is not None:
            invite.is_consumed = True
            invite.consumed_response_id = existing[0]
            invite.consumed_at = invite.consumed_at or now_iso()
            db.commit()
            raise HTTPException(
                status_code=409,
                detail="one-time link already used"
            )

        response.respondent_id = respondent_id
        result = create_response_and_features(db, invite.survey_id, response)

        invite.is_consumed = True
        invite.consumed_response_id = result.get("response_id")
        invite.consumed_at = now_iso()
        db.commit()

        return result

    finally:
        db.close()


@router.get("/{survey_id}")
def get_survey(survey_id: str):
    db = SessionLocal()

    survey = db.query(models.Survey).filter_by(
        survey_id=survey_id
    ).first()

    if survey is None:
        db.close()
        return {"error": "survey not found"}

    result = build_survey_response(db, survey)
    db.close()
    return result


@router.get("/{survey_id}/reliability-distribution")
def get_survey_reliability_distribution(survey_id: str):
    db = SessionLocal()

    try:
        survey = db.query(models.Survey).filter_by(survey_id=survey_id).first()
        if survey is None:
            raise HTTPException(status_code=404, detail="survey not found")

        rows = db.query(
            models.Response,
            models.ResponseFeature
        ).join(
            models.ResponseFeature,
            models.Response.response_id == models.ResponseFeature.response_id
        ).filter(
            models.Response.survey_id == survey_id,
            models.Response.is_completed == True
        ).order_by(
            models.Response.submitted_at.asc()
        ).all()

        respondents = []
        sincere_count = 0
        insincere_count = 0

        for response, response_feature in rows:
            compact = response_feature.compact_features or {}
            reliability = calculate_reliability_summary(compact)

            score = compact.get("reliability_score")
            if score is None:
                score = reliability["score"]

            try:
                score = float(score)
            except Exception:
                score = reliability["score"]

            status = resolve_binary_reliability_status(
                status=compact.get("reliability_status"),
                score=score
            )

            if status == "sincere":
                sincere_count += 1
            else:
                insincere_count += 1

            avg_item_time_ms = compact.get("avg_item_time_ms")
            time_per_item = []

            try:
                if avg_item_time_ms is not None:
                    time_per_item = [float(avg_item_time_ms) / 1000.0]
            except Exception:
                time_per_item = []

            reason_text = ""
            if reliability.get("reasons"):
                reason_text = ", ".join(reliability["reasons"])

            respondents.append({
                "id": response.response_id,
                "submittedAt": response.submitted_at,
                "reliabilityScore": round(score, 1),
                "timePerItem": time_per_item,
                "flagged": status == "insincere",
                "reason": reason_text
            })

        return {
            "survey_id": survey_id,
            "total_count": len(respondents),
            "sincere_count": sincere_count,
            "insincere_count": insincere_count,
            "high_count": sincere_count,
            "mid_count": 0,
            "low_count": insincere_count,
            "distribution": [
                {"level": "sincere", "label": "성실", "count": sincere_count},
                {"level": "insincere", "label": "비성실", "count": insincere_count}
            ],
            "respondents": respondents
        }

    finally:
        db.close()


@router.get("/{survey_id}/response-features.csv")
def download_survey_response_features_csv(survey_id: str):
    db = SessionLocal()

    try:
        survey = db.query(models.Survey).filter_by(survey_id=survey_id).first()
        if survey is None:
            raise HTTPException(status_code=404, detail="survey not found")

        survey_items = db.query(models.SurveyItem).filter_by(
            survey_id=survey_id
        ).order_by(models.SurveyItem.item_order.asc()).all()

        ordered_item_orders = [
            item.item_order
            for item in survey_items
            if item.item_order is not None
        ]
        item_order_by_id = {
            item.item_id: item.item_order
            for item in survey_items
            if item.item_order is not None
        }

        rows = db.query(
            models.Response,
            models.ResponseFeature,
        ).join(
            models.ResponseFeature,
            models.Response.response_id == models.ResponseFeature.response_id,
        ).filter(
            models.Response.survey_id == survey_id,
            models.Response.is_completed == True,
        ).order_by(
            models.Response.submitted_at.asc(),
        ).all()

        compact_keys = set()
        for _, feature in rows:
            compact = feature.compact_features or {}
            compact_keys.update(compact.keys())

        ordered_compact_keys = sorted(compact_keys)

        response_ids = [response.response_id for response, _ in rows]
        item_logs_by_response = {}
        if response_ids:
            item_logs = db.query(models.ResponseItemLog).filter(
                models.ResponseItemLog.response_id.in_(response_ids)
            ).all()

            for item_log in item_logs:
                item_order = item_order_by_id.get(item_log.item_id)
                if item_order is None:
                    continue

                response_map = item_logs_by_response.setdefault(item_log.response_id, {})
                value = item_log.item_time_ms

                if value is None:
                    continue

                previous = response_map.get(item_order)
                if previous is None or value > previous:
                    response_map[item_order] = value

        item_time_columns = [f"item_{order}_time_ms" for order in ordered_item_orders]

        header = [
            "response_id",
            "respondent_id",
            "started_at",
            "submitted_at",
            "is_completed",
            "reliability_score",
            "reliability_status",
        ] + ordered_compact_keys + item_time_columns + [
            "item_time_ms_by_order_json",
            "log_features_json",
            "content_features_json",
            "relation_features_json",
            "population_features_json",
        ]

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)

        for response, feature in rows:
            compact = feature.compact_features or {}
            reliability = calculate_reliability_summary(compact)

            compact_score = compact.get("reliability_score")
            compact_status = compact.get("reliability_status")
            reliability_score = (
                _safe_float_or_empty(compact_score)
                if compact_score is not None
                else reliability.get("score", "")
            )
            reliability_status = compact_status or reliability.get("status", "")

            row = [
                response.response_id,
                response.respondent_id or "",
                response.started_at or "",
                response.submitted_at or "",
                bool(response.is_completed),
                reliability_score,
                reliability_status,
            ]

            for key in ordered_compact_keys:
                value = compact.get(key)
                if isinstance(value, (dict, list)):
                    row.append(_json_text(value))
                else:
                    row.append(value if value is not None else "")

            item_time_map = item_logs_by_response.get(response.response_id, {})
            for order in ordered_item_orders:
                row.append(_safe_float_or_empty(item_time_map.get(order)))

            item_time_json = {
                str(order): item_time_map.get(order)
                for order in ordered_item_orders
                if item_time_map.get(order) is not None
            }

            row.extend([
                _json_text(item_time_json),
                _json_text(feature.log_features),
                _json_text(feature.content_features),
                _json_text(feature.relation_features),
                _json_text(feature.population_features),
            ])

            writer.writerow(row)

        csv_text = "\ufeff" + buffer.getvalue()
        filename = f"survey-{survey_id}-response-features.csv"

        return PlainTextResponse(
            content=csv_text,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )

    finally:
        db.close()


@router.get("/{survey_id}/item-evaluations.csv")
def download_survey_item_evaluations_csv(survey_id: str):
    db = SessionLocal()

    try:
        survey = db.query(models.Survey).filter_by(survey_id=survey_id).first()
        if survey is None:
            raise HTTPException(status_code=404, detail="survey not found")

        items = db.query(models.SurveyItem).filter_by(
            survey_id=survey_id
        ).order_by(
            models.SurveyItem.item_order.asc()
        ).all()

        item_ids = [item.item_id for item in items]

        options_map = {}
        if item_ids:
            options = db.query(models.SurveyItemOption).filter(
                models.SurveyItemOption.item_id.in_(item_ids)
            ).order_by(
                models.SurveyItemOption.item_id.asc(),
                models.SurveyItemOption.option_order.asc(),
            ).all()

            for opt in options:
                options_map.setdefault(opt.item_id, []).append({
                    "option_order": opt.option_order,
                    "option_label": opt.option_label,
                    "option_score": opt.option_score,
                })

        quality_map = {
            row.item_id: row
            for row in db.query(models.ItemQualityEvaluation).filter_by(survey_id=survey_id).all()
        }
        construct_map = {
            row.item_id: row
            for row in db.query(models.ConstructEvaluation).filter_by(survey_id=survey_id).all()
        }

        statistics = db.query(models.SurveyStatisticalEvaluation).filter_by(
            survey_id=survey_id
        ).order_by(
            models.SurveyStatisticalEvaluation.created_at.desc()
        ).first()

        item_citc_map = (statistics.item_citc_results or {}) if statistics else {}
        alpha_if_deleted_map = (statistics.alpha_if_item_deleted or {}) if statistics else {}

        statistics_response_count = statistics.response_count if statistics else ""
        statistics_cronbach_alpha = (
            _safe_float_or_empty(statistics.cronbach_alpha) if statistics else ""
        )
        statistics_alpha_status = (
            _score_status(statistics.cronbach_alpha, good=0.7, warning=0.6)
            if statistics
            else "unknown"
        )
        statistics_created_at = statistics.created_at if statistics else ""

        header = [
            "survey_id",
            "item_id",
            "item_order",
            "item_role",
            "is_generated",
            "source_item_id",
            "item_category",
            "question_text",
            "options_json",
            "quality_score",
            "quality_status",
            "quality_problem_categories_json",
            "quality_detected_terms_json",
            "quality_llm_comment",
            "quality_suggested_rewrite",
            "quality_created_at",
            "construct_embedding_score",
            "construct_llm_score",
            "construct_combined_score",
            "construct_status",
            "construct_predicted_citc",
            "construct_predicted_alpha_impact",
            "construct_embedding_features_json",
            "construct_llm_features_json",
            "construct_created_at",
            "statistics_response_count",
            "statistics_cronbach_alpha",
            "statistics_alpha_status",
            "statistics_item_citc",
            "statistics_item_citc_status",
            "statistics_alpha_if_item_deleted",
            "statistics_created_at",
        ]

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)

        for item in items:
            quality = quality_map.get(item.item_id)
            construct = construct_map.get(item.item_id)

            quality_score = quality.quality_score if quality else None
            quality_status = _score_status(quality_score, good=8.0, warning=6.0)

            embedding_score = construct.embedding_score if construct else None
            llm_score = construct.llm_score if construct else None
            combined_score = None
            if embedding_score is not None and llm_score is not None:
                try:
                    combined_score = round(float(embedding_score) * 0.4 + float(llm_score) * 0.6, 3)
                except Exception:
                    combined_score = None

            construct_status = _score_status(combined_score, good=8.0, warning=6.0)

            statistics_item_citc = item_citc_map.get(item.item_id)
            statistics_item_citc_status = _score_status(
                statistics_item_citc,
                good=0.4,
                warning=0.2,
            )
            statistics_alpha_if_item_deleted = alpha_if_deleted_map.get(item.item_id)

            row = [
                survey_id,
                item.item_id,
                item.item_order,
                item.item_role or "",
                bool(item.is_generated),
                item.source_item_id or "",
                item.item_category or "",
                item.question_text or "",
                _json_text(options_map.get(item.item_id, [])),
                _safe_float_or_empty(quality_score),
                quality_status,
                _json_text(quality.problem_categories if quality else None),
                _json_text(quality.detected_terms if quality else None),
                (quality.llm_comment if quality and quality.llm_comment is not None else ""),
                (quality.suggested_rewrite if quality and quality.suggested_rewrite is not None else ""),
                (quality.created_at if quality and quality.created_at is not None else ""),
                _safe_float_or_empty(embedding_score),
                _safe_float_or_empty(llm_score),
                _safe_float_or_empty(combined_score),
                construct_status,
                _safe_float_or_empty(construct.predicted_citc if construct else None),
                _safe_float_or_empty(construct.predicted_alpha_impact if construct else None),
                _json_text(construct.embedding_features if construct else None),
                _json_text(construct.llm_features if construct else None),
                (construct.created_at if construct and construct.created_at is not None else ""),
                statistics_response_count,
                statistics_cronbach_alpha,
                statistics_alpha_status,
                _safe_float_or_empty(statistics_item_citc),
                statistics_item_citc_status,
                _safe_float_or_empty(statistics_alpha_if_item_deleted),
                statistics_created_at,
            ]
            writer.writerow(row)

        csv_text = "\ufeff" + buffer.getvalue()
        filename = f"survey-{survey_id}-item-evaluations.csv"

        return PlainTextResponse(
            content=csv_text,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )

    finally:
        db.close()


@router.delete("/{survey_id}")
def delete_survey(survey_id: str):
    db = SessionLocal()

    try:
        survey = db.query(models.Survey).filter_by(survey_id=survey_id).first()

        if survey is None:
            raise HTTPException(status_code=404, detail="survey not found")

        item_ids = [
            row.item_id
            for row in db.query(models.SurveyItem.item_id).filter_by(survey_id=survey_id).all()
        ]

        db.query(models.ConnectionEvent).filter_by(survey_id=survey_id).delete(synchronize_session=False)
        db.query(models.ResponseItemLog).filter_by(survey_id=survey_id).delete(synchronize_session=False)
        db.query(models.ResponseAnswer).filter_by(survey_id=survey_id).delete(synchronize_session=False)
        db.query(models.ResponseLog).filter_by(survey_id=survey_id).delete(synchronize_session=False)
        db.query(models.ResponseFeature).filter_by(survey_id=survey_id).delete(synchronize_session=False)
        db.query(models.Response).filter_by(survey_id=survey_id).delete(synchronize_session=False)

        db.query(models.ItemQualityEvaluation).filter_by(survey_id=survey_id).delete(synchronize_session=False)
        db.query(models.ConstructEvaluation).filter_by(survey_id=survey_id).delete(synchronize_session=False)
        db.query(models.SurveyStatisticalEvaluation).filter_by(survey_id=survey_id).delete(synchronize_session=False)
        db.query(models.SurveyLogStatistics).filter_by(survey_id=survey_id).delete(synchronize_session=False)
        db.query(models.PublicSurveyInvite).filter_by(survey_id=survey_id).delete(synchronize_session=False)

        if item_ids:
            db.query(models.SurveyItemOption).filter(
                models.SurveyItemOption.item_id.in_(item_ids)
            ).delete(synchronize_session=False)

        db.query(models.SurveyItem).filter_by(survey_id=survey_id).delete(synchronize_session=False)
        db.query(models.Survey).filter_by(survey_id=survey_id).delete(synchronize_session=False)

        db.commit()

        return {
            "survey_id": survey_id,
            "message": "survey deleted"
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"failed to delete survey: {repr(e)}")

    finally:
        db.close()


@router.post("/{survey_id}/responses")
def create_response(survey_id: str, response: schemas.ResponseCreate):
    db = SessionLocal()
    try:
        return create_response_and_features(db, survey_id, response)
    finally:
        db.close()


@router.post("/{survey_id}/refresh-population-features")
def refresh_population_features(survey_id: str):
    db = SessionLocal()
    try:
        updated_count = _refresh_population_features_for_survey(db=db, survey_id=survey_id)
        return {
            "survey_id": survey_id,
            "updated_count": updated_count,
            "message": "population features refreshed"
        }
    finally:
        db.close()
