export type QuestionType = 'likert-5' | 'likert-7' | 'multiple' | 'short'
export type BackendQuestionType = 'likert_5' | string
export type EvaluationStatus = 'good' | 'warning' | 'bad' | 'unknown'

export interface ItemQualityResult {
  score: number
  flaggedWords: string[]
  suggestion: string | null
}

export interface CitcResult {
  id: string
  citcScore: number
  embeddingScore: number
  llmScore: number
}

export interface SurveyItem {
  id: string
  backendItemId?: string
  text: string
  type: QuestionType
  options: string[]
  backendOptions?: BackendSurveyItemOption[]
  isTrap?: boolean
  isReverse?: boolean
  quality?: ItemQualityResult
  citc?: CitcResult
}

export interface SurveySettings {
  title: string
  surveyContext: string
}

export interface EvaluateItemQualityRequest {
  text: string
}

export interface CitcPredictRequest {
  items: {
    id: string
    text: string
  }[]
}

export interface CitcPredictResponse {
  results: CitcResult[]
}

export interface GenerateTrapRequest {
  surveyContext: string
  items: string[]
}

export interface GenerateTrapResponse {
  trapItem: string
  suggestedPosition: number
}

export interface GenerateReverseRequest {
  originalItem: string
}

export interface GenerateReverseResponse {
  reverseItem: string
}

export interface ReliabilityRespondent {
  id: string
  submittedAt: string
  reliabilityScore: number
  timePerItem: number[]
  flagged: boolean
  reason: string
}

export type ReliabilityLevel = 'high' | 'mid' | 'low'

export interface ReliabilityBucket {
  level: ReliabilityLevel
  label: string
  count: number
}

export interface SurveyReliabilityResponse {
  survey_id?: string
  total_count?: number
  high_count?: number
  mid_count?: number
  low_count?: number
  distribution?: ReliabilityBucket[]
  respondents: ReliabilityRespondent[]
}

export interface ItemStat {
  itemId: string
  text: string
  mean: number
  variance: number
  count: number
  missing: number
  distribution: number[]
}

export interface ItemStatsResponse {
  items: ItemStat[]
}

export interface BackendSurveyItemOptionCreate {
  option_order: number
  option_label: string
}

export interface BackendSurveyItemCreate {
  item_order: number
  question_text: string
  question_type: BackendQuestionType
  is_required: boolean
  options: BackendSurveyItemOptionCreate[]
}

export interface BackendSurveyCreatePayload {
  title: string
  description?: string | null
  construct_name?: string | null
  construct_description?: string | null
  enable_validation_items: boolean
  items: BackendSurveyItemCreate[]
}

export type BackendSurveyUpdatePayload = BackendSurveyCreatePayload

export interface BackendSurveyItemOption {
  option_id: string
  option_order: number
  option_label: string
  option_score: number
}

export interface BackendSurveyItem {
  item_id: string
  item_order: number
  question_text: string
  question_type: BackendQuestionType
  item_role: 'normal' | 'reverse' | 'trap' | string
  is_generated: boolean
  source_item_id: string | null
  trap_correct_option_order: number | null
  reverse_expected_rule: string | null
  insert_after_index?: number | null
  options: BackendSurveyItemOption[]
}

export interface BackendSurveyResponse {
  survey_id: string
  title: string
  description?: string | null
  construct_name?: string | null
  construct_description?: string | null
  status?: string
  items: BackendSurveyItem[]
  message?: string
}

export interface SurveySummary {
  survey_id: string
  title: string
  description?: string | null
  construct_name?: string | null
  construct_description?: string | null
  status?: string
  item_count: number
  normal_item_count: number
  response_count: number
  last_response_at?: string | null
}

export interface SurveyListResponse {
  surveys: SurveySummary[]
}

export interface ResponseAnswerSubmit {
  item_id: string
  selected_option_id?: string | null
  selected_option_order?: number | null
  selected_score?: number | null
  answer_text?: string | null
  answered_at?: string | null
}

