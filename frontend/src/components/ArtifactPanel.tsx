import { useStore } from '../store'
import { ARTIFACT_KEYS, ARTIFACT_LABELS, type ArtifactKey } from '../types'
import RoadmapTab from './artifacts/RoadmapTab'
import RiceTab from './artifacts/RiceTab'
import MetricsTab from './artifacts/MetricsTab'
import QuadrantTab from './artifacts/QuadrantTab'
import KeyFocusTab from './artifacts/KeyFocusTab'
import RequirementsTab from './artifacts/RequirementsTab'
import { Loader2, Zap } from 'lucide-react'

const TAB_ICONS: Record<string, string> = {
  roadmap:         '🗺',
  key_focus_areas: '🎯',
  requirements:    '📋',
  success_metrics: '📊',
  impact_quadrant: '⚡',
  rice_score:      '🔢',
}

function renderTab(key: ArtifactKey, content: string, artifacts: Record<string, string>) {
  if (key === 'roadmap')          return <RoadmapTab content={content} timelineContent={artifacts['roadmap_timeline']} />
  if (key === 'rice_score')       return <RiceTab content={content} />
  if (key === 'success_metrics')  return <MetricsTab content={content} />
  if (key === 'impact_quadrant')  return <QuadrantTab content={content} />
  if (key === 'key_focus_areas')  return <KeyFocusTab content={content} />
  if (key === 'requirements')     return <RequirementsTab content={content} />
  return <pre className="text-xs text-gray-500 whitespace-pre-wrap">{content}</pre>
}

export default function ArtifactPanel() {
  const { artifacts, activeTab, setActiveTab, isGenerating, generateArtifacts, chunksIndexed } = useStore()
  const hasArtifacts = ARTIFACT_KEYS.some(k => artifacts[k])

  if (isGenerating) {
    return (
      <div className="card p-16 flex flex-col items-center justify-center gap-4 text-gray-400">
        <div className="relative">
          <div className="w-14 h-14 rounded-2xl bg-zepto-tint flex items-center justify-center">
            <Zap size={24} className="text-zepto-purple" />
          </div>
          <Loader2 size={16} className="animate-spin text-zepto-purple absolute -top-1 -right-1" />
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-zepto-dark">Generating artifacts</p>
          <p className="text-xs text-gray-400 mt-1">Running 8 semantic queries — ~30 seconds</p>
        </div>
        <div className="flex gap-1 mt-1">
          {[0, 1, 2].map(i => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-zepto-purple animate-bounce"
              style={{ animationDelay: `${i * 150}ms` }}
            />
          ))}
        </div>
      </div>
    )
  }

  if (!hasArtifacts) {
    return (
      <div className="card p-12 text-center flex flex-col items-center gap-5">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-zepto-purple to-zepto-pale flex items-center justify-center">
          <Zap size={28} className="text-white" />
        </div>
        <div>
          <h2 className="text-base font-bold text-zepto-dark">Your insights are one click away</h2>
          <p className="text-sm text-gray-400 mt-1">Index your documents, then generate artifacts to get started.</p>
        </div>
        <div className="flex justify-center gap-3 flex-wrap">
          {[
            { icon: '🔍', step: '1', label: 'Index Documents', done: chunksIndexed > 0 },
            { icon: '⚡', step: '2', label: 'Generate Artifacts', done: false },
            { icon: '💬', step: '3', label: 'Chat & explore', done: false },
          ].map(({ icon, step, label, done }) => (
            <div
              key={label}
              className={`rounded-xl px-5 py-4 text-center w-36 border transition-colors ${
                done ? 'bg-emerald-50 border-emerald-100' : 'bg-zepto-tint border-zepto-muted'
              }`}
            >
              <div className="text-2xl">{done ? '✅' : icon}</div>
              <p className={`text-[11px] font-semibold mt-2 ${done ? 'text-emerald-600' : 'text-zepto-dark'}`}>
                {step}. {label}
              </p>
            </div>
          ))}
        </div>
        {chunksIndexed > 0 && (
          <button
            onClick={() => generateArtifacts()}
            className="btn-primary flex items-center gap-2"
          >
            <Zap size={14} />
            Generate Artifacts
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="card overflow-hidden">
      {/* Tab bar */}
      <div className="px-4 pt-3 pb-0 border-b border-zepto-muted">
        <div className="flex gap-0.5 overflow-x-auto scrollbar-none">
          {ARTIFACT_KEYS.map(key => {
            const active = activeTab === key
            const hasContent = !!artifacts[key]
            return (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`
                  flex items-center gap-1.5 px-3.5 py-2.5 text-xs font-semibold whitespace-nowrap
                  border-b-2 transition-all duration-150
                  ${active
                    ? 'border-zepto-purple text-zepto-purple'
                    : 'border-transparent text-gray-400 hover:text-zepto-dark hover:border-zepto-muted'
                  }
                `}
              >
                <span>{TAB_ICONS[key]}</span>
                {ARTIFACT_LABELS[key]}
                {!hasContent && (
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Tab content */}
      <div className="p-5">
        {ARTIFACT_KEYS.map(key => {
          if (activeTab !== key) return null
          const content = artifacts[key]
          if (!content) return (
            <div key={key} className="flex flex-col items-center justify-center gap-3 py-12 text-center">
              <div className="text-3xl">{TAB_ICONS[key]}</div>
              <p className="text-sm text-gray-400">No data for <strong>{ARTIFACT_LABELS[key]}</strong> yet.</p>
              <button onClick={() => generateArtifacts()} className="btn-primary text-xs flex items-center gap-1.5">
                <Zap size={12} /> Generate
              </button>
            </div>
          )
          return <div key={key}>{renderTab(key, content, artifacts)}</div>
        })}
      </div>
    </div>
  )
}
