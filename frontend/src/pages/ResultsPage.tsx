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
  downloadSurveyItemEvaluationsCsv,
  downloadSurveyResponseFeaturesCsv,
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
  ReliabilityStatus,
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
    const trimmed = data.trim()
    const looksLikeHtml =
      trimmed.startsWith('<!doctype html') ||
      trimmed.startsWith('<html') ||
      trimmed.includes('<head>') ||
      trimmed.includes('<body>')

    if (looksLikeHtml) {
      return 'API ????꾨줎??HTML???묐떟?섏뿀?듬땲?? VITE_API_BASE_URL ?먮뒗 ?꾨줉???쇱슦???ㅼ젙???뺤씤??二쇱꽭??'
    }

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
  const failedItems = items.filter((item) => Boolean(item.llm_error?.trim()))

  if (failedItems.length === 0) {
    return null
  }

  const firstError = failedItems[0]?.llm_error ?? ''

  if (firstError.includes('insufficient_quota')) {
    return `OpenAI ?좊떦??遺議깆쑝濡?${failedItems.length}媛?臾명빆??LLM ?됯?媛 ?ㅽ뙣?덉뒿?덈떎.`
  }

  if (firstError.includes('OPENAI_API_KEY is not configured')) {
    return `OPENAI_API_KEY 誘몄꽕?뺤쑝濡?${failedItems.length}媛?臾명빆??LLM ?됯?媛 ?ㅽ뙣?덉뒿?덈떎.`
  }

  return `${failedItems.length}媛?臾명빆??LLM ?됯?媛 ?ㅽ뙣?덉뒿?덈떎. 諛깆뿏???ㅼ젙/濡쒓렇瑜??뺤씤??二쇱꽭??`
}

function statusLabel(status?: EvaluationStatus | ReliabilityStatus) {
  if (status === 'sincere') {
    return '?깆떎'
  }

  if (status === 'insincere') {
    return '鍮꾩꽦??
  }

  if (status === 'good') {
    return '?좊ː???믪쓬'
  }

  if (status === 'ok') {
    return 'OK'
  }

  if (status === 'problem') {
    return '臾몄젣'
  }

  if (status === 'error') {
    return '?ㅻ쪟'
  }

  if (status === 'warning') {
    return '二쇱쓽'
  }

  if (status === 'bad') {
    return '?좊ː????쓬'
  }

  return '寃곌낵 ?놁쓬'
}

function statusClassName(status?: EvaluationStatus | ReliabilityStatus) {
  if (status === 'sincere' || status === 'good') {
    return 'bg-emerald-50 text-emerald-700 ring-emerald-200'
  }

  if (status === 'ok') {
    return 'bg-emerald-50 text-emerald-700 ring-emerald-200'
  }

  if (status === 'warning') {
    return 'bg-amber-50 text-amber-700 ring-amber-200'
  }

  if (status === 'problem') {
    return 'bg-amber-50 text-amber-700 ring-amber-200'
  }

  if (status === 'error') {
    return 'bg-rose-50 text-rose-700 ring-rose-200'
  }

  if (status === 'insincere' || status === 'bad') {
    return 'bg-rose-50 text-rose-700 ring-rose-200'
  }

  return 'bg-slate-100 text-slate-600 ring-slate-200'
}

function DetailButton({
  open,
  onClick,
  label = '?먯꽭??蹂닿린',
}: {
  open: boolean
  onClick: () => void
  label?: string
}) {
  return (
    <button
      type="button"
      className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
      onClick={(event) => {
        event.stopPropagation()
        onClick()
      }}
    >
      {open ? '?묎린' : label}
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
    return '?곗씠???놁쓬'
  }

  return `${number.toLocaleString('ko-KR', { maximumFractionDigits })}${unit}`
}

