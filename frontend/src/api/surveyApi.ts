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
  BackendSurveyCreatePayload,
  BackendSurveyItem,
  BackendSurveyItemOption,
  BackendSurveyResponse,
  BackendSurveyUpdatePayload,
  CitcPredictRequest,
  CitcPredictResponse,
  ConstructEvaluationResponse,
  EvaluateItemQualityRequest,
  GenerateReverseRequest,
  GenerateReverseResponse,
  GenerateTrapRequest,
  GenerateTrapResponse,
  ItemQualityResult,
  ItemStatsResponse,
  QualityEvaluationResponse,
  StatisticsEvaluationResponse,
  SurveyListResponse,
  SurveyReliabilityResponse,
  SurveyResponseSubmitPayload,
  SurveyResponseSubmitResult,
} from '../types/survey'

export const DEFAULT_LIKERT_5_OPTIONS = [
  '전혀 그렇지 않다',
  '그렇지 않다',
  '보통이다',
  '그렇다',
  '매우 그렇다',
]

export const responseResultStorageKey = (surveyId: string) =>
  `survey-response-result:${surveyId}`

const createMockId = (prefix: string) =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? `${prefix}-${crypto.randomUUID()}`
    : `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`

const buildMockOptions = (itemId: string): BackendSurveyItemOption[] =>
  DEFAULT_LIKERT_5_OPTIONS.map((label, index) => ({
    option_id: `${itemId}-option-${index + 1}`,
    option_order: index + 1,
    option_label: label,
    option_score: index + 1,
  }))

function buildMockSurvey(payload: BackendSurveyCreatePayload): BackendSurveyResponse {
  const surveyId = createMockId('survey')
  const items: BackendSurveyItem[] = payload.items.map((item, index) => {
    const itemId = createMockId('item')

    return {
      item_id: itemId,
      item_order: index + 1,
      question_text: item.question_text,
      question_type: item.question_type,
      item_role: 'normal',
      is_generated: false,
      source_item_id: null,
      trap_correct_option_order: null,
      reverse_expected_rule: null,
      insert_after_index: null,
      options: item.options?.length
        ? item.options.map((option) => ({
            option_id: `${itemId}-option-${option.option_order}`,
            option_order: option.option_order,
            option_label: option.option_label,
            option_score: option.option_order,
          }))
        : buildMockOptions(itemId),
    }
  })

  return {
    survey_id: surveyId,
    title: payload.title,
    description: payload.description ?? null,
    construct_name: payload.construct_name ?? null,
    construct_description: payload.construct_description ?? null,
    status: 'draft',
    items,
    message: 'mock survey created',
  }
}

function getMockSurveyStorageKey(surveyId: string) {
  return `mock-survey:${surveyId}`
}

export function saveResponseResultToStorage(
  surveyId: string,
  result: SurveyResponseSubmitResult,
) {
  window.localStorage.setItem(responseResultStorageKey(surveyId), JSON.stringify(result))
}

export function readResponseResultFromStorage(surveyId: string) {
  const raw = window.localStorage.getItem(responseResultStorageKey(surveyId))
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as SurveyResponseSubmitResult
  } catch {
    return null
  }
}

export async function createSurvey(
  payload: BackendSurveyCreatePayload,
): Promise<BackendSurveyResponse> {
  if (useMockApi) {
    const survey = buildMockSurvey(payload)
    window.localStorage.setItem(getMockSurveyStorageKey(survey.survey_id), JSON.stringify(survey))
    return survey
  }

  const { data } = await http.post<BackendSurveyResponse>('/surveys/', payload)
  return data
}

export async function updateSurvey(
  surveyId: string,
  payload: BackendSurveyUpdatePayload,
): Promise<BackendSurveyResponse> {
  if (useMockApi) {
    const raw = window.localStorage.getItem(getMockSurveyStorageKey(surveyId))

    if (!raw) {
      throw new Error('Mock survey not found')
    }

    const current = JSON.parse(raw) as BackendSurveyResponse
    const items: BackendSurveyItem[] = payload.items.map((item, index) => {
      const itemId = createMockId('item')

      return {
        item_id: itemId,
        item_order: index + 1,
        question_text: item.question_text,
        question_type: item.question_type,
        item_role: 'normal',
        is_generated: false,
        source_item_id: null,
        trap_correct_option_order: null,
        reverse_expected_rule: null,
        insert_after_index: null,
        options: item.options?.length
          ? item.options.map((option) => ({
              option_id: `${itemId}-option-${option.option_order}`,
              option_order: option.option_order,
              option_label: option.option_label,
              option_score: option.option_order,
            }))
          : buildMockOptions(itemId),
      }
    })

    const updated: BackendSurveyResponse = {
      ...current,
      title: payload.title,
      description: payload.description ?? null,
      construct_name: payload.construct_name ?? null,
      construct_description: payload.construct_description ?? null,
      items,
      message: 'mock survey updated',
    }

    window.localStorage.setItem(getMockSurveyStorageKey(surveyId), JSON.stringify(updated))
    return updated
  }

  try {
    const { data } = await http.put<BackendSurveyResponse>(`/surveys/${surveyId}`, payload)
    return data
  } catch (error) {
    const status = (error as { response?: { status?: number } })?.response?.status

    if (status === 404 || status === 405) {
      const { data } = await http.patch<BackendSurveyResponse>(`/surveys/${surveyId}`, payload)
      return data
    }

    throw error
  }
}

