import StyledTable, { parseMarkdownTable } from './StyledTable'

interface FocusArea { title: string; description: string; bullets: string[] }

const CARD_COLORS = ['#5E17EB', '#10B981', '#F59E0B', '#0EA5E9', '#EC4899', '#F97316']

function parseFocusAreas(content: string): FocusArea[] {
  const areas: FocusArea[] = []
  let current: FocusArea | null = null

  for (const raw of content.split('\n')) {
    const line = raw.trim()
    if (!line) continue

    // "1. **Title**: rest of paragraph" — the real LLM output format
    const numbered = line.match(/^\d+\.\s+\*\*(.+?)\*\*[:\s-]*(.*)/)
    if (numbered) {
      if (current) areas.push(current)
      current = { title: numbered[1].trim(), description: numbered[2].trim(), bullets: [] }
      continue
    }

    // "## Title" or "### Title" fallback
    const heading = line.match(/^#{2,3}\s+(.+)/)
    if (heading) {
      if (current) areas.push(current)
      current = { title: heading[1].replace(/^\d+\.\s*/, '').trim(), description: '', bullets: [] }
      continue
    }

    if (!current) continue

    // Bullet under a section
    if (line.startsWith('- ') || line.startsWith('* ')) {
      current.bullets.push(line.replace(/^[-*]\s+/, '').trim())
      continue
    }

    // Continuation paragraph — append to description
    if (!line.startsWith('#')) {
      current.description = current.description
        ? `${current.description} ${line}`
        : line
    }
  }
  if (current) areas.push(current)
  return areas.filter(a => a.title)
}

export default function KeyFocusTab({ content }: { content: string }) {
  const areas = parseFocusAreas(content)

  if (!areas.length) {
    const fallback = parseMarkdownTable(content)
    if (fallback) return <StyledTable headers={fallback.headers} rows={fallback.rows} />
    return <pre className="text-xs text-gray-400 bg-zepto-bg rounded-xl p-4 whitespace-pre-wrap">{content}</pre>
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {areas.map((area, i) => {
        const color = CARD_COLORS[i % CARD_COLORS.length]
        return (
          <div key={i} className="rounded-xl border overflow-hidden" style={{ borderColor: `${color}30` }}>
            {/* Header strip */}
            <div className="px-4 py-3 flex items-center gap-3" style={{ background: `${color}12` }}>
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-extrabold text-white shrink-0"
                style={{ background: color }}
              >
                {i + 1}
              </div>
              <p className="text-sm font-bold leading-tight" style={{ color }}>{area.title}</p>
            </div>

            {/* Body */}
            <div className="bg-white px-4 py-3 space-y-2">
              {area.description && (
                <p className="text-xs text-gray-600 leading-relaxed">{area.description}</p>
              )}
              {area.bullets.map((b, j) => (
                <div key={j} className="flex items-start gap-2">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0" style={{ background: color }} />
                  <p className="text-xs text-gray-600 leading-relaxed">{b}</p>
                </div>
              ))}
              {!area.description && !area.bullets.length && (
                <p className="text-xs text-gray-300">No details.</p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
