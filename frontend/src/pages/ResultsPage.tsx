import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  BarChart3,
  ChevronDown,
  ClipboardCheck,
  FileText,
  ShieldCheck,
} from 'lucide-react'
import { useLocation, useParams } from 'react-router-dom'
import {
  evaluateSurveyConstruct,
  evaluateSurveyQuality,
  evaluateSurveyStatistics,
  getSurvey,
  getSurveyConstruct,
  getSurveyQuality,
  getSurveyReliability,
  getSurveyStatistics,
  readResponseResultFromStorage,
} from '../api/surveyApi'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ReliabilityBadge } from '../components/ReliabilityBadge'
import { ScoreBar } from '../components/ScoreBar'
import { useToastStore } from '../store/toastStore'
import type {
  BackendSurveyItem,
  CompactResponseFeatures,
  ConstructEvaluationItem,
  EvaluationStatus,
  QualityEvaluationItem,
  SurveyReliabilityResponse,
  StatisticsEvaluationResponse,
  SurveyResponseSubmitResult,
} from '../types/survey'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function getErrorMessage(error: unknown, fallback: string) {
  if (typeof error !== 'object' || error === null) {
    return fallback
  }

  const response = (error as { response?: { data?: unknown } }).response
  const data = response?.data

  if (typeof data === 'string') {
    return data
  }

  if (typeof data === 'object' && data !== null) {
    const detail = (data as { detail?: unknown; error?: unknown; message?: unknown }).detail
    const apiError = (data as { error?: unknown }).error
    const message = (data as { message?: unknown }).message

    if (typeof detail === 'string') {
      return detail
    }

    if (typeof apiError === 'string') {
      return apiError
    }

    if (typeof message === 'string') {
      return message
    }
  }

  return fallback
}

function compactError(error: unknown) {
  if (typeof error !== 'object' || error === null) {
    return error ?? null
  }

  const message = (error as { message?: unknown }).message
  const response = (error as { response?: { status?: unknown; data?: unknown } }).response

  return {
    message: typeof message === 'string' ? message : null,
    status: response?.status ?? null,
    data: response?.data ?? null,
  }
}

function summarizeQualityLlmFailures(items: QualityEvaluationItem[]) {
  const failedItems = items.filter((item) => item.quality_score == null && item.llm_error)

  if (failedItems.length === 0) {
    return null
  }

  const firstError = failedItems[0]?.llm_error ?? ''

  if (firstError.includes('insufficient_quota')) {
    return `OpenAI 할당량 부족으로 ${failedItems.length}개 문항의 LLM 평가가 실패했습니다.`
  }

  if (firstError.includes('OPENAI_API_KEY is not configured')) {
    return `OPENAI_API_KEY 미설정으로 ${failedItems.length}개 문항의 LLM 평가가 실패했습니다.`
  }

  return `${failedItems.length}개 문항의 LLM 평가가 실패했습니다. 백엔드 설정/로그를 확인해 주세요.`
}

function statusLabel(status?: EvaluationStatus) {
  if (status === 'good') {
    return '신뢰도 높음'
  }

  if (status === 'warning') {
    return '주의'
  }

  if (status === 'bad') {
    return '신뢰도 낮음'
  }

  return '결과 없음'
}

function statusClassName(status?: EvaluationStatus) {
  if (status === 'good') {
    return 'bg-emerald-50 text-emerald-700 ring-emerald-200'
  }

  if (status === 'warning') {
    return 'bg-amber-50 text-amber-700 ring-amber-200'
  }

  if (status === 'bad') {
    return 'bg-rose-50 text-rose-700 ring-rose-200'
  }

  return 'bg-slate-100 text-slate-600 ring-slate-200'
}

function DetailButton({
  open,
  onClick,
  label = '자세히 보기',
}: {
  open: boolean
  onClick: () => void
  label?: string
}) {
  return (
    <button
      type="button"
      className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
      onClick={onClick}
    >
      {open ? '접기' : label}
      <ChevronDown size={16} className={open ? 'rotate-180 transition' : 'transition'} />
    </button>
  )
}

