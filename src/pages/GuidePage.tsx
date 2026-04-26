/**
 * 페이지: 문항 작성 가이드라인
 * 역할: 설문 문항 작성 시 피해야 할 표현과 좋은 예시를 아코디언 형태로 제공한다.
 * 주요 기능:
 *   - 문항 작성 원칙별 나쁜 예시/좋은 예시 비교
 *   - 설문 생성 화면으로 이동하는 고정 CTA
 * API 연동: 없음
 */
import { useState } from 'react'
import { ChevronDown, FilePlus2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'

const guides = [
  {
    title: '이중 부정 표현 금지',
    description: '부정어가 겹치면 응답자가 문항의 방향을 헷갈릴 가능성이 커집니다.',
    bad: '이 서비스가 불편하지 않다고 생각하지 않는다.',
    good: '이 서비스는 이용하기 편리하다.',
  },
  {
    title: '유도 질문 금지',
    description: '특정 답변을 암시하는 표현은 응답 편향을 만들 수 있습니다.',
    bad: '많은 사용자가 만족한 이 기능에 얼마나 만족하시나요?',
    good: '이 기능에 대한 만족도를 선택해 주세요.',
  },
  {
    title: '한 문항에 두 가지 내용 포함 금지',
    description: '두 개 이상의 평가 대상이 들어가면 어떤 요소에 대한 응답인지 알기 어렵습니다.',
    bad: '이 서비스는 빠르고 디자인이 만족스럽다.',
    good: '이 서비스의 응답 속도는 만족스럽다.',
  },
  {
    title: '추상적 용어 사용 주의',
    description: '응답자가 같은 기준으로 이해할 수 있도록 구체적인 맥락을 제공합니다.',
    bad: '서비스가 전반적으로 적절하다.',
    good: '서비스의 메뉴 구성은 원하는 기능을 찾기에 적절하다.',
  },
]

export function GuidePage() {
  const [openIndex, setOpenIndex] = useState(0)

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-5">
          <p className="text-sm font-bold text-teal-700">작성 원칙</p>
          <h1 className="mt-1 text-2xl font-black text-slate-950">문항 작성 가이드라인</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            품질 평가 API의 결과를 해석할 때도 아래 기준을 함께 보면 문항 수정 방향을 잡기 쉽습니다.
          </p>
        </div>

        <div className="space-y-3">
          {guides.map((guide, index) => {
            const open = openIndex === index

            return (
              <article key={guide.title} className="rounded-lg border border-slate-200">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
                  onClick={() => setOpenIndex(open ? -1 : index)}
                >
                  <span>
                    <span className="block text-sm font-black text-slate-950">{guide.title}</span>
                    <span className="mt-1 block text-xs text-slate-500">{guide.description}</span>
                  </span>
                  <ChevronDown
                    size={18}
                    className={clsx('shrink-0 text-slate-500 transition', open && 'rotate-180')}
                  />
                </button>

                {open ? (
                  <div className="grid gap-3 border-t border-slate-200 p-4 md:grid-cols-2">
                    <div className="rounded-lg border border-rose-200 bg-rose-50 p-4">
                      <p className="text-xs font-black text-rose-700">나쁜 예시</p>
                      <p className="mt-2 text-sm leading-6 text-slate-800">{guide.bad}</p>
                    </div>
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                      <p className="text-xs font-black text-emerald-700">좋은 예시</p>
                      <p className="mt-2 text-sm leading-6 text-slate-800">{guide.good}</p>
                    </div>
                  </div>
                ) : null}
              </article>
            )
          })}
        </div>
      </section>

      <aside className="lg:sticky lg:top-24 lg:self-start">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-black text-slate-950">바로 적용하기</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            가이드를 확인한 뒤 설문 생성 화면에서 문항 품질 평가를 실행해 보세요.
          </p>
          <Link
            to="/survey/create"
            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700"
          >
            <FilePlus2 size={16} />
            지금 설문 만들기
          </Link>
        </div>
      </aside>
    </div>
  )
}
