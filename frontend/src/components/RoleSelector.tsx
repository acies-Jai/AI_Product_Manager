import { useStore } from '../store'
import { ROLES, ROLE_CONFIG } from '../types'

export default function RoleSelector() {
  const { role, setRole } = useStore()
  const cfg = ROLE_CONFIG[role] ?? { color: '#9CA3AF', icon: '👥', access: 'Public only' }

  return (
    <div className="card px-5 py-4">
      <p className="text-[10px] font-bold text-gray-400 uppercase tracking-[1.5px] mb-2">
        Viewing as
      </p>
      <div className="flex items-center gap-3">
        <select
          value={role}
          onChange={e => setRole(e.target.value)}
          className="flex-1 text-sm font-medium text-zepto-dark bg-zepto-bg border border-zepto-muted
                     rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-zepto-purple/30
                     cursor-pointer appearance-none"
          style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%235E17EB' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 12px center', paddingRight: '32px' }}
        >
          {ROLES.map(r => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <div
          className="role-badge shrink-0"
          style={{
            background: `${cfg.color}18`,
            color: cfg.color,
            borderColor: `${cfg.color}40`,
          }}
        >
          {cfg.icon} {role}
        </div>
        <span className="text-xs text-gray-400 shrink-0">{cfg.access}</span>
      </div>
    </div>
  )
}
