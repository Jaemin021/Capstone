import { useState } from 'react'
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
  getSurveyStatistics,
  readResponseResultFromStorage,
} from '../api/surveyApi'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ReliabilityBadge } from '../components/ReliabilityBadge'
import { ScoreBar } from '../components/ScoreBar'
import { useToastStore } from '../store/toastStore'
import type {
  CompactResponseFeatures,
  ConstructEvaluationItem,
  EvaluationStatus,
  QualityEvaluationItem,
  StatisticsEvaluationResponse,
  SurveyResponseSubmitResult,
} from '../types/survey'

function statusLabel(status?: EvaluationStatus) {
  if (status === 'good') {
    return '신뢰 가능'
  }

  if (status === 'warning') {
    return '주의'
  }

  if (status === 'bad') {
    return '신뢰 낮음'
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

function formatDecimal(value: unknown, unit = '', maximumFractionDigits = 1) {
  const number = numberFeature(value)

  if (number == null) {
    return '데이터 없음'
  }

  return `${number.toLocaleString('ko-KR', { maximumFractionDigits })}${unit}`
}

function formatMilliseconds(value: unknown) {
  const ms = numberFeature(value)

  if (ms == null) {
    return '데이터 없음'
  }

  if (ms < 1000) {
    return `${Math.round(ms).toLocaleString('ko-KR')}ms`
  }

  return `${(ms / 1000).toLocaleString('ko-KR', {
    maximumFractionDigits: 1,
  })}초`
}

function formatRatio(value: unknown) {
  const ratio = numberFeature(value)

  if (ratio == null) {
    return '데이터 없음'
  }

  return `${(ratio * 100).toLocaleString('ko-KR', {
    maximumFractionDigits: 1,
  })}%`
}

function formatConnectionLost(value: unknown) {
  const number = numberFeature(value)

  if (number == null) {
    return '데이터 없음'
  }

  return number > 0 ? '있음' : '없음'
}

function ResponseFeatureDetails({ features }: { features?: CompactResponseFeatures }) {
  if (!features) {
    return (
      <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
        제출된 응답 세부 정보가 아직 없습니다.
      </p>
    )
  }

  const groups = [
    {
      title: '응답 시간',
      description: '문항을 읽고 선택하는 데 걸린 시간을 봅니다.',
      items: [
        { label: '문항당 평균 응답 시간', value: formatMilliseconds(features.avg_item_time_ms) },
        {
          label: '너무 빠르게 응답한 문항',
          value: formatRatio(features.too_fast_item_ratio),
        },
        {
          label: '첫 선택까지 평균 시간',
          value: formatMilliseconds(features.mean_time_to_first_answer_ms),
        },
        {
          label: '첫 선택까지 최단 시간',
          value: formatMilliseconds(features.min_time_to_first_answer_ms),
        },
        {
          label: '마지막 선택 후 이동까지 평균 시간',
          value: formatMilliseconds(features.mean_time_after_last_answer_ms),
        },
      ],
    },
    {
      title: '수정 및 재방문',
      description: '답을 바꾸거나 이전 문항으로 돌아간 흔적을 봅니다.',
      items: [
        { label: '문항당 평균 클릭/터치', value: formatDecimal(features.avg_touch_per_item, '회') },
        { label: '문항당 평균 답변 수정', value: formatDecimal(features.mean_change_count, '회') },
        { label: '전체 답변 수정 횟수', value: formatDecimal(features.total_change_count, '회', 0) },
        { label: '문항당 평균 방문 횟수', value: formatDecimal(features.mean_visit_count, '회') },
        {
          label: '문항당 평균 뒤로가기 방문',
          value: formatDecimal(features.mean_back_visit_count, '회'),
        },
        { label: '전체 뒤로가기 횟수', value: formatDecimal(features.total_back_visit_count, '회', 0) },
        { label: '재방문 문항 비율', value: formatRatio(features.revisit_item_ratio) },
        { label: '답변 변경 문항 비율', value: formatRatio(features.answer_changed_ratio) },
        {
          label: '재방문 후 수정 비율',
          value: formatRatio(features.changed_after_revisit_ratio),
        },
        { label: '평균 재방문 시간', value: formatMilliseconds(features.mean_revisit_time_ms) },
        { label: '최대 재방문 시간', value: formatMilliseconds(features.max_revisit_time_ms) },
      ],
    },
    {
      title: '연결 및 검증',
      description: '네트워크 상태와 함정/역문항 관련 신호를 봅니다.',
      items: [
        { label: '오프라인 비율', value: formatRatio(features.offline_ratio) },
        { label: '응답 중 연결 끊김', value: formatConnectionLost(features.connection_lost) },
        { label: '함정 문항 실패 비율', value: formatRatio(features.trap_fail_ratio) },
        { label: '역문항 평균 차이', value: formatDecimal(features.reverse_avg_diff) },
        {
          label: '역문항 일관성 점수',
          value: formatRatio(features.reverse_consistency_score),
        },
        { label: '응답 시간 패턴 편차', value: formatDecimal(features.time_curve_deviation) },
        { label: '비교 응답 표본 수', value: formatDecimal(features.population_sample_count, '명', 0) },
        { label: '분석 문항 수', value: formatDecimal(features.item_count, '개', 0) },
      ],
    },
  ]

  return (
    <div className="grid gap-3 lg:grid-cols-3">
      {groups.map((group) => (
        <article key={group.title} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-black text-slate-950">{group.title}</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">{group.description}</p>
          <dl className="mt-4 space-y-3">
            {group.items.map((item) => (
              <div
                key={item.label}
                className="flex items-start justify-between gap-3 border-t border-slate-200 pt-3 first:border-t-0 first:pt-0"
              >
                <dt className="text-sm font-semibold leading-5 text-slate-600">{item.label}</dt>
                <dd className="shrink-0 text-right text-sm font-black text-slate-950">
                  {item.value}
                </dd>
              </div>
            ))}
          </dl>
        </article>
      ))}
    </div>
  )
}

function QualityRow({
  item,
  open,
  onToggle,
}: {
  item: QualityEvaluationItem
  open: boolean
  onToggle: () => void
}) {
  const problem = item.status === 'warning' || item.status === 'bad'

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
        {(item.llm_comment || item.suggested_rewrite) && problem ? (
          <DetailButton open={open} onClick={onToggle} label="수정 제안 보기" />
        ) : null}
      </div>

      {open ? (
        <div className="mt-4 space-y-3 rounded-lg border border-white bg-white p-4 text-sm leading-6 text-slate-700">
          {item.llm_comment ? (
            <div>
              <p className="font-black text-slate-900">LLM 코멘트</p>
              <p className="mt-1">{item.llm_comment}</p>
            </div>
          ) : null}
          {item.suggested_rewrite ? (
            <div>
              <p className="font-black text-slate-900">수정 제안</p>
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

function ConstructRow({
  item,
  open,
  onToggle,
}: {
  item: ConstructEvaluationItem
  open: boolean
  onToggle: () => void
}) {
  const status = item.status ?? 'unknown'
  const features = item.llm_features ?? {}
  const reason = typeof features.reason === 'string' ? features.reason : null
  const suggestion = typeof features.suggestion === 'string' ? features.suggestion : null

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
        {reason || suggestion ? <DetailButton open={open} onClick={onToggle} /> : null}
      </div>

      {open ? (
        <div className="mt-4 space-y-3 rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-700">
          {reason ? (
            <div>
              <p className="font-black text-slate-900">판단 근거</p>
              <p className="mt-1">{reason}</p>
            </div>
          ) : null}
          {suggestion ? (
            <div>
              <p className="font-black text-slate-900">제안</p>
              <p className="mt-1">{suggestion}</p>
            </div>
          ) : null}
        </div>
      ) : null}
    </article>
  )
}

function StatisticsPanel({ statistics }: { statistics?: StatisticsEvaluationResponse }) {
  if (!statistics || statistics.result === null) {
    return (
      <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
        저장된 통계 분석 결과가 없습니다. 응답이 2개 이상 쌓인 뒤 통계 분석을 실행해 주세요.
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

export function ResultsPage() {
  const { id = 'demo' } = useParams()
  const location = useLocation()
  const queryClient = useQueryClient()
  const { pushToast } = useToastStore()
  const [responseDetailsOpen, setResponseDetailsOpen] = useState(false)
  const [openQualityItemId, setOpenQualityItemId] = useState<string | null>(null)
  const [openConstructItemId, setOpenConstructItemId] = useState<string | null>(null)

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

  const qualityMutation = useMutation({
    mutationFn: () => evaluateSurveyQuality(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['survey-quality', id] })
      pushToast({ type: 'success', title: '문항 품질 평가 완료' })
    },
    onError: () => {
      pushToast({
        type: 'error',
        title: '문항 품질 평가 실패',
        description: 'OPENAI_API_KEY 또는 백엔드 로그를 확인해 주세요.',
      })
    },
  })

  const constructMutation = useMutation({
    mutationFn: () => evaluateSurveyConstruct(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['survey-construct', id] })
      pushToast({ type: 'success', title: '문항 구성 타당도 평가 완료' })
    },
    onError: () => {
      pushToast({
        type: 'error',
        title: '문항 구성 타당도 평가 실패',
        description: '실제 OpenAI API 키가 필요합니다.',
      })
    },
  })

  const statisticsMutation = useMutation({
    mutationFn: () => evaluateSurveyStatistics(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['survey-statistics', id] })
      pushToast({ type: 'success', title: '통계 분석 완료' })
    },
    onError: () => {
      pushToast({
        type: 'error',
        title: '통계 분석 실패',
        description: '응답 수가 충분한지 확인해 주세요.',
      })
    },
  })

  const qualityResults = qualityQuery.data?.results ?? []
  const constructResults = constructQuery.data?.results ?? []
  const problemQualityCount = qualityResults.filter(
    (item) => item.status === 'warning' || item.status === 'bad',
  ).length
  const responseScore = responseResult?.reliability?.score ?? responseResult?.features.reliability_score
  const responseStatus =
    responseResult?.reliability?.status ?? responseResult?.features.reliability_status

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
              기본 화면은 핵심 상태만 보여주고, 세부 feature와 LLM 코멘트는 펼쳐보기로 확인합니다.
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
              <p className="mt-1 text-sm text-slate-600">
                응답 제출 직후 백엔드가 계산한 feature를 기준으로 표시합니다.
              </p>
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
            응답 화면에서 설문을 제출하면 이곳에 신뢰도 요약이 표시됩니다.
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
                warning/bad 문항만 강조하고, LLM 코멘트는 필요할 때만 펼칩니다.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700 disabled:bg-slate-300"
            disabled={qualityMutation.isPending}
            onClick={() => qualityMutation.mutate()}
          >
            {qualityMutation.isPending ? <LoadingSpinner compact label="평가 중" /> : '문항 품질 평가'}
          </button>
        </div>

        <p className="mb-4 text-sm font-bold text-slate-600">
          문제 문항: {problemQualityCount}개 / 전체 {qualityResults.length}개
        </p>

        <div className="space-y-3">
          {qualityResults.length > 0 ? (
            qualityResults.map((item) => (
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
              저장된 품질 평가 결과가 없습니다. 버튼을 눌러 백엔드 평가를 실행하세요.
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
              <p className="mt-1 text-sm text-slate-600">
                이 문항이 설문 목적에 맞는지 상태 중심으로 확인합니다.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:bg-slate-300"
            disabled={constructMutation.isPending}
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
              <ConstructRow
                key={item.item_id}
                item={item}
                open={openConstructItemId === item.item_id}
                onToggle={() =>
                  setOpenConstructItemId((current) =>
                    current === item.item_id ? null : item.item_id,
                  )
                }
              />
            ))
          ) : (
            <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
              저장된 construct 평가 결과가 없습니다. 실제 OpenAI API 키가 있을 때 실행하세요.
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
                응답이 충분히 쌓이면 Cronbach alpha와 문항별 CITC를 확인합니다.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:bg-slate-100"
            disabled={statisticsMutation.isPending}
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

        <StatisticsPanel statistics={statisticsQuery.data} />
      </section>
    </div>
  )
}
