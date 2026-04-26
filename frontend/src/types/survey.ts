export type QuestionType = 'likert-5' | 'likert-7' | 'multiple' | 'short'

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
  text: string
  type: QuestionType
  options?: string[]
  isTrap?: boolean
  isReverse?: boolean
  quality?: ItemQualityResult
  citc?: CitcResult
}

export interface SurveySettings {
  title: string
  surveyContext: string
  trapEnabled: boolean
  reverseEnabled: boolean
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

export interface SurveyReliabilityResponse {
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
