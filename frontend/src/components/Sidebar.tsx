import { useState } from 'react'
import { RefreshCw, Search, Zap, Mail, Loader2, ChevronDown, ChevronRight, FileText } from 'lucide-react'
import { useStore } from '../store'
import { ARTIFACT_KEYS } from '../types'

export default function Sidebar() {
  const { files, chunksIndexed, artifacts, isIndexing, isGenerating, loadInitial, indexDocuments, generateArtifacts } = useStore()
  const [filesOpen, setFilesOpen] = useState(false)
  const isIndexed = chunksIndexed > 0
  const artifactCount = ARTIFACT_KEYS.filter(k => artifacts[k]).length

  async function handleIndex() {
    try { await indexDocuments() } catch { /* surfaced in UI */ }
  }
  async function handleGenerate() {
    try { await generateArtifacts() } catch { /* surfaced in UI */ }
  }
  async function handleNotify() {
    await fetch('/api/notify-team', { method: 'POST' })
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
            <span className="font-semibold uppercase tracking-[1.5px] text-[10px]">
              Context Files
            </span>
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
              <div
                key={name}
                className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-purple-100/70"
              >
                <span style={{ color: isIndexed ? '#10B981' : '#6B7280' }} className="text-[10px] font-bold">
                  {isIndexed ? '✓' : '○'}
                </span>
                <span className="truncate">{name}.md</span>
              </div>
            ))}
            <div className="pt-1">
              <button
                onClick={() => loadInitial()}
                className="w-full flex items-center justify-center gap-1.5 text-[11px] text-purple-300/50 hover:text-purple-200 transition-colors py-1 rounded-lg hover:bg-white/5"
              >
                <RefreshCw size={10} />
                Reload files
              </button>
            </div>
          </div>
        )}

        <div className="h-px bg-white/10" />

        {/* ── Action buttons ── */}
        <button
          className="btn-ghost w-full flex items-center justify-center gap-2 text-xs"
          onClick={handleIndex}
          disabled={isIndexing}
        >
          {isIndexing ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
          {isIndexing ? 'Indexing…' : 'Index Documents'}
        </button>

        <button
          className="btn-primary w-full flex items-center justify-center gap-2 text-xs"
          onClick={handleGenerate}
          disabled={isGenerating || !isIndexed}
        >
          {isGenerating ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
          {isGenerating ? 'Generating…' : 'Generate Artifacts'}
        </button>

        {artifactCount > 0 && (
          <>
            <div className="h-px bg-white/10" />
            <button
              className="btn-ghost w-full flex items-center justify-center gap-2 text-xs"
              onClick={handleNotify}
            >
              <Mail size={12} />
              Notify Team
            </button>
            <p className="text-center text-[10px] text-purple-300/30">Outputs saved to outputs/</p>
          </>
        )}
      </div>
    </aside>
  )
}
