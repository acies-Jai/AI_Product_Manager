import StyledTable, { parseMarkdownTable } from './StyledTable'

interface MetricRow { initiative: string; pre: string; post: string; owner: string }

function parseMetrics(content: string): MetricRow[] {
  const rows: MetricRow[] = []
  const lines = content.split('\n').filter(l => l.trim().startsWith('|'))
  let headers: string[] = []
  lines.forEach((line, i) => {
    if (line.replace(/\|/g, '').trim().match(/^[-: ]+$/)) return
    const cells = line.split('|').map(c => c.trim()).filter(Boolean)
    if (!headers.length || i === 0) { headers = cells.map(h => h.toLowerCase()); return }
    const get = (keys: string[]) => {
      for (const k of keys) {
        const idx = headers.findIndex(h => h.includes(k))
        if (idx !== -1 && cells[idx]) return cells[idx]
      }
      return ''
    }
    rows.push({
      initiative: get(['initiative', 'metric', 'name', 'feature', 'title', 'kpi']),
      pre:        get(['pre', 'before', 'current', 'baseline']),
      post:       get(['post', 'after', 'target', 'goal']),
      owner:      get(['owner', 'team', 'dri', 'assigned']),
    })
  })
  return rows.filter(r => r.initiative)
}

const OWNER_COLORS = ['#5E17EB', '#10B981', '#F59E0B', '#0EA5E9', '#EC4899', '#F97316', '#8B5CF6', '#14B8A6']
const ownerColorCache: Record<string, string> = {}
let ownerColorIdx = 0
function ownerColor(name: string) {
  if (!ownerColorCache[name]) ownerColorCache[name] = OWNER_COLORS[ownerColorIdx++ % OWNER_COLORS.length]
  return ownerColorCache[name]
}

export default function MetricsTab({ content }: { content: string }) {
  const rows = parseMetrics(content)

  if (rows.length) {
    return (
      <StyledTable
        headers={['Initiative / Metric', 'Before', 'After', 'Owner']}
        rows={rows.map(r => [r.initiative, r.pre, r.post, r.owner])}
        colTemplate="2.5fr 1fr 1fr 1fr"
        renderCell={(value, _ri, ci) => {
          if (ci === 0) return (
            <span className="text-xs font-semibold text-zepto-dark leading-snug block">{value}</span>
          )
          if (ci === 2) return (
            <span className="text-xs font-semibold text-emerald-500">
              {value && !value.startsWith('↑') ? `↑ ${value}` : value}
            </span>
          )
          if (ci === 3 && value) {
            const c = ownerColor(value)
            return (
              <span
                className="text-[11px] font-semibold rounded-full px-2.5 py-0.5 border inline-block truncate max-w-full"
                style={{ background: `${c}15`, color: c, borderColor: `${c}40` }}
              >
                {value}
              </span>
            )
          }
          return <span className="text-xs text-gray-400">{value || '—'}</span>
        }}
      />
    )
  }

  // fallback: try to render any pipe-table from raw content
  const fallback = parseMarkdownTable(content)
  if (fallback) return <StyledTable headers={fallback.headers} rows={fallback.rows} />

  return <pre className="text-xs text-gray-400 bg-zepto-bg rounded-xl p-4 whitespace-pre-wrap">{content}</pre>
}
