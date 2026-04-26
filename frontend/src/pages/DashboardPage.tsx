/**
 * 페이지: 랜딩 / 대시보드
 * 역할: 설문 품질 평가 앱의 시작 화면으로 최근 작업, 핵심 지표, 주요 이동 경로를 제공한다.
 * 주요 기능:
 *   - 설문 생성/결과/가이드 진입
 *   - 현재 프론트 구현 범위 안내
 *   - 목업 기반 신뢰도 요약 표시
 * API 연동: 결과 상세 데이터는 /survey/:id/results 화면에서 조회
 */
import { ArrowRight, BarChart3, ClipboardCheck, FilePlus2, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { StatChart } from '../components/StatChart'

const miniDistribution = [
  { name: '0-39', value: 2 },
  { name: '40-59', value: 5 },
  { name: '60-79', value: 14 },
  { name: '80-100', value: 15 },
]

export function DashboardPage() {
  return (
    <div className="space-y-5">
      <section className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-5 inline-flex items-center gap-2 rounded-md bg-teal-50 px-3 py-1 text-sm font-bold text-teal-700">
            <ShieldCheck size={16} />
            프론트 우선 구현 모드
          </div>
          <h1 className="max-w-3xl text-3xl font-black leading-tight text-slate-950 md:text-4xl">
            설문 문항 품질과 응답 신뢰도를 한 화면에서 점검합니다.
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 md:text-base">
            현재는 mock API로 전체 흐름을 확인할 수 있고, 백엔드가 준비되면
            `src/api/surveyApi.ts`의 함수만 실제 응답에 맞춰 연결하면 됩니다.
          </p>
          <div className="mt-6 flex flex-col gap-2 sm:flex-row">
            <Link
              to="/survey/create"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700"
            >
              <FilePlus2 size={17} />
              설문 만들기
            </Link>
            <Link
              to="/survey/demo/results"
              className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
            >
              <BarChart3 size={17} />
              결과 통계 보기
            </Link>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-black text-slate-950">신뢰도 분포 미리보기</h2>
          <p className="mt-1 text-sm text-slate-600">응답 결과 화면과 동일한 차트 컴포넌트를 사용합니다.</p>
          <div className="mt-4">
            <StatChart data={miniDistribution} height={220} valueLabel="응답자 수" />
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          {
            icon: ClipboardCheck,
            title: '문항 품질 평가',
            text: '점수, 문제 어휘, 대체 문항 추천 UI까지 연결했습니다.',
          },
          {
            icon: ShieldCheck,
            title: 'CITC 예측',
            text: '전체 일관성 분석과 낮은 문항 경고 흐름을 제공합니다.',
          },
          {
            icon: BarChart3,
            title: '응답 통계',
            text: '신뢰도 분포, 문항별 통계, 응답자 상세 모달을 확인할 수 있습니다.',
          },
        ].map((item) => {
          const Icon = item.icon

          return (
            <article key={item.title} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-800">
                <Icon size={20} />
              </div>
              <h3 className="text-base font-black text-slate-950">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.text}</p>
            </article>
          )
        })}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-black text-slate-950">백엔드 연결 전 확인 순서</h2>
            <p className="mt-1 text-sm text-slate-600">
              프론트 흐름 확인 후 `docs/backend-integration.md` 표를 백엔드 팀원에게 공유하면 됩니다.
            </p>
          </div>
          <Link
            to="/guide"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
          >
            문항 작성 가이드
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>
    </div>
  )
}
