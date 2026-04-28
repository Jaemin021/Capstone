/**
 * 페이지: 설문지 생성/편집
 * 역할: 설문 문항을 추가·편집하고 품질 평가를 받는 메인 편집 화면
 * 주요 기능:
 *   - 문항 CRUD 및 드래그앤드롭 정렬
 *   - 문항 품질 평가 API 호출 및 결과 표시
 *   - CITC 예측 점수 조회
 *   - 함정/역문항 생성 및 삽입
 * API 연동: /api/item/quality, /api/survey/citc-predict, /api/item/generate-trap, /api/item/generate-reverse
 */
import { useEffect, useMemo, useState } from 'react'
import {
  closestCenter,
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useMutation } from '@tanstack/react-query'
import {
  AlertTriangle,
  Eye,
  GripVertical,
  ListChecks,
  Plus,
  RefreshCcw,
  Save,
  Settings,
  Sparkles,
  Wand2,
  X,
} from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  DEFAULT_LIKERT_5_OPTIONS,
  createSurvey,
  evaluateItemQuality,
  generateReverseItem,
  generateTrapItem,
  predictSurveyCitc,
} from '../api/surveyApi'
import { useMockApi } from '../api/http'
import { ItemCard } from '../components/ItemCard'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ScoreBar } from '../components/ScoreBar'
import { SettingsPanel } from '../components/SettingsPanel'
import { SuggestionModal } from '../components/SuggestionModal'
import { useSurveyStore } from '../store/surveyStore'
import { useToastStore } from '../store/toastStore'
import type { BackendSurveyCreatePayload, QuestionType, SurveyItem } from '../types/survey'

export interface SurveyEditorPageProps {
  mode: 'create' | 'edit'
}

interface QuestionFormValues {
  text: string
  type: QuestionType
}

const questionTypeOptions: { value: QuestionType; label: string }[] = [
  { value: 'likert-5', label: '리커트 척도 5점' },
  { value: 'likert-7', label: '리커트 척도 7점' },
  { value: 'multiple', label: '객관식' },
  { value: 'short', label: '주관식' },
]

function toBackendQuestionType(type: QuestionType) {
  if (type === 'likert-5') {
    return 'likert_5'
  }

  return 'likert_5'
}

function emptyToNull(value?: string) {
  const trimmed = value?.trim()
  return trimmed ? trimmed : null
}

function buildSurveyCreatePayload(
  settings: ReturnType<typeof useSurveyStore.getState>['settings'],
  items: SurveyItem[],
): BackendSurveyCreatePayload {
  return {
    title: settings.title.trim() || 'Untitled survey',
    description: emptyToNull(settings.description),
    construct_name: emptyToNull(settings.constructName),
    construct_description: emptyToNull(settings.constructDescription || settings.surveyContext),
    enable_validation_items: settings.trapEnabled || settings.reverseEnabled,
    items: items
      .filter((item) => item.text.trim().length > 0)
      .map((item, index) => ({
        item_order: index + 1,
        question_text: item.text.trim(),
        question_type: toBackendQuestionType(item.type),
        is_required: true,
        options: DEFAULT_LIKERT_5_OPTIONS.map((label, optionIndex) => ({
          option_order: optionIndex + 1,
          option_label: label,
        })),
      })),
  }
}

