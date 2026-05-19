# backend/models.py

import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Survey(Base):
    __tablename__ = "surveys"

    survey_id = Column(String, primary_key=True, default=generate_uuid)

    # 외부 데이터와 연결하기 위한 키
    external_survey_key = Column(String, nullable=True)

    # 사용자가 입력하는 핵심 정보
    title = Column(String, nullable=False)

    # 지금은 사용자 입력에서 제외하지만, 나중 확장을 위해 DB에는 유지 가능
    description = Column(String, nullable=True)

    # 나중에 LLM이 자동 추론하거나 CITC 근사에서 사용할 수 있음
    construct_name = Column(String, nullable=True)
    construct_description = Column(String, nullable=True)

    status = Column(String, default="draft")

    items = relationship("SurveyItem", back_populates="survey")


class PublicSurveyInvite(Base):
    __tablename__ = "public_survey_invites"

    invite_id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)
    invite_key = Column(String, nullable=False, unique=True, index=True)
    is_consumed = Column(Boolean, default=False)
    created_at = Column(String, nullable=True)
    consumed_at = Column(String, nullable=True)
    consumed_response_id = Column(String, nullable=True)


class SurveyItem(Base):
    __tablename__ = "survey_items"

    item_id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)

    # 외부 문항 키
    external_item_key = Column(String, nullable=True)

    item_order = Column(Integer, nullable=False)
    question_text = Column(String, nullable=False)
    item_category = Column(String, nullable=True)

    # 기본은 5점 리커트
    question_type = Column(String, default="likert_5")
    is_required = Column(Boolean, default=True)

    # normal: 원본 일반 문항
    # reverse: LLM 생성 역문항
    # trap: LLM 생성 함정문항
    item_role = Column(String, default="normal")

    # 사용자가 입력한 문항인지, LLM이 생성한 문항인지 구분
    is_generated = Column(Boolean, default=False)

    # reverse 문항이면 원본 문항 item_id 저장
    source_item_id = Column(String, nullable=True)

    # trap 문항이면 정답 option_order 저장
    trap_correct_option_order = Column(Integer, nullable=True)

    # reverse 문항 계산 규칙
    # 예: opposite_likert_5
    reverse_expected_rule = Column(String, nullable=True)

    survey = relationship("Survey", back_populates="items")
    options = relationship("SurveyItemOption", back_populates="item")


class SurveyItemOption(Base):
    __tablename__ = "survey_item_options"

    option_id = Column(String, primary_key=True, default=generate_uuid)
    item_id = Column(String, ForeignKey("survey_items.item_id"), nullable=False)

    # 외부 옵션 키
    external_option_key = Column(String, nullable=True)

    option_order = Column(Integer, nullable=False)
    option_label = Column(String, nullable=False)

    # 사용자는 입력하지 않음
    # 백엔드에서 option_score = option_order 로 자동 저장
    option_score = Column(Integer, nullable=False)

    item = relationship("SurveyItem", back_populates="options")


class Response(Base):
    __tablename__ = "responses"

    response_id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)

    respondent_id = Column(String, nullable=True)

    started_at = Column(String, nullable=True)
    submitted_at = Column(String, nullable=True)

    is_completed = Column(Boolean, default=True)

    # sincere | insincere | null
    label = Column(String, nullable=True)


class ResponseAnswer(Base):
    __tablename__ = "response_answers"

    answer_id = Column(String, primary_key=True, default=generate_uuid)
    response_id = Column(String, ForeignKey("responses.response_id"), nullable=False)
    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)
    item_id = Column(String, ForeignKey("survey_items.item_id"), nullable=False)

    selected_option_id = Column(String, nullable=True)
    selected_option_order = Column(Integer, nullable=True)

    # 사용자가 직접 보내지 않아도 됨
    # 백엔드에서 selected_score = selected_option_order 로 자동 처리 가능
    selected_score = Column(Integer, nullable=True)

    answer_text = Column(String, nullable=True)
    answered_at = Column(String, nullable=True)


class ResponseLog(Base):
    __tablename__ = "response_logs"

    log_id = Column(String, primary_key=True, default=generate_uuid)
    response_id = Column(String, ForeignKey("responses.response_id"), nullable=False)
    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)

    started_at = Column(String, nullable=True)
    submitted_at = Column(String, nullable=True)

    total_time_ms = Column(Float, default=0)
    total_touch_count = Column(Integer, default=0)

    connection_lost = Column(Boolean, default=False)
    offline_count = Column(Integer, default=0)
    offline_total_ms = Column(Float, default=0)


