/**
 * 페이지: 응답 통계 확인
 * 역할: 설문 응답의 신뢰도 분포, 문항별 통계, 응답자별 상태를 분석한다.
 * 주요 기능:
 *   - 상단 요약 카드
 *   - 응답 신뢰도 분포 차트
 *   - 문항별 통계 테이블 및 상세 분포 모달
 *   - 응답자 목록 필터링 및 상세 근거 모달
 * API 연동: /api/survey/:id/reliability, /api/survey/:id/item-stats
 */
import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Clock, Filter, ShieldCheck, Users, X } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { getSurveyItemStats, getSurveyReliability } from '../api/surveyApi'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ReliabilityBadge } from '../components/ReliabilityBadge'
import { StatChart, type ChartDataPoint } from '../components/StatChart'
import { useToastStore } from '../store/toastStore'
import type { ItemStat, ReliabilityRespondent } from '../types/survey'

type ReliabilityFilter = 'all' | 'low' | 'medium' | 'high'

function getReliabilityStatus(score: number) {
  if (score >= 75) {
    return '정상'
  }

  if (score >= 55) {
    return '주의'
  }

  return '불량'
}

function matchesFilter(score: number, filter: ReliabilityFilter) {
  if (filter === 'all') {
    return true
  }

  if (filter === 'high') {
    return score >= 75
  }

  if (filter === 'medium') {
    return score >= 55 && score < 75
  }

  return score < 55
}

function buildReliabilityDistribution(respondents: ReliabilityRespondent[]): ChartDataPoint[] {
  const bins = [
    { name: '0-39', min: 0, max: 39 },
    { name: '40-59', min: 40, max: 59 },
    { name: '60-79', min: 60, max: 79 },
    { name: '80-100', min: 80, max: 100 },
  ]

  return bins.map((bin) => ({
    name: bin.name,
    value: respondents.filter(
      (respondent) =>
        respondent.reliabilityScore >= bin.min && respondent.reliabilityScore <= bin.max,
    ).length,
  }))
}

function distributionToChartData(distribution: number[]): ChartDataPoint[] {
  return distribution.map((value, index) => ({
    name: `${index + 1}점`,
    value,
  }))
}

