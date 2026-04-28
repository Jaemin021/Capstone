# backend/schemas.py

from typing import List, Optional
from pydantic import BaseModel, Field


class SurveyItemOptionCreate(BaseModel):
    option_order: int
    option_label: str


class SurveyItemCreate(BaseModel):
    item_order: int
    question_text: str

    # 기본은 5점 리커트
    question_type: str = "likert_5"
    is_required: bool = True

    options: Optional[List[SurveyItemOptionCreate]] = None


class SurveyCreate(BaseModel):
    title: str

    # 지금은 사용자가 안 넣어도 됨
    description: Optional[str] = None
    construct_name: Optional[str] = None
    construct_description: Optional[str] = None

    # True면 LLM으로 역문항/함정문항 자동 생성
    enable_validation_items: bool = False

    items: List[SurveyItemCreate]


class ResponseAnswerCreate(BaseModel):
    item_id: str

    selected_option_id: Optional[str] = None
    selected_option_order: Optional[int] = None

    # 현재는 selected_option_order와 동일하게 처리
    selected_score: Optional[int] = None

    answer_text: Optional[str] = None
    answered_at: Optional[str] = None


class ResponseItemLogCreate(BaseModel):
    item_id: str

    # 기존 호환용 필드
    checked_at: Optional[str] = None
    previous_checked_at: Optional[str] = None

    # 문항 단위 방문/선택 시각
    entered_at: Optional[str] = None
    first_selected_at: Optional[str] = None
    last_selected_at: Optional[str] = None
    last_exited_at: Optional[str] = None

    # 문항 단위 시간 feature
    item_time_ms: float = 0
    time_share: Optional[float] = None
    time_to_first_answer_ms: Optional[float] = None
    time_after_last_answer_ms: Optional[float] = None

    # 터치/선택 변경 feature
    touch_count: int = 0
    change_count: int = 0

    # 뒤로가기/재방문 feature
    visit_count: int = 1
    back_visit_count: int = 0
    is_revisited: bool = False
    initial_visit_time_ms: float = 0
    revisit_time_ms: float = 0

    # 답변 변경 feature
    answer_changed: bool = False
    changed_after_revisit: bool = False
    first_selected_option_order: Optional[int] = None
    final_selected_option_order: Optional[int] = None


class ConnectionEventCreate(BaseModel):
    event_type: str
    timestamp: Optional[str] = None


class ResponseLogCreate(BaseModel):
    started_at: Optional[str] = None
    submitted_at: Optional[str] = None

    total_time_ms: float = 0
    total_touch_count: int = 0

    connection_lost: bool = False
    offline_count: int = 0
    offline_total_ms: float = 0

    item_logs: List[ResponseItemLogCreate] = Field(default_factory=list)
    connection_events: List[ConnectionEventCreate] = Field(default_factory=list)


class ResponseCreate(BaseModel):
    respondent_id: Optional[str] = None

    started_at: Optional[str] = None
    submitted_at: Optional[str] = None

    is_completed: bool = True
    label: Optional[str] = None

    answers: List[ResponseAnswerCreate]
    log: ResponseLogCreate


class ItemQualityResult(BaseModel):
    item_id: str
    quality_score: float
    problem_categories: List[str]
    detected_terms: List[str]
    suggested_rewrite: Optional[str] = None


class ConstructEvaluationResult(BaseModel):
    item_id: str
    embedding_score: float
    llm_score: float
    predicted_citc: Optional[float] = None


class SurveyEvaluationResponse(BaseModel):
    survey_id: str
    item_quality_results: List[ItemQualityResult]
    construct_results: List[ConstructEvaluationResult]