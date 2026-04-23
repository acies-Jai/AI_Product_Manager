import { useStore } from '../store'

export default function PendingWriteCard() {
  const { pendingWrite, confirmWrite } = useStore()
  if (!pendingWrite) return null

  const isDelete = pendingWrite.tool === 'propose_delete_file'
  const accent = isDelete ? '#EF4444' : '#F59E0B'
  const bg = isDelete ? '#FEF2F2' : '#FFFBEB'
  const title = isDelete ? '⚠️ Pending File Deletion' : '⏳ Pending File Change'
  const body = isDelete
    ? 'This action is irreversible. Confirm only if certain.'
    : 'Nothing is written until you confirm.'

  const preview = pendingWrite.tool === 'propose_update_section'
    ? `Update section "## ${pendingWrite.args.heading}" in ${pendingWrite.args.filename}.md`
    : pendingWrite.tool === 'propose_create_file'
    ? `Create new file: ${pendingWrite.args.filename}.md`
    : `Delete file: ${pendingWrite.args.filename}.md`

  return (
    <div className="mx-4 mb-2 rounded-xl border overflow-hidden" style={{ borderColor: `${accent}40` }}>
      <div className="px-4 py-3 flex items-start gap-3" style={{ background: bg, borderLeft: `4px solid ${accent}` }}>
        <div className="flex-1">
          <p className="text-sm font-bold" style={{ color: accent }}>{title}</p>
          <p className="text-xs text-gray-500 mt-0.5">{body}</p>
          <p className="text-xs font-medium text-gray-700 mt-1.5 bg-white/60 rounded-lg px-2 py-1">
            {preview}
          </p>
        </div>
      </div>
      <div className="flex border-t" style={{ borderColor: `${accent}20` }}>
        <button
          onClick={() => confirmWrite(true)}
          className="flex-1 py-2.5 text-sm font-semibold text-white transition-colors"
          style={{ background: accent }}
        >
          ✅ Confirm
        </button>
        <button
          onClick={() => confirmWrite(false)}
          className="flex-1 py-2.5 text-sm font-medium text-gray-600 bg-white hover:bg-gray-50 transition-colors border-l"
          style={{ borderColor: `${accent}20` }}
        >
          ❌ Cancel
        </button>
      </div>
    </div>
  )
}
