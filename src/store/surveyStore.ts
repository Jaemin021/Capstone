import { create } from 'zustand'
import type {
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

const initialItems: SurveyItem[] = [
  {
    id: createId(),
    text: '이 서비스는 필요한 기능을 쉽게 찾을 수 있게 구성되어 있다.',
    type: 'likert-5',
  },
  {
    id: createId(),
    text: '서비스 이용 과정에서 제공되는 설명은 이해하기 쉽다.',
    type: 'likert-5',
  },
]

interface SurveyStore {
  items: SurveyItem[]
  selectedItemId: string | null
  settings: SurveySettings
  addItem: () => void
  insertGeneratedItem: (text: string, position: number, flags?: Partial<SurveyItem>) => void
  selectItem: (id: string) => void
  updateItem: (id: string, updates: Partial<Pick<SurveyItem, 'text' | 'type'>>) => void
  removeItem: (id: string) => void
  reorderItems: (activeId: string, overId: string) => void
  replaceItemText: (id: string, text: string) => void
  setItemQuality: (id: string, quality: ItemQualityResult) => void
  setCitcResults: (results: CitcResult[]) => void
  toggleReverse: (id: string, checked: boolean) => void
  setSettings: (settings: Partial<SurveySettings>) => void
}

export const useSurveyStore = create<SurveyStore>((set, get) => ({
  items: initialItems,
  selectedItemId: initialItems[0]?.id ?? null,
  settings: {
    title: '응답 신뢰도 분석 설문',
    surveyContext: '디지털 서비스 사용성 만족도 조사',
    trapEnabled: true,
    reverseEnabled: true,
  },
  addItem: () => {
    const item: SurveyItem = {
      id: createId(),
      text: '',
      type: 'likert-5',
    }

    set((state) => ({
      items: [...state.items, item],
      selectedItemId: item.id,
    }))
  },
  insertGeneratedItem: (text, position, flags) => {
    const item: SurveyItem = {
      id: createId(),
      text,
      type: (flags?.type as QuestionType | undefined) ?? 'likert-5',
      isTrap: flags?.isTrap,
      isReverse: flags?.isReverse,
    }

    set((state) => {
      const nextItems = [...state.items]
      const safePosition = Math.max(0, Math.min(position, nextItems.length))
      nextItems.splice(safePosition, 0, item)

      return {
        items: nextItems,
        selectedItemId: item.id,
      }
    })
  },
  selectItem: (id) => set({ selectedItemId: id }),
  updateItem: (id, updates) =>
    set((state) => ({
      items: state.items.map((item) =>
        item.id === id ? { ...item, ...updates, quality: undefined, citc: undefined } : item,
      ),
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
  toggleReverse: (id, checked) =>
    set((state) => ({
      items: state.items.map((item) =>
        item.id === id ? { ...item, isReverse: checked } : item,
      ),
    })),
  setSettings: (settings) =>
    set((state) => ({
      settings: {
        ...state.settings,
        ...settings,
      },
    })),
}))