export function ResultsPage() {
  const { id = 'demo' } = useParams()
  const [filter, setFilter] = useState<ReliabilityFilter>('all')
  const [selectedItemStat, setSelectedItemStat] = useState<ItemStat | null>(null)
  const [selectedRespondent, setSelectedRespondent] = useState<ReliabilityRespondent | null>(null)
  const { pushToast } = useToastStore()

  const reliabilityQuery = useQuery({
    queryKey: ['survey-reliability', id],
    queryFn: () => getSurveyReliability(id),
  })

  const itemStatsQuery = useQuery({
    queryKey: ['survey-item-stats', id],
    queryFn: () => getSurveyItemStats(id),
  })

  useEffect(() => {
    if (reliabilityQuery.isError || itemStatsQuery.isError) {
      pushToast({
        type: 'error',
        title: '통계 데이터 조회 실패',
        description: '백엔드 API 주소 또는 응답 타입을 확인해 주세요.',
      })
    }
  }, [itemStatsQuery.isError, pushToast, reliabilityQuery.isError])

  const respondents = useMemo(
    () => reliabilityQuery.data?.respondents ?? [],
    [reliabilityQuery.data],
  )
  const itemStats = itemStatsQuery.data?.items ?? []

  const summary = useMemo(() => {
    const total = respondents.length
    const averageReliability =
      total === 0
        ? 0
        : respondents.reduce((sum, respondent) => sum + respondent.reliabilityScore, 0) / total
    const lowCount = respondents.filter((respondent) => respondent.reliabilityScore < 55).length
    const averageTime =
      total === 0
        ? 0
        : respondents.reduce(
            (sum, respondent) =>
              sum +
              respondent.timePerItem.reduce((timeSum, time) => timeSum + time, 0) /
                respondent.timePerItem.length,
            0,
          ) / total

    return {
      total,
      averageReliability,
      lowCount,
      averageTime,
    }
  }, [respondents])

  const filteredRespondents = respondents.filter((respondent) =>
    matchesFilter(respondent.reliabilityScore, filter),
  )
  const reliabilityDistribution = buildReliabilityDistribution(respondents)

  if (reliabilityQuery.isLoading || itemStatsQuery.isLoading) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <LoadingSpinner label="응답 통계를 불러오는 중" />
      </section>
    )
  }

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <p className="text-sm font-bold text-teal-700">설문 ID: {id}</p>
          <h1 className="mt-1 text-2xl font-black text-slate-950">응답 통계 확인</h1>
          <p className="mt-1 text-sm text-slate-600">
            응답 신뢰도와 문항별 통계를 함께 확인해 낮은 품질의 응답과 문항을 빠르게 찾습니다.
          </p>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: '총 응답 수',
            value: `${summary.total}명`,
            icon: Users,
          },
          {
            label: '평균 응답 신뢰도',
            value: `${summary.averageReliability.toFixed(1)}점`,
            icon: ShieldCheck,
          },
          {
            label: '신뢰도 낮은 응답',
            value: `${summary.lowCount}건`,
            icon: AlertTriangle,
          },
          {
            label: '평균 문항 소요 시간',
            value: `${summary.averageTime.toFixed(1)}초`,
            icon: Clock,
          },
        ].map((card) => {
          const Icon = card.icon

          return (
            <article key={card.label} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-800">
                {card.label === '평균 응답 신뢰도' ? (
                  <ReliabilityBadge score={summary.averageReliability} showScore={false} />
                ) : (
                  <Icon size={20} />
                )}
              </div>
              <p className="text-sm font-semibold text-slate-500">{card.label}</p>
              <p className="mt-1 text-2xl font-black text-slate-950">{card.value}</p>
            </article>
          )
        })}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-lg font-black text-slate-950">응답 신뢰도 분포</h2>
            <p className="mt-1 text-sm text-slate-600">점수 구간별 응답자 수를 막대 차트로 표시합니다.</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs font-bold">
            <span className="rounded-md bg-rose-50 px-2 py-1 text-rose-700">낮음: 0-54</span>
            <span className="rounded-md bg-amber-50 px-2 py-1 text-amber-700">보통: 55-74</span>
            <span className="rounded-md bg-emerald-50 px-2 py-1 text-emerald-700">높음: 75-100</span>
          </div>
        </div>
        <StatChart data={reliabilityDistribution} valueLabel="응답자 수" />
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-black text-slate-950">문항별 통계 테이블</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[760px] border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-xs font-bold uppercase text-slate-500">
                <th className="border-b border-slate-200 px-3 py-2">문항 번호</th>
                <th className="border-b border-slate-200 px-3 py-2">문항 텍스트</th>
                <th className="border-b border-slate-200 px-3 py-2">평균</th>
                <th className="border-b border-slate-200 px-3 py-2">분산</th>
                <th className="border-b border-slate-200 px-3 py-2">응답 수</th>
                <th className="border-b border-slate-200 px-3 py-2">결측 수</th>
              </tr>
            </thead>
            <tbody>
              {itemStats.map((item, index) => {
                const varianceRisk = item.variance < 0.25 || item.variance > 1.2

                return (
                  <tr
                    key={item.itemId}
                    className={varianceRisk ? 'bg-amber-50' : 'hover:bg-slate-50'}
                    onClick={() => setSelectedItemStat(item)}
                  >
                    <td className="border-b border-slate-100 px-3 py-3 font-bold text-slate-800">
                      Q{index + 1}
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 text-slate-700">
                      {item.text}
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3">{item.mean}</td>
                    <td className="border-b border-slate-100 px-3 py-3">
                      <span className={varianceRisk ? 'font-black text-amber-700' : ''}>
                        {item.variance}
                      </span>
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3">{item.count}</td>
                    <td className="border-b border-slate-100 px-3 py-3">{item.missing}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-black text-slate-950">응답자 목록</h2>
            <p className="mt-1 text-sm text-slate-600">
              행을 클릭하면 신뢰도 산출 근거와 문항별 소요 시간을 확인합니다.
            </p>
          </div>
          <label className="inline-flex items-center gap-2 text-sm font-bold text-slate-700">
            <Filter size={16} />
            <select
              className="rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              value={filter}
              onChange={(event) => setFilter(event.target.value as ReliabilityFilter)}
            >
              <option value="all">전체</option>
              <option value="low">낮음</option>
              <option value="medium">보통</option>
              <option value="high">높음</option>
            </select>
          </label>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-xs font-bold uppercase text-slate-500">
                <th className="border-b border-slate-200 px-3 py-2">응답 ID</th>
                <th className="border-b border-slate-200 px-3 py-2">응답 일시</th>
                <th className="border-b border-slate-200 px-3 py-2">소요 시간</th>
                <th className="border-b border-slate-200 px-3 py-2">신뢰도 점수</th>
                <th className="border-b border-slate-200 px-3 py-2">상태</th>
              </tr>
            </thead>
            <tbody>
              {filteredRespondents.map((respondent) => {
                const totalTime = respondent.timePerItem.reduce((sum, time) => sum + time, 0)

                return (
                  <tr
                    key={respondent.id}
                    className="hover:bg-slate-50"
                    onClick={() => setSelectedRespondent(respondent)}
                  >
                    <td className="border-b border-slate-100 px-3 py-3 font-bold text-slate-800">
                      {respondent.id}
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3">{respondent.submittedAt}</td>
                    <td className="border-b border-slate-100 px-3 py-3">{totalTime}초</td>
                    <td className="border-b border-slate-100 px-3 py-3">
                      <ReliabilityBadge score={respondent.reliabilityScore} />
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 font-bold">
                      {getReliabilityStatus(respondent.reliabilityScore)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {selectedItemStat ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4">
          <section className="w-full max-w-2xl rounded-lg bg-white p-5 shadow-xl">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-black text-slate-950">문항 응답 분포</h2>
                <p className="mt-1 text-sm text-slate-600">{selectedItemStat.text}</p>
              </div>
              <button
                type="button"
                className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
                aria-label="문항 통계 닫기"
                onClick={() => setSelectedItemStat(null)}
              >
                <X size={18} />
              </button>
            </div>
            <StatChart data={distributionToChartData(selectedItemStat.distribution)} valueLabel="응답 수" />
          </section>
        </div>
      ) : null}

      {selectedRespondent ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4">
          <section className="w-full max-w-xl rounded-lg bg-white p-5 shadow-xl">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-black text-slate-950">응답자 상세</h2>
                <p className="mt-1 text-sm text-slate-600">{selectedRespondent.id}</p>
              </div>
              <button
                type="button"
                className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
                aria-label="응답자 상세 닫기"
                onClick={() => setSelectedRespondent(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between rounded-lg bg-slate-50 p-3">
                <span className="font-bold text-slate-600">신뢰도 점수</span>
                <ReliabilityBadge score={selectedRespondent.reliabilityScore} />
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="font-bold text-slate-600">산출 근거</p>
                <p className="mt-1 leading-6 text-slate-700">{selectedRespondent.reason}</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="font-bold text-slate-600">문항별 소요 시간</p>
                <p className="mt-1 text-slate-700">
                  {selectedRespondent.timePerItem.map((time, index) => `Q${index + 1}: ${time}초`).join(' / ')}
                </p>
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  )
}