function HighlightedText({ text, words }: { text: string; words: string[] }) {
  if (words.length === 0) {
    return <>{text || '문항 평가 후 감지된 표현이 여기에 표시됩니다.'}</>
  }

  const pattern = new RegExp(`(${words.map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'g')
  const parts = text.split(pattern)

  return (
    <>
      {parts.map((part, index) =>
        words.includes(part) ? (
          <mark key={`${part}-${index}`} className="rounded bg-amber-200 px-1 text-slate-950">
            {part}
          </mark>
        ) : (
          <span key={`${part}-${index}`}>{part}</span>
        ),
      )}
    </>
  )
}

function SortableQuestionCard({
  item,
  index,
  selected,
}: {
  item: SurveyItem
  index: number
  selected: boolean
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.id,
  })
  const selectItem = useSurveyStore((state) => state.selectItem)
  const removeItem = useSurveyStore((state) => state.removeItem)
  const toggleReverse = useSurveyStore((state) => state.toggleReverse)

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.65 : 1,
      }}
    >
      <ItemCard
        item={item}
        index={index}
        isSelected={selected}
        onSelect={() => selectItem(item.id)}
        onDelete={() => removeItem(item.id)}
        onToggleReverse={(checked) => toggleReverse(item.id, checked)}
        dragActivator={
          <button
            type="button"
            className="mt-1 rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="문항 순서 변경"
            {...attributes}
            {...listeners}
          >
            <GripVertical size={16} />
          </button>
        }
      />
    </div>
  )
}

export function SurveyEditorPage({ mode }: SurveyEditorPageProps) {
  const { id } = useParams()
  const navigate = useNavigate()
  const [savedSurveyId, setSavedSurveyId] = useState<string | null>(id ?? null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [suggestionOpen, setSuggestionOpen] = useState(false)
  const { pushToast } = useToastStore()
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))

  const {
    items,
    selectedItemId,
    settings,
    addItem,
    insertGeneratedItem,
    updateItem,
    replaceItemText,
    setItemQuality,
    setCitcResults,
    setSettings,
    reorderItems,
    setItemsFromBackendSurvey,
  } = useSurveyStore()

  const selectedItem = useMemo(
    () => items.find((item) => item.id === selectedItemId) ?? null,
    [items, selectedItemId],
  )
  const selectedIndex = selectedItem ? items.findIndex((item) => item.id === selectedItem.id) : -1

  const { register, handleSubmit, reset, getValues } = useForm<QuestionFormValues>({
    defaultValues: {
      text: selectedItem?.text ?? '',
      type: selectedItem?.type ?? 'likert-5',
    },
  })

  useEffect(() => {
    reset({
      text: selectedItem?.text ?? '',
      type: selectedItem?.type ?? 'likert-5',
    })
  }, [reset, selectedItem])

  const createSurveyMutation = useMutation({
    mutationFn: () => {
      const payload = buildSurveyCreatePayload(settings, items)

      if (payload.items.length === 0) {
        throw new Error('설문 문항을 1개 이상 입력해 주세요.')
      }

      return createSurvey(payload)
    },
    onSuccess: (survey) => {
      setSavedSurveyId(survey.survey_id)
      setItemsFromBackendSurvey(survey)
      pushToast({
        type: 'success',
        title: '설문 생성 완료',
        description: `백엔드 survey_id: ${survey.survey_id}`,
      })
    },
    onError: (error) => {
      pushToast({
        type: 'error',
        title: '설문 생성 실패',
        description: error instanceof Error ? error.message : '백엔드 연결 또는 요청 형식을 확인해 주세요.',
      })
    },
  })

  const qualityMutation = useMutation({
    mutationFn: evaluateItemQuality,
    onSuccess: (result) => {
      if (!selectedItem) {
        return
      }

      setItemQuality(selectedItem.id, result)
      setSuggestionOpen(Boolean(result.suggestion))
      pushToast({
        type: 'success',
        title: '문항 품질 평가 완료',
        description: `품질 점수 ${result.score}점을 확인했습니다.`,
      })
    },
    onError: () => {
      pushToast({
        type: 'error',
        title: '문항 품질 평가 실패',
        description: '백엔드 API 연결 또는 응답 형식을 확인해 주세요.',
      })
    },
  })

  const citcMutation = useMutation({
    mutationFn: predictSurveyCitc,
    onSuccess: (response) => {
      setCitcResults(response.results)
      pushToast({
        type: 'success',
        title: '전체 일관성 분석 완료',
        description: '각 문항의 CITC 예측 점수를 업데이트했습니다.',
      })
    },
    onError: () => {
      pushToast({
        type: 'error',
        title: 'CITC 분석 실패',
        description: '문항 배열 요청/응답 구조를 백엔드와 확인해 주세요.',
      })
    },
  })

  const trapMutation = useMutation({
    mutationFn: generateTrapItem,
    onSuccess: (response) => {
      insertGeneratedItem(response.trapItem, response.suggestedPosition, { isTrap: true })
      pushToast({
        type: 'success',
        title: '함정 문항 생성 완료',
        description: `추천 위치 ${response.suggestedPosition + 1}번에 삽입했습니다.`,
      })
    },
    onError: () => {
      pushToast({
        type: 'error',
        title: '함정 문항 생성 실패',
        description: 'surveyContext와 items 요청값을 확인해 주세요.',
      })
    },
  })

  const reverseMutation = useMutation({
    mutationFn: generateReverseItem,
    onSuccess: (response) => {
      if (!selectedItem) {
        return
      }

      insertGeneratedItem(response.reverseItem, selectedIndex + 1, { isReverse: true })
      pushToast({
        type: 'success',
        title: '역문항 생성 완료',
        description: '선택한 문항 바로 아래에 삽입했습니다.',
      })
    },
    onError: () => {
      pushToast({
        type: 'error',
        title: '역문항 생성 실패',
        description: 'originalItem 요청값과 응답 형식을 확인해 주세요.',
      })
    },
  })

  const applyItemChanges = (values: QuestionFormValues) => {
    if (!selectedItem) {
      return
    }

    updateItem(selectedItem.id, {
      text: values.text,
      type: values.type,
    })
    pushToast({
      type: 'info',
      title: '문항 내용 반영',
      description: '현재 편집 내용이 좌측 목록에 반영되었습니다.',
    })
  }

  const handleEvaluateQuality = () => {
    if (!useMockApi) {
      pushToast({
        type: 'info',
        title: '백엔드 평가는 결과 화면에서 실행합니다',
        description: '설문을 생성한 뒤 결과 화면의 문항 품질 평가 버튼을 사용해 주세요.',
      })
      return
    }

    if (!selectedItem) {
      return
    }

    const values = getValues()
    const text = values.text.trim()

    if (text.length < 4) {
      pushToast({
        type: 'error',
        title: '문항을 먼저 입력해 주세요',
        description: '품질 평가에는 최소 4자 이상의 문항 텍스트가 필요합니다.',
      })
      return
    }

    updateItem(selectedItem.id, { text, type: values.type })

    // [API 연동 필요 - 문항 품질 평가]
    // 엔드포인트: POST /api/item/quality
    // 요청: { text: string }
    // 응답: { score: number, flaggedWords: string[], suggestion: string | null }
    qualityMutation.mutate({ text })
  }

  const handlePredictCitc = () => {
    if (!useMockApi) {
      pushToast({
        type: 'info',
        title: '백엔드 construct 평가로 대체됩니다',
        description: '설문 생성 후 결과 화면에서 문항 구성 타당도 평가를 실행해 주세요.',
      })
      return
    }

    const validItems = items
      .filter((item) => item.text.trim().length > 0)
      .map((item) => ({ id: item.id, text: item.text.trim() }))

    if (validItems.length < 2) {
      pushToast({
        type: 'error',
        title: '문항이 2개 이상 필요합니다',
        description: '전체 일관성 분석을 위해 문항을 더 추가해 주세요.',
      })
      return
    }

    // [API 연동 필요 - CITC 예측]
    // 엔드포인트: POST /api/survey/citc-predict
    // 요청: { items: { id: string, text: string }[] }
    // 응답: { results: { id: string, citcScore: number, embeddingScore: number, llmScore: number }[] }
    // 내부 로직: citcScore = a * embeddingScore + b * llmScore (가중합, a+b=1)
    citcMutation.mutate({ items: validItems })
  }

  const handleGenerateTrap = () => {
    if (!useMockApi) {
      pushToast({
        type: 'info',
        title: '자동 검증 문항은 설문 생성 시 처리됩니다',
        description: '설정에서 옵션을 켠 뒤 설문 생성 버튼을 누르면 백엔드가 생성을 시도합니다.',
      })
      return
    }

    // [API 연동 필요 - 함정 문항 생성]
    // 엔드포인트: POST /api/item/generate-trap
    // 요청: { surveyContext: string, items: string[] }
    // 응답: { trapItem: string, suggestedPosition: number }
    trapMutation.mutate({
      surveyContext: settings.surveyContext,
      items: items.map((item) => item.text),
    })
  }

  const handleGenerateReverse = () => {
    if (!useMockApi) {
      pushToast({
        type: 'info',
        title: '자동 검증 문항은 설문 생성 시 처리됩니다',
        description: '설정에서 옵션을 켠 뒤 설문 생성 버튼을 누르면 백엔드가 생성을 시도합니다.',
      })
      return
    }

    if (!selectedItem) {
      return
    }

    const text = getValues().text.trim() || selectedItem.text

    if (!settings.reverseEnabled) {
      pushToast({
        type: 'error',
        title: '역문항 설정이 꺼져 있습니다',
        description: '설문 설정에서 역문항 기능을 켠 뒤 다시 시도해 주세요.',
      })
      return
    }

    // [API 연동 필요 - 역문항 생성]
    // 엔드포인트: POST /api/item/generate-reverse
    // 요청: { originalItem: string }
    // 응답: { reverseItem: string }
    reverseMutation.mutate({ originalItem: text })
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      reorderItems(String(active.id), String(over.id))
    }
  }

  const handleReplaceSuggestion = () => {
    if (!selectedItem?.quality?.suggestion) {
      return
    }

    replaceItemText(selectedItem.id, selectedItem.quality.suggestion)
    setSuggestionOpen(false)
  }

  const handleSaveDraft = () => {
    createSurveyMutation.mutate()
  }

  const pageTitle = mode === 'edit' ? `설문지 편집 ${id ? `#${id}` : ''}` : '설문지 생성'

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-black text-slate-950">{pageTitle}</h1>
            <p className="mt-1 text-sm text-slate-600">
              설문을 생성하면 백엔드에 저장되고, 생성된 survey_id로 응답 화면과 평가 화면을 확인할 수 있습니다.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
              onClick={() => setPreviewOpen(true)}
            >
              <Eye size={16} />
              미리보기
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
              onClick={() => setSettingsOpen(true)}
            >
              <Settings size={16} />
              설정
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md bg-teal-600 px-3 py-2 text-sm font-bold text-white hover:bg-teal-700 disabled:bg-slate-300"
              disabled={createSurveyMutation.isPending}
              onClick={handleSaveDraft}
            >
              {createSurveyMutation.isPending ? <LoadingSpinner compact label="저장 중" /> : <Save size={16} />}
              {createSurveyMutation.isPending ? null : '설문 생성'}
            </button>
            {savedSurveyId ? (
              <>
                <button
                  type="button"
                  className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-bold text-white hover:bg-slate-800"
                  onClick={() => navigate(`/survey/${savedSurveyId}/respond`)}
                >
                  응답 화면
                </button>
                <Link
                  to={`/survey/${savedSurveyId}/results`}
                  className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
                >
                  결과 보기
                </Link>
              </>
            ) : null}
          </div>
        </div>
      </section>

      <section className="grid min-h-[calc(100vh-210px)] gap-4 lg:grid-cols-[360px_1fr]">
        <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-black text-slate-950">문항 목록</h2>
              <p className="text-xs text-slate-500">드래그해서 순서를 바꿀 수 있습니다.</p>
            </div>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-2 text-sm font-bold text-white hover:bg-slate-800"
              onClick={addItem}
            >
              <Plus size={16} />
              추가
            </button>
          </div>

          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={items.map((item) => item.id)} strategy={verticalListSortingStrategy}>
              <div className="space-y-3">
                {items.map((item, index) => (
                  <SortableQuestionCard
                    key={item.id}
                    item={item}
                    index={index}
                    selected={item.id === selectedItemId}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>

          <button
            type="button"
            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md border border-teal-200 bg-teal-50 px-3 py-2 text-sm font-bold text-teal-700 hover:bg-teal-100 disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
            disabled={items.length < 2 || citcMutation.isPending}
            onClick={handlePredictCitc}
          >
            {citcMutation.isPending ? (
              <LoadingSpinner compact label="분석 중" />
            ) : (
              <>
                <ListChecks size={16} />
                전체 일관성 분석
              </>
            )}
          </button>
        </aside>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          {selectedItem ? (
            <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
              <form className="space-y-4" onSubmit={handleSubmit(applyItemChanges)}>
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <h2 className="text-lg font-black text-slate-950">
                      Q{selectedIndex + 1}. 문항 상세 편집
                    </h2>
                    <p className="text-sm text-slate-600">
                      문항을 수정한 뒤 평가하거나 역문항을 자동 생성할 수 있습니다.
                    </p>
                  </div>
                  <button
                    type="submit"
                    className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
                  >
                    <RefreshCcw size={16} />
                    문항 내용 반영
                  </button>
                </div>

                <label className="block">
                  <span className="mb-2 block text-sm font-bold text-slate-700">문항 텍스트</span>
                  <textarea
                    className="min-h-40 w-full resize-y rounded-lg border border-slate-300 px-3 py-3 text-sm leading-6 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                    placeholder="예: 이 서비스는 필요한 기능을 쉽게 찾을 수 있게 구성되어 있다."
                    {...register('text')}
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-bold text-slate-700">문항 유형</span>
                  <select
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                    {...register('type')}
                  >
                    {questionTypeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="flex flex-col gap-2 sm:flex-row">
                  <button
                    type="button"
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700 disabled:bg-slate-300"
                    disabled={qualityMutation.isPending}
                    onClick={handleEvaluateQuality}
                  >
                    {qualityMutation.isPending ? (
                      <LoadingSpinner compact label="평가 중" />
                    ) : (
                      <>
                        <Sparkles size={16} />
                        문항 평가하기
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center justify-center gap-2 rounded-md border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-bold text-indigo-700 hover:bg-indigo-100 disabled:bg-slate-100 disabled:text-slate-400"
                    disabled={reverseMutation.isPending}
                    onClick={handleGenerateReverse}
                  >
                    {reverseMutation.isPending ? (
                      <LoadingSpinner compact label="생성 중" />
                    ) : (
                      <>
                        <Wand2 size={16} />
                        역문항 자동 생성
                      </>
                    )}
                  </button>
                </div>
              </form>

              <div className="space-y-4">
                <section className="rounded-lg border border-slate-200 p-4">
                  <h3 className="mb-3 text-base font-black text-slate-950">문항 품질 평가</h3>
                  {selectedItem.quality ? (
                    <div className="space-y-4">
                      <ScoreBar score={selectedItem.quality.score} label="품질 점수" />
                      <div>
                        <p className="mb-2 text-sm font-bold text-slate-700">감지된 문제 어휘</p>
                        <p className="rounded-lg bg-slate-50 p-3 text-sm leading-7 text-slate-700">
                          <HighlightedText
                            text={selectedItem.text}
                            words={selectedItem.quality.flaggedWords}
                          />
                        </p>
                      </div>
                      {selectedItem.quality.score <= 60 ? (
                        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                          <div className="flex items-start gap-2">
                            <AlertTriangle className="mt-0.5 shrink-0 text-amber-600" size={17} />
                            <div>
                              <p className="text-sm font-black text-amber-900">대체 문항 추천 필요</p>
                              <p className="mt-1 text-sm leading-6 text-amber-900/85">
                                점수가 60점 이하라 추천 문항 확인 모달을 열 수 있습니다.
                              </p>
                              <button
                                type="button"
                                className="mt-3 rounded-md bg-amber-600 px-3 py-2 text-sm font-bold text-white hover:bg-amber-700"
                                onClick={() => setSuggestionOpen(true)}
                              >
                                추천 문항 보기
                              </button>
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
                      문항 입력 후 <strong>문항 평가하기</strong>를 누르면 품질 점수, 문제 어휘,
                      대체 문항 추천이 표시됩니다.
                    </p>
                  )}
                </section>

                <section className="rounded-lg border border-slate-200 p-4">
                  <h3 className="mb-3 text-base font-black text-slate-950">CITC 예측 점수</h3>
                  {selectedItem.citc ? (
                    <div className="space-y-3">
                      <ScoreBar score={selectedItem.citc.citcScore * 100} label="CITC 예측" />
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="rounded-lg bg-slate-50 p-3">
                          <span className="block text-xs font-semibold text-slate-500">Embedding</span>
                          <strong className="text-slate-950">{selectedItem.citc.embeddingScore}</strong>
                        </div>
                        <div className="rounded-lg bg-slate-50 p-3">
                          <span className="block text-xs font-semibold text-slate-500">LLM</span>
                          <strong className="text-slate-950">{selectedItem.citc.llmScore}</strong>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
                      문항이 2개 이상일 때 좌측 하단의 <strong>전체 일관성 분석</strong>을 실행하세요.
                    </p>
                  )}
                </section>
              </div>
            </div>
          ) : (
            <div className="flex min-h-96 flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 p-8 text-center">
              <h2 className="text-lg font-black text-slate-950">선택된 문항이 없습니다</h2>
              <p className="mt-2 text-sm text-slate-600">문항을 추가해서 설문 편집을 시작하세요.</p>
              <button
                type="button"
                className="mt-4 inline-flex items-center gap-2 rounded-md bg-teal-600 px-4 py-2 text-sm font-bold text-white"
                onClick={addItem}
              >
                <Plus size={16} />
                문항 추가
              </button>
            </div>
          )}
        </section>
      </section>

      <SettingsPanel
        open={settingsOpen}
        settings={settings}
        itemsCount={items.length}
        isGeneratingTrap={trapMutation.isPending}
        onClose={() => setSettingsOpen(false)}
        onChange={setSettings}
        onGenerateTrap={handleGenerateTrap}
      />

      <SuggestionModal
        open={suggestionOpen}
        suggestion={selectedItem?.quality?.suggestion ?? null}
        onReplace={handleReplaceSuggestion}
        onIgnore={() => setSuggestionOpen(false)}
      />

      {previewOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4">
          <section className="max-h-[84vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-5 shadow-xl">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-black text-slate-950">{settings.title}</h2>
                <p className="mt-1 text-sm text-slate-600">{settings.surveyContext}</p>
              </div>
              <button
                type="button"
                className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
                aria-label="미리보기 닫기"
                onClick={() => setPreviewOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
            <ol className="space-y-3">
              {items.map((item, index) => (
                <li key={item.id} className="rounded-lg border border-slate-200 p-4">
                  <p className="text-sm font-bold text-slate-500">Q{index + 1}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-800">
                    {item.text || '빈 문항입니다.'}
                  </p>
                </li>
              ))}
            </ol>
          </section>
        </div>
      ) : null}
    </div>
  )
}
