export interface TableData { headers: string[]; rows: string[][] }

/** Parse any markdown pipe-table into headers + rows */
export function parseMarkdownTable(content: string): TableData | null {
  const lines = content.split('\n').filter(l => l.trim().startsWith('|'))
  if (lines.length < 2) return null

  let headers: string[] = []
  const rows: string[][] = []

  for (const line of lines) {
    if (line.replace(/\|/g, '').trim().match(/^[-: ]+$/)) continue
    const cells = line.split('|').map(c => c.trim()).filter(Boolean)
    if (!cells.length) continue
    if (!headers.length) { headers = cells; continue }
    rows.push(cells)
  }

  if (!headers.length || !rows.length) return null
  return { headers, rows }
}

interface StyledTableProps {
  headers: string[]
  rows: string[][]
  /** Optional render override for a cell: (value, rowIndex, colIndex) => ReactNode */
  renderCell?: (value: string, rowIdx: number, colIdx: number) => React.ReactNode
  /** Optional CSS grid column template, e.g. "2fr 1fr 1fr auto" */
  colTemplate?: string
}

export default function StyledTable({ headers, rows, renderCell, colTemplate }: StyledTableProps) {
  const cols = headers.length
  const template = colTemplate ?? `repeat(${cols}, minmax(0, 1fr))`

  return (
    <div className="rounded-xl overflow-hidden border border-zepto-muted shadow-sm">
      {/* Header */}
      <div
        className="grid px-4 py-2.5 gap-4"
        style={{ gridTemplateColumns: template, background: '#1A0533' }}
      >
        {headers.map((h, i) => (
          <span key={i} className="text-[10px] font-bold text-white/50 uppercase tracking-widest truncate">
            {h}
          </span>
        ))}
      </div>

      {/* Rows */}
      {rows.map((row, ri) => (
        <div
          key={ri}
          className="grid px-4 py-3 gap-4 border-t border-zepto-muted items-center transition-colors hover:bg-zepto-tint/40"
          style={{
            gridTemplateColumns: template,
            background: ri % 2 === 0 ? '#ffffff' : '#FAF8FF',
          }}
        >
          {headers.map((_, ci) => {
            const value = row[ci] ?? '—'
            return (
              <div key={ci} className="min-w-0">
                {renderCell
                  ? renderCell(value, ri, ci)
                  : (
                    <span className={`text-xs truncate block ${ci === 0 ? 'font-semibold text-zepto-dark' : 'text-gray-500'}`}>
                      {value}
                    </span>
                  )
                }
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
