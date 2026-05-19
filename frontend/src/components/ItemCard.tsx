import type { ReactNode } from 'react'
import { AlertTriangle, BadgeCheck, Trash2 } from 'lucide-react'
import { clsx } from 'clsx'
import type { SurveyItem } from '../types/survey'
import { ReliabilityBadge } from './ReliabilityBadge'

/**
 * 컴포넌트: ItemCard
 * 역할: 문항 하나를 목록에서 표시하고 선택, 삭제, 품질/CITC 상태를 보여준다.
 */
export interface ItemCardProps {
  item: SurveyItem
  index: number
  isSelected: boolean
  onSelect: () => void
  onDelete: () => void
  dragActivator?: ReactNode
}

const typeLabels: Record<SurveyItem['type'], string> = {
  'likert-5': '5점 리커트',
  'likert-7': '7점 리커트',
  multiple: '객관식',
  short: '주관식',
}

export function ItemCard({
  item,
  index,
  isSelected,
  onSelect,
  onDelete,
  dragActivator,
}: ItemCardProps) {
  const isLowCitc = item.citc ? item.citc.citcScore < 0.55 : false

  return (
    <article
      className={clsx(
        'rounded-lg border bg-white p-3 text-left shadow-sm transition',
        isSelected ? 'border-teal-500 ring-2 ring-teal-100' : 'border-slate-200 hover:border-slate-300',
      )}
    >
      <div className="flex items-start gap-2">
        {dragActivator}
        <button type="button" className="min-w-0 flex-1 text-left" onClick={onSelect}>
          <div className="mb-2 flex flex-wrap items-center gap-1.5">
            <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700">
              Q{index + 1}
            </span>
            <span className="rounded-md bg-cyan-50 px-2 py-1 text-xs font-semibold text-cyan-700">
              {typeLabels[item.type]}
            </span>
            {item.isTrap ? (
              <span className="rounded-md bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700">
                함정
              </span>
            ) : null}
            {item.isReverse ? (
              <span className="rounded-md bg-indigo-50 px-2 py-1 text-xs font-semibold text-indigo-700">
                역문항
              </span>
            ) : null}
          </div>
          <p className="line-clamp-3 text-sm font-medium leading-6 text-slate-800">
            {item.text || '새 문항을 입력해 주세요.'}
          </p>
          {item.itemCategory ? (
            <p className="mt-2 text-xs font-semibold text-indigo-700">유형: {item.itemCategory}</p>
          ) : null}
        </button>
        <button
          type="button"
          className="rounded-md p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
          aria-label="문항 삭제"
          onClick={onDelete}
        >
          <Trash2 size={16} />
        </button>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {item.quality ? (
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
            <BadgeCheck size={14} />
            품질 {item.quality.score}점
          </span>
        ) : null}
        {item.citc ? <ReliabilityBadge score={item.citc.citcScore} kind="citc" /> : null}
        {isLowCitc ? (
          <span
            className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700"
            title="수정 또는 삭제 권장"
          >
            <AlertTriangle size={14} />
            수정 권장
          </span>
        ) : null}
      </div>
    </article>
  )
}
