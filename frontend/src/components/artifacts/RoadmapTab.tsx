import StyledTable, { parseMarkdownTable } from './StyledTable'

// ── Shared month helpers ───────────────────────────────────────────────────────

const MONTH_MAP: Record<string, number> = {
  Jan:0, Feb:1, Mar:2, Apr:3, May:4, Jun:5,
  Jul:6, Aug:7, Sep:8, Oct:9, Nov:10, Dec:11,
}

/** Parse "Apr 2026" → Date(2026, 3, 1). Returns null on failure. */
function parseMonthYear(s: string): Date | null {
  const m = s.trim().match(/^([A-Za-z]{3})\s+(\d{4})$/)
  if (!m) return null
  const month = MONTH_MAP[m[1]]
  const year  = parseInt(m[2])
  if (month === undefined || isNaN(year)) return null
  return new Date(year, month, 1)
}

function addMonths(d: Date, n: number) {
  return new Date(d.getFullYear(), d.getMonth() + n, 1)
}

function monthDiff(a: Date, b: Date) {
  return (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth())
}

function fmtMonth(d: Date, opts: Intl.DateTimeFormatOptions = { month: 'short' }) {
  return d.toLocaleDateString('en-US', opts)
}

// ── Timeline data ─────────────────────────────────────────────────────────────

interface TimelineRow {
  initiative: string
  start: Date
  end: Date
  phase: string
}

const PHASE_COLORS: Record<string, string> = {
  Now:   '#10B981',
  Next:  '#F59E0B',
  Later: '#6B7280',
}
const PHASE_ORDER = ['Now', 'Next', 'Later']

function parseTimeline(content: string): TimelineRow[] {
  const rows: TimelineRow[] = []
  for (const raw of content.split('\n')) {
    const line = raw.trim()
    if (!line.startsWith('|')) continue
    if (line.replace(/\|/g, '').trim().match(/^[-: ]+$/)) continue
    const cells = line.split('|').map(c => c.trim()).filter(Boolean)
    if (cells.length < 4) continue
    const start = parseMonthYear(cells[1])
    const end   = parseMonthYear(cells[2])
    if (!start || !end) continue
    rows.push({ initiative: cells[0], start, end, phase: cells[3] })
  }
  // Sort by phase order then by start date
  return rows.sort((a, b) => {
    const pd = PHASE_ORDER.indexOf(a.phase) - PHASE_ORDER.indexOf(b.phase)
    if (pd !== 0) return pd
    return a.start.getTime() - b.start.getTime()
  })
}

// ── Gantt chart ───────────────────────────────────────────────────────────────

const LABEL_W = 188   // px — label column width

