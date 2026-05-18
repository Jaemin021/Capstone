import { CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { clsx } from 'clsx'
import { useToastStore, type ToastType } from '../store/toastStore'

const toastStyles: Record<ToastType, string> = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  error: 'border-rose-200 bg-rose-50 text-rose-800',
  info: 'border-sky-200 bg-sky-50 text-sky-800',
}

const toastIcons: Record<ToastType, typeof CheckCircle2> = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
}

export function ToastHost() {
  const { messages, removeToast } = useToastStore()

  return (
    <div className="fixed bottom-4 right-4 z-[60] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2">
      {messages.map((message) => {
        const Icon = toastIcons[message.type]

        return (
          <div
            key={message.id}
            className={clsx(
              'rounded-lg border p-3 shadow-lg backdrop-blur',
              toastStyles[message.type],
            )}
          >
            <div className="flex items-start gap-3">
              <Icon className="mt-0.5 shrink-0" size={18} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold">{message.title}</p>
                {message.description ? (
                  <p className="mt-1 text-xs leading-5 opacity-85">{message.description}</p>
                ) : null}
              </div>
              <button
                type="button"
                className="rounded-md p-1 opacity-70 hover:bg-white/60 hover:opacity-100"
                aria-label="알림 닫기"
                onClick={() => removeToast(message.id)}
              >
                <X size={14} />
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
