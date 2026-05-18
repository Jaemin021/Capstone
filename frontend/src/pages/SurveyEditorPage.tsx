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
import { useMutation, useQuery } from '@tanstack/react-query'
import { Eye, GripVertical, Plus, Save, X } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  createSurvey,
  DEFAULT_LIKERT_5_OPTIONS,
  getSurvey,
  updateSurvey,
} from '../api/surveyApi'
import { ItemCard } from '../components/ItemCard'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { useSurveyStore } from '../store/surveyStore'
import { useToastStore } from '../store/toastStore'
import type { BackendSurveyCreatePayload, SurveyItem } from '../types/survey'

export interface SurveyEditorPageProps {
  mode: 'create' | 'edit'
}

type SaveSurveyResult = {
  survey: Awaited<ReturnType<typeof createSurvey>>
  action: 'create' | 'update'
}

const emptyOptionValues = ['', '', '', '', '']

function getApiErrorMessage(error: unknown, fallback: string) {
  if (typeof error !== 'object' || error === null) {
    return fallback
  }

  const response = (error as { response?: { data?: unknown } }).response
  const data = response?.data

  if (typeof data === 'string') {
    return data
  }

  if (typeof data === 'object' && data !== null) {
    const detail = (data as { detail?: unknown; error?: unknown; message?: unknown }).detail
    const apiError = (data as { error?: unknown }).error
    const message = (data as { message?: unknown }).message

    if (typeof detail === 'string') {
      return detail
    }

    if (typeof apiError === 'string') {
      return apiError
    }

    if (typeof message === 'string') {
      return message
    }
  }

  return fallback
}

function toBackendQuestionType() {
  return 'likert_5'
}

function emptyToNull(value?: string) {
  const trimmed = value?.trim()
  return trimmed ? trimmed : null
}

function isEditableItem(item: SurveyItem) {
  return !item.isTrap && !item.isReverse
}

function getEditableItems(items: SurveyItem[]) {
  return items.filter(isEditableItem)
}

function validateSurveyForSave(
  title: string,
  surveyContext: string,
  items: SurveyItem[],
) {
  if (!title.trim()) {
    return '설문 제목을 입력해 주세요.'
  }

  if (!surveyContext.trim()) {
    return '설문 맥락을 입력해 주세요.'
  }

  const editableItems = getEditableItems(items)
  const validItems = editableItems.filter((item) => item.text.trim().length > 0)

  if (validItems.length === 0) {
    return '설문 문항을 1개 이상 입력해 주세요.'
  }

  const optionIssue = validItems.findIndex((item) =>
    item.options.slice(0, 5).some((option) => option.trim().length === 0),
  )

  if (optionIssue >= 0) {
    return `Q${optionIssue + 1}의 보기 5개를 모두 입력해 주세요.`
  }

  return null
}

