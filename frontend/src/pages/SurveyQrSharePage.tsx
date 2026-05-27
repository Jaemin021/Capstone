import { Copy, Expand } from 'lucide-react'
import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useToastStore } from '../store/toastStore'

function buildQrImageUrl(target: string) {
  const encoded = encodeURIComponent(target)
  return `https://api.qrserver.com/v1/create-qr-code/?size=900x900&margin=20&data=${encoded}`
}

export function SurveyQrSharePage() {
  const [searchParams] = useSearchParams()
  const pushToast = useToastStore((state) => state.pushToast)

  const target = (searchParams.get('target') || '').trim()
  const title = (searchParams.get('title') || '설문 응답 QR').trim()

  const qrImageUrl = useMemo(() => {
    if (!target) {
      return ''
    }
    return buildQrImageUrl(target)
  }, [target])

  const onCopyTarget = async () => {
    if (!target) {
      return
    }
    try {
      await navigator.clipboard.writeText(target)
      pushToast({ type: 'success', title: '응답 링크 복사 완료' })
    } catch {
      pushToast({ type: 'error', title: '응답 링크 복사 실패' })
    }
  }

  const onEnterFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen()
      }
    } catch {
      pushToast({ type: 'error', title: '전체화면 전환 실패' })
    }
  }

  if (!target) {
    return (
      <section className="mx-auto flex min-h-[70vh] w-full max-w-3xl items-center justify-center p-6">
        <div className="w-full rounded-xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
          <h1 className="text-xl font-black">QR 링크 정보가 없습니다.</h1>
          <p className="mt-2 text-sm leading-6">
            `target` 쿼리 파라미터가 포함된 링크로 접속해 주세요.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col items-center justify-center gap-6 px-4 py-8">
      <header className="text-center">
        <h1 className="text-2xl font-black text-slate-950">{title}</h1>
        <p className="mt-2 text-sm text-slate-600">아래 QR 코드를 스캔해서 설문에 참여해 주세요.</p>
      </header>

      <div className="w-full max-w-[560px] rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <img
          src={qrImageUrl}
          alt="설문 응답 QR 코드"
          className="mx-auto aspect-square w-full max-w-[520px] rounded-lg bg-white"
        />
      </div>

      <div className="w-full max-w-4xl rounded-lg border border-slate-200 bg-white p-3">
        <p className="truncate text-xs text-slate-600">{target}</p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2">
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
          onClick={onCopyTarget}
        >
          <Copy size={15} />
          응답 링크 복사
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-bold text-white hover:bg-slate-800"
          onClick={onEnterFullscreen}
        >
          <Expand size={15} />
          전체화면
        </button>
      </div>
    </section>
  )
}

