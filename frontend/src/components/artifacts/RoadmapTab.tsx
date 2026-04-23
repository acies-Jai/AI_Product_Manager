import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'
import StyledTable, { parseMarkdownTable } from './StyledTable'

function parseRoadmap(content: string) {
  const result: Record<string, string[]> = { now: [], next: [], later: [] }
  const lines = content.split('\n').filter(l => l.trim().startsWith('|'))
  lines.forEach((line, i) => {
    if (i === 0 || line.replace(/\|/g, '').trim().match(/^[-: ]+$/)) return
    const cells = line.split('|').map(c => c.trim()).filter(Boolean)
    if (cells.length >= 3) {
      if (cells[0]) result.now.push(cells[0])
      if (cells[1]) result.next.push(cells[1])
      if (cells[2]) result.later.push(cells[2])
    }
  })
  return result
}

interface TimelineRow {
  initiative: string
  start: Date
  end: Date
  phase: string
  startMs: number
  durationMs: number
}

const PHASE_COLORS: Record<string, string> = {
  Now: '#10B981', Next: '#F59E0B', Later: '#6B7280',
}

function parseTimeline(content: string): TimelineRow[] {
  const rows: TimelineRow[] = []
  const lines = content.split('\n').filter(l => l.trim().startsWith('|'))
  lines.forEach((line, i) => {
    if (i === 0 || line.replace(/\|/g, '').trim().match(/^[-: ]+$/)) return
    const cells = line.split('|').map(c => c.trim()).filter(Boolean)
    if (cells.length < 4) return
    try {
      const start = new Date(cells[1])
      const end   = new Date(cells[2])
      if (isNaN(start.getTime()) || isNaN(end.getTime())) return
      rows.push({
        initiative: cells[0],
        start, end,
        phase: cells[3],
        startMs: start.getTime(),
        durationMs: end.getTime() - start.getTime(),
      })
    } catch { /* skip */ }
  })
  return rows.sort((a, b) => a.startMs - b.startMs)
}

function GanttChart({ content }: { content: string }) {
  const rows = parseTimeline(content)
  if (!rows.length) return null

  const minMs = Math.min(...rows.map(r => r.startMs))
  const data = rows.map(r => ({
    ...r,
    offset: r.startMs - minMs,
    label: `${r.start.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })} → ${r.end.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })}`,
  }))

  return (
    <div className="mt-6">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-0.5 h-5 rounded-full bg-gradient-to-b from-zepto-purple to-zepto-pale" />
        <h3 className="text-sm font-bold text-zepto-dark">Delivery Timeline</h3>
        <div className="flex gap-2">
          {Object.entries(PHASE_COLORS).map(([phase, color]) => (
            <span
              key={phase}
              className="text-[10px] font-semibold rounded-full px-2 py-0.5 border"
              style={{ background: `${color}18`, color, borderColor: `${color}40` }}
            >
              {phase}
            </span>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={Math.max(200, rows.length * 44)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 20, left: 8, bottom: 4 }}>
          <CartesianGrid horizontal={false} stroke="#F0EAFF" />
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="initiative" width={160} tick={{ fontSize: 12, fill: '#374151' }} axisLine={false} tickLine={false} />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const r = payload[0].payload
              return (
                <div className="bg-white border border-zepto-muted rounded-xl p-3 shadow-lg text-xs">
                  <p className="font-bold text-zepto-dark">{r.initiative}</p>
                  <p className="text-gray-500 mt-0.5">{r.label}</p>
                  <p className="mt-0.5" style={{ color: PHASE_COLORS[r.phase] ?? '#6B7280' }}>
                    Phase: {r.phase}
                  </p>
                </div>
              )
            }}
          />
          {/* transparent offset bar to position the real bar */}
          <Bar dataKey="offset" stackId="a" fill="transparent" />
          <Bar dataKey="durationMs" stackId="a" radius={[0, 6, 6, 0]}>
            {data.map((r, i) => (
              <Cell key={i} fill={PHASE_COLORS[r.phase] ?? '#5E17EB'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

const COLS = [
  { key: 'now',   label: 'Now',   color: '#10B981' },
  { key: 'next',  label: 'Next',  color: '#F59E0B' },
  { key: 'later', label: 'Later', color: '#6B7280' },
] as const

export default function RoadmapTab({
  content,
  timelineContent,
}: {
  content: string
  timelineContent?: string
}) {
  const data = parseRoadmap(content)
  const hasData = Object.values(data).some(v => v.length > 0)

  return (
    <div>
      {hasData ? (
        <div className="grid grid-cols-3 gap-4">
          {COLS.map(({ key, label, color }) => (
            <div key={key} style={{ borderTop: `3px solid ${color}` }} className="rounded-b-xl overflow-hidden">
              <div style={{ background: `${color}10` }} className="px-4 py-3">
                <p className="text-xs font-bold uppercase tracking-[1px]" style={{ color }}>{label}</p>
              </div>
              <div className="bg-white px-3 pb-3 pt-1 space-y-2 min-h-[100px]">
                {data[key].length === 0
                  ? <p className="text-xs text-gray-400 pt-2">No items</p>
                  : data[key].map((item, i) => (
                    <div key={i} className="bg-zepto-bg rounded-lg px-3 py-2 text-xs text-zepto-dark shadow-sm">
                      {item}
                    </div>
                  ))
                }
              </div>
            </div>
          ))}
        </div>
      ) : (() => {
        const fallback = parseMarkdownTable(content)
        return fallback
          ? <StyledTable headers={fallback.headers} rows={fallback.rows} />
          : <pre className="text-xs text-gray-400 bg-zepto-bg rounded-xl p-4 whitespace-pre-wrap">{content}</pre>
      })()}

      {timelineContent && <GanttChart content={timelineContent} />}
    </div>
  )
}