export async function getSurvey(surveyId: string): Promise<BackendSurveyResponse> {
  if (useMockApi) {
    const raw = window.localStorage.getItem(getMockSurveyStorageKey(surveyId))

    if (!raw) {
      throw new Error('Mock survey not found')
    }

    return JSON.parse(raw) as BackendSurveyResponse
  }

  const { data } = await http.get<BackendSurveyResponse>(`/surveys/${surveyId}`)
  return data
}

export async function getSurveyList(): Promise<SurveyListResponse> {
  if (useMockApi) {
    const surveys = Object.keys(window.localStorage)
      .filter((key) => key.startsWith('mock-survey:'))
      .map((key) => {
        const survey = JSON.parse(window.localStorage.getItem(key) || '{}') as BackendSurveyResponse

        return {
          survey_id: survey.survey_id,
          title: survey.title,
          description: survey.description ?? null,
          construct_name: survey.construct_name ?? null,
          construct_description: survey.construct_description ?? null,
          status: survey.status ?? 'draft',
          item_count: survey.items?.length ?? 0,
          normal_item_count:
            survey.items?.filter((item) => item.item_role === 'normal').length ?? 0,
          response_count: 0,
          last_response_at: null,
        }
      })

    return { surveys }
  }

  const { data } = await http.get<SurveyListResponse>('/surveys/')
  return data
}

export async function deleteSurvey(surveyId: string): Promise<void> {
  if (useMockApi) {
    window.localStorage.removeItem(getMockSurveyStorageKey(surveyId))
    window.localStorage.removeItem(responseResultStorageKey(surveyId))
    return
  }

  try {
    await http.delete(`/surveys/${surveyId}`)
  } catch (error) {
    console.error('[survey] delete failed', {
      surveyId,
      error,
      response: (error as { response?: { data?: unknown; status?: number } })?.response,
    })
    throw error
  }
}

export async function submitSurveyResponse(
  surveyId: string,
  payload: SurveyResponseSubmitPayload,
): Promise<SurveyResponseSubmitResult> {
  if (useMockApi) {
    const itemCount = payload.log.item_logs.length || 1
    const tooFastRatio =
      payload.log.item_logs.filter((item) => item.item_time_ms < 1500).length / itemCount
    const changeRatio =
      payload.log.item_logs.filter((item) => item.answer_changed).length / itemCount
    const revisitRatio =
      payload.log.item_logs.filter((item) => item.is_revisited).length / itemCount
    const score = Math.max(
      0,
      Math.round(100 - tooFastRatio * 35 - changeRatio * 12 - revisitRatio * 8),
    )
    const status = score >= 75 ? 'good' : score >= 55 ? 'warning' : 'bad'

    const result: SurveyResponseSubmitResult = {
      response_id: createMockId('response'),
      survey_id: surveyId,
      response_feature_id: createMockId('feature'),
      log_features: { ...payload.log },
      content_features: {},
      population_features: {},
      relation_features: {},
      features: {
        avg_item_time_ms: payload.log.total_time_ms / itemCount,
        too_fast_item_ratio: tooFastRatio,
        answer_changed_ratio: changeRatio,
        revisit_item_ratio: revisitRatio,
        connection_lost: payload.log.connection_lost ? 1 : 0,
        offline_ratio:
          payload.log.total_time_ms > 0 ? payload.log.offline_total_ms / payload.log.total_time_ms : 0,
        item_count: itemCount,
        reliability_score: score,
        reliability_status: status,
      },
      reliability: {
        score,
        status,
        reasons: ['mock response log was processed locally'],
      },
      message: 'mock response and features created',
    }

    saveResponseResultToStorage(surveyId, result)
    return result
  }

  const { data } = await http.post<SurveyResponseSubmitResult>(
    `/surveys/${surveyId}/responses`,
    payload,
  )
  saveResponseResultToStorage(surveyId, data)
  return data
}

export async function evaluateSurveyQuality(
  surveyId: string,
): Promise<QualityEvaluationResponse> {
  const endpoint = `/survey-evaluations/${surveyId}/quality`
  console.log('[survey-eval] POST quality request', { surveyId, endpoint })
  try {
    const { data } = await http.post<QualityEvaluationResponse>(endpoint)
    console.log('[survey-eval] POST quality response', data)
    return data
  } catch (error) {
    console.error('[survey-eval] POST quality failed', {
      surveyId,
      endpoint,
      error,
      response: (error as { response?: { data?: unknown; status?: number } })?.response,
    })
    throw error
  }
}