function numberFeature(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function formatValue(value: unknown, unit = '', maximumFractionDigits = 1) {
  const number = numberFeature(value)

  if (number == null) {
    return '데이터 없음'
  }

  return `${number.toLocaleString('ko-KR', { maximumFractionDigits })}${unit}`
}

function formatMs(value: unknown) {
  const ms = numberFeature(value)

  if (ms == null) {
    return '데이터 없음'
  }

  if (ms < 1000) {
    return `${Math.round(ms).toLocaleString('ko-KR')}ms`
  }

  return `${(ms / 1000).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}초`
}

function formatRatio(value: unknown) {
  const ratio = numberFeature(value)
  if (ratio == null) {
    return '데이터 없음'
  }

  return `${(ratio * 100).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}%`
}

function ResponseFeatureDetails({ features }: { features?: CompactResponseFeatures }) {
  if (!features) {
    return (
      <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
        제출된 응답 feature 데이터가 아직 없습니다.
      </p>
    )
  }

  const rows = [
    { label: '문항당 평균 응답 시간', value: formatMs(features.avg_item_time_ms) },
    { label: '너무 빠른 응답 비율', value: formatRatio(features.too_fast_item_ratio) },
    { label: '답안 변경 비율', value: formatRatio(features.answer_changed_ratio) },
    { label: '재방문 문항 비율', value: formatRatio(features.revisit_item_ratio) },
    { label: '오프라인 비율', value: formatRatio(features.offline_ratio) },
    { label: '함정 문항 실패 비율', value: formatRatio(features.trap_fail_ratio) },
    { label: '역문항 일관성 점수', value: formatRatio(features.reverse_consistency_score) },
    { label: '분석 문항 수', value: formatValue(features.item_count, '개', 0) },
  ]

  return (
    <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <h3 className="text-sm font-black text-slate-950">응답 로그 상세</h3>
      <dl className="mt-3 space-y-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-start justify-between gap-3">
            <dt className="text-sm font-semibold text-slate-600">{row.label}</dt>
            <dd className="text-sm font-black text-slate-900">{row.value}</dd>
          </div>
        ))}
      </dl>
    </article>
  )
}

type QualityDisplayItem = QualityEvaluationItem & {
  item_role: BackendSurveyItem['item_role']
}