export interface ResponseItemLogSubmit {
  item_id: string
  checked_at?: string | null
  previous_checked_at?: string | null
  entered_at?: string | null
  first_selected_at?: string | null
  last_selected_at?: string | null
  last_exited_at?: string | null
  item_time_ms: number
  time_share?: number | null
  time_to_first_answer_ms?: number | null
  time_after_last_answer_ms?: number | null
  touch_count: number
  change_count: number
  visit_count: number
  back_visit_count: number
  is_revisited: boolean
  initial_visit_time_ms: number
  revisit_time_ms: number
  answer_changed: boolean
  changed_after_revisit: boolean
  first_selected_option_order?: number | null
  final_selected_option_order?: number | null
}

export interface ConnectionEventSubmit {
  event_type: 'offline' | 'online' | string
  timestamp?: string | null
}

export interface ResponseLogSubmit {
  started_at?: string | null
  submitted_at?: string | null
  total_time_ms: number
  total_touch_count: number
  connection_lost: boolean
  offline_count: number
  offline_total_ms: number
  item_logs: ResponseItemLogSubmit[]
  connection_events: ConnectionEventSubmit[]
}

export interface SurveyResponseSubmitPayload {
  respondent_id?: string | null
  started_at?: string | null
  submitted_at?: string | null
  is_completed: boolean
  label?: string | null
  answers: ResponseAnswerSubmit[]
  log: ResponseLogSubmit
}

export interface CompactResponseFeatures {
  avg_item_time_ms?: number
  too_fast_item_ratio?: number
  avg_touch_per_item?: number
  offline_ratio?: number
  connection_lost?: number
  mean_time_to_first_answer_ms?: number
  min_time_to_first_answer_ms?: number
  mean_time_after_last_answer_ms?: number
  mean_change_count?: number
  total_change_count?: number
  mean_visit_count?: number
  mean_back_visit_count?: number
  total_back_visit_count?: number
  revisit_item_ratio?: number
  answer_changed_ratio?: number
  changed_after_revisit_ratio?: number
  mean_revisit_time_ms?: number
  max_revisit_time_ms?: number
  trap_fail_ratio?: number
  reverse_avg_diff?: number | null
  reverse_consistency_score?: number | null
  time_curve_deviation?: number | null
  population_sample_count?: number
  item_count?: number
  reliability_score?: number
  reliability_status?: EvaluationStatus
  [key: string]: unknown
}

export interface BackendReliabilitySummary {
  score: number
  status: EvaluationStatus
  reasons: string[]
}

export interface SurveyResponseSubmitResult {
  response_id: string
  survey_id: string
  response_feature_id: string
  log_features: Record<string, unknown>
  content_features: Record<string, unknown>
  population_features: Record<string, unknown>
  relation_features: Record<string, unknown>
  features: CompactResponseFeatures
  reliability?: BackendReliabilitySummary
  message: string
}

export interface QualityEvaluationItem {
  item_id: string
  item_order: number
  question_text: string
  quality_score: number | null
  status: EvaluationStatus
  problem_categories?: string[] | null
  detected_terms?: string[] | null
  llm_comment?: string | null
  suggested_rewrite?: string | null
  created_at?: string | null
}

export interface QualityEvaluationResponse {
  survey_id: string
  results: QualityEvaluationItem[]
}

export interface ConstructEvaluationItem {
  construct_eval_id?: string
  item_id: string
  item_order: number
  question_text: string
  embedding_features?: Record<string, unknown> | null
  embedding_score?: number | null
  llm_features?: Record<string, unknown> | null
  llm_score?: number | null
  combined_score?: number | null
  status?: EvaluationStatus
  predicted_citc?: number | null
  predicted_alpha_impact?: number | null
  created_at?: string | null
}

export interface ConstructEvaluationResponse {
  survey_id: string
  item_count?: number
  results: ConstructEvaluationItem[]
  message?: string
}

export interface StatisticsEvaluationItem {
  item_id: string
  item_order: number
  question_text: string
  citc?: number | null
  citc_status?: EvaluationStatus
  alpha_if_item_deleted?: number | null
}

export interface StatisticsEvaluationResponse {
  stat_eval_id?: string
  survey_id: string
  response_count: number
  raw_response_count?: number
  excluded_response_count?: number
  item_count?: number
  cronbach_alpha?: number | null
  alpha_status?: EvaluationStatus
  item_citc_results?: Record<string, number | null>
  alpha_if_item_deleted?: Record<string, number | null>
  items?: StatisticsEvaluationItem[]
  created_at?: string | null
  result?: null
  error?: string
  message?: string
}