function GanttChart({ content }: { content: string }) {
  const rows = parseTimeline(content)
  if (!rows.length) return null

  // Compute grid bounds: origin = first month of earliest start
  //                      totalMonths = last end month (inclusive) + 1
  const allStarts = rows.map(r => r.start)
  const allEnds   = rows.map(r => r.end)
  const originDate = allStarts.reduce((min, d) => d < min ? d : min)
  const origin = new Date(originDate.getFullYear(), originDate.getMonth(), 1)

  const lastEnd = allEnds.reduce((max, d) => d > max ? d : max)
  // end month is inclusive → extend grid 1 month beyond
  const totalMonths = monthDiff(origin, lastEnd) + 2

  const months = Array.from({ length: totalMonths }, (_, i) => addMonths(origin, i))

  // Group rows by phase
  const grouped: Record<string, TimelineRow[]> = {}
  for (const r of rows) {
    ;(grouped[r.phase] ??= []).push(r)
  }

  return (
    <div className="mt-6 select-none">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-0.5 h-5 rounded-full bg-gradient-to-b from-zepto-purple to-zepto-pale" />
        <h3 className="text-sm font-bold text-zepto-dark">Delivery Timeline</h3>
        <div className="flex gap-2 ml-1">
          {PHASE_ORDER.map(phase => {
            const color = PHASE_COLORS[phase]
            return (
              <span key={phase} className="text-[10px] font-semibold rounded-full px-2.5 py-0.5 border"
                style={{ background: `${color}15`, color, borderColor: `${color}40` }}>
                {phase}
              </span>
            )
          })}
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-zepto-muted">
        {/* Month header row */}
        <div className="flex border-b border-zepto-muted bg-zepto-tint/60">
          <div style={{ width: LABEL_W, minWidth: LABEL_W }} className="shrink-0 px-3 py-1.5">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Initiative</span>
          </div>
          <div className="flex flex-1 min-w-0">
            {months.map((m, i) => (
              <div key={i} style={{ flex: 1 }}
                className="text-[10px] font-semibold text-gray-400 text-center py-1.5 border-l border-zepto-muted first:border-0 whitespace-nowrap px-0.5">
                {fmtMonth(m, { month: 'short' })}{' '}
                <span className="text-[9px] opacity-60">{fmtMonth(m, { year: '2-digit' })}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Phase groups */}
        {PHASE_ORDER.map(phase => {
          const phaseRows = grouped[phase]
          if (!phaseRows?.length) return null
          const color = PHASE_COLORS[phase]

          return (
            <div key={phase}>
              {/* Phase label row */}
              <div className="flex items-center border-b border-zepto-muted/40"
                style={{ background: `${color}08` }}>
                <div style={{ width: LABEL_W, minWidth: LABEL_W }}
                  className="shrink-0 px-3 py-1 flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
                  <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color }}>
                    {phase}
                  </span>
                </div>
                <div className="flex-1 h-px" style={{ background: `${color}20` }} />
              </div>

              {/* Initiative rows */}
              {phaseRows.map((row, ri) => {
                const startIdx = monthDiff(origin, row.start)
                // end is inclusive month → bar spans through end of that month
                const endIdx   = monthDiff(origin, row.end) + 1
                const spanW    = Math.max(endIdx - startIdx, 1)
                const tailW    = Math.max(totalMonths - endIdx, 0)
                const isLast   = ri === phaseRows.length - 1
                const dateLabel = `${fmtMonth(row.start, { month: 'short' })} → ${fmtMonth(row.end, { month: 'short', year: '2-digit' })}`

                return (
                  <div key={ri}
                    className={`flex items-center ${!isLast ? 'border-b border-zepto-muted/30' : ''} hover:bg-zepto-tint/30 transition-colors`}
                    style={{ height: 40 }}>
                    {/* Label */}
                    <div style={{ width: LABEL_W, minWidth: LABEL_W }}
                      className="shrink-0 px-3 text-xs text-gray-600 font-medium truncate"
                      title={row.initiative}>
                      {row.initiative}
                    </div>

                    {/* Bar track */}
                    <div className="flex flex-1 min-w-0 items-stretch py-2 pr-2">
                      {/* Leading space */}
                      {startIdx > 0 && (
                        <div style={{ flex: startIdx }} className="shrink-0" />
                      )}

                      {/* The bar */}
                      <div
                        style={{ flex: spanW, background: color, minWidth: 4 }}
                        className="rounded-md flex items-center px-2 shrink-0 relative group"
                        title={`${row.initiative}\n${dateLabel}`}
                      >
                        {spanW >= 2 && (
                          <span className="text-[9px] text-white/90 font-semibold truncate leading-none">
                            {dateLabel}
                          </span>
                        )}
                      </div>

                      {/* Trailing space */}
                      {tailW > 0 && (
                        <div style={{ flex: tailW }} className="shrink-0" />
                      )}
                    </div>

                    {/* Month grid lines overlay (decorative) */}
                  </div>
                )
              })}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Roadmap Now / Next / Later ────────────────────────────────────────────────

function splitItems(cell: string): string[] {
  return cell.split(/,\s*|\n/).map(s => s.replace(/^\d+\.\s*/, '').trim()).filter(Boolean)
}

function parseRoadmap(content: string) {
  const result: Record<string, string[]> = { now: [], next: [], later: [] }
  const lines = content.split('\n').filter(l => l.trim().startsWith('|'))
  lines.forEach((line, i) => {
    if (i === 0 || line.replace(/\|/g, '').trim().match(/^[-: ]+$/)) return
    const cells = line.split('|').map(c => c.trim()).filter(Boolean)
    if (cells.length >= 3) {
      splitItems(cells[0]).forEach(s => result.now.push(s))
      splitItems(cells[1]).forEach(s => result.next.push(s))
      splitItems(cells[2]).forEach(s => result.later.push(s))
    }
  })
  return result
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