export async function getSurveyQuality(
  surveyId: string,
): Promise<QualityEvaluationResponse> {
  const endpoint = `/survey-evaluations/${surveyId}/quality`
  try {
    const { data } = await http.get<QualityEvaluationResponse>(endpoint)
    console.log('[survey-eval] GET quality response', data)
    return data
  } catch (error) {
    console.error('[survey-eval] GET quality failed', {
      surveyId,
      endpoint,
      error,
      response: (error as { response?: { data?: unknown; status?: number } })?.response,
    })
    throw error
  }
}

export async function evaluateSurveyConstruct(
  surveyId: string,
): Promise<ConstructEvaluationResponse> {
  const endpoint = `/survey-evaluations/${surveyId}/construct`
  console.log('[survey-eval] POST construct request', { surveyId, endpoint })
  try {
    const { data } = await http.post<ConstructEvaluationResponse>(endpoint)
    console.log('[survey-eval] POST construct response', data)
    return data
  } catch (error) {
    console.error('[survey-eval] POST construct failed', {
      surveyId,
      endpoint,
      error,
      response: (error as { response?: { data?: unknown; status?: number } })?.response,
    })
    throw error
  }
}

export async function getSurveyConstruct(
  surveyId: string,
): Promise<ConstructEvaluationResponse> {
  const endpoint = `/survey-evaluations/${surveyId}/construct`
  try {
    const { data } = await http.get<ConstructEvaluationResponse>(endpoint)
    console.log('[survey-eval] GET construct response', data)
    return data
  } catch (error) {
    console.error('[survey-eval] GET construct failed', {
      surveyId,
      endpoint,
      error,
      response: (error as { response?: { data?: unknown; status?: number } })?.response,
    })
    throw error
  }
}

export async function evaluateSurveyStatistics(
  surveyId: string,
): Promise<StatisticsEvaluationResponse> {
  const { data } = await http.post<StatisticsEvaluationResponse>(
    `/survey-evaluations/${surveyId}/statistics`,
  )
  return data
}

export async function getSurveyStatistics(
  surveyId: string,
): Promise<StatisticsEvaluationResponse> {
  const { data } = await http.get<StatisticsEvaluationResponse>(
    `/survey-evaluations/${surveyId}/statistics`,
  )
  return data
}

export async function evaluateItemQuality(
  request: EvaluateItemQualityRequest,
): Promise<ItemQualityResult> {
  return mockEvaluateItemQuality(request)
}

export async function predictSurveyCitc(
  request: CitcPredictRequest,
): Promise<CitcPredictResponse> {
  return mockPredictCitc(request)
}

export async function generateTrapItem(
  request: GenerateTrapRequest,
): Promise<GenerateTrapResponse> {
  return mockGenerateTrapItem(request)
}

export async function generateReverseItem(
  request: GenerateReverseRequest,
): Promise<GenerateReverseResponse> {
  return mockGenerateReverseItem(request)
}

export async function getSurveyReliability(
  surveyId: string,
): Promise<SurveyReliabilityResponse> {
  if (useMockApi) {
    return mockGetSurveyReliability()
  }

  try {
    const { data } = await http.get<SurveyReliabilityResponse>(
      `/surveys/${surveyId}/reliability-distribution`,
    )
    return data
  } catch (error) {
    console.error('[survey] reliability distribution fetch failed', {
      surveyId,
      error,
      response: (error as { response?: { data?: unknown; status?: number } })?.response,
    })

    const stored = readResponseResultFromStorage(surveyId)
    if (!stored?.reliability) {
      return { respondents: [] }
    }

    return {
      total_count: 1,
      high_count: stored.reliability.status === 'good' ? 1 : 0,
      mid_count: stored.reliability.status === 'warning' ? 1 : 0,
      low_count: stored.reliability.status === 'bad' ? 1 : 0,
      distribution: [
        { level: 'high', label: '상', count: stored.reliability.status === 'good' ? 1 : 0 },
        { level: 'mid', label: '중', count: stored.reliability.status === 'warning' ? 1 : 0 },
        { level: 'low', label: '하', count: stored.reliability.status === 'bad' ? 1 : 0 },
      ],
      respondents: [
        {
          id: stored.response_id,
          submittedAt: new Date().toISOString(),
          reliabilityScore: stored.reliability.score,
          timePerItem: [Number(stored.features.avg_item_time_ms ?? 0) / 1000],
          flagged: stored.reliability.status === 'bad',
          reason: stored.reliability.reasons.join(', '),
        },
      ],
    }
  }
}

export async function getSurveyItemStats(surveyId: string): Promise<ItemStatsResponse> {
  if (useMockApi) {
    return mockGetSurveyItemStats()
  }

  const statistics = await getSurveyStatistics(surveyId)

  return {
    items:
      statistics.items?.map((item) => ({
        itemId: item.item_id,
        text: item.question_text,
        mean: item.citc ?? 0,
        variance: item.alpha_if_item_deleted ?? 0,
        count: statistics.response_count,
        missing: 0,
        distribution: [],
      })) ?? [],
  }
}
