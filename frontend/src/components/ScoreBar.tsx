/**
 * 컴포넌트: ScoreBar
 * 역할: 0~100 점수를 색상 그라데이션 진행 바로 표시한다.
 */
export interface ScoreBarProps {
  score: number
  label?: string
  compact?: boolean
}

const clampScore = (score: number) => Math.max(0, Math.min(100, Math.round(score)))

export function ScoreBar({ score, label = '점수', compact = false }: ScoreBarProps) {
  const safeScore = clampScore(score)

  return (
    <div className="w-full">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-slate-700">{label}</span>
        <span className="text-sm font-bold text-slate-950">{safeScore}점</span>
      </div>
      <div className={`w-full rounded-full bg-slate-200 ${compact ? 'h-2' : 'h-3'}`}>
        <div
          className="h-full rounded-full bg-gradient-to-r from-rose-500 via-amber-400 to-emerald-500 transition-all"
          style={{ width: `${safeScore}%` }}
        />
      </div>
    </div>
  )
}
