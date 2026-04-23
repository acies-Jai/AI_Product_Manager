import { create } from 'zustand'
import type { Message, TaoStep, PendingWrite, Artifacts } from './types'
import * as api from './api'

const TOOL_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  search:       { icon: '🔍', color: '#0EA5E9', label: 'Dispatching query' },
  email:        { icon: '📧', color: '#10B981', label: 'Delivering message' },
  inbox:        { icon: '📬', color: '#F59E0B', label: 'Checking inbox' },
  write_staged: { icon: '✏️', color: '#8B5CF6', label: 'Staging change' },
}

interface AppStore {
  chunksIndexed: number
  files: string[]
  artifacts: Artifacts
  staleArtifacts: boolean
  role: string
  activeTab: string
  isIndexing: boolean
  isGenerating: boolean
  messages: Message[]
  isThinking: boolean
  taoSteps: TaoStep[]
  pendingWrite: PendingWrite | null
  threadId: string

  loadInitial: () => Promise<void>
  indexDocuments: () => Promise<void>
  generateArtifacts: () => Promise<void>
  sendMessage: (message: string) => Promise<void>
  confirmWrite: (confirmed: boolean) => Promise<void>
  setRole: (role: string) => void
  setActiveTab: (tab: string) => void
}

export const useStore = create<AppStore>((set, get) => ({
  chunksIndexed: 0,
  files: [],
  artifacts: {},
  staleArtifacts: false,
  role: 'Product Manager',
  activeTab: 'roadmap',
  isIndexing: false,
  isGenerating: false,
  messages: [],
  isThinking: false,
  taoSteps: [],
  pendingWrite: null,
  threadId: crypto.randomUUID(),

  loadInitial: async () => {
    try {
      const [filesData, artifactsData] = await Promise.all([
        api.fetchFiles(),
        api.fetchArtifacts(),
      ])
      set({ chunksIndexed: filesData.chunks, files: filesData.files, artifacts: artifactsData })
    } catch (e) {
      console.error('loadInitial failed', e)
    }
  },

  indexDocuments: async () => {
    set({ isIndexing: true })
    try {
      const res = await api.indexDocuments()
      set({ chunksIndexed: res.chunks, files: res.files, isIndexing: false })
    } catch (e) {
      set({ isIndexing: false })
      throw e
    }
  },

  generateArtifacts: async () => {
    set({ isGenerating: true })
    try {
      await api.generateArtifacts()
      const artifacts = await api.fetchArtifacts()
      set({ artifacts, staleArtifacts: false, isGenerating: false, activeTab: 'roadmap' })
    } catch (e) {
      set({ isGenerating: false })
      throw e
    }
  },

  sendMessage: async (message: string) => {
    const { role, threadId } = get()

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      roleLabel: role,
    }
    set(s => ({ messages: [...s.messages, userMsg], isThinking: true, taoSteps: [] }))

    const steps: TaoStep[] = []
    let reply = ''
    let pendingWrite: PendingWrite | null = null
    let toolEvents: any[] = []

    try {
      for await (const event of api.streamChat(message, role, threadId)) {
        if (event.node === '__done__') break
        const updates = event.updates ?? {}

        if (event.node === 'classify_intent') {
          steps.push({
            id: crypto.randomUUID(),
            node: 'classify_intent',
            label: 'Order received',
            detail: `intent: ${updates.intent ?? 'general_chat'}`,
            color: '#0EA5E9',
            icon: '🧾',
          })
          set({ taoSteps: [...steps] })
        }

        if (event.node === 'retrieve_context') {
          const ctx: any[] = updates.retrieved_context ?? []
          const sources = [...new Set(ctx.map((r: any) => r.file as string))]
          steps.push({
            id: crypto.randomUUID(),
            node: 'retrieve_context',
            label: 'Packing context',
            detail: ctx.length > 0 ? `${ctx.length} chunks from ${sources.join(', ')}` : 'skipped — direct response',
            color: '#8B5CF6',
            icon: '📦',
          })
          set({ taoSteps: [...steps] })
        }

        if (event.node === 'generate_response') {
          toolEvents = updates.tool_events ?? []
          reply = updates.reply ?? ''
          pendingWrite = updates.pending_write ?? null

          for (const e of toolEvents) {
            const cfg = TOOL_CONFIG[e.type] ?? { icon: '⚡', color: '#5E17EB', label: e.type }
            steps.push({
              id: crypto.randomUUID(),
              node: 'tool',
              label: cfg.label,
              detail: (e.detail ?? '').slice(0, 70),
              color: cfg.color,
              icon: cfg.icon,
            })
          }
          if (toolEvents.length === 0) {
            steps.push({
              id: crypto.randomUUID(),
              node: 'direct',
              label: 'Express delivery',
              detail: 'no tools needed — direct from knowledge',
              color: '#5E17EB',
              icon: '🚀',
            })
          }
          set({ taoSteps: [...steps] })
        }
      }

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: reply,
        toolEvents,
      }
      set(s => ({
        messages: [...s.messages, assistantMsg],
        isThinking: false,
        taoSteps: [],
        pendingWrite,
      }))
    } catch (e) {
      set({ isThinking: false, taoSteps: [] })
      console.error('sendMessage error', e)
    }
  },

  confirmWrite: async (confirmed: boolean) => {
    const { threadId } = get()
    try {
      const result = await api.confirmWrite(threadId, confirmed)
      const msg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: result.reply,
      }
      set(s => ({
        messages: [...s.messages, msg],
        pendingWrite: null,
        staleArtifacts: confirmed,
      }))
    } catch (e) {
      console.error('confirmWrite error', e)
    }
  },

  setRole: (role) => set({ role }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}))
