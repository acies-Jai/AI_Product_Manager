import { useRef, useEffect, useState, KeyboardEvent } from 'react'
import { Send, Loader2, MessageSquare, Search, Mail } from 'lucide-react'
import { useStore } from '../store'
import { ROLE_CONFIG } from '../types'
import TaoStepper from './TaoStepper'
import PendingWriteCard from './PendingWriteCard'

function MessageBubble({ msg }: { msg: { id: string; role: string; content: string; roleLabel?: string; toolEvents?: any[] } }) {
  const isUser = msg.role === 'user'
  const cfg = ROLE_CONFIG[msg.roleLabel ?? ''] ?? { color: '#9CA3AF', icon: '👥' }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-[88%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        {isUser && msg.roleLabel && (
          <div className="flex justify-end">
            <span
              className="role-badge text-[10px]"
              style={{ background: `${cfg.color}18`, color: cfg.color, borderColor: `${cfg.color}40` }}
            >
              {cfg.icon} {msg.roleLabel}
            </span>
          </div>
        )}
        <div
          className={`rounded-2xl px-3.5 py-2.5 text-xs ${
            isUser
              ? 'bg-zepto-purple text-white rounded-tr-sm'
              : 'bg-white border border-zepto-muted text-zepto-dark rounded-tl-sm'
          }`}
        >
          <div className="msg-content whitespace-pre-wrap leading-relaxed">{msg.content}</div>
        </div>
        {!isUser && msg.toolEvents && msg.toolEvents.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-0.5 px-1">
            {msg.toolEvents.filter(e => e.type === 'search').length > 0 && (
              <span className="inline-flex items-center gap-1 text-[10px] bg-blue-50 text-blue-500 border border-blue-100 rounded-full px-2 py-0.5">
                <Search size={9} /> {msg.toolEvents.filter(e => e.type === 'search').length} search(es)
              </span>
            )}
            {msg.toolEvents.filter(e => e.type === 'email').map((e: any, i: number) => (
              <span key={i} className="inline-flex items-center gap-1 text-[10px] bg-emerald-50 text-emerald-600 border border-emerald-100 rounded-full px-2 py-0.5">
                <Mail size={9} /> Email sent
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function ChatPanel() {
  const { messages, isThinking, taoSteps, pendingWrite, sendMessage, chunksIndexed } = useStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function autoResize(el: HTMLTextAreaElement) {
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, taoSteps, isThinking])

  function handleSend() {
    const text = input.trim()
    if (!text || isThinking || chunksIndexed === 0) return
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    sendMessage(text)
  }

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="w-80 flex-shrink-0 h-full border-l border-zepto-muted bg-white flex flex-col">
      {/* Header */}
      <div className="px-4 py-3.5 border-b border-zepto-muted flex items-center gap-2.5 shrink-0 bg-white">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-zepto-purple to-zepto-pale flex items-center justify-center shrink-0">
          <MessageSquare size={13} className="text-white" />
        </div>
        <div>
          <p className="text-xs font-bold text-zepto-dark leading-none">Live Intelligence Feed</p>
          <div className="flex items-center gap-1 mt-0.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <p className="text-[10px] text-gray-400">Ask anything, instant insight</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center gap-3 text-center px-4">
            <div className="w-10 h-10 rounded-2xl bg-zepto-tint flex items-center justify-center">
              <MessageSquare size={18} className="text-zepto-purple" />
            </div>
            <div>
              <p className="text-xs font-semibold text-zepto-dark">Start a conversation</p>
              <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">
                Ask about roadmaps, metrics, requirements, or anything in your docs.
              </p>
            </div>
            <div className="flex flex-col gap-1.5 w-full">
              {[
                'What are the top priorities?',
                'Summarise the roadmap',
                'What metrics should I track?',
              ].map(s => (
                <button
                  key={s}
                  onClick={() => { if (chunksIndexed > 0) { sendMessage(s) } }}
                  disabled={chunksIndexed === 0}
                  className="text-[11px] text-zepto-purple bg-zepto-tint border border-zepto-muted rounded-xl
                             px-3 py-2 text-left hover:bg-purple-100 transition-colors disabled:opacity-40"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map(msg => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        {isThinking && taoSteps.length > 0 && (
          <div className="flex justify-start mb-3">
            <div className="w-full">
              <TaoStepper steps={taoSteps} />
            </div>
          </div>
        )}
        {isThinking && taoSteps.length === 0 && (
          <div className="flex items-center gap-2 text-[11px] text-gray-400 mb-3 px-1">
            <Loader2 size={11} className="animate-spin text-zepto-purple" />
            On it…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Pending write card */}
      {pendingWrite && <PendingWriteCard />}

      {/* Input */}
      <div className="px-3 py-3 border-t border-zepto-muted shrink-0">
        {chunksIndexed === 0 && (
          <p className="text-[11px] text-amber-500 mb-2 text-center">Index documents first</p>
        )}
        <div className="flex items-end gap-2 bg-zepto-bg rounded-xl border border-zepto-muted px-3 py-2
                        focus-within:border-zepto-purple/50 focus-within:ring-2 focus-within:ring-zepto-purple/10 transition-all">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => { setInput(e.target.value); autoResize(e.target) }}
            onKeyDown={handleKey}
            placeholder={chunksIndexed > 0 ? 'Ask anything… (Shift+Enter for newline)' : 'Index first…'}
            disabled={isThinking || chunksIndexed === 0}
            rows={1}
            className="flex-1 bg-transparent text-xs text-zepto-dark placeholder-gray-400 outline-none resize-none disabled:opacity-50 leading-relaxed"
            style={{ minHeight: '20px', maxHeight: '140px' }}
          />
          <button
            onClick={handleSend}
            disabled={isThinking || !input.trim() || chunksIndexed === 0}
            className="btn-primary px-2.5 py-1.5 rounded-lg shrink-0"
          >
            {isThinking ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
          </button>
        </div>
      </div>
    </div>
  )
}
