import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AlertTriangle, ArrowLeft, ArrowRight, CheckCircle2 } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getPublicSurvey,
  getPublicSurveyAvailability,
  getSurvey,
  saveResponseResultToStorage,
  submitPublicSurveyResponse,
  submitSurveyResponse,
} from '../api/surveyApi'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { useToastStore } from '../store/toastStore'
import type {
  BackendSurveyItem,
  ConnectionEventSubmit,
  ResponseItemLogSubmit,
  SurveyResponseSubmitPayload,
} from '../types/survey'

interface DraftItemLog extends ResponseItemLogSubmit {
  entered_at_ms: number | null
  first_selected_at_ms: number | null
  last_selected_at_ms: number | null
  current_visit_started_ms: number | null
  current_visit_is_revisit: boolean
}

interface ResponseSession {
  respondentId: string
  startedAt: string
  startedAtMs: number
  totalTouchCount: number
  connectionLost: boolean
  offlineCount: number
  offlineTotalMs: number
  offlineStartedAtMs: number | null
  connectionEvents: ConnectionEventSubmit[]
  itemLogs: Record<string, DraftItemLog>
  answers: Record<string, number>
}

const nowIso = () => new Date().toISOString()
const nowMs = () => Date.now()
const publicDeviceStorageKey = 'survey-public-device-id'

