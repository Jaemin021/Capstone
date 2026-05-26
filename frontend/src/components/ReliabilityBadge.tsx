import { clsx } from 'clsx'

/**
 * 컴포넌트: ReliabilityBadge
 * 역할: 신뢰도 또는 CITC 점수 수준을 색상 배지로 표시한다.
 */
export interface ReliabilityBadgeProps {
  score: number
  kind?: 'reliability' | 'citc'
  showScore?: boolean
}

function resolveLevel(score: number, kind: 'reliability' | 'citc') {
  const normalizedScore = kind === 'citc' ? score * 100 : score

  if (kind === 'reliability') {
    if (normalizedScore >= 55) {
      return {
        label: '성실',
        className: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
      }
    }

    return {
      label: '비성실',
      className: 'bg-rose-50 text-rose-700 ring-rose-200',
    }
  }

  if (normalizedScore >= 75) {
    return {
      label: '좋음',
      className: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    }
  }

  if (normalizedScore >= 55) {
    return {
      label: '중간',
      className: 'bg-amber-50 text-amber-700 ring-amber-200',
    }
  }

  return {
    label: '낮음',
    className: 'bg-rose-50 text-rose-700 ring-rose-200',
  }
}

export function ReliabilityBadge({
  score,
  kind = 'reliability',
  showScore = true,
}: ReliabilityBadgeProps) {
  const level = resolveLevel(score, kind)
  const formattedScore = kind === 'citc' ? score.toFixed(2) : `${Math.round(score)}점`

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-md px-2 py-1 text-xs font-semibold ring-1',
        level.className,
      )}
    >
      {level.label}
      {showScore ? <span className="ml-1 font-medium opacity-80">{formattedScore}</span> : null}
    </span>
  )
}
