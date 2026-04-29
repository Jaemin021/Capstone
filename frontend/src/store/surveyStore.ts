import { create } from 'zustand'
import type {
  BackendSurveyResponse,
  CitcResult,
  ItemQualityResult,
  QuestionType,
  SurveyItem,
  SurveySettings,
} from '../types/survey'

const createId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `item-${Date.now()}-${Math.random().toString(16).slice(2)}`

const defaultOptions = [
  '전혀 그렇지 않다',
  '그렇지 않다',
  '보통이다',
  '그렇다',
  '매우 그렇다',
]

const normalizeOptions = (options?: string[]) => {
  const next = (options ?? []).slice(0, 5)

  while (next.length < 5) {
    next.push(`보기 ${next.length + 1}`)
  }

  return next
}

const initialItems: SurveyItem[] = [
  {
    id: createId(),
    text: '이 서비스는 필요한 기능을 쉽게 찾을 수 있게 구성되어 있다.',
    type: 'likert-5',
    options: [...defaultOptions],
  },
  {
    id: createId(),
    text: '서비스 이용 과정에서 제공되는 설명은 이해하기 쉽다.',
    type: 'likert-5',
    options: [...defaultOptions],
  },
]

const createInitialItems = (): SurveyItem[] =>
  initialItems.map((item) => ({
    ...item,
    id: createId(),
    options: [...item.options],
    quality: undefined,
    citc: undefined,
  }))

const initialSettings: SurveySettings = {
  title: '',
  surveyContext: '',
}

function fromBackendQuestionType(questionType: string): QuestionType {
  if (questionType === 'likert_5') {
    return 'likert-5'
  }

  return 'likert-5'
}

interface SurveyStore {
  items: SurveyItem[]
  selectedItemId: string | null
  settings: SurveySettings
  draftResetAt: number
  resetDraft: () => void
  addItem: () => void
  selectItem: (id: string) => void
  updateItem: (id: string, updates: Partial<Pick<SurveyItem, 'text' | 'type'>>) => void
  updateItemOption: (id: string, optionIndex: number, value: string) => void
  removeItem: (id: string) => void
  reorderItems: (activeId: string, overId: string) => void
  replaceItemText: (id: string, text: string) => void
  setItemQuality: (id: string, quality: ItemQualityResult) => void
  setCitcResults: (results: CitcResult[]) => void
  setSettings: (settings: Partial<SurveySettings>) => void
  setItemsFromBackendSurvey: (
    survey: BackendSurveyResponse,
    options?: { normalItemsOnly?: boolean },
  ) => void
}

const seededItems = createInitialItems()

export const useSurveyStore = create<SurveyStore>((set, get) => ({
  items: seededItems,
  selectedItemId: seededItems[0]?.id ?? null,
  draftResetAt: 0,
  settings: {
    title: '응답 신뢰도 분석 설문',
    surveyContext: '디지털 서비스 사용성 만족도 조사',
  },
  resetDraft: () =>
    set(() => {
      const items = createInitialItems()

      return {
        items,
        selectedItemId: items[0]?.id ?? null,
        draftResetAt: Date.now(),
        settings: { ...initialSettings },
      }
    }),
  addItem: () => {
    const item: SurveyItem = {
      id: createId(),
      text: '',
      type: 'likert-5',
      options: [...defaultOptions],
    }

    set((state) => ({
      items: [...state.items, item],
      selectedItemId: item.id,
    }))
  },
  selectItem: (id) => set({ selectedItemId: id }),
  updateItem: (id, updates) =>
    set((state) => ({
      items: state.items.map((item) =>
        item.id === id ? { ...item, ...updates, quality: undefined, citc: undefined } : item,
      ),
    })),
  updateItemOption: (id, optionIndex, value) =>
    set((state) => ({
      items: state.items.map((item) => {
        if (item.id !== id) {
          return item
        }

        const nextOptions = [...item.options]
        nextOptions[optionIndex] = value

        return {
          ...item,
          options: normalizeOptions(nextOptions),
          quality: undefined,
          citc: undefined,
        }
      }),
    })),
  removeItem: (id) =>
    set((state) => {
      const nextItems = state.items.filter((item) => item.id !== id)
      const nextSelectedId =
        state.selectedItemId === id ? nextItems[0]?.id ?? null : state.selectedItemId

      return {
        items: nextItems,
        selectedItemId: nextSelectedId,
      }
    }),
  reorderItems: (activeId, overId) => {
    const { items } = get()
    const oldIndex = items.findIndex((item) => item.id === activeId)
    const newIndex = items.findIndex((item) => item.id === overId)

    if (oldIndex < 0 || newIndex < 0 || oldIndex === newIndex) {
      return
    }

    const nextItems = [...items]
    const [moved] = nextItems.splice(oldIndex, 1)
    nextItems.splice(newIndex, 0, moved)
    set({ items: nextItems })
  },
  replaceItemText: (id, text) =>
    set((state) => ({
      items: state.items.map((item) =>
        item.id === id ? { ...item, text, quality: undefined, citc: undefined } : item,
      ),
    })),
  setItemQuality: (id, quality) =>
    set((state) => ({
      items: state.items.map((item) => (item.id === id ? { ...item, quality } : item)),
    })),
  setCitcResults: (results) =>
    set((state) => ({
      items: state.items.map((item) => ({
        ...item,
        citc: results.find((result) => result.id === item.id),
      })),
    })),
  setSettings: (settings) =>
    set((state) => ({
      settings: {
        ...state.settings,
        ...settings,
      },
    })),
  setItemsFromBackendSurvey: (survey, options) =>
    set(() => {
      const sourceItems = options?.normalItemsOnly
        ? survey.items.filter((item) => item.item_role === 'normal')
        : survey.items

      const items = sourceItems.map((item) => ({
        id: item.item_id,
        backendItemId: item.item_id,
        text: item.question_text,
        type: fromBackendQuestionType(item.question_type),
        options: normalizeOptions(item.options.map((option) => option.option_label)),
        backendOptions: item.options,
        isTrap: item.item_role === 'trap',
        isReverse: item.item_role === 'reverse',
      }))

      return {
        items,
        selectedItemId: items[0]?.id ?? null,
        settings: {
          title: survey.title,
          surveyContext: survey.description ?? survey.construct_description ?? '',
        },
      }
    }),
}))