function buildSurveyPayload(
  title: string,
  surveyContext: string,
  items: SurveyItem[],
  enableValidationItems: boolean,
): BackendSurveyCreatePayload {
  return {
    title: title.trim(),
    description: emptyToNull(surveyContext),
    enable_validation_items: enableValidationItems,
    items: getEditableItems(items)
      .filter((item) => item.text.trim().length > 0)
      .map((item, index) => ({
        item_order: index + 1,
        question_text: item.text.trim(),
        question_type: toBackendQuestionType(),
        is_required: true,
        options: item.options.slice(0, 5).map((label, optionIndex) => ({
          option_order: optionIndex + 1,
          option_label: label.trim(),
        })),
      })),
  }
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
  const { pushToast } = useToastStore()
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))
  const isEditMode = mode === 'edit' && Boolean(id)

  const [savedSurveyId, setSavedSurveyId] = useState<string | null>(id ?? null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [createConfirmOpen, setCreateConfirmOpen] = useState(false)
  const [loadedSurveyId, setLoadedSurveyId] = useState<string | null>(null)

  const {
    items,
    selectedItemId,
    settings,
    draftResetAt,
    resetDraft,
    addItem,
    updateItem,
    updateItemOption,
    setItemOptions,
    setSettings,
    reorderItems,
    setItemsFromBackendSurvey,
  } = useSurveyStore()

  const editSurveyQuery = useQuery({
    queryKey: ['survey-edit', id],
    queryFn: () => getSurvey(id as string),
    enabled: isEditMode,
    retry: false,
  })

  useEffect(() => {
    if (!isEditMode) {
      return
    }

    const survey = editSurveyQuery.data
    if (!survey || loadedSurveyId === survey.survey_id) {
      return
    }

    setItemsFromBackendSurvey(survey, { normalItemsOnly: true })
    setSavedSurveyId(survey.survey_id)
    setLoadedSurveyId(survey.survey_id)
  }, [editSurveyQuery.data, isEditMode, loadedSurveyId, setItemsFromBackendSurvey])

  useEffect(() => {
    if (isEditMode) {
      return
    }

    resetDraft()
  }, [isEditMode, resetDraft])

  useEffect(() => {
    if (isEditMode) {
      return
    }

    setSavedSurveyId(null)
    setLoadedSurveyId(null)
    setCreateConfirmOpen(false)
  }, [isEditMode, draftResetAt])

  const selectedItem = useMemo(
    () => items.find((item) => item.id === selectedItemId) ?? null,
    [items, selectedItemId],
  )
  const selectedIndex = selectedItem ? items.findIndex((item) => item.id === selectedItem.id) : -1

  const saveSurveyMutation = useMutation<SaveSurveyResult, unknown, boolean>({
    mutationFn: (enableValidationItems: boolean) => {
      const errorMessage = validateSurveyForSave(settings.title, settings.surveyContext, items)

      if (errorMessage) {
        throw new Error(errorMessage)
      }

      const payload = buildSurveyPayload(
        settings.title,
        settings.surveyContext,
        items,
        enableValidationItems,
      )

      const targetSurveyId = isEditMode ? id ?? null : savedSurveyId

      if (targetSurveyId) {
        return updateSurvey(targetSurveyId, payload).then((survey) => ({
          survey,
          action: 'update' as const,
        }))
      }

      return createSurvey(payload).then((survey) => ({
        survey,
        action: 'create' as const,
      }))
    },
    onSuccess: ({ survey, action }, enableValidationItems) => {
      setSavedSurveyId(survey.survey_id)
      setItemsFromBackendSurvey(survey, { normalItemsOnly: true })
      setCreateConfirmOpen(false)
      pushToast({
        type: 'success',
        title: action === 'update' ? '설문 저장 완료' : '설문 생성 완료',
        description: enableValidationItems
          ? `함정/역문항 포함 처리 완료 (survey_id: ${survey.survey_id})`
          : `기본 설문 저장 완료 (survey_id: ${survey.survey_id})`,
      })
    },
    onError: (error) => {
      console.error('[survey-editor] save failed', {
        mode,
        surveyId: id ?? savedSurveyId,
        error,
        response: (error as { response?: { data?: unknown; status?: number } })?.response,
      })
      pushToast({
        type: 'error',
        title: isEditMode || Boolean(savedSurveyId) ? '설문 저장 실패' : '설문 생성 실패',
        description: getApiErrorMessage(
          error,
          error instanceof Error ? error.message : '요청 처리 중 오류가 발생했습니다.',
        ),
      })
    },
  })

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      reorderItems(String(active.id), String(over.id))
    }
  }

  const pageTitle = isEditMode ? `설문지 수정${id ? ` #${id}` : ''}` : '설문지 생성'
  const hasExistingSurveyTarget = isEditMode ? Boolean(id) : Boolean(savedSurveyId)
  const primaryActionLabel = hasExistingSurveyTarget ? '설문 저장' : '설문 생성'
  const isLoadingEditSurvey = isEditMode && editSurveyQuery.isLoading && loadedSurveyId === null

  if (isEditMode && editSurveyQuery.isError && loadedSurveyId === null) {
    return (
      <section className="rounded-lg border border-rose-200 bg-white p-6 shadow-sm">
        <h1 className="text-lg font-black text-slate-950">설문을 불러오지 못했습니다.</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          설문 ID를 확인하거나 백엔드 서버 상태를 확인해 주세요.
        </p>
      </section>
    )
  }

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h1 className="text-2xl font-black text-slate-950">{pageTitle}</h1>
              <p className="mt-1 text-sm text-slate-600">
                설문 제목, 설문 맥락, 문항과 보기 5개만 작성해 설문을 저장해 주세요.
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
                className="inline-flex items-center gap-2 rounded-md bg-teal-600 px-3 py-2 text-sm font-bold text-white hover:bg-teal-700 disabled:bg-slate-300"
                disabled={saveSurveyMutation.isPending || isLoadingEditSurvey}
                onClick={() => setCreateConfirmOpen(true)}
              >
                {saveSurveyMutation.isPending ? (
                  <LoadingSpinner compact label="저장 중" />
                ) : (
                  <Save size={16} />
                )}
                {saveSurveyMutation.isPending ? null : primaryActionLabel}
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

          {isLoadingEditSurvey ? (
            <div className="rounded-lg bg-slate-50 p-3">
              <LoadingSpinner compact label="설문 불러오는 중" />
            </div>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-sm font-bold text-slate-700">설문 제목</span>
              <input
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                value={settings.title}
                onChange={(event) => setSettings({ title: event.target.value })}
                placeholder="예: 서비스 만족도 설문"
              />
            </label>

            <label className="block lg:col-span-2">
              <span className="mb-2 block text-sm font-bold text-slate-700">설문 맥락</span>
              <textarea
                className="min-h-24 w-full resize-y rounded-lg border border-slate-300 px-3 py-2 text-sm leading-6 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                value={settings.surveyContext}
                onChange={(event) => setSettings({ surveyContext: event.target.value })}
                placeholder="응답자가 어떤 맥락에서 답하는지 설명해 주세요."
              />
            </label>
          </div>
        </div>
      </section>

      <section className="grid min-h-[calc(100vh-230px)] gap-4 lg:grid-cols-[360px_1fr]">
        <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-black text-slate-950">문항 목록</h2>
              <p className="text-xs text-slate-500">드래그해서 문항 순서를 바꿀 수 있습니다.</p>
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
            className="mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
            onClick={addItem}
          >
            <Plus size={16} />
            문항 추가
          </button>
        </aside>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          {selectedItem ? (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-black text-slate-950">Q{selectedIndex + 1}. 문항 상세 편집</h2>
                <p className="text-sm text-slate-600">문항 텍스트와 보기 5개를 직접 입력해 주세요.</p>
              </div>

              <label className="block">
                <span className="mb-2 block text-sm font-bold text-slate-700">문항 텍스트</span>
                <textarea
                  className="min-h-40 w-full resize-y rounded-lg border border-slate-300 px-3 py-3 text-sm leading-6 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                  placeholder="문항 텍스트를 입력해 주세요."
                  value={selectedItem.text}
                  onChange={(event) => updateItem(selectedItem.id, { text: event.target.value })}
                />
              </label>

              <div className="rounded-lg border border-slate-200 p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-black text-slate-900">보기 입력 (5개)</h3>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-bold text-slate-700 hover:bg-slate-50"
                      onClick={() => setItemOptions(selectedItem.id, DEFAULT_LIKERT_5_OPTIONS)}
                    >
                      표준 보기 채우기
                    </button>
                    <button
                      type="button"
                      className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-bold text-slate-700 hover:bg-slate-50"
                      onClick={() => setItemOptions(selectedItem.id, emptyOptionValues)}
                    >
                      모두 비우기
                    </button>
                  </div>
                </div>
                <div className="space-y-2">
                  {selectedItem.options.slice(0, 5).map((option, optionIndex) => (
                    <label key={`${selectedItem.id}-option-${optionIndex}`} className="block">
                      <span className="mb-1 block text-xs font-bold text-slate-600">보기 {optionIndex + 1}</span>
                      <input
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                        value={option}
                        placeholder={DEFAULT_LIKERT_5_OPTIONS[optionIndex] ?? `보기 ${optionIndex + 1}`}
                        onChange={(event) => updateItemOption(selectedItem.id, optionIndex, event.target.value)}
                      />
                    </label>
                  ))}
                </div>
              </div>

              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
                onClick={addItem}
              >
                <Plus size={16} />
                아래에 문항 추가
              </button>
            </div>
          ) : (
            <div className="flex min-h-96 flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 p-8 text-center">
              <h2 className="text-lg font-black text-slate-950">선택된 문항이 없습니다.</h2>
              <p className="mt-2 text-sm text-slate-600">문항을 추가해서 설문 작성을 시작해 주세요.</p>
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

      {createConfirmOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4">
          <section className="w-full max-w-xl rounded-lg bg-white p-5 shadow-xl">
            <h2 className="text-lg font-black text-slate-950">설문 저장 옵션 선택</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              함정 문항과 역문항을 자동 생성하면 응답 신뢰도를 더 정확하게 계산할 수 있습니다.
              필요하면 기본 설문만 저장할 수도 있습니다.
            </p>
            <div className="mt-5 flex flex-col gap-2 sm:flex-row">
              <button
                type="button"
                className="inline-flex flex-1 items-center justify-center rounded-md bg-slate-900 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:bg-slate-300"
                disabled={saveSurveyMutation.isPending || isLoadingEditSurvey}
                onClick={() => saveSurveyMutation.mutate(true)}
              >
                함정/역문항 포함해서 저장
              </button>
              <button
                type="button"
                className="inline-flex flex-1 items-center justify-center rounded-md border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:text-slate-400"
                disabled={saveSurveyMutation.isPending || isLoadingEditSurvey}
                onClick={() => saveSurveyMutation.mutate(false)}
              >
                기본 설문만 저장
              </button>
            </div>
            <button
              type="button"
              className="mt-3 inline-flex w-full items-center justify-center rounded-md px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-100"
              disabled={saveSurveyMutation.isPending || isLoadingEditSurvey}
              onClick={() => setCreateConfirmOpen(false)}
            >
              닫기
            </button>
          </section>
        </div>
      ) : null}

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
                  <p className="mt-1 text-sm leading-6 text-slate-800">{item.text || '빈 문항입니다.'}</p>
                  <ul className="mt-3 space-y-1">
                    {item.options.slice(0, 5).map((option, optionIndex) => (
                      <li
                        key={`${item.id}-preview-${optionIndex}`}
                        className="rounded-md bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-600"
                      >
                        {optionIndex + 1}. {option || '(보기 미입력)'}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          </section>
        </div>
      ) : null}
    </div>
  )
}