function QualityRow({
  item,
  open,
  onToggle,
}: {
  item: QualityDisplayItem
  open: boolean
  onToggle: () => void
}) {
  if (item.item_role !== 'normal') {
    const isReverse = item.item_role === 'reverse'

    return (
      <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-black text-slate-700">
            Q{item.item_order}
          </span>
          <span
            className={`rounded-md px-2 py-1 text-xs font-black ring-1 ${
              isReverse
                ? 'bg-indigo-50 text-indigo-700 ring-indigo-200'
                : 'bg-rose-50 text-rose-700 ring-rose-200'
            }`}
          >
            {isReverse ? '역문항' : '함정문항'}
          </span>
          <span className="text-xs font-bold text-slate-500">평가 제외 문항</span>
        </div>
        <p className="text-sm leading-6 text-slate-800">{item.question_text}</p>
      </article>
    )
  }

  const hasLlmError = Boolean(item.llm_error?.trim())
  const problem = item.status === 'warning' || item.status === 'bad' || hasLlmError

  return (
    <article
      className={`rounded-lg border p-4 ${
        problem ? 'border-amber-200 bg-amber-50/60' : 'border-slate-200 bg-white'
      }`}
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-black text-slate-700">
              Q{item.item_order}
            </span>
            <span
              className={`rounded-md px-2 py-1 text-xs font-black ring-1 ${statusClassName(
                item.status,
              )}`}
            >
              {item.status}
            </span>
            <span className="text-sm font-black text-slate-900">
              {item.quality_score == null ? '점수 없음' : `${item.quality_score}/10`}
            </span>
          </div>
          <p className="text-sm leading-6 text-slate-800">{item.question_text}</p>
        </div>
        {item.llm_comment || item.suggested_rewrite || hasLlmError ? (
          <DetailButton open={open} onClick={onToggle} label="제안본 보기" />
        ) : null}
      </div>

      {open ? (
        <div className="mt-4 space-y-3 rounded-lg border border-white bg-white p-4 text-sm leading-6 text-slate-700">
          {hasLlmError ? (
            <div className="rounded-md bg-rose-50 p-3 text-rose-900">
              <p className="font-black">LLM 평가 오류</p>
              <p className="mt-1 break-all text-xs leading-5">{item.llm_error}</p>
            </div>
          ) : null}
          {item.llm_comment ? (
            <div>
              <p className="font-black text-slate-900">LLM 코멘트</p>
              <p className="mt-1">{item.llm_comment}</p>
            </div>
          ) : null}
          {item.suggested_rewrite ? (
            <div>
              <p className="font-black text-slate-900">제안본</p>
              <p className="mt-1 rounded-md bg-teal-50 p-3 font-semibold text-teal-900">
                {item.suggested_rewrite}
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
    </article>
  )
}

function ConstructRow({ item }: { item: ConstructEvaluationItem }) {
  const status = item.status ?? 'unknown'

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-black text-slate-700">
              Q{item.item_order}
            </span>
            <span className={`rounded-md px-2 py-1 text-xs font-black ring-1 ${statusClassName(status)}`}>
              {status}
            </span>
            {item.combined_score != null ? (
              <span className="text-sm font-black text-slate-900">
                {item.combined_score.toFixed(2)}/10
              </span>
            ) : null}
          </div>
          <p className="text-sm leading-6 text-slate-800">{item.question_text}</p>
        </div>
      </div>
    </article>
  )
}

function StatisticsPanel({ statistics }: { statistics?: StatisticsEvaluationResponse }) {
  if (!statistics || statistics.result === null) {
    return (
      <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
        저장된 통계 분석 결과가 없습니다. 응답이 충분히 쌓인 뒤 통계 분석을 실행해 주세요.
      </p>
    )
  }

  if (statistics.error) {
    return (
      <p className="rounded-lg bg-amber-50 p-4 text-sm font-semibold leading-6 text-amber-900">
        {statistics.error}
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-xs font-black text-slate-500">응답 수</p>
          <p className="mt-1 text-2xl font-black text-slate-950">{statistics.response_count}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-xs font-black text-slate-500">Cronbach alpha</p>
          <p className="mt-1 text-2xl font-black text-slate-950">
            {statistics.cronbach_alpha == null ? '-' : statistics.cronbach_alpha}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-xs font-black text-slate-500">상태</p>
          <span
            className={`mt-2 inline-flex rounded-md px-2 py-1 text-xs font-black ring-1 ${statusClassName(
              statistics.alpha_status,
            )}`}
          >
            {statistics.alpha_status ?? 'unknown'}
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-separate border-spacing-0 text-left text-sm">
          <thead>
            <tr className="text-xs font-black uppercase text-slate-500">
              <th className="border-b border-slate-200 px-3 py-2">문항</th>
              <th className="border-b border-slate-200 px-3 py-2">CITC</th>
              <th className="border-b border-slate-200 px-3 py-2">CITC 상태</th>
              <th className="border-b border-slate-200 px-3 py-2">제거 시 alpha</th>
            </tr>
          </thead>
          <tbody>
            {statistics.items?.map((item) => {
              const problem = item.citc_status === 'warning' || item.citc_status === 'bad'

              return (
                <tr key={item.item_id} className={problem ? 'bg-amber-50' : 'hover:bg-slate-50'}>
                  <td className="border-b border-slate-100 px-3 py-3">
                    <p className="font-black text-slate-800">Q{item.item_order}</p>
                    <p className="mt-1 text-slate-600">{item.question_text}</p>
                  </td>
                  <td className="border-b border-slate-100 px-3 py-3">{item.citc ?? '-'}</td>
                  <td className="border-b border-slate-100 px-3 py-3">
                    {item.citc_status ?? 'unknown'}
                  </td>
                  <td className="border-b border-slate-100 px-3 py-3">
                    {item.alpha_if_item_deleted ?? '-'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ReliabilityDistributionPanel({ data }: { data?: SurveyReliabilityResponse }) {
  const respondents = data?.respondents ?? []
  const fallbackHigh = respondents.filter((row) => row.reliabilityScore >= 75).length
  const fallbackMid = respondents.filter(
    (row) => row.reliabilityScore >= 55 && row.reliabilityScore < 75,
  ).length
  const fallbackLow = respondents.filter((row) => row.reliabilityScore < 55).length

  const high = data?.high_count ?? fallbackHigh
  const mid = data?.mid_count ?? fallbackMid
  const low = data?.low_count ?? fallbackLow
  const total = data?.total_count ?? respondents.length

  const chartData = [
    { label: '상', count: high, color: '#10b981' },
    { label: '중', count: mid, color: '#f59e0b' },
    { label: '하', count: low, color: '#ef4444' },
  ]

  if (total <= 0) {
    return (
      <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
        신뢰도 분포를 표시할 응답이 아직 없습니다.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm font-bold text-slate-600">
        총 응답 {total}명 (상 {high}명 / 중 {mid}명 / 하 {low}명)
      </p>
      <div className="h-64 w-full rounded-lg border border-slate-200 bg-slate-50 p-3">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 10, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="label" tick={{ fill: '#334155', fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fill: '#334155', fontSize: 12 }} />
            <Tooltip
              formatter={(value) => [`${Number(value ?? 0)}명`, '응답 수']}
              cursor={{ fill: '#f1f5f9' }}
            />
            <Bar dataKey="count" radius={[6, 6, 0, 0]}>
              {chartData.map((entry) => (
                <Cell key={entry.label} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export function ResultsPage() {
  const { id = 'demo' } = useParams()
  const location = useLocation()
  const queryClient = useQueryClient()
  const { pushToast } = useToastStore()
  const [responseDetailsOpen, setResponseDetailsOpen] = useState(false)
  const [openQualityItemId, setOpenQualityItemId] = useState<string | null>(null)

  const responseResult =
    (location.state as { responseResult?: SurveyResponseSubmitResult } | null)?.responseResult ??
    readResponseResultFromStorage(id)

  const surveyQuery = useQuery({
    queryKey: ['survey', id],
    queryFn: () => getSurvey(id),
    enabled: Boolean(id) && id !== 'demo',
  })

  const qualityQuery = useQuery({
    queryKey: ['survey-quality', id],
    queryFn: () => getSurveyQuality(id),
    enabled: Boolean(id) && id !== 'demo',
    retry: false,
  })

  const constructQuery = useQuery({
    queryKey: ['survey-construct', id],
    queryFn: () => getSurveyConstruct(id),
    enabled: Boolean(id) && id !== 'demo',
    retry: false,
  })

  const statisticsQuery = useQuery({
    queryKey: ['survey-statistics', id],
    queryFn: () => getSurveyStatistics(id),
    enabled: Boolean(id) && id !== 'demo',
    retry: false,
  })

  const reliabilityQuery = useQuery({
    queryKey: ['survey-reliability', id],
    queryFn: () => getSurveyReliability(id),
    enabled: Boolean(id) && id !== 'demo',
    retry: false,
  })

  const qualityMutation = useMutation({
    mutationFn: () => evaluateSurveyQuality(id),
    onSuccess: (data) => {
      console.log('[results] quality mutation response', data)
      queryClient.invalidateQueries({ queryKey: ['survey-quality', id] })
      const llmFailureMessage = summarizeQualityLlmFailures(data.results)

      if (llmFailureMessage) {
        pushToast({
          type: 'error',
          title: '문항 품질 평가 실패',
          description: llmFailureMessage,
        })
        return
      }

      pushToast({ type: 'success', title: '문항 품질 평가 완료' })
    },
    onError: (error) => {
      console.error('[results] quality mutation failed', error)
      pushToast({
        type: 'error',
        title: '문항 품질 평가 실패',
        description: getErrorMessage(error, '평가 실행 중 오류가 발생했습니다.'),
      })
    },
  })

  const constructMutation = useMutation({
    mutationFn: () => evaluateSurveyConstruct(id),
    onSuccess: (data) => {
      console.log('[results] construct mutation response', data)
      queryClient.invalidateQueries({ queryKey: ['survey-construct', id] })
      pushToast({ type: 'success', title: '문항 구성 타당도 평가 완료' })
    },
    onError: (error) => {
      console.error('[results] construct mutation failed', error)
      pushToast({
        type: 'error',
        title: '문항 구성 타당도 평가 실패',
        description: getErrorMessage(error, '평가 실행 중 오류가 발생했습니다.'),
      })
    },
  })

  const statisticsMutation = useMutation({
    mutationFn: () => evaluateSurveyStatistics(id),
    onSuccess: (data) => {
      console.log('[results] statistics mutation response', data)
      queryClient.invalidateQueries({ queryKey: ['survey-statistics', id] })
      pushToast({ type: 'success', title: '통계 분석 완료' })
    },
    onError: (error) => {
      console.error('[results] statistics mutation failed', error)
      pushToast({
        type: 'error',
        title: '통계 분석 실패',
        description: getErrorMessage(error, '응답 수가 충분한지 확인해 주세요.'),
      })
    },
  })

  const evaluationPending =
    qualityMutation.isPending || constructMutation.isPending || statisticsMutation.isPending

  const qualityResults = qualityQuery.data?.results ?? []
  const constructResults = constructQuery.data?.results ?? []
  const surveyItems = surveyQuery.data?.items ?? []
  const qualityResultMap = useMemo(
    () => new Map(qualityResults.map((item) => [item.item_id, item])),
    [qualityResults],
  )

  const qualityDisplayItems: QualityDisplayItem[] = useMemo(
    () =>
      surveyItems.map((surveyItem) => {
        const quality = qualityResultMap.get(surveyItem.item_id)

        if (quality) {
          return {
            ...quality,
            item_role: surveyItem.item_role,
          }
        }

        return {
          item_id: surveyItem.item_id,
          item_order: surveyItem.item_order,
          question_text: surveyItem.question_text,
          quality_score: null,
          status: 'unknown',
          problem_categories: null,
          detected_terms: null,
          llm_comment: null,
          suggested_rewrite: null,
          llm_error: null,
          created_at: null,
          item_role: surveyItem.item_role,
        }
      }),
    [qualityResultMap, surveyItems],
  )

  const evaluationTargetItems = qualityDisplayItems.filter((item) => item.item_role === 'normal')
  const evaluatedQualityCount = evaluationTargetItems.filter((item) => item.quality_score != null).length
  const problemQualityCount = evaluationTargetItems.filter(
    (item) => item.status === 'warning' || item.status === 'bad',
  ).length

  const responseScore = responseResult?.reliability?.score ?? responseResult?.features.reliability_score
  const responseStatus =
    responseResult?.reliability?.status ?? responseResult?.features.reliability_status
  const reliabilityRespondentCount = reliabilityQuery.data?.total_count ?? reliabilityQuery.data?.respondents.length ?? 0

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm font-bold text-teal-700">설문 ID: {id}</p>
            <h1 className="mt-1 text-2xl font-black text-slate-950">
              {surveyQuery.data?.title ?? '응답 및 평가 결과'}
            </h1>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              응답 신뢰도, 문항 평가, 통계 분석 결과를 한 화면에서 확인합니다.
            </p>
          </div>
          {surveyQuery.isLoading ? <LoadingSpinner compact label="설문 조회 중" /> : null}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
              <ShieldCheck size={22} />
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-950">응답 신뢰도 요약</h2>
              <p className="mt-1 text-sm text-slate-600">응답 제출 직후 계산된 결과입니다.</p>
            </div>
          </div>
          {responseScore != null ? (
            <ReliabilityBadge score={responseScore} showScore />
          ) : (
            <span className="rounded-md bg-slate-100 px-3 py-2 text-sm font-bold text-slate-600">
              응답 결과 없음
            </span>
          )}
        </div>

        <p className="mt-3 text-sm font-semibold text-slate-600">
          전체 응답 기준 신뢰도 분포는 아래 통계 섹션에서 확인할 수 있습니다.
          {` (현재 누적 응답 ${reliabilityRespondentCount}명)`}
        </p>

        {responseScore != null ? (
          <div className="mt-5 space-y-4">
            <ScoreBar score={responseScore} label={`상태: ${statusLabel(responseStatus)}`} />
            <DetailButton
              open={responseDetailsOpen}
              onClick={() => setResponseDetailsOpen((open) => !open)}
            />
            {responseDetailsOpen ? (
              <ResponseFeatureDetails features={responseResult?.features} />
            ) : null}
          </div>
        ) : (
          <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            응답 화면에서 제출을 완료하면 신뢰도 요약이 표시됩니다.
          </p>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50 text-amber-700">
              <ClipboardCheck size={20} />
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-950">문항 품질 평가</h2>
              <p className="mt-1 text-sm text-slate-600">
                일반 문항만 점수/상태를 표시하고, 역문항/함정문항은 태그로 구분합니다.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700 disabled:bg-slate-300"
            disabled={evaluationPending}
            onClick={() => qualityMutation.mutate()}
          >
            {qualityMutation.isPending ? <LoadingSpinner compact label="평가 중" /> : '문항 품질 평가'}
          </button>
        </div>

        <p className="mb-4 text-sm font-bold text-slate-600">
          전체 문항: {qualityDisplayItems.length}개 / 평가 대상 문항: {evaluationTargetItems.length}
          개 / 평가 완료: {evaluatedQualityCount}개 / 문제 문항: {problemQualityCount}개
        </p>

        <div className="space-y-3">
          {qualityDisplayItems.length > 0 ? (
            qualityDisplayItems.map((item) => (
              <QualityRow
                key={item.item_id}
                item={item}
                open={openQualityItemId === item.item_id}
                onToggle={() =>
                  setOpenQualityItemId((current) =>
                    current === item.item_id ? null : item.item_id,
                  )
                }
              />
            ))
          ) : (
            <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
              저장된 품질 평가 결과가 없습니다. 버튼을 눌러 평가를 실행해 주세요.
            </p>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700">
              <FileText size={20} />
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-950">문항 구성 타당도 평가</h2>
              <p className="mt-1 text-sm text-slate-600">일반 문항 기준으로 결과를 제공합니다.</p>
            </div>
          </div>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:bg-slate-300"
            disabled={evaluationPending}
            onClick={() => constructMutation.mutate()}
          >
            {constructMutation.isPending ? (
              <LoadingSpinner compact label="평가 중" />
            ) : (
              '문항 구성 타당도 평가'
            )}
          </button>
        </div>

        <div className="space-y-3">
          {constructResults.length > 0 ? (
            constructResults.map((item) => (
              <ConstructRow key={item.item_id} item={item} />
            ))
          ) : (
            <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
              저장된 구성 타당도 평가 결과가 없습니다.
            </p>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-800">
              <BarChart3 size={20} />
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-950">통계 분석</h2>
              <p className="mt-1 text-sm text-slate-600">
                응답 수가 충분할 때 Cronbach alpha와 CITC를 확인할 수 있습니다.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:bg-slate-100"
            disabled={evaluationPending}
            onClick={() => statisticsMutation.mutate()}
          >
            {statisticsMutation.isPending ? <LoadingSpinner compact label="분석 중" /> : '통계 분석'}
          </button>
        </div>

        {statisticsQuery.isError ? (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-amber-50 p-4 text-sm font-semibold text-amber-900">
            <AlertTriangle size={18} />
            통계 결과를 조회하지 못했습니다. 아직 분석 결과가 없을 수 있습니다.
          </div>
        ) : null}

        <div className="mb-5 rounded-lg border border-slate-200 p-4">
          <h3 className="text-base font-black text-slate-950">응답 신뢰도 분포</h3>
          <p className="mt-1 text-sm text-slate-600">
            최근 1건이 아닌 전체 응답 기준으로 상/중/하 인원을 보여줍니다.
          </p>
          <div className="mt-3">
            {reliabilityQuery.isLoading ? (
              <LoadingSpinner compact label="신뢰도 분포 불러오는 중" />
            ) : reliabilityQuery.isError ? (
              <div className="rounded-lg bg-amber-50 p-4 text-sm font-semibold text-amber-900">
                신뢰도 분포를 불러오지 못했습니다.
              </div>
            ) : (
              <ReliabilityDistributionPanel data={reliabilityQuery.data} />
            )}
          </div>
        </div>

        <StatisticsPanel statistics={statisticsQuery.data} />
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-black text-slate-950">디버깅 응답(JSON)</h2>
        <p className="mt-1 text-sm text-slate-600">평가 API 응답 원문을 확인할 수 있습니다.</p>
        <pre className="mt-3 max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
{JSON.stringify(
  {
    surveyId: id,
    quality: qualityQuery.data ?? null,
    construct: constructQuery.data ?? null,
    statistics: statisticsQuery.data ?? null,
    reliability: reliabilityQuery.data ?? null,
    qualityQueryError: compactError(qualityQuery.error),
    constructQueryError: compactError(constructQuery.error),
    statisticsQueryError: compactError(statisticsQuery.error),
    reliabilityQueryError: compactError(reliabilityQuery.error),
  },
  null,
  2,
)}
        </pre>
      </section>
    </div>
  )
}
