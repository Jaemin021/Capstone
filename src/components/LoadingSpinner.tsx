/**
 * 컴포넌트: LoadingSpinner
 * 역할: API 호출 또는 화면 전환 중 로딩 상태를 일관된 형태로 표시한다.
 */
export interface LoadingSpinnerProps {
  label?: string
  compact?: boolean
}

export function LoadingSpinner({ label = '불러오는 중', compact = false }: LoadingSpinnerProps) {
  return (
    <div className={`flex items-center justify-center gap-2 ${compact ? 'py-1' : 'py-8'}`}>
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-teal-600" />
      <span className="text-sm font-medium text-slate-600">{label}</span>
    </div>
  )
}
