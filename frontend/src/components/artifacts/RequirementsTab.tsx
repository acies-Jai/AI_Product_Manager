import StyledTable, { parseMarkdownTable } from './StyledTable'

interface ReqRow { id: string; requirement: string; priority: string; category: string; notes: string }

const PRIORITY_STYLE: Record<string, { bg: string; text: string; border: string }> = {
  High:   { bg: '#FEF2F2', text: '#EF4444', border: '#FCA5A5' },
  Medium: { bg: '#FFFBEB', text: '#F59E0B', border: '#FCD34D' },
  Low:    { bg: '#F0FDF4', text: '#10B981', border: '#86EFAC' },
  Must:   { bg: '#FEF2F2', text: '#EF4444', border: '#FCA5A5' },
  Should: { bg: '#FFFBEB', text: '#F59E0B', border: '#FCD34D' },
  Could:  { bg: '#F0FDF4', text: '#10B981', border: '#86EFAC' },
}

function priorityStyle(p: string) {
  return PRIORITY_STYLE[p] ?? { bg: '#F4F0FC', text: '#5E17EB', border: '#C4B5FD' }
}

function parseTable(content: string): ReqRow[] {
  const rows: ReqRow[] = []
  const lines = content.split('\n').filter(l => l.trim().startsWith('|'))
  let headers: string[] = []
  lines.forEach((line, i) => {
    if (line.replace(/\|/g, '').trim().match(/^[-: ]+$/)) return
    const cells = line.split('|').map(c => c.trim()).filter(Boolean)
    if (i === 0 || headers.length === 0) {
      headers = cells.map(h => h.toLowerCase())
      return
    }
    const get = (keys: string[]) => {
      for (const k of keys) {
        const idx = headers.findIndex(h => h.includes(k))
        if (idx !== -1 && cells[idx]) return cells[idx]
      }
      return ''
    }
    rows.push({
      id: get(['id', '#', 'ref']) || String(rows.length + 1),
      requirement: get(['requirement', 'feature', 'description', 'name', 'title', 'item']),
      priority: get(['priority', 'prio', 'level', 'must', 'type']),
      category: get(['category', 'area', 'module', 'section', 'type', 'tag']),
      notes: get(['note', 'comment', 'detail', 'acceptance', 'criteria', 'owner']),
    })
  })
  return rows.filter(r => r.requirement)
}

interface ReqSection { title: string; items: string[] }

function parseBullets(content: string): ReqSection[] {
  const sections: ReqSection[] = []
  let current: ReqSection = { title: 'Requirements', items: [] }
  for (const raw of content.split('\n')) {
    const line = raw.trim()
    if (line.startsWith('## ') || line.startsWith('### ')) {
      if (current.items.length) sections.push(current)
      current = { title: line.replace(/^#{2,3}\s*/, '').replace(/^\d+\.\s*/, ''), items: [] }
    } else if (line.startsWith('- ') || line.startsWith('* ') || line.match(/^\d+\.\s/)) {
      current.items.push(line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '').trim())
    }
  }
  if (current.items.length) sections.push(current)
  return sections
}

export default function RequirementsTab({ content }: { content: string }) {
  const rows = parseTable(content)

  if (rows.length) {
    return (
      <div className="space-y-2">
        {rows.map((r, i) => {
          const ps = priorityStyle(r.priority)
          return (
            <div
              key={i}
              className="flex items-start gap-3 bg-white border border-zepto-muted rounded-xl px-4 py-3 hover:shadow-sm transition-shadow"
            >
              {/* ID chip */}
              <span className="shrink-0 text-[10px] font-extrabold text-zepto-purple bg-zepto-tint rounded-lg px-2 py-1 mt-0.5 font-mono">
                {r.id}
              </span>

              {/* body */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-zepto-dark leading-snug">{r.requirement}</p>
                {r.notes && <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">{r.notes}</p>}
              </div>

              {/* badges */}
              <div className="flex flex-col items-end gap-1.5 shrink-0">
                {r.priority && (
                  <span
                    className="text-[10px] font-bold rounded-full px-2 py-0.5 border"
                    style={{ background: ps.bg, color: ps.text, borderColor: ps.border }}
                  >
                    {r.priority}
                  </span>
                )}
                {r.category && (
                  <span className="text-[10px] text-gray-400 bg-zepto-bg border border-zepto-muted rounded-full px-2 py-0.5">
                    {r.category}
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  // fallback: bullet-based sections
  const sections = parseBullets(content)
  if (sections.length) {
    return (
      <div className="space-y-5">
        {sections.map((sec, si) => (
          <div key={si}>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-0.5 h-4 rounded-full bg-zepto-purple" />
              <p className="text-xs font-bold uppercase tracking-wide text-zepto-dark">{sec.title}</p>
            </div>
            <div className="space-y-1.5">
              {sec.items.map((item, ii) => (
                <div key={ii} className="flex items-start gap-2.5 bg-white border border-zepto-muted rounded-xl px-4 py-2.5">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-zepto-purple shrink-0" />
                  <p className="text-sm text-gray-700 leading-relaxed">{item}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    )
  }

  const fallback = parseMarkdownTable(content)
  if (fallback) return <StyledTable headers={fallback.headers} rows={fallback.rows} />
  return <pre className="text-xs text-gray-400 bg-zepto-bg rounded-xl p-4 whitespace-pre-wrap">{content}</pre>
}
