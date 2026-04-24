import { useState, useEffect } from 'react'
import { RefreshCw, Search, Zap, Mail, Loader2, ChevronDown, ChevronRight, FileText, Send, X } from 'lucide-react'
import { useStore } from '../store'
import { ARTIFACT_KEYS } from '../types'
import * as api from '../api'
import type { Department } from '../api'

export default function Sidebar() {
  const {
    files, chunksIndexed, artifacts,
    isIndexing, isGenerating, isNotifying,
    loadInitial, indexDocuments, generateArtifacts, notifyTeam,
  } = useStore()

  const [filesOpen, setFilesOpen]       = useState(false)
  const [notifyOpen, setNotifyOpen]     = useState(false)
  const [departments, setDepartments]   = useState<Department[]>([])
  const [allRecipients, setAllRecipients] = useState<string[]>([])
  const [selected, setSelected]         = useState<Set<string>>(new Set())
  const [loadingTeam, setLoadingTeam]   = useState(false)

  const isIndexed     = chunksIndexed > 0
  const artifactCount = ARTIFACT_KEYS.filter(k => artifacts[k]).length

  // Fetch team whenever the notify panel opens
  useEffect(() => {
    if (!notifyOpen || departments.length) return
    setLoadingTeam(true)
    api.fetchTeam()
      .then(data => {
        setDepartments(data.departments)
        setAllRecipients(data.all_recipients)
        // Default: all selected
        setSelected(new Set(data.all_recipients))
      })
      .catch(console.error)
      .finally(() => setLoadingTeam(false))
  }, [notifyOpen])

  function toggleDept(emails: string[]) {
    setSelected(prev => {
      const next = new Set(prev)
      const allIn = emails.every(e => next.has(e))
      emails.forEach(e => allIn ? next.delete(e) : next.add(e))
      return next
    })
  }

  function toggleAll() {
    setSelected(prev =>
      prev.size === allRecipients.length ? new Set() : new Set(allRecipients)
    )
  }

  async function handleSend() {
    const recipients = [...selected]
    await notifyTeam(recipients.length === allRecipients.length ? [] : recipients)
    setNotifyOpen(false)
  }

  return (
    <aside className="w-60 flex-shrink-0 h-full bg-zepto-dark flex flex-col overflow-y-auto">
      {/* Brand */}
      <div className="px-5 pt-6 pb-5 border-b border-white/10">
        <div className="text-xl font-extrabold text-white tracking-tight">⚡ Zepto</div>
        <div className="text-[10px] text-purple-300/70 uppercase tracking-[2px] mt-0.5 font-semibold">
          PM Intelligence Layer
        </div>
      </div>

      <div className="flex-1 px-3 py-4 space-y-2 overflow-y-auto">

        {/* ── Status summary ── */}
        <div className="rounded-xl bg-white/5 border border-white/10 px-3 py-3 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-purple-300/60">Sources indexed</span>
            <span className={`font-bold ${isIndexed ? 'text-emerald-400' : 'text-gray-500'}`}>
              {isIndexed ? chunksIndexed : '—'}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-purple-300/60">Artifacts ready</span>
            <span className={`font-bold ${artifactCount === 6 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {artifactCount}/6
            </span>
          </div>
          <div className="w-full bg-white/10 rounded-full h-1 mt-1">
            <div
              className="h-1 rounded-full bg-gradient-to-r from-zepto-purple to-zepto-pale transition-all duration-500"
              style={{ width: `${(artifactCount / 6) * 100}%` }}
            />
          </div>
        </div>

        {/* ── Collapsible context files ── */}
        <button
          onClick={() => setFilesOpen(o => !o)}
          className="w-full flex items-center justify-between px-2 py-2 rounded-lg text-xs text-purple-200/70 hover:bg-white/5 transition-colors"
        >
          <div className="flex items-center gap-2">
            <FileText size={12} />
            <span className="font-semibold uppercase tracking-[1.5px] text-[10px]">Context Files</span>
            <span className="bg-white/10 text-purple-300 text-[9px] font-bold rounded-full px-1.5 py-0.5">
              {files.length}
            </span>
          </div>
          {filesOpen
            ? <ChevronDown size={12} className="text-purple-300/50" />
            : <ChevronRight size={12} className="text-purple-300/50" />
          }
        </button>

        {filesOpen && (
          <div className="rounded-xl bg-white/5 border border-white/10 px-2 py-2 space-y-1">
            {files.length === 0 && (
              <p className="px-2 text-xs text-purple-300/40 py-1">No files in inputs/</p>
            )}
            {files.map(name => (
              <div key={name} className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-purple-100/70">
                <span style={{ color: isIndexed ? '#10B981' : '#6B7280' }} className="text-[10px] font-bold">
                  {isIndexed ? '✓' : '○'}
                </span>
                <span className="truncate">{name}.md</span>
              </div>
            ))}
            <button
              onClick={() => loadInitial()}
              className="w-full flex items-center justify-center gap-1.5 text-[11px] text-purple-300/50 hover:text-purple-200 transition-colors py-1 rounded-lg hover:bg-white/5"
            >
              <RefreshCw size={10} /> Reload files
            </button>
          </div>
        )}

        <div className="h-px bg-white/10" />

        {/* ── Action buttons ── */}
        <button
          className="btn-ghost w-full flex items-center justify-center gap-2 text-xs"
          onClick={indexDocuments}
          disabled={isIndexing}
        >
          {isIndexing ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
          {isIndexing ? 'Indexing…' : 'Index Documents'}
        </button>

        <button
          className="btn-primary w-full flex items-center justify-center gap-2 text-xs"
          onClick={generateArtifacts}
          disabled={isGenerating || !isIndexed}
        >
          {isGenerating ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
          {isGenerating ? 'Generating…' : 'Generate Artifacts'}
        </button>

        {/* ── Notify Team section ── */}
        {artifactCount > 0 && (
          <>
            <div className="h-px bg-white/10" />

            <button
              className="btn-ghost w-full flex items-center justify-center gap-2 text-xs"
              onClick={() => setNotifyOpen(o => !o)}
              disabled={isNotifying}
            >
              <Mail size={12} />
              {isNotifying ? 'Sending…' : 'Notify Team'}
              {notifyOpen
                ? <X size={10} className="ml-auto opacity-50" />
                : <ChevronDown size={10} className="ml-auto opacity-50" />
              }
            </button>

            {notifyOpen && (
              <div className="rounded-xl bg-white/5 border border-white/10 overflow-hidden">
                {/* Panel header */}
                <div className="px-3 py-2 border-b border-white/10 flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-purple-300/60">
                    Select recipients
                  </span>
                  <button
                    onClick={toggleAll}
                    className="text-[10px] text-purple-300/50 hover:text-purple-200 transition-colors"
                  >
                    {selected.size === allRecipients.length ? 'Deselect all' : 'Select all'}
                  </button>
                </div>

                {/* Department list */}
                <div className="px-2 py-2 space-y-1">
                  {loadingTeam ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 size={14} className="animate-spin text-purple-300/50" />
                    </div>
                  ) : departments.map(dept => {
                    const emails = dept.emails
                    const allIn = emails.every(e => selected.has(e))
                    const someIn = emails.some(e => selected.has(e))
                    return (
                      <button
                        key={dept.key}
                        onClick={() => toggleDept(emails)}
                        className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-white/5 transition-colors text-left"
                      >
                        <div
                          className="w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors"
                          style={{
                            background: allIn ? '#5E17EB' : someIn ? '#5E17EB40' : 'transparent',
                            borderColor: allIn || someIn ? '#5E17EB' : 'rgba(255,255,255,0.2)',
                          }}
                        >
                          {(allIn || someIn) && (
                            <svg width="8" height="6" viewBox="0 0 8 6" fill="none">
                              <path d="M1 3L3 5L7 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs text-purple-100/80 font-medium truncate">{dept.label}</p>
                          <p className="text-[10px] text-purple-300/40 truncate">{emails[0]}</p>
                        </div>
                      </button>
                    )
                  })}
                </div>

                {/* Send button */}
                <div className="px-3 py-2.5 border-t border-white/10">
                  <button
                    onClick={handleSend}
                    disabled={selected.size === 0 || isNotifying}
                    className="w-full flex items-center justify-center gap-2 text-xs font-semibold
                               bg-gradient-to-r from-zepto-purple to-zepto-light text-white
                               rounded-lg py-2 disabled:opacity-40 transition-opacity"
                  >
                    {isNotifying
                      ? <><Loader2 size={11} className="animate-spin" /> Sending…</>
                      : <><Send size={11} /> Send to {selected.size} recipient{selected.size !== 1 ? 's' : ''}</>
                    }
                  </button>
                </div>
              </div>
            )}

            <p className="text-center text-[10px] text-purple-300/30">Outputs saved to outputs/</p>
          </>
        )}
      </div>
    </aside>
  )
}