function formatMs(value: unknown) {
  const ms = numberFeature(value)

  if (ms == null) {
    return '?곗씠???놁쓬'
  }

  if (ms < 1000) {
    return `${Math.round(ms).toLocaleString('ko-KR')}ms`
  }

  return `${(ms / 1000).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}珥?
}

function formatRatio(value: unknown) {
  const ratio = numberFeature(value)
  if (ratio == null) {
    return '?곗씠???놁쓬'
  }

  return `${(ratio * 100).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}%`
}

function parseItemCategoryTokens(value?: string | null) {
  const raw = (value ?? '').trim()
  if (!raw) {
    return []
  }

  const unique: string[] = []
  const seen = new Set<string>()

  raw
    .split('/')
    .map((token) => token.trim())
    .filter((token) => token.length > 0)
    .forEach((token) => {
      const key = token.toLowerCase()
      if (!seen.has(key)) {
        seen.add(key)
        unique.push(token)
      }
    })

  return unique
}

function meanOrNull(sum: number, count: number) {
  if (count <= 0) {
    return null
  }
  return sum / count
}

function getConstructCombinedScore(item?: ConstructEvaluationItem) {
  if (!item) {
    return null
  }

  if (typeof item.combined_score === 'number' && Number.isFinite(item.combined_score)) {
    return item.combined_score
  }

  if (
    typeof item.embedding_score === 'number' &&
    Number.isFinite(item.embedding_score) &&
    typeof item.llm_score === 'number' &&
    Number.isFinite(item.llm_score)
  ) {
    return item.embedding_score * 0.4 + item.llm_score * 0.6
  }

  return null
}

type ItemFeatureSnapshot = {
  item_id: string
  item_order: number
  question_text: string
  item_category: string
  category_tokens: string[]
  quality_status: EvaluationStatus
  quality_has_problem: boolean
  quality_problem_categories: string[]
  quality_detected_terms: string[]
  construct_embedding_score: number | null
  construct_llm_score: number | null
  construct_combined_score: number | null
  construct_status: EvaluationStatus
  construct_predicted_citc: number | null
  construct_predicted_alpha_impact: number | null
  construct_embedding_features: Record<string, unknown> | null
  construct_llm_features: Record<string, unknown> | null
  statistics_item_citc: number | null
  statistics_item_citc_status: EvaluationStatus
  statistics_alpha_if_item_deleted: number | null
}

type CategoryFeatureSummary = {
  category: string
  item_count: number
  quality_problem_count: number
  quality_problem_ratio: number | null
  construct_avg: number | null
  citc_avg: number | null
  alpha_if_deleted_avg: number | null
}

function ResponseFeatureDetails({ features }: { features?: CompactResponseFeatures }) {
  if (!features) {
    return (
      <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
        ?쒖텧???묐떟 feature ?곗씠?곌? ?꾩쭅 ?놁뒿?덈떎.
      </p>
    )
  }

  const rows = [
    { label: '臾명빆???됯퇏 ?묐떟 ?쒓컙', value: formatMs(features.avg_item_time_ms) },
    { label: '?덈Т 鍮좊Ⅸ ?묐떟 鍮꾩쑉', value: formatRatio(features.too_fast_item_ratio) },
    { label: '?듭븞 蹂寃?鍮꾩쑉', value: formatRatio(features.answer_changed_ratio) },
    { label: '?щ갑臾?臾명빆 鍮꾩쑉', value: formatRatio(features.revisit_item_ratio) },
    { label: '?ㅽ봽?쇱씤 鍮꾩쑉', value: formatRatio(features.offline_ratio) },
    { label: '?⑥젙 臾명빆 ?ㅽ뙣 鍮꾩쑉', value: formatRatio(features.trap_fail_ratio) },
    { label: '??Ц???쇨????먯닔', value: formatRatio(features.reverse_consistency_score) },
    { label: '遺꾩꽍 臾명빆 ??, value: formatValue(features.item_count, '媛?, 0) },
  ]

  return (
    <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <h3 className="text-sm font-black text-slate-950">?묐떟 濡쒓렇 ?곸꽭</h3>
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
            {isReverse ? '??Ц?? : '?⑥젙臾명빆'}
          </span>
          <span className="text-xs font-bold text-slate-500">?됯? ?쒖쇅 臾명빆</span>
        </div>
        <p className="text-sm leading-6 text-slate-800">{item.question_text}</p>
      </article>
    )
  }

  const hasLlmError = Boolean(item.llm_error?.trim())
  const hasLlmComment = Boolean(item.llm_comment?.trim())
  const hasProblemFlag = Boolean(item.has_problem)
  const hasProblemCategory = (item.problem_categories?.length ?? 0) > 0
  const hasDetectedTerms = (item.detected_terms?.length ?? 0) > 0
  const isProblemStatus =
    item.status === 'problem' || item.status === 'warning' || item.status === 'bad'
  const isProblem = hasProblemFlag || hasProblemCategory || isProblemStatus
  const canOpenDetail =
    isProblem &&
    (hasLlmError || hasLlmComment || hasProblemCategory || hasDetectedTerms)
  const cardClassName = hasLlmError
    ? 'border-rose-200 bg-rose-50/40'
    : isProblem
      ? 'border-amber-200 bg-amber-50/60'
      : 'border-slate-200 bg-white'
  const statusText = hasLlmError ? 'error' : isProblem ? 'problem' : 'ok'

  return (
    <article
      onClick={canOpenDetail ? onToggle : undefined}
      className={`rounded-lg border p-4 ${cardClassName} ${canOpenDetail ? 'cursor-pointer' : ''}`}
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-black text-slate-700">
              Q{item.item_order}
            </span>
            <span
              className={`rounded-md px-2 py-1 text-xs font-black ring-1 ${statusClassName(
                statusText,
              )}`}
            >
              {statusText}
            </span>
          </div>
          <p className="text-sm leading-6 text-slate-800">{item.question_text}</p>
        </div>
        {isProblem && canOpenDetail ? (
          <DetailButton open={open} onClick={onToggle} />
        ) : null}
      </div>

      {open && canOpenDetail ? (
        <div className="mt-4 space-y-3 rounded-lg border border-white bg-white p-4 text-sm leading-6 text-slate-700">
          {hasLlmError ? (
            <div className="rounded-md bg-rose-50 p-3 text-rose-900">
              <p className="font-black">LLM ?됯? ?ㅻ쪟</p>
              <p className="mt-1 break-all text-xs leading-5">{item.llm_error}</p>
            </div>
          ) : null}
          {item.llm_comment ? (
            <div>
              <p className="font-black text-slate-900">LLM 肄붾찘??/p>
              <p className="mt-1">{item.llm_comment}</p>
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
        ??λ맂 ?듦퀎 遺꾩꽍 寃곌낵媛 ?놁뒿?덈떎. ?묐떟??異⑸텇???볦씤 ???듦퀎 遺꾩꽍???ㅽ뻾??二쇱꽭??
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
          <p className="text-xs font-black text-slate-500">?묐떟 ??/p>
          <p className="mt-1 text-2xl font-black text-slate-950">{statistics.response_count}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-xs font-black text-slate-500">Cronbach alpha</p>
          <p className="mt-1 text-2xl font-black text-slate-950">
            {statistics.cronbach_alpha == null ? '-' : statistics.cronbach_alpha}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-xs font-black text-slate-500">?곹깭</p>
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
              <th className="border-b border-slate-200 px-3 py-2">臾명빆</th>
              <th className="border-b border-slate-200 px-3 py-2">CITC</th>
              <th className="border-b border-slate-200 px-3 py-2">CITC ?곹깭</th>
              <th className="border-b border-slate-200 px-3 py-2">?쒓굅 ??alpha</th>
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
  const fallbackSincere = respondents.filter((row) => !row.flagged).length
  const fallbackInsincere = respondents.length - fallbackSincere

  const sincere = data?.sincere_count ?? data?.high_count ?? fallbackSincere
  const insincere = data?.insincere_count ?? data?.low_count ?? fallbackInsincere
  const total = data?.total_count ?? respondents.length

  const chartData = [
    { label: '?깆떎', count: sincere, color: '#10b981' },
    { label: '鍮꾩꽦??, count: insincere, color: '#ef4444' },
  ]

  if (total <= 0) {
    return (
      <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
        ?좊ː??遺꾪룷瑜??쒖떆???묐떟???꾩쭅 ?놁뒿?덈떎.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm font-bold text-slate-600">
        珥??묐떟 {total}紐?(?깆떎 {sincere}紐?/ 鍮꾩꽦??{insincere}紐?
      </p>
      <div className="h-64 w-full rounded-lg border border-slate-200 bg-slate-50 p-3">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 10, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="label" tick={{ fill: '#334155', fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fill: '#334155', fontSize: 12 }} />
            <Tooltip
              formatter={(value) => [`${Number(value ?? 0)}紐?, '?묐떟 ??]}
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

function CategoryFeaturePanel({ rows }: { rows: CategoryFeatureSummary[] }) {
  if (rows.length === 0) {
    return (
      <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
        ?좏삎蹂꾨줈 吏묎퀎???쇰컲 臾명빆???꾩쭅 ?놁뒿?덈떎.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] border-separate border-spacing-0 text-left text-sm">
        <thead>
          <tr className="text-xs font-black uppercase text-slate-500">
            <th className="border-b border-slate-200 px-3 py-2">?좏삎</th>
            <th className="border-b border-slate-200 px-3 py-2">臾명빆 ??/th>
            <th className="border-b border-slate-200 px-3 py-2">?덉쭏 臾몄젣 ??/th>
            <th className="border-b border-slate-200 px-3 py-2">?덉쭏 臾몄젣 鍮꾩쑉</th>
            <th className="border-b border-slate-200 px-3 py-2">援ъ꽦 ?됯퇏</th>
            <th className="border-b border-slate-200 px-3 py-2">CITC ?됯퇏</th>
            <th className="border-b border-slate-200 px-3 py-2">alpha(臾명빆 ?쒓굅 ?? ?됯퇏</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.category} className="hover:bg-slate-50">
              <td className="border-b border-slate-100 px-3 py-3 font-semibold text-slate-800">
                {row.category}
              </td>
              <td className="border-b border-slate-100 px-3 py-3">{row.item_count}</td>
              <td className="border-b border-slate-100 px-3 py-3">
                {row.quality_problem_count}
              </td>
              <td className="border-b border-slate-100 px-3 py-3">
                {row.quality_problem_ratio == null
                  ? '-'
                  : `${(row.quality_problem_ratio * 100).toFixed(1)}%`}
              </td>
              <td className="border-b border-slate-100 px-3 py-3">
                {row.construct_avg == null ? '-' : row.construct_avg.toFixed(2)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3">
                {row.citc_avg == null ? '-' : row.citc_avg.toFixed(3)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3">
                {row.alpha_if_deleted_avg == null ? '-' : row.alpha_if_deleted_avg.toFixed(3)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ItemFeaturePanel({ rows }: { rows: ItemFeatureSnapshot[] }) {
  if (rows.length === 0) {
    return (
      <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
        臾명빆蹂?feature瑜??쒖떆???쇰컲 臾명빆???꾩쭅 ?놁뒿?덈떎.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <details key={row.item_id} className="rounded-lg border border-slate-200 bg-white p-4">
          <summary className="cursor-pointer list-none">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-black text-slate-900">Q{row.item_order}</p>
                <p className="mt-1 text-sm text-slate-700">{row.question_text}</p>
                <p className="mt-1 text-xs font-semibold text-indigo-700">
                  ?좏삎: {row.item_category || '(誘몃텇瑜?'}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700">
                  ?덉쭏 {row.quality_status === 'unknown' ? '-' : row.quality_has_problem ? '臾몄젣' : 'OK'}
                </span>
                <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700">
                  援ъ꽦 {row.construct_combined_score == null ? '-' : row.construct_combined_score.toFixed(2)}
                </span>
                <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700">
                  CITC {row.statistics_item_citc == null ? '-' : row.statistics_item_citc.toFixed(3)}
                </span>
              </div>
            </div>
          </summary>

          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            <article className="rounded-lg bg-slate-50 p-3">
              <h4 className="text-xs font-black uppercase text-slate-600">?덉쭏 Feature</h4>
              <dl className="mt-2 space-y-1 text-sm text-slate-700">
                <div className="flex justify-between gap-2">
                  <dt>臾몄젣 ?щ?</dt>
                  <dd>{row.quality_status === 'unknown' ? '-' : row.quality_has_problem ? 'problem' : 'ok'}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>?곹깭</dt>
                  <dd>{row.quality_status}</dd>
                </div>
                <div>
                  <dt className="font-semibold">臾몄젣 移댄뀒怨좊━</dt>
                  <dd className="mt-1">
                    {row.quality_problem_categories.length > 0
                      ? row.quality_problem_categories.join(', ')
                      : '-'}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold">媛먯? ?쒗쁽</dt>
                  <dd className="mt-1">
                    {row.quality_detected_terms.length > 0
                      ? row.quality_detected_terms.join(', ')
                      : '-'}
                  </dd>
                </div>
              </dl>
            </article>

            <article className="rounded-lg bg-slate-50 p-3">
              <h4 className="text-xs font-black uppercase text-slate-600">援ъ꽦 Feature</h4>
              <dl className="mt-2 space-y-1 text-sm text-slate-700">
                <div className="flex justify-between gap-2">
                  <dt>Embedding</dt>
                  <dd>{row.construct_embedding_score == null ? '-' : row.construct_embedding_score.toFixed(3)}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>LLM</dt>
                  <dd>{row.construct_llm_score == null ? '-' : row.construct_llm_score.toFixed(3)}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>Combined</dt>
                  <dd>{row.construct_combined_score == null ? '-' : row.construct_combined_score.toFixed(3)}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>?덉륫 CITC</dt>
                  <dd>{row.construct_predicted_citc == null ? '-' : row.construct_predicted_citc.toFixed(3)}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>?덉륫 Alpha ?곹뼢</dt>
                  <dd>
                    {row.construct_predicted_alpha_impact == null
                      ? '-'
                      : row.construct_predicted_alpha_impact.toFixed(3)}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>?곹깭</dt>
                  <dd>{row.construct_status}</dd>
                </div>
              </dl>
            </article>

            <article className="rounded-lg bg-slate-50 p-3">
              <h4 className="text-xs font-black uppercase text-slate-600">?듦퀎 Feature</h4>
              <dl className="mt-2 space-y-1 text-sm text-slate-700">
                <div className="flex justify-between gap-2">
                  <dt>CITC</dt>
                  <dd>{row.statistics_item_citc == null ? '-' : row.statistics_item_citc.toFixed(3)}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>CITC ?곹깭</dt>
                  <dd>{row.statistics_item_citc_status}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>臾명빆 ?쒓굅 ??alpha</dt>
                  <dd>
                    {row.statistics_alpha_if_item_deleted == null
                      ? '-'
                      : row.statistics_alpha_if_item_deleted.toFixed(3)}
                  </dd>
                </div>
              </dl>
            </article>
          </div>

          <details className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-700">
            <summary className="cursor-pointer font-bold">?먮낯 feature JSON 蹂닿린</summary>
            <pre className="mt-2 overflow-auto rounded-md bg-slate-900 p-3 text-[11px] text-slate-100">
{JSON.stringify(
  {
    construct_embedding_features: row.construct_embedding_features,
    construct_llm_features: row.construct_llm_features,
  },
  null,
  2,
)}
            </pre>
          </details>
        </details>
      ))}
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
  const [qualityRowsOpen, setQualityRowsOpen] = useState(false)
  const [constructRowsOpen, setConstructRowsOpen] = useState(false)
  const [itemFeatureRowsOpen, setItemFeatureRowsOpen] = useState(false)
  const [statisticsRowsOpen, setStatisticsRowsOpen] = useState(false)
  const [downloadingFeaturesCsv, setDownloadingFeaturesCsv] = useState(false)
  const [downloadingItemEvaluationsCsv, setDownloadingItemEvaluationsCsv] = useState(false)

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
      queryClient.setQueryData(['survey-quality', id], data)
      queryClient.invalidateQueries({ queryKey: ['survey-quality', id] })
      const llmFailureMessage = summarizeQualityLlmFailures(data.results)

      if (llmFailureMessage) {
        pushToast({
          type: 'error',
          title: '臾명빆 ?덉쭏 ?됯? ?ㅽ뙣',
          description: llmFailureMessage,
        })
        return
      }

      setQualityRowsOpen(true)
      if ((data.results?.length ?? 0) === 0) {
        pushToast({
          type: 'error',
          title: '문항 품질 평가 결과 없음',
          description: '평가 대상(normal) 문항이 없는지 확인해주세요.',
        })
        return
      }

      pushToast({ type: 'success', title: '문항 품질 평가 완료' })
    },
    onError: (error) => {
      console.error('[results] quality mutation failed', error)
      pushToast({
        type: 'error',
        title: '臾명빆 ?덉쭏 ?됯? ?ㅽ뙣',
        description: getErrorMessage(error, '?됯? ?ㅽ뻾 以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎.'),
      })
    },
  })

  const constructMutation = useMutation({
    mutationFn: () => evaluateSurveyConstruct(id),
    onSuccess: (data) => {
      console.log('[results] construct mutation response', data)
      queryClient.invalidateQueries({ queryKey: ['survey-construct', id] })
      setConstructRowsOpen(true)
      pushToast({ type: 'success', title: '臾명빆 援ъ꽦 ??밸룄 ?됯? ?꾨즺' })
    },
    onError: (error) => {
      console.error('[results] construct mutation failed', error)
      pushToast({
        type: 'error',
        title: '臾명빆 援ъ꽦 ??밸룄 ?됯? ?ㅽ뙣',
        description: getErrorMessage(error, '?됯? ?ㅽ뻾 以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎.'),
      })
    },
  })

  const statisticsMutation = useMutation({
    mutationFn: () => evaluateSurveyStatistics(id),
    onSuccess: (data) => {
      console.log('[results] statistics mutation response', data)
      queryClient.invalidateQueries({ queryKey: ['survey-statistics', id] })
      setStatisticsRowsOpen(true)
      pushToast({ type: 'success', title: '?듦퀎 遺꾩꽍 ?꾨즺' })
    },
    onError: (error) => {
      console.error('[results] statistics mutation failed', error)
      pushToast({
        type: 'error',
        title: '?듦퀎 遺꾩꽍 ?ㅽ뙣',
        description: getErrorMessage(error, '?묐떟 ?섍? 異⑸텇?쒖? ?뺤씤??二쇱꽭??'),
      })
    },
  })

  const evaluationPending =
    qualityMutation.isPending || constructMutation.isPending || statisticsMutation.isPending

  const qualityResults = qualityQuery.data?.results ?? qualityMutation.data?.results ?? []
  const constructResults = constructQuery.data?.results ?? []
  const surveyItems = surveyQuery.data?.items ?? []
  const statisticsItems = statisticsQuery.data?.items ?? []
  const qualityResultMap = useMemo(
    () => new Map(qualityResults.map((item) => [item.item_id, item])),
    [qualityResults],
  )
  const constructResultMap = useMemo(
    () => new Map(constructResults.map((item) => [item.item_id, item])),
    [constructResults],
  )
  const statisticsResultMap = useMemo(
    () => new Map(statisticsItems.map((item) => [item.item_id, item])),
    [statisticsItems],
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
          has_problem: false,
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
  const evaluatedQualityCount = evaluationTargetItems.filter((item) => item.status !== 'unknown').length
  const problemQualityCount = evaluationTargetItems.filter(
    (item) =>
      Boolean(item.has_problem) ||
      (item.problem_categories?.length ?? 0) > 0 ||
      item.status === 'problem' ||
      item.status === 'warning' ||
      item.status === 'bad',
  ).length

  const normalSurveyItems = useMemo(
    () => surveyItems.filter((item) => item.item_role === 'normal'),
    [surveyItems],
  )

  const constructDisplayItems: ConstructEvaluationItem[] = useMemo(
    () =>
      normalSurveyItems.map((surveyItem) => {
        const construct = constructResultMap.get(surveyItem.item_id)
        if (construct) {
          return construct
        }

        return {
          item_id: surveyItem.item_id,
          item_order: surveyItem.item_order,
          question_text: surveyItem.question_text,
          embedding_features: null,
          embedding_score: null,
          llm_features: null,
          llm_score: null,
          combined_score: null,
          status: 'unknown',
          predicted_citc: null,
          predicted_alpha_impact: null,
          created_at: null,
        }
      }),
    [constructResultMap, normalSurveyItems],
  )
  const evaluatedConstructCount = constructDisplayItems.filter((item) => {
    if (item.combined_score != null) {
      return true
    }
    return item.embedding_score != null || item.llm_score != null
  }).length

  const itemFeatureRows = useMemo<ItemFeatureSnapshot[]>(() => {
    return normalSurveyItems.map((surveyItem) => {
      const quality = qualityResultMap.get(surveyItem.item_id)
      const construct = constructResultMap.get(surveyItem.item_id)
      const statistics = statisticsResultMap.get(surveyItem.item_id)
      const combinedScore = getConstructCombinedScore(construct)

      return {
        item_id: surveyItem.item_id,
        item_order: surveyItem.item_order,
        question_text: surveyItem.question_text,
        item_category: surveyItem.item_category?.trim() ?? '',
        category_tokens: parseItemCategoryTokens(surveyItem.item_category),
        quality_status: quality?.status ?? 'unknown',
        quality_has_problem:
          Boolean(quality?.has_problem) || (quality?.problem_categories?.length ?? 0) > 0,
        quality_problem_categories: quality?.problem_categories ?? [],
        quality_detected_terms: quality?.detected_terms ?? [],
        construct_embedding_score: construct?.embedding_score ?? null,
        construct_llm_score: construct?.llm_score ?? null,
        construct_combined_score: combinedScore,
        construct_status: construct?.status ?? 'unknown',
        construct_predicted_citc: construct?.predicted_citc ?? null,
        construct_predicted_alpha_impact: construct?.predicted_alpha_impact ?? null,
        construct_embedding_features: construct?.embedding_features ?? null,
        construct_llm_features: construct?.llm_features ?? null,
        statistics_item_citc: statistics?.citc ?? null,
        statistics_item_citc_status: statistics?.citc_status ?? 'unknown',
        statistics_alpha_if_item_deleted: statistics?.alpha_if_item_deleted ?? null,
      }
    })
  }, [constructResultMap, normalSurveyItems, qualityResultMap, statisticsResultMap])

  const categoryFeatureSummaries = useMemo<CategoryFeatureSummary[]>(() => {
    const grouped = new Map<
      string,
      {
        itemCount: number
        qualityProblemCount: number
        constructSum: number
        constructCount: number
        citcSum: number
        citcCount: number
        alphaIfDeletedSum: number
        alphaIfDeletedCount: number
      }
    >()

    itemFeatureRows.forEach((row) => {
      const categories = row.category_tokens.length > 0 ? row.category_tokens : ['(誘몃텇瑜?']
      categories.forEach((category) => {
        const stats = grouped.get(category) ?? {
          itemCount: 0,
          qualityProblemCount: 0,
          constructSum: 0,
          constructCount: 0,
          citcSum: 0,
          citcCount: 0,
          alphaIfDeletedSum: 0,
          alphaIfDeletedCount: 0,
        }

        stats.itemCount += 1
        if (row.quality_has_problem) {
          stats.qualityProblemCount += 1
        }
        if (row.construct_combined_score != null) {
          stats.constructSum += row.construct_combined_score
          stats.constructCount += 1
        }
        if (row.statistics_item_citc != null) {
          stats.citcSum += row.statistics_item_citc
          stats.citcCount += 1
        }
        if (row.statistics_alpha_if_item_deleted != null) {
          stats.alphaIfDeletedSum += row.statistics_alpha_if_item_deleted
          stats.alphaIfDeletedCount += 1
        }

        grouped.set(category, stats)
      })
    })

    return Array.from(grouped.entries())
      .map(([category, stats]) => ({
        category,
        item_count: stats.itemCount,
        quality_problem_count: stats.qualityProblemCount,
        quality_problem_ratio: stats.itemCount > 0 ? stats.qualityProblemCount / stats.itemCount : null,
        construct_avg: meanOrNull(stats.constructSum, stats.constructCount),
        citc_avg: meanOrNull(stats.citcSum, stats.citcCount),
        alpha_if_deleted_avg: meanOrNull(stats.alphaIfDeletedSum, stats.alphaIfDeletedCount),
      }))
      .sort((a, b) => b.item_count - a.item_count || a.category.localeCompare(b.category, 'ko'))
  }, [itemFeatureRows])

  const responseScore = responseResult?.reliability?.score ?? responseResult?.features.reliability_score
  const responseStatus =
    responseResult?.reliability?.status ?? responseResult?.features.reliability_status
  const reliabilityRespondentCount = reliabilityQuery.data?.total_count ?? reliabilityQuery.data?.respondents.length ?? 0

  const handleDownloadFeaturesCsv = async () => {
    if (!id || id === 'demo') {
      pushToast({
        type: 'error',
        title: 'CSV ?ㅼ슫濡쒕뱶 ?ㅽ뙣',
        description: '?좏슚???ㅻЦ ID媛 ?놁뒿?덈떎.',
      })
      return
    }

    setDownloadingFeaturesCsv(true)
    try {
      await downloadSurveyResponseFeaturesCsv(id)
      pushToast({ type: 'success', title: '?묐떟 feature CSV ?ㅼ슫濡쒕뱶 ?꾨즺' })
    } catch (error) {
      pushToast({
        type: 'error',
        title: 'CSV ?ㅼ슫濡쒕뱶 ?ㅽ뙣',
        description: getErrorMessage(error, 'CSV ?앹꽦 以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎.'),
      })
    } finally {
      setDownloadingFeaturesCsv(false)
    }
  }

  const handleDownloadItemEvaluationsCsv = async () => {
    if (!id || id === 'demo') {
      pushToast({
        type: 'error',
        title: 'CSV ?ㅼ슫濡쒕뱶 ?ㅽ뙣',
        description: '?좏슚???ㅻЦ ID媛 ?놁뒿?덈떎.',
      })
      return
    }

    setDownloadingItemEvaluationsCsv(true)
    try {
      await downloadSurveyItemEvaluationsCsv(id)
      pushToast({ type: 'success', title: '臾명빆 ?됯? feature CSV ?ㅼ슫濡쒕뱶 ?꾨즺' })
    } catch (error) {
      pushToast({
        type: 'error',
        title: 'CSV ?ㅼ슫濡쒕뱶 ?ㅽ뙣',
        description: getErrorMessage(error, 'CSV ?앹꽦 以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎.'),
      })
    } finally {
      setDownloadingItemEvaluationsCsv(false)
    }
  }

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm font-bold text-teal-700">?ㅻЦ ID: {id}</p>
            <h1 className="mt-1 text-2xl font-black text-slate-950">
              {surveyQuery.data?.title ?? '?묐떟 諛??됯? 寃곌낵'}
            </h1>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              ?묐떟 ?좊ː?? 臾명빆 ?됯?, ?듦퀎 遺꾩꽍 寃곌낵瑜????붾㈃?먯꽌 ?뺤씤?⑸땲??
            </p>
          </div>
          {surveyQuery.isLoading ? <LoadingSpinner compact label="?ㅻЦ 議고쉶 以? /> : null}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
              <ShieldCheck size={22} />
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-950">?묐떟 ?좊ː???붿빟</h2>
              <p className="mt-1 text-sm text-slate-600">?묐떟 ?쒖텧 吏곹썑 怨꾩궛??寃곌낵?낅땲??</p>
            </div>
          </div>
          {responseScore != null ? (
            <ReliabilityBadge score={responseScore} showScore />
          ) : (
            <span className="rounded-md bg-slate-100 px-3 py-2 text-sm font-bold text-slate-600">
              ?묐떟 寃곌낵 ?놁쓬
            </span>
          )}
        </div>

        <p className="mt-3 text-sm font-semibold text-slate-600">
          ?꾩껜 ?묐떟 湲곗? ?좊ː??遺꾪룷???꾨옒 ?듦퀎 ?뱀뀡?먯꽌 ?뺤씤?????덉뒿?덈떎.
          {` (?꾩옱 ?꾩쟻 ?묐떟 ${reliabilityRespondentCount}紐?`}
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:bg-slate-100 disabled:text-slate-400"
            disabled={downloadingFeaturesCsv || !id || id === 'demo'}
            onClick={handleDownloadFeaturesCsv}
          >
            {downloadingFeaturesCsv ? (
              <LoadingSpinner compact label="CSV ?앹꽦 以? />
            ) : (
              '?묐떟 feature CSV ?ㅼ슫濡쒕뱶'
            )}
          </button>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:bg-slate-100 disabled:text-slate-400"
            disabled={downloadingItemEvaluationsCsv || !id || id === 'demo'}
            onClick={handleDownloadItemEvaluationsCsv}
          >
            {downloadingItemEvaluationsCsv ? (
              <LoadingSpinner compact label="CSV ?앹꽦 以? />
            ) : (
              '臾명빆 ?됯? feature CSV ?ㅼ슫濡쒕뱶'
            )}
          </button>
        </div>

        {responseScore != null ? (
          <div className="mt-5 space-y-4">
            <ScoreBar score={responseScore} label={`?곹깭: ${statusLabel(responseStatus)}`} />
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
            ?묐떟 ?붾㈃?먯꽌 ?쒖텧???꾨즺?섎㈃ ?좊ː???붿빟???쒖떆?⑸땲??
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
              <h2 className="text-lg font-black text-slate-950">臾명빆 ?덉쭏 ?됯?</h2>
              <p className="mt-1 text-sm text-slate-600">
                ?쇰컲 臾명빆留?臾몄젣 ?щ?瑜??쒖떆?섍퀬, ??Ц???⑥젙臾명빆? ?쒓렇濡?援щ텇?⑸땲??
                臾몄젣 臾명빆 移대뱶瑜??대┃?섎㈃ LLM 肄붾찘?몄? ?쒖븞臾몄쓣 諛붾줈 ?뺤씤?????덉뒿?덈떎.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700 disabled:bg-slate-300"
            disabled={evaluationPending}
            onClick={() => qualityMutation.mutate()}
          >
            {qualityMutation.isPending ? <LoadingSpinner compact label="?됯? 以? /> : '臾명빆 ?덉쭏 ?됯?'}
          </button>
        </div>

        <p className="mb-4 text-sm font-bold text-slate-600">
          ?꾩껜 臾명빆: {qualityDisplayItems.length}媛?/ ?됯? ???臾명빆: {evaluationTargetItems.length}
          媛?/ ?됯? ?꾨즺: {evaluatedQualityCount}媛?/ 臾몄젣 臾명빆: {problemQualityCount}媛?
        </p>

        <div className="mb-4">
          <DetailButton
            open={qualityRowsOpen}
            onClick={() => setQualityRowsOpen((open) => !open)}
            label={`臾명빆 紐⑸줉 蹂닿린 (${qualityDisplayItems.length}媛?`}
          />
        </div>

        {qualityRowsOpen ? (
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
                ??λ맂 ?덉쭏 ?됯? 寃곌낵媛 ?놁뒿?덈떎. 踰꾪듉???뚮윭 ?됯?瑜??ㅽ뻾??二쇱꽭??
              </p>
            )}
          </div>
        ) : null}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700">
              <FileText size={20} />
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-950">臾명빆 援ъ꽦 ??밸룄 ?됯?</h2>
              <p className="mt-1 text-sm text-slate-600">?쇰컲 臾명빆 湲곗??쇰줈 寃곌낵瑜??쒓났?⑸땲??</p>
            </div>
          </div>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:bg-slate-300"
            disabled={evaluationPending}
            onClick={() => constructMutation.mutate()}
          >
            {constructMutation.isPending ? (
              <LoadingSpinner compact label="?됯? 以? />
            ) : (
              '臾명빆 援ъ꽦 ??밸룄 ?됯?'
            )}
          </button>
        </div>

        <div className="mb-4">
          <DetailButton
            open={constructRowsOpen}
            onClick={() => setConstructRowsOpen((open) => !open)}
            label={`臾명빆 紐⑸줉 蹂닿린 (${constructDisplayItems.length}媛?`}
          />
        </div>

        <p className="mb-4 text-sm font-bold text-slate-600">
          ?됯? ???臾명빆: {normalSurveyItems.length}媛?/ ?됯? ?꾨즺: {evaluatedConstructCount}媛?
        </p>

        {constructRowsOpen ? (
          <div className="space-y-3">
            {constructDisplayItems.length > 0 ? (
              constructDisplayItems.map((item) => (
                <ConstructRow key={item.item_id} item={item} />
              ))
            ) : (
              <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
                ??λ맂 援ъ꽦 ??밸룄 ?됯? 寃곌낵媛 ?놁뒿?덈떎.
              </p>
            )}
          </div>
        ) : null}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-black text-slate-950">?좏삎蹂?Feature ?붿빟</h2>
        <p className="mt-1 text-sm text-slate-600">
          臾명빆??`?좏삎` 媛믪쓣 `/`濡?遺꾨━??吏묎퀎?섎ŉ, 以묐났 ?좏삎? ?먮룞 ?쒓굅?⑸땲??
        </p>
        <div className="mt-4">
          <CategoryFeaturePanel rows={categoryFeatureSummaries} />
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-black text-slate-950">臾명빆蹂?Feature ?곸꽭</h2>
        <p className="mt-1 text-sm text-slate-600">
          臾명빆留덈떎 ?덉쭏/援ъ꽦/?듦퀎 feature瑜???踰덉뿉 ?뺤씤?????덉뒿?덈떎.
        </p>
        <div className="mt-4">
          <DetailButton
            open={itemFeatureRowsOpen}
            onClick={() => setItemFeatureRowsOpen((open) => !open)}
            label={`臾명빆蹂?feature ?쇱튂湲?(${itemFeatureRows.length}媛?`}
          />
        </div>
        {itemFeatureRowsOpen ? (
          <div className="mt-4">
            <ItemFeaturePanel rows={itemFeatureRows} />
          </div>
        ) : null}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-800">
              <BarChart3 size={20} />
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-950">?듦퀎 遺꾩꽍</h2>
              <p className="mt-1 text-sm text-slate-600">
                ?꾩옱 ??λ맂 ?꾩꽦 ?묐떟 湲곗??쇰줈 Cronbach alpha? CITC瑜??ㅼ떆 怨꾩궛??理쒖떊?뷀븷 ???덉뒿?덈떎.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700 disabled:bg-slate-300"
            disabled={evaluationPending}
            onClick={() => {
              setStatisticsRowsOpen(true)
              statisticsMutation.mutate()
            }}
          >
            {statisticsMutation.isPending ? (
              <LoadingSpinner compact label="CITC 理쒖떊??以? />
            ) : (
              '?꾩옱 ?묐떟?쇰줈 CITC 理쒖떊??
            )}
          </button>
        </div>

        {statisticsQuery.isError ? (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-amber-50 p-4 text-sm font-semibold text-amber-900">
            <AlertTriangle size={18} />
            ?듦퀎 寃곌낵瑜?議고쉶?섏? 紐삵뻽?듬땲?? ?꾩쭅 遺꾩꽍 寃곌낵媛 ?놁쓣 ???덉뒿?덈떎.
          </div>
        ) : null}

        <div className="mb-5 rounded-lg border border-slate-200 p-4">
          <h3 className="text-base font-black text-slate-950">?묐떟 ?좊ː??遺꾪룷</h3>
          <p className="mt-1 text-sm text-slate-600">
            理쒓렐 1嫄댁씠 ?꾨땶 ?꾩껜 ?묐떟 湲곗??쇰줈 ??以????몄썝??蹂댁뿬以띾땲??
          </p>
          <div className="mt-3">
            {reliabilityQuery.isLoading ? (
              <LoadingSpinner compact label="?좊ː??遺꾪룷 遺덈윭?ㅻ뒗 以? />
            ) : reliabilityQuery.isError ? (
              <div className="rounded-lg bg-amber-50 p-4 text-sm font-semibold text-amber-900">
                ?좊ː??遺꾪룷瑜?遺덈윭?ㅼ? 紐삵뻽?듬땲??
              </div>
            ) : (
              <ReliabilityDistributionPanel data={reliabilityQuery.data} />
            )}
          </div>
        </div>

        <div className="mt-4">
          <DetailButton
            open={statisticsRowsOpen}
            onClick={() => setStatisticsRowsOpen((open) => !open)}
            label="臾명빆 ?듦퀎 ?곸꽭 ?쇱튂湲?
          />
        </div>

        {statisticsRowsOpen ? (
          <div className="mt-4">
            <StatisticsPanel statistics={statisticsQuery.data} />
          </div>
        ) : null}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-black text-slate-950">?붾쾭源??묐떟(JSON)</h2>
        <p className="mt-1 text-sm text-slate-600">?됯? API ?묐떟 ?먮Ц???뺤씤?????덉뒿?덈떎.</p>
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