function getOrCreatePublicDeviceId() {
  if (typeof window === 'undefined') {
    return ''
  }

  const existing = window.localStorage.getItem(publicDeviceStorageKey)
  if (existing) {
    return existing
  }

  const created =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`

  window.localStorage.setItem(publicDeviceStorageKey, created)
  return created
}

function createEmptyItemLog(itemId: string, enteredAt: string, enteredAtMs: number): DraftItemLog {
  return {
    item_id: itemId,
    checked_at: null,
    previous_checked_at: null,
    entered_at: enteredAt,
    entered_at_ms: enteredAtMs,
    first_selected_at: null,
    first_selected_at_ms: null,
    last_selected_at: null,
    last_selected_at_ms: null,
    last_exited_at: null,
    item_time_ms: 0,
    time_share: null,
    time_to_first_answer_ms: null,
    time_after_last_answer_ms: null,
    touch_count: 0,
    change_count: 0,
    visit_count: 1,
    back_visit_count: 0,
    is_revisited: false,
    initial_visit_time_ms: 0,
    revisit_time_ms: 0,
    answer_changed: false,
    changed_after_revisit: false,
    first_selected_option_order: null,
    final_selected_option_order: null,
    current_visit_started_ms: enteredAtMs,
    current_visit_is_revisit: false,
  }
}

function toSubmitItemLog(log: DraftItemLog, totalTimeMs: number): ResponseItemLogSubmit {
  const itemTimeMs = Math.max(0, log.initial_visit_time_ms + log.revisit_time_ms)

  return {
    item_id: log.item_id,
    checked_at: log.checked_at ?? null,
    previous_checked_at: log.previous_checked_at ?? null,
    entered_at: log.entered_at ?? null,
    first_selected_at: log.first_selected_at ?? null,
    last_selected_at: log.last_selected_at ?? null,
    last_exited_at: log.last_exited_at ?? null,
    item_time_ms: itemTimeMs,
    time_share: totalTimeMs > 0 ? itemTimeMs / totalTimeMs : 0,
    time_to_first_answer_ms: log.time_to_first_answer_ms ?? null,
    time_after_last_answer_ms: log.time_after_last_answer_ms ?? null,
    touch_count: log.touch_count,
    change_count: log.change_count,
    visit_count: log.visit_count,
    back_visit_count: log.back_visit_count,
    is_revisited: log.is_revisited,
    initial_visit_time_ms: log.initial_visit_time_ms,
    revisit_time_ms: log.revisit_time_ms,
    answer_changed: log.answer_changed,
    changed_after_revisit: log.changed_after_revisit,
    first_selected_option_order: log.first_selected_option_order ?? null,
    final_selected_option_order: log.final_selected_option_order ?? null,
  }
}

function getDisplayOptions(item: BackendSurveyItem) {
  if (item.options.length > 0) {
    return item.options
  }

  return [1, 2, 3, 4, 5].map((order) => ({
    option_id: `${item.item_id}-option-${order}`,
    option_order: order,
    option_label: String(order),
    option_score: order,
  }))
}

function getRoleBadge(item: BackendSurveyItem) {
  if (item.item_role === 'reverse') {
    return {
      label: '역문항',
      className: 'bg-indigo-50 text-indigo-700',
    }
  }

  if (item.item_role === 'trap') {
    return {
      label: '함정문항',
      className: 'bg-rose-50 text-rose-700',
    }
  }

  return null
}

export function SurveyRespondPage() {
  const { id = '', accessKey = '' } = useParams()
  const isPublicMode = Boolean(accessKey)
  const surveyIdentifier = isPublicMode ? accessKey : id
  const navigate = useNavigate()
  const { pushToast } = useToastStore()
  const sessionRef = useRef<ResponseSession | null>(null)
  const initializedRef = useRef(false)
  const [session, setSession] = useState<ResponseSession | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const publicDeviceId = useMemo(
    () => (isPublicMode ? getOrCreatePublicDeviceId() : ''),
    [isPublicMode],
  )

  const surveyQuery = useQuery({
    queryKey: ['survey', isPublicMode ? 'public' : 'private', surveyIdentifier],
    queryFn: () => (isPublicMode ? getPublicSurvey(accessKey) : getSurvey(id)),
    enabled: Boolean(surveyIdentifier),
  })

  const publicAvailabilityQuery = useQuery({
    queryKey: ['public-availability', accessKey, publicDeviceId],
    queryFn: () => getPublicSurveyAvailability(accessKey, publicDeviceId),
    enabled: isPublicMode && surveyQuery.isSuccess && Boolean(accessKey) && Boolean(publicDeviceId),
    retry: false,
  })

  const survey = surveyQuery.data
  const items = useMemo(() => survey?.items ?? [], [survey])
  const currentItem = items[currentIndex]
  const progress = items.length > 0 ? ((currentIndex + 1) / items.length) * 100 : 0
  const isPublicBlocked = isPublicMode && publicAvailabilityQuery.data?.available === false

  useEffect(() => {
    initializedRef.current = false
    sessionRef.current = null
    setSession(null)
    setCurrentIndex(0)
  }, [surveyIdentifier, isPublicMode])

  const commitSession = (updater: (value: ResponseSession) => ResponseSession) => {
    if (!sessionRef.current) {
      return null
    }

    const next = updater(sessionRef.current)
    sessionRef.current = next
    setSession(next)
    return next
  }

  const enterItem = (item: BackendSurveyItem, viaBack: boolean) => {
    const enteredAt = nowIso()
    const enteredAtMs = nowMs()

    commitSession((value) => {
      const existing = value.itemLogs[item.item_id]
      const itemLog = existing
        ? {
            ...existing,
            visit_count: existing.visit_count + 1,
            back_visit_count: existing.back_visit_count + (viaBack ? 1 : 0),
            is_revisited: true,
            current_visit_started_ms: enteredAtMs,
            current_visit_is_revisit: true,
          }
        : createEmptyItemLog(item.item_id, enteredAt, enteredAtMs)

      return {
        ...value,
        itemLogs: {
          ...value.itemLogs,
          [item.item_id]: itemLog,
        },
      }
    })
  }

  const leaveItem = (item: BackendSurveyItem, value: ResponseSession) => {
    const exitedAt = nowIso()
    const exitedAtMs = nowMs()
    const existing = value.itemLogs[item.item_id]

    if (!existing) {
      return value
    }

    const visitStartedAt = existing.current_visit_started_ms ?? exitedAtMs
    const visitDuration = Math.max(0, exitedAtMs - visitStartedAt)
    const initialVisitTime = existing.current_visit_is_revisit
      ? existing.initial_visit_time_ms
      : existing.initial_visit_time_ms + visitDuration
    const revisitTime = existing.current_visit_is_revisit
      ? existing.revisit_time_ms + visitDuration
      : existing.revisit_time_ms
    const itemTimeMs = initialVisitTime + revisitTime
    const timeToFirstAnswer =
      existing.first_selected_at_ms !== null && existing.entered_at_ms !== null
        ? Math.max(0, existing.first_selected_at_ms - existing.entered_at_ms)
        : null
    const timeAfterLastAnswer =
      existing.last_selected_at_ms !== null
        ? Math.max(0, exitedAtMs - existing.last_selected_at_ms)
        : null

    return {
      ...value,
      itemLogs: {
        ...value.itemLogs,
        [item.item_id]: {
          ...existing,
          last_exited_at: exitedAt,
          item_time_ms: itemTimeMs,
          time_to_first_answer_ms: timeToFirstAnswer,
          time_after_last_answer_ms: timeAfterLastAnswer,
          initial_visit_time_ms: initialVisitTime,
          revisit_time_ms: revisitTime,
          current_visit_started_ms: null,
          current_visit_is_revisit: false,
        },
      },
    }
  }

  const submitMutation = useMutation({
    mutationFn: (payload: SurveyResponseSubmitPayload) =>
      isPublicMode
        ? submitPublicSurveyResponse(accessKey, publicDeviceId, payload)
        : submitSurveyResponse(id, payload),
    onSuccess: (result) => {
      if (isPublicMode) {
        pushToast({
          type: 'success',
          title: '설문 제출 완료',
          description: '응답이 정상적으로 저장되었습니다.',
        })
        navigate(`/public/s/${accessKey}/complete`, { replace: true })
        return
      }

      saveResponseResultToStorage(id, result)
      pushToast({
        type: 'success',
        title: '응답 제출 완료',
        description: '백엔드에서 응답 로그를 저장하고 feature를 계산했습니다.',
      })
      navigate(`/survey/${id}/results`, { state: { responseResult: result } })
    },
    onError: (error) => {
      const status = (error as { response?: { status?: number } })?.response?.status
      if (status === 409) {
        pushToast({
          type: 'error',
          title: '이미 응답한 기기입니다',
          description: '같은 기기에서는 한 번만 응답할 수 있습니다.',
        })
        return
      }

      pushToast({
        type: 'error',
        title: '응답 제출 실패',
        description: '백엔드 연결 또는 응답 로그 형식을 확인해 주세요.',
      })
    },
  })
  useEffect(() => {
    if (!survey || initializedRef.current || items.length === 0 || isPublicBlocked) {
      return
    }

    initializedRef.current = true
    const startedAt = nowIso()
    const startedAtMs = nowMs()
    const firstItem = items[0]
    const initialSession: ResponseSession = {
      respondentId: isPublicMode ? `device:${publicDeviceId}` : `user-${startedAtMs}`,
      startedAt,
      startedAtMs,
      totalTouchCount: 0,
      connectionLost: false,
      offlineCount: 0,
      offlineTotalMs: 0,
      offlineStartedAtMs: null,
      connectionEvents: [],
      itemLogs: {
        [firstItem.item_id]: createEmptyItemLog(firstItem.item_id, startedAt, startedAtMs),
      },
      answers: {},
    }

    sessionRef.current = initialSession
    setSession(initialSession)
  }, [items, survey, isPublicBlocked, isPublicMode, publicDeviceId])

  useEffect(() => {
    const handleOffline = () => {
      commitSession((value) => ({
        ...value,
        connectionLost: true,
        offlineCount: value.offlineCount + 1,
        offlineStartedAtMs: nowMs(),
        connectionEvents: [
          ...value.connectionEvents,
          { event_type: 'offline', timestamp: nowIso() },
        ],
      }))
    }

    const handleOnline = () => {
      commitSession((value) => {
        const offlineDuration =
          value.offlineStartedAtMs === null ? 0 : Math.max(0, nowMs() - value.offlineStartedAtMs)

        return {
          ...value,
          offlineStartedAtMs: null,
          offlineTotalMs: value.offlineTotalMs + offlineDuration,
          connectionEvents: [
            ...value.connectionEvents,
            { event_type: 'online', timestamp: nowIso() },
          ],
        }
      })
    }

    window.addEventListener('offline', handleOffline)
    window.addEventListener('online', handleOnline)

    return () => {
      window.removeEventListener('offline', handleOffline)
      window.removeEventListener('online', handleOnline)
    }
  }, [])

  const recordTouch = () =>
    commitSession((value) => {
      if (!currentItem) {
        return value
      }

      const itemLog = value.itemLogs[currentItem.item_id]

      if (!itemLog) {
        return {
          ...value,
          totalTouchCount: value.totalTouchCount + 1,
        }
      }

      return {
        ...value,
        totalTouchCount: value.totalTouchCount + 1,
        itemLogs: {
          ...value.itemLogs,
          [currentItem.item_id]: {
            ...itemLog,
            touch_count: itemLog.touch_count + 1,
          },
        },
      }
    })

  const handleSelect = (optionOrder: number) => {
    if (!currentItem) {
      return
    }

    const selectedAt = nowIso()
    const selectedAtMs = nowMs()

    commitSession((value) => {
      const itemLog = value.itemLogs[currentItem.item_id]
      if (!itemLog) {
        return value
      }

      const previousAnswer = value.answers[currentItem.item_id]
      const changed = previousAnswer !== undefined && previousAnswer !== optionOrder
      const firstOption = itemLog.first_selected_option_order ?? optionOrder
      const finalOption = optionOrder

      return {
        ...value,
        totalTouchCount: value.totalTouchCount + 1,
        answers: {
          ...value.answers,
          [currentItem.item_id]: optionOrder,
        },
        itemLogs: {
          ...value.itemLogs,
          [currentItem.item_id]: {
            ...itemLog,
            first_selected_at: itemLog.first_selected_at ?? selectedAt,
            first_selected_at_ms: itemLog.first_selected_at_ms ?? selectedAtMs,
            last_selected_at: selectedAt,
            last_selected_at_ms: selectedAtMs,
            first_selected_option_order: firstOption,
            final_selected_option_order: finalOption,
            answer_changed: firstOption !== finalOption,
            changed_after_revisit:
              itemLog.changed_after_revisit || (itemLog.is_revisited && changed),
            change_count: changed ? itemLog.change_count + 1 : itemLog.change_count,
            touch_count: itemLog.touch_count + 1,
          },
        },
      }
    })
  }

  const moveTo = (nextIndex: number, viaBack: boolean) => {
    if (!currentItem || !sessionRef.current) {
      return
    }

    const left = leaveItem(currentItem, sessionRef.current)
    sessionRef.current = left
    setSession(left)
    setCurrentIndex(nextIndex)
    window.setTimeout(() => {
      const nextItem = items[nextIndex]
      if (nextItem) {
        enterItem(nextItem, viaBack)
      }
    }, 0)
  }

  const handleNext = () => {
    recordTouch()

    if (currentIndex < items.length - 1) {
      moveTo(currentIndex + 1, false)
    }
  }

  const handlePrevious = () => {
    recordTouch()

    if (currentIndex > 0) {
      moveTo(currentIndex - 1, true)
    }
  }

  const handleSubmit = () => {
    if (isPublicMode && !publicDeviceId) {
      pushToast({
        type: 'error',
        title: '기기 식별 정보를 확인하지 못했습니다',
        description: '페이지를 새로고침한 뒤 다시 시도해 주세요.',
      })
      return
    }

    if (isPublicBlocked) {
      pushToast({
        type: 'error',
        title: '이미 응답한 기기입니다',
        description: '같은 기기에서는 한 번만 응답할 수 있습니다.',
      })
      return
    }

    const touched = recordTouch()
    const baseSession = touched ?? sessionRef.current

    if (!baseSession || !currentItem) {
      return
    }

    const completed = leaveItem(currentItem, baseSession)
    const submittedAt = nowIso()
    const submittedAtMs = nowMs()
    const offlineDuration =
      completed.offlineStartedAtMs === null
        ? 0
        : Math.max(0, submittedAtMs - completed.offlineStartedAtMs)
    const totalTimeMs = Math.max(0, submittedAtMs - completed.startedAtMs)
    const finalSession = {
      ...completed,
      offlineStartedAtMs: null,
      offlineTotalMs: completed.offlineTotalMs + offlineDuration,
    }

    sessionRef.current = finalSession
    setSession(finalSession)

    const itemLogs = items.map((item) =>
      toSubmitItemLog(
        finalSession.itemLogs[item.item_id] ??
          createEmptyItemLog(item.item_id, finalSession.startedAt, finalSession.startedAtMs),
        totalTimeMs,
      ),
    )

    const payload: SurveyResponseSubmitPayload = {
      respondent_id: finalSession.respondentId,
      started_at: finalSession.startedAt,
      submitted_at: submittedAt,
      is_completed: true,
      label: null,
      answers: items
        .filter((item) => finalSession.answers[item.item_id] !== undefined)
        .map((item) => {
          const selectedOptionOrder = finalSession.answers[item.item_id]
          const selectedOption = item.options.find(
            (option) => option.option_order === selectedOptionOrder,
          )
          const itemLog = finalSession.itemLogs[item.item_id]

          return {
            item_id: item.item_id,
            selected_option_id: selectedOption?.option_id ?? null,
            selected_option_order: selectedOptionOrder,
            selected_score: selectedOptionOrder,
            answer_text: null,
            answered_at: itemLog?.last_selected_at ?? submittedAt,
          }
        }),
      log: {
        started_at: finalSession.startedAt,
        submitted_at: submittedAt,
        total_time_ms: totalTimeMs,
        total_touch_count: finalSession.totalTouchCount,
        connection_lost: finalSession.connectionLost,
        offline_count: finalSession.offlineCount,
        offline_total_ms: finalSession.offlineTotalMs,
        item_logs: itemLogs,
        connection_events: finalSession.connectionEvents,
      },
    }

    submitMutation.mutate(payload)
  }

  if (surveyQuery.isLoading) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <LoadingSpinner label="설문을 불러오는 중" />
      </section>
    )
  }

  if (isPublicMode && publicAvailabilityQuery.isLoading) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <LoadingSpinner label="응답 가능 여부를 확인하는 중" />
      </section>
    )
  }

  if (isPublicMode && publicAvailabilityQuery.isError) {
    return (
      <section className="rounded-lg border border-rose-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-1 text-rose-600" size={20} />
          <div>
            <h1 className="text-lg font-black text-slate-950">응답 상태 확인에 실패했습니다</h1>
            <p className="mt-1 text-sm text-slate-600">
              네트워크 상태를 확인한 뒤 다시 시도해 주세요.
            </p>
          </div>
        </div>
      </section>
    )
  }

  if (isPublicBlocked) {
    return (
      <section className="rounded-lg border border-amber-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-1 text-amber-600" size={20} />
          <div>
            <h1 className="text-lg font-black text-slate-950">이미 제출된 설문입니다</h1>
            <p className="mt-1 text-sm text-slate-600">
              이 링크는 한 기기에서 한 번만 응답할 수 있습니다. 같은 기기에서는 재응답이 제한됩니다.
            </p>
          </div>
        </div>
      </section>
    )
  }

  if (surveyQuery.isError || !survey || items.length === 0) {
    return (
      <section className="rounded-lg border border-rose-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-1 text-rose-600" size={20} />
          <div>
            <h1 className="text-lg font-black text-slate-950">설문을 불러올 수 없습니다</h1>
            <p className="mt-1 text-sm text-slate-600">
              링크 또는 설문 ID가 올바른지, 백엔드 서버가 실행 중인지 확인해 주세요.
            </p>
          </div>
        </div>
      </section>
    )
  }

  const selectedOptionOrder = currentItem ? session?.answers[currentItem.item_id] : undefined
  const isLast = currentIndex === items.length - 1
  const canContinue = selectedOptionOrder !== undefined

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm font-bold text-teal-700">{survey.title}</p>
        <h1 className="mt-1 text-2xl font-black text-slate-950">설문 응답</h1>
        {survey.description ? (
          <p className="mt-2 text-sm leading-6 text-slate-600">{survey.description}</p>
        ) : null}
        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between text-sm font-bold text-slate-600">
            <span>
              {currentIndex + 1} / {items.length}
            </span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-teal-600 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <p className="text-sm font-black text-slate-500">Q{currentIndex + 1}</p>
          {(() => {
            const roleBadge = getRoleBadge(currentItem)

            if (!roleBadge) {
              return null
            }

            return (
              <span className={`rounded-md px-2 py-1 text-xs font-bold ${roleBadge.className}`}>
                {roleBadge.label}
              </span>
            )
          })()}
        </div>
        <h2 className="mt-2 text-xl font-black leading-8 text-slate-950">
          {currentItem.question_text}
        </h2>

        <div className="mt-6 space-y-2">
          {getDisplayOptions(currentItem).map((option) => (
            <label
              key={option.option_id}
              className="flex cursor-pointer items-center gap-3 rounded-lg border border-slate-200 p-4 text-sm font-bold text-slate-800 hover:border-teal-300 hover:bg-teal-50"
            >
              <input
                type="radio"
                name={currentItem.item_id}
                className="h-4 w-4 text-teal-600"
                checked={selectedOptionOrder === option.option_order}
                onChange={() => handleSelect(option.option_order)}
              />
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-100 text-xs">
                {option.option_order}
              </span>
              <span>{option.option_label}</span>
            </label>
          ))}
        </div>

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
            disabled={currentIndex === 0 || submitMutation.isPending}
            onClick={handlePrevious}
          >
            <ArrowLeft size={16} />
            이전
          </button>

          {isLast ? (
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-teal-600 px-5 py-2 text-sm font-bold text-white hover:bg-teal-700 disabled:bg-slate-300"
              disabled={!canContinue || submitMutation.isPending}
              onClick={handleSubmit}
            >
              {submitMutation.isPending ? (
                <LoadingSpinner compact label="제출 중" />
              ) : (
                <>
                  <CheckCircle2 size={17} />
                  제출하기
                </>
              )}
            </button>
          ) : (
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-900 px-5 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:bg-slate-300"
              disabled={!canContinue || submitMutation.isPending}
              onClick={handleNext}
            >
              다음
              <ArrowRight size={16} />
            </button>
          )}
        </div>
      </section>
    </div>
  )
}
