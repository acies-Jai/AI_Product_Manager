import StyledTable, { parseMarkdownTable } from './StyledTable'

// ── types ─────────────────────────────────────────────────────────────────────
interface SectionItem { text: string; isSubheader: boolean }
interface ReqSection  { title: string; description: string; items: SectionItem[] }
interface ReqRow      { id: string; requirement: string; priority: string; category: string; notes: string }

// ── priority badge styles ─────────────────────────────────────────────────────
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

// ── column colors ─────────────────────────────────────────────────────────────
const COL_COLORS = ['#5E17EB', '#10B981', '#F59E0B', '#0EA5E9', '#EC4899']

// ── parsers ───────────────────────────────────────────────────────────────────
function parseTable(content: string): ReqRow[] {
  const rows: ReqRow[] = []
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
    rows.push({
      id:          get(['id', '#', 'ref']) || String(rows.length + 1),
      requirement: get(['requirement', 'feature', 'description', 'name', 'title', 'item']),
      priority:    get(['priority', 'prio', 'level', 'must', 'type']),
      category:    get(['category', 'area', 'module', 'section', 'type', 'tag']),
      notes:       get(['note', 'comment', 'detail', 'acceptance', 'criteria', 'owner']),
    })
  })
  return rows.filter(r => r.requirement)
}

function parseSections(content: string): ReqSection[] {
  const sections: ReqSection[] = []
  let current: ReqSection | null = null

  for (const raw of content.split('\n')) {
    const line = raw.trim()
    if (!line) continue

    // Section header (## or ###)
    if (line.match(/^#{2,3}\s/)) {
      if (current) sections.push(current)
      current = { title: line.replace(/^#{2,3}\s*/, '').replace(/^\d+\.\s*/, ''), description: '', items: [] }
      continue
    }

    if (!current) {
      current = { title: 'Requirements', description: '', items: [] }
    }

    const isBullet = line.startsWith('- ') || line.startsWith('* ') || !!line.match(/^\d+\.\s/)
    const text = line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '').trim()

    if (isBullet) {
      current.items.push({ text, isSubheader: false })
    } else {
      // Plain line — sub-header if it ends with ':', otherwise description
      if (line.endsWith(':') && !current.items.length && !current.description) {
        current.description = line
      } else if (line.endsWith(':')) {
        current.items.push({ text: line, isSubheader: true })
      } else if (!current.items.length) {
        current.description = current.description ? `${current.description} ${line}` : line
      } else {
        current.items.push({ text: line, isSubheader: false })
      }
    }
  }
  if (current) sections.push(current)
  return sections.filter(s => s.items.length || s.description)
}

// ── components ────────────────────────────────────────────────────────────────
export default function RequirementsTab({ content }: { content: string }) {
  // Table format (structured with ID/priority/category)
  const rows = parseTable(content)
  if (rows.length) {
    return (
      <StyledTable
        headers={['#', 'Requirement', 'Priority', 'Category', 'Notes']}
        rows={rows.map(r => [r.id, r.requirement, r.priority, r.category, r.notes])}
        colTemplate="40px 2fr 80px 100px 1.5fr"
        renderCell={(value, _ri, ci) => {
          if (ci === 0) return (
            <span className="text-[10px] font-extrabold text-zepto-purple font-mono">{value}</span>
          )
          if (ci === 1) return (
            <span className="text-xs font-semibold text-zepto-dark leading-snug">{value}</span>
          )
          if (ci === 2 && value) {
            const ps = priorityStyle(value)
            return (
              <span className="text-[10px] font-bold rounded-full px-2 py-0.5 border inline-block"
                style={{ background: ps.bg, color: ps.text, borderColor: ps.border }}>
                {value}
              </span>
            )
          }
          return <span className="text-xs text-gray-400">{value || '—'}</span>
        }}
      />
    )
  }

  // Bullet / section format — 3-column layout
  const sections = parseSections(content)
  if (sections.length) {
    return (
      <div className={`grid gap-3 ${sections.length >= 3 ? 'grid-cols-3' : sections.length === 2 ? 'grid-cols-2' : 'grid-cols-1'}`}>
        {sections.map((sec, si) => {
          const color = COL_COLORS[si % COL_COLORS.length]
          return (
            <div key={si} className="rounded-xl overflow-hidden border" style={{ borderColor: `${color}25` }}>
              {/* Column header */}
              <div className="px-3 py-2.5" style={{ borderTop: `3px solid ${color}`, background: `${color}0E` }}>
                <p className="text-[11px] font-bold uppercase tracking-[1px]" style={{ color }}>{sec.title}</p>
                {sec.description && (
                  <p className="text-[10px] text-gray-400 mt-0.5 italic">{sec.description}</p>
                )}
              </div>

              {/* Items */}
              <div className="bg-white px-3 py-2.5 space-y-1.5 min-h-[60px]">
                {sec.items.length === 0 ? (
                  <p className="text-xs text-gray-300">No items.</p>
                ) : sec.items.map((item, ii) => (
                  item.isSubheader ? (
                    <p key={ii} className="text-[10px] font-bold uppercase tracking-wide pt-1.5 pb-0.5"
                      style={{ color }}>
                      {item.text.replace(/:$/, '')}
                    </p>
                  ) : (
                    <div key={ii} className="flex items-start gap-1.5">
                      <span className="mt-[5px] w-1 h-1 rounded-full shrink-0" style={{ background: color }} />
                      <p className="text-xs text-gray-600 leading-relaxed">{item.text}</p>
                    </div>
                  )
                ))}
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  const fallback = parseMarkdownTable(content)
  if (fallback) return <StyledTable headers={fallback.headers} rows={fallback.rows} />
  return <pre className="text-xs text-gray-400 bg-zepto-bg rounded-xl p-4 whitespace-pre-wrap">{content}</pre>
}
