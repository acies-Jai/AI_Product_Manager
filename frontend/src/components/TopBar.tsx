import { Loader2 } from 'lucide-react'
import { useStore } from '../store'
import { ROLES, ROLE_CONFIG, ARTIFACT_KEYS } from '../types'

export default function TopBar() {
  const { chunksIndexed, artifacts, role, setRole, staleArtifacts, isGenerating, generateArtifacts } = useStore()
  const artifactCount = ARTIFACT_KEYS.filter(k => artifacts[k]).length
  const cfg = ROLE_CONFIG[role] ?? { color: '#9CA3AF', icon: '👥', access: 'Public only' }
  const allReady = artifactCount === 6

  return (
    <div className="h-14 flex items-center gap-4 px-6 border-b border-zepto-muted bg-white shrink-0">
      {/* Title */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-sm font-extrabold text-zepto-dark tracking-tight">PM Assistant</span>
        <span className="hidden sm:block text-[11px] text-gray-400 border-l border-zepto-muted pl-2">
          Customer App &amp; Checkout
        </span>
      </div>

      {/* Status chips */}
      <div className="flex items-center gap-2">
        <span className="text-[11px] bg-zepto-bg border border-zepto-muted rounded-full px-2.5 py-0.5 text-gray-500 font-medium">
          🗄️ <strong className="text-zepto-dark">{chunksIndexed}</strong> sources
        </span>
        <span
          className="text-[11px] rounded-full px-2.5 py-0.5 font-semibold border"
          style={
            allReady
              ? { background: '#ECFDF5', color: '#10B981', borderColor: '#A7F3D0' }
              : { background: '#FFFBEB', color: '#F59E0B', borderColor: '#FCD34D' }
          }
        >
          {allReady ? '⚡' : '○'} {artifactCount}/6 artifacts
        </span>

        {staleArtifacts && (
          <button
            onClick={() => generateArtifacts()}
            disabled={isGenerating}
            className="flex items-center gap-1 text-[11px] font-semibold bg-amber-50 border border-amber-200
                       text-amber-700 rounded-full px-2.5 py-0.5 hover:bg-amber-100 transition-colors
                       disabled:opacity-50"
          >
            {isGenerating
              ? <><Loader2 size={10} className="animate-spin" /> Regenerating…</>
              : <>↻ Regenerate</>
            }
          </button>
        )}
      </div>

      <div className="flex-1" />

      {/* Role selector */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-[11px] text-gray-400 hidden md:block">Viewing as</span>
        <div className="relative">
          <select
            value={role}
            onChange={e => setRole(e.target.value)}
            className="text-xs font-semibold text-zepto-dark bg-zepto-bg border border-zepto-muted
                       rounded-xl pl-3 pr-7 py-1.5 outline-none focus:ring-2 focus:ring-zepto-purple/30
                       cursor-pointer appearance-none"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%235E17EB' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
              backgroundRepeat: 'no-repeat',
              backgroundPosition: 'right 8px center',
            }}
          >
            {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <span
          className="role-badge text-[10px] shrink-0"
          style={{ background: `${cfg.color}18`, color: cfg.color, borderColor: `${cfg.color}40` }}
        >
          {cfg.icon} {cfg.access}
        </span>
      </div>
    </div>
  )
}
