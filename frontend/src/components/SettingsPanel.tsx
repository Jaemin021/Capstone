import { Wand2, X } from 'lucide-react'
import type { SurveySettings } from '../types/survey'
import { LoadingSpinner } from './LoadingSpinner'

/**
 * 컴포넌트: SettingsPanel
 * 역할: 설문 제목, 맥락, 함정 문항/역문항 기능 토글과 자동 생성 액션을 관리한다.
 */
export interface SettingsPanelProps {
  open: boolean
  settings: SurveySettings
  itemsCount: number
  isGeneratingTrap: boolean
  onClose: () => void
  onChange: (settings: Partial<SurveySettings>) => void
  onGenerateTrap: () => void
}

export function SettingsPanel({
  open,
  settings,
  itemsCount,
  isGeneratingTrap,
  onClose,
  onChange,
  onGenerateTrap,
}: SettingsPanelProps) {
  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-950/30">
      <aside className="h-full w-full max-w-md overflow-y-auto bg-white p-5 shadow-xl">
        <div className="mb-5 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-950">설문 설정</h2>
            <p className="mt-1 text-sm text-slate-600">
              백엔드 생성 API에 전달할 설문 맥락도 여기서 관리합니다.
            </p>
          </div>
          <button
            type="button"
            className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
            aria-label="설정 닫기"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>

        <div className="space-y-5">
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-slate-700">설문 제목</span>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              value={settings.title}
              onChange={(event) => onChange({ title: event.target.value })}
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-slate-700">설문 맥락</span>
            <textarea
              className="min-h-28 w-full resize-y rounded-lg border border-slate-300 px-3 py-2 text-sm leading-6 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              value={settings.surveyContext}
              onChange={(event) => onChange({ surveyContext: event.target.value })}
            />
          </label>

          <div className="rounded-lg border border-slate-200 p-4">
            <label className="flex items-center justify-between gap-3">
              <span>
                <span className="block text-sm font-bold text-slate-800">함정 문항 사용</span>
                <span className="text-xs text-slate-500">응답 신뢰도 검증용 문항을 추가합니다.</span>
              </span>
              <input
                type="checkbox"
                className="h-5 w-5 rounded border-slate-300 text-teal-600"
                checked={settings.trapEnabled}
                onChange={(event) => onChange({ trapEnabled: event.target.checked })}
              />
            </label>
            <button
              type="button"
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-300"
              disabled={!settings.trapEnabled || itemsCount === 0 || isGeneratingTrap}
              onClick={onGenerateTrap}
            >
              {isGeneratingTrap ? <LoadingSpinner compact label="생성 중" /> : <Wand2 size={16} />}
              {isGeneratingTrap ? null : '함정 문항 자동 생성'}
            </button>
          </div>

          <div className="rounded-lg border border-slate-200 p-4">
            <label className="flex items-center justify-between gap-3">
              <span>
                <span className="block text-sm font-bold text-slate-800">역문항 사용</span>
                <span className="text-xs text-slate-500">문항별 역문항 지정 및 자동 생성을 허용합니다.</span>
              </span>
              <input
                type="checkbox"
                className="h-5 w-5 rounded border-slate-300 text-teal-600"
                checked={settings.reverseEnabled}
                onChange={(event) => onChange({ reverseEnabled: event.target.checked })}
              />
            </label>
          </div>
        </div>
      </aside>
    </div>
  )
}
