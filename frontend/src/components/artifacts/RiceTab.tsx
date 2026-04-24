import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import StyledTable, { parseMarkdownTable } from './StyledTable'

interface RiceRow {
  initiative: string
  reach: string
  impact: string
  confidence: string
  effort: string
  score: number
}

function parseRice(content: string): RiceRow[] {
  const rows: RiceRow[] = []
  const lines = content.split('\n').filter(l => l.trim().startsWith('|'))
  let headers: string[] = []
  lines.forEach((line) => {
    if (line.replace(/\|/g, '').trim().match(/^[-: ]+$/)) return
    const cells = line.split('|').map(c => c.trim()).filter(Boolean)
    if (!headers.length) { headers = cells.map(h => h.toLowerCase()); return }
    const get = (keys: string[]) => {
      for (const k of keys) {
        const idx = headers.findIndex(h => h.includes(k))
        if (idx !== -1 && cells[idx]) return cells[idx]
      }
      return ''
    }
    const scoreRaw = get(['score', 'rice', 'total', 'final'])
    const score = parseFloat(scoreRaw.replace(/,/g, '')) || 0
    rows.push({
      initiative: get(['initiative', 'feature', 'name', 'item', 'title']),
      reach:      get(['reach']),
      impact:     get(['impact']),
      confidence: get(['confidence', 'conf']),
      effort:     get(['effort']),
      score,
    })
  })
  return rows.filter(r => r.initiative && r.score > 0).sort((a, b) => b.score - a.score)
}

// Relative thresholds — top 40% green, next 30% amber, rest red
function makeColorFn(rows: RiceRow[]) {
  const max = Math.max(...rows.map(r => r.score), 1)
  return (score: number) => {
    const r = score / max
    if (r >= 0.6) return '#10B981'
    if (r >= 0.3) return '#F59E0B'
    return '#EF4444'
  }
}

function scoreTier(score: number, max: number) {
  const r = score / Math.max(max, 1)
  if (r >= 0.6) return 'High'
  if (r >= 0.3) return 'Med'
  return 'Low'
}

const LEGEND: [string, string][] = [
  ['#10B981', 'High priority'],
  ['#F59E0B', 'Medium priority'],
  ['#EF4444', 'Lower priority'],
]

export default function RiceTab({ content }: { content: string }) {
  const rows = parseRice(content)

  if (rows.length) {
    const barColor = makeColorFn(rows)
    const max = Math.max(...rows.map(r => r.score), 1)

    return (
      <div className="space-y-5">
        {/* Legend */}
        <div className="flex items-center gap-4 flex-wrap">
          {LEGEND.map(([color, label]) => (
            <div key={label} className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
              <span className="text-[11px] text-gray-500">{label}</span>
            </div>
          ))}
          <span className="ml-auto text-[11px] text-gray-400">Score = (Reach × Impact × Confidence%) ÷ Effort</span>
        </div>

        {/* Bar chart */}
        <ResponsiveContainer width="100%" height={Math.max(180, rows.length * 46)}>
          <BarChart data={rows} layout="vertical" margin={{ top: 2, right: 64, left: 0, bottom: 2 }}>
            <CartesianGrid horizontal={false} stroke="#F0EAFF" />
            <XAxis type="number" tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey="initiative"
              width={190}
              tick={{ fontSize: 11, fill: '#374151' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: string) => v.length > 28 ? v.slice(0, 26) + '…' : v}
            />
            <Tooltip
              cursor={{ fill: '#F0EAFF' }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const r = payload[0].payload as RiceRow
                const c = barColor(r.score)
                return (
                  <div className="bg-white border border-zepto-muted rounded-xl p-3 shadow-lg text-xs space-y-1.5 min-w-[190px]">
                    <p className="font-bold text-zepto-dark leading-snug">{r.initiative}</p>
                    <span className="text-[10px] font-bold rounded-full px-2 py-0.5 border inline-block"
                      style={{ background: `${c}15`, color: c, borderColor: `${c}40` }}>
                      {scoreTier(r.score, max)} · {r.score.toFixed(1)}
                    </span>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[11px] text-gray-500 pt-1">
                      <span>Reach <strong className="text-zepto-dark">{r.reach}</strong></span>
                      <span>Impact <strong className="text-zepto-dark">{r.impact}</strong></span>
                      <span>Conf. <strong className="text-zepto-dark">{r.confidence}</strong></span>
                      <span>Effort <strong className="text-zepto-dark">{r.effort}</strong></span>
                    </div>
                  </div>
                )
              }}
            />
            <Bar dataKey="score" radius={[0, 6, 6, 0]}
              label={{ position: 'right', fontSize: 11, fill: '#6B7280', formatter: (v: number) => v.toFixed(1) }}
            >
              {rows.map((r, i) => <Cell key={i} fill={barColor(r.score)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Breakdown table */}
        <details className="group">
          <summary className="cursor-pointer text-xs text-gray-400 hover:text-zepto-purple flex items-center gap-1.5 list-none select-none mb-3">
            <span className="group-open:rotate-90 inline-block transition-transform">▶</span>
            View score breakdown
          </summary>
          <StyledTable
            headers={['Initiative', 'Reach', 'Impact', 'Confidence', 'Effort', 'Score']}
            rows={rows.map(r => [r.initiative, r.reach, r.impact, r.confidence, r.effort, r.score.toFixed(1)])}
            colTemplate="2.5fr 1fr 1fr 1fr 1fr 1fr"
            renderCell={(value, _ri, ci) => {
              if (ci === 0) return <span className="text-xs font-semibold text-zepto-dark leading-snug">{value}</span>
              if (ci === 5) {
                const score = parseFloat(value)
                const c = barColor(score)
                return (
                  <span className="text-[11px] font-bold rounded-full px-2 py-0.5 border inline-block"
                    style={{ background: `${c}15`, color: c, borderColor: `${c}40` }}>
                    {value}
                  </span>
                )
              }
              return <span className="text-xs text-gray-500">{value}</span>
            }}
          />
        </details>
      </div>
    )
  }

  const fallback = parseMarkdownTable(content)
  if (fallback) return <StyledTable headers={fallback.headers} rows={fallback.rows} />
  return <pre className="text-xs text-gray-400 bg-zepto-bg rounded-xl p-4 whitespace-pre-wrap">{content}</pre>
}
