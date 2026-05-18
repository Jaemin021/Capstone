import { create } from 'zustand'

export type ToastType = 'success' | 'error' | 'info'

export interface ToastMessage {
  id: string
  type: ToastType
  title: string
  description?: string
}

interface ToastStore {
  messages: ToastMessage[]
  pushToast: (message: Omit<ToastMessage, 'id'>) => void
  removeToast: (id: string) => void
}

const createToastId = () => `toast-${Date.now()}-${Math.random().toString(16).slice(2)}`

export const useToastStore = create<ToastStore>((set, get) => ({
  messages: [],
  pushToast: (message) => {
    const id = createToastId()

    set((state) => ({
      messages: [...state.messages, { ...message, id }],
    }))

    window.setTimeout(() => {
      get().removeToast(id)
    }, 3600)
  },
  removeToast: (id) =>
    set((state) => ({
      messages: state.messages.filter((message) => message.id !== id),
    })),
}))
