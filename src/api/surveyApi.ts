import { http, useMockApi } from './http'
import {
  mockEvaluateItemQuality,
  mockGenerateReverseItem,
  mockGenerateTrapItem,
  mockGetSurveyItemStats,
  mockGetSurveyReliability,
  mockPredictCitc,
} from './mock/surveyMock'
import type {
  CitcPredictRequest,
  CitcPredictResponse,
  EvaluateItemQualityRequest,
  GenerateReverseRequest,
  GenerateReverseResponse,
  GenerateTrapRequest,
  GenerateTrapResponse,
  ItemQualityResult,
  ItemStatsResponse,
  SurveyReliabilityResponse,
} from '../types/survey'

/**
 * [evaluateItemQuality]
 * 설명: 설문 문항 텍스트의 품질 점수, 문제 어휘, 대체 문항 추천을 조회한다.
 * 엔드포인트: POST /api/item/quality
 * 요청 타입: EvaluateItemQualityRequest
 * 응답 타입: ItemQualityResult
 * 백엔드 담당자 확인 필요 항목: score 범위는 0~100, flaggedWords는 원문 내 하이라이트 가능한 문자열이어야 함.
 */
export async function evaluateItemQuality(
  request: EvaluateItemQualityRequest,
): Promise<ItemQualityResult> {
  if (useMockApi) {
    return mockEvaluateItemQuality(request)
  }

  // [API 연동 필요 - 문항 품질 평가]
  // 엔드포인트: POST /api/item/quality
  // 요청: { text: string }
  // 응답: { score: number, flaggedWords: string[], suggestion: string | null }
  const { data } = await http.post<ItemQualityResult>('/api/item/quality', request)
  return data
}

/**
 * [predictSurveyCitc]
 * 설명: 설문 전체 문항의 CITC 예측 점수와 보조 점수를 조회한다.
 * 엔드포인트: POST /api/survey/citc-predict
 * 요청 타입: CitcPredictRequest
 * 응답 타입: CitcPredictResponse
 * 백엔드 담당자 확인 필요 항목: citcScore = a * embeddingScore + b * llmScore, a+b=1 가중치 공유 필요.
 */
export async function predictSurveyCitc(
  request: CitcPredictRequest,
): Promise<CitcPredictResponse> {
  if (useMockApi) {
    return mockPredictCitc(request)
  }

  // [API 연동 필요 - CITC 예측]
  // 엔드포인트: POST /api/survey/citc-predict
  // 요청: { items: { id: string, text: string }[] }
  // 응답: { results: { id: string, citcScore: number, embeddingScore: number, llmScore: number }[] }
  // 내부 로직: citcScore = a * embeddingScore + b * llmScore (가중합, a+b=1)
  const { data } = await http.post<CitcPredictResponse>('/api/survey/citc-predict', request)
  return data
}

/**
 * [generateTrapItem]
 * 설명: 설문 맥락과 기존 문항 목록을 기반으로 함정 문항을 생성한다.
 * 엔드포인트: POST /api/item/generate-trap
 * 요청 타입: GenerateTrapRequest
 * 응답 타입: GenerateTrapResponse
 * 백엔드 담당자 확인 필요 항목: suggestedPosition은 0 기반 index인지 1 기반 순서인지 프론트와 합의 필요.
 */
export async function generateTrapItem(
  request: GenerateTrapRequest,
): Promise<GenerateTrapResponse> {
  if (useMockApi) {
    return mockGenerateTrapItem(request)
  }

  // [API 연동 필요 - 함정 문항 생성]
  // 엔드포인트: POST /api/item/generate-trap
  // 요청: { surveyContext: string, items: string[] }
  // 응답: { trapItem: string, suggestedPosition: number }
  const { data } = await http.post<GenerateTrapResponse>('/api/item/generate-trap', request)
  return data
}

/**
 * [generateReverseItem]
 * 설명: 선택된 원문 문항을 기반으로 역문항을 생성한다.
 * 엔드포인트: POST /api/item/generate-reverse
 * 요청 타입: GenerateReverseRequest
 * 응답 타입: GenerateReverseResponse
 * 백엔드 담당자 확인 필요 항목: 의미 반전은 유지하되 부정 표현이 과도하게 복잡해지지 않도록 검수 기준 필요.
 */
export async function generateReverseItem(
  request: GenerateReverseRequest,
): Promise<GenerateReverseResponse> {
  if (useMockApi) {
    return mockGenerateReverseItem(request)
  }

  // [API 연동 필요 - 역문항 생성]
  // 엔드포인트: POST /api/item/generate-reverse
  // 요청: { originalItem: string }
  // 응답: { reverseItem: string }
  const { data } = await http.post<GenerateReverseResponse>('/api/item/generate-reverse', request)
  return data
}

/**
 * [getSurveyReliability]
 * 설명: 설문별 응답자의 신뢰도 점수와 응답 로그 요약을 조회한다.
 * 엔드포인트: GET /api/survey/:id/reliability
 * 요청 타입: surveyId(path param)
 * 응답 타입: SurveyReliabilityResponse
 * 백엔드 담당자 확인 필요 항목: timePerItem 단위는 초로 통일.
 */
export async function getSurveyReliability(
  surveyId: string,
): Promise<SurveyReliabilityResponse> {
  if (useMockApi) {
    return mockGetSurveyReliability()
  }

  // [API 연동 필요 - 응답 신뢰도 데이터]
  // 엔드포인트: GET /api/survey/:id/reliability
  // 응답: { respondents: { id: string, reliabilityScore: number, timePerItem: number[], flagged: boolean }[] }
  // 신뢰도 계산 로직 (백엔드): 로그 데이터 + 함정/역문항 결과 + 평균 편차
  const { data } = await http.get<SurveyReliabilityResponse>(
    `/api/survey/${surveyId}/reliability`,
  )
  return data
}

/**
 * [getSurveyItemStats]
 * 설명: 설문별 문항 통계와 응답 분포 데이터를 조회한다.
 * 엔드포인트: GET /api/survey/:id/item-stats
 * 요청 타입: surveyId(path param)
 * 응답 타입: ItemStatsResponse
 * 백엔드 담당자 확인 필요 항목: distribution 배열 index가 척도값과 매칭되는 방식 정의 필요.
 */
export async function getSurveyItemStats(surveyId: string): Promise<ItemStatsResponse> {
  if (useMockApi) {
    return mockGetSurveyItemStats()
  }

  // [API 연동 필요 - 문항별 통계]
  // 엔드포인트: GET /api/survey/:id/item-stats
  // 응답: { items: { itemId: string, text: string, mean: number, variance: number, count: number, missing: number, distribution: number[] }[] }
  const { data } = await http.get<ItemStatsResponse>(`/api/survey/${surveyId}/item-stats`)
  return data
}
