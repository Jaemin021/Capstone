import { CheckCircle2 } from 'lucide-react'

export function PublicSurveyCompletePage() {
  return (
    <div className="mx-auto max-w-2xl">
      <section className="rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
        <CheckCircle2 className="mx-auto text-teal-600" size={46} />
        <h1 className="mt-4 text-2xl font-black text-slate-950">설문 제출이 완료되었습니다</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          참여해 주셔서 감사합니다. 이 링크에서는 설문 응답만 가능하며, 제출 후 다시 응답할 수 없습니다.
        </p>
      </section>
    </div>
  )
}
