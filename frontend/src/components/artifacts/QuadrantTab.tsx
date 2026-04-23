function parseQuadrant(content: string) {
  const sections: Record<string, string> = {}
  const patterns: [string, string][] = [
    ['quick_wins',  '--QUICK_WINS--'],
    ['major_bets',  '--MAJOR_BETS--'],
    ['low_hanging', '--LOW_HANGING--'],
    ['deprioritise','--DEPRIORITISE--'],
  ]
  patterns.forEach(([key, marker]) => {
    const start = content.indexOf(marker)
    if (start === -1) return
    const afterMarker = content.slice(start + marker.length)
    const nextMarker = afterMarker.search(/--[A-Z_]+--/)
    const raw = nextMarker === -1 ? afterMarker : afterMarker.slice(0, nextMarker)
    sections[key] = raw.trim()
  })
  return sections
}

const QUADS = [
  { key: 'quick_wins',   label: '🟢 Quick Wins',       sub: 'High Impact · Low Effort',  color: '#10B981' },
  { key: 'major_bets',   label: '🔴 Major Bets',        sub: 'High Impact · High Effort', color: '#EF4444' },
  { key: 'low_hanging',  label: '🟡 Low-hanging Fruit', sub: 'Low Impact · Low Effort',   color: '#F59E0B' },
  { key: 'deprioritise', label: '⚪ Deprioritise',       sub: 'Low Impact · High Effort',  color: '#9CA3AF' },
] as const

export default function QuadrantTab({ content }: { content: string }) {
  const sections = parseQuadrant(content)

  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-400 text-center pb-1">◀ Low Effort &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; High Effort ▶</p>
      <div className="grid grid-cols-2 gap-3">
        {QUADS.map(({ key, label, sub, color }) => (
          <div key={key} className="rounded-xl border p-4" style={{ borderColor: `${color}30`, background: `${color}08` }}>
            <p className="font-bold text-sm mb-0.5" style={{ color }}>{label}</p>
            <p className="text-[10px] text-gray-400 mb-3">{sub}</p>
            <div className="text-xs text-gray-600 space-y-1 whitespace-pre-wrap">
              {sections[key] || <span className="text-gray-300">No items.</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