class ResponseItemLog(Base):
    __tablename__ = "response_item_logs"

    item_log_id = Column(String, primary_key=True, default=generate_uuid)
    response_id = Column(String, ForeignKey("responses.response_id"), nullable=False)
    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)
    item_id = Column(String, ForeignKey("survey_items.item_id"), nullable=False)

    # 기존 호환용 필드
    checked_at = Column(String, nullable=True)
    previous_checked_at = Column(String, nullable=True)

    # 문항 단위 방문/선택 시각
    entered_at = Column(String, nullable=True)
    first_selected_at = Column(String, nullable=True)
    last_selected_at = Column(String, nullable=True)
    last_exited_at = Column(String, nullable=True)

    # 문항 단위 시간 feature
    item_time_ms = Column(Float, default=0)
    time_share = Column(Float, nullable=True)
    time_to_first_answer_ms = Column(Float, nullable=True)
    time_after_last_answer_ms = Column(Float, nullable=True)

    # 터치/선택 변경 feature
    touch_count = Column(Integer, default=0)
    change_count = Column(Integer, default=0)

    # 뒤로가기/재방문 feature
    visit_count = Column(Integer, default=1)
    back_visit_count = Column(Integer, default=0)
    is_revisited = Column(Boolean, default=False)
    initial_visit_time_ms = Column(Float, default=0)
    revisit_time_ms = Column(Float, default=0)

    # 답변 변경 feature
    answer_changed = Column(Boolean, default=False)
    changed_after_revisit = Column(Boolean, default=False)
    first_selected_option_order = Column(Integer, nullable=True)
    final_selected_option_order = Column(Integer, nullable=True)


class ConnectionEvent(Base):
    __tablename__ = "connection_events"

    event_id = Column(String, primary_key=True, default=generate_uuid)
    response_id = Column(String, ForeignKey("responses.response_id"), nullable=False)
    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)

    event_type = Column(String, nullable=False)
    timestamp = Column(String, nullable=True)


class ResponseFeature(Base):
    __tablename__ = "response_features"

    response_feature_id = Column(String, primary_key=True, default=generate_uuid)
    response_id = Column(String, ForeignKey("responses.response_id"), nullable=False)
    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)

    log_features = Column(JSON, nullable=True)
    content_features = Column(JSON, nullable=True)
    relation_features = Column(JSON, nullable=True)
    population_features = Column(JSON, nullable=True)
    compact_features = Column(JSON, nullable=True)

    created_at = Column(String, nullable=True)


class SurveyLogStatistics(Base):
    __tablename__ = "survey_log_statistics"

    stat_id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)

    response_count = Column(Integer, default=0)
    item_count = Column(Integer, default=0)

    mean_time_share_vector = Column(JSON, nullable=True)
    std_time_share_vector = Column(JSON, nullable=True)

    updated_at = Column(String, nullable=True)


# -----------------------------
# 설문 문항 품질 평가 결과
# -----------------------------
class ItemQualityEvaluation(Base):
    __tablename__ = "item_quality_evaluations"

    quality_eval_id = Column(String, primary_key=True, default=generate_uuid)

    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)
    item_id = Column(String, ForeignKey("survey_items.item_id"), nullable=False)

    # 전체 품질 점수
    quality_score = Column(Float, nullable=True)

    # 예: ambiguous, double_barreled, leading, difficult_wording
    problem_categories = Column(JSON, nullable=True)

    # 단어사전에서 탐지된 표현
    detected_terms = Column(JSON, nullable=True)

    # LLM 평가 코멘트
    llm_comment = Column(String, nullable=True)

    # LLM 수정 제안 문항
    suggested_rewrite = Column(String, nullable=True)

    created_at = Column(String, nullable=True)


# -----------------------------
# 설문 내용 평가 / CITC 사전 근사 결과
# -----------------------------
class ConstructEvaluation(Base):
    __tablename__ = "construct_evaluations"

    construct_eval_id = Column(String, primary_key=True, default=generate_uuid)

    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)
    item_id = Column(String, ForeignKey("survey_items.item_id"), nullable=False)

    # embedding 기반 feature와 점수
    embedding_features = Column(JSON, nullable=True)
    embedding_score = Column(Float, nullable=True)

    # LLM 기반 feature와 점수
    llm_features = Column(JSON, nullable=True)
    llm_score = Column(Float, nullable=True)

    # 나중에 실제 CITC에 근사해서 채울 값
    predicted_citc = Column(Float, nullable=True)
    predicted_alpha_impact = Column(Float, nullable=True)

    created_at = Column(String, nullable=True)


# -----------------------------
# 응답이 충분히 쌓인 뒤 실제 통계 계산 결과
# -----------------------------
class SurveyStatisticalEvaluation(Base):
    __tablename__ = "survey_statistical_evaluations"

    stat_eval_id = Column(String, primary_key=True, default=generate_uuid)

    survey_id = Column(String, ForeignKey("surveys.survey_id"), nullable=False)

    response_count = Column(Integer, default=0)

    cronbach_alpha = Column(Float, nullable=True)

    # item_id별 CITC
    item_citc_results = Column(JSON, nullable=True)

    # item_id별 alpha if item deleted
    alpha_if_item_deleted = Column(JSON, nullable=True)

    created_at = Column(String, nullable=True)
