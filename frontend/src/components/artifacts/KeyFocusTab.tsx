interface FocusArea { title: string; bullets: string[] }

const CARD_COLORS = ['#5E17EB', '#10B981', '#F59E0B', '#0EA5E9', '#EC4899', '#F97316']

function parseFocusAreas(content: string): FocusArea[] {
  const areas: FocusArea[] = []
  const lines = content.split('\n')
  let current: FocusArea | null = null

  for (const raw of lines) {
    const line = raw.trim()
    if (line.startsWith('## ')) {
      if (current) areas.push(current)
      current = { title: line.replace(/^##\s*/, '').replace(/^\d+\.\s*/, ''), bullets: [] }
    } else if (line.startsWith('### ')) {
      if (current) areas.push(current)
      current = { title: line.replace(/^###\s*/, '').replace(/^\d+\.\s*/, ''), bullets: [] }
    } else if ((line.startsWith('- ') || line.startsWith('* ') || line.match(/^\d+\.\s/)) && current) {
      const bullet = line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '').trim()
      if (bullet) current.bullets.push(bullet)
    } else if (line && current && !line.startsWith('#')) {
      // plain paragraph text — treat as a bullet if no bullets yet
      if (current.bullets.length === 0) current.bullets.push(line)
    }
  }
  if (current) areas.push(current)
  return areas.filter(a => a.title)
}

import StyledTable, { parseMarkdownTable } from './StyledTable'

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
          <div
            key={i}
            className="rounded-xl border overflow-hidden"
            style={{ borderColor: `${color}30` }}
          >
            {/* header strip */}
            <div
              className="px-4 py-3 flex items-center gap-2"
              style={{ background: `${color}12` }}
            >
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-extrabold text-white shrink-0"
                style={{ background: color }}
              >
                {i + 1}
              </div>
              <p className="text-sm font-bold leading-tight" style={{ color }}>{area.title}</p>
            </div>

            {/* bullets */}
            <div className="bg-white px-4 py-3 space-y-2">
              {area.bullets.length === 0 ? (
                <p className="text-xs text-gray-300">No details provided.</p>
              ) : (
                area.bullets.map((b, j) => (
                  <div key={j} className="flex items-start gap-2">
                    <span
                      className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ background: color }}
                    />
                    <p className="text-xs text-gray-600 leading-relaxed">{b}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
