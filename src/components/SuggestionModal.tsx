import { Lightbulb, X } from 'lucide-react'

/**
 * 컴포넌트: SuggestionModal
 * 역할: 낮은 품질 점수 문항에 대한 대체 문항 추천과 교체 확인 액션을 제공한다.
 */
export interface SuggestionModalProps {
  open: boolean
  suggestion: string | null
  onReplace: () => void
  onIgnore: () => void
}

export function SuggestionModal({ open, suggestion, onReplace, onIgnore }: SuggestionModalProps) {
  if (!open || !suggestion) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4">
      <section className="w-full max-w-xl rounded-lg bg-white p-5 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <div className="mb-2 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
              <Lightbulb size={20} />
            </div>
            <h2 className="text-lg font-bold text-slate-950">대체 문항 추천</h2>
            <p className="mt-1 text-sm text-slate-600">
              품질 점수가 낮아 더 명확한 표현의 문항을 제안합니다.
            </p>
          </div>
          <button
            type="button"
            className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
            aria-label="추천 닫기"
            onClick={onIgnore}
          >
            <X size={18} />
          </button>
        </div>
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm font-semibold leading-6 text-slate-800">
          {suggestion}
        </p>
        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            onClick={onIgnore}
          >
            무시하기
          </button>
          <button
            type="button"
            className="rounded-md bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700"
            onClick={onReplace}
          >
            이 문항으로 교체하기
          </button>
        </div>
      </section>
    </div>
  )
}
