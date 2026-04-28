# backend/routers/surveys.py

from fastapi import APIRouter
from database import SessionLocal
import models
import schemas

from services.llm_validation_item_service import generate_validation_plan_with_llm

from services.feature_service import (
    calculate_log_features,
    calculate_content_features,
    calculate_relation_features,
    build_compact_features,
    calculate_reliability_summary
)
from services.population_feature_service import calculate_population_features


router = APIRouter(prefix="/surveys")


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
        "items": created_items,
        "message": "survey created"
    }

    db.close()
    return result


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


@router.get("/{survey_id}")
def get_survey(survey_id: str):
    db = SessionLocal()

    survey = db.query(models.Survey).filter_by(
        survey_id=survey_id
    ).first()

    if survey is None:
        db.close()
        return {"error": "survey not found"}

    items = db.query(models.SurveyItem).filter_by(
        survey_id=survey_id
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

    db.close()
    return result


@router.post("/{survey_id}/responses")
def create_response(survey_id: str, response: schemas.ResponseCreate):
    db = SessionLocal()

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

    result = {
        "response_id": response_id,
        "survey_id": survey_id,
        "response_feature_id": db_feature.response_feature_id,
        "log_features": log_features,
        "content_features": content_features,
        "population_features": population_features,
        "relation_features": relation_features,
        "features": compact_features,
        "reliability": calculate_reliability_summary(compact_features),
        "message": "response and features created"
    }

    db.close()
    return result


@router.post("/{survey_id}/refresh-population-features")
def refresh_population_features(survey_id: str):
    db = SessionLocal()

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

    result = {
        "survey_id": survey_id,
        "updated_count": updated_count,
        "message": "population features refreshed"
    }

    db.close()
    return result
