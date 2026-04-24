import { X } from 'lucide-react'
import { useStore } from '../store'

const TYPE_CONFIG = {
  success: { bar: '#10B981', icon: '✅', bg: '#ECFDF5', border: '#A7F3D0' },
  error:   { bar: '#EF4444', icon: '❌', bg: '#FEF2F2', border: '#FCA5A5' },
  info:    { bar: '#5E17EB', icon: '📧', bg: '#F4F0FC', border: '#C4B5FD' },
}

export default function NotificationToast() {
  const { toasts, removeToast } = useStore()
  if (!toasts.length) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-72">
      {toasts.map(t => {
        const cfg = TYPE_CONFIG[t.type]
        return (
          <div
            key={t.id}
            className="rounded-xl overflow-hidden shadow-lg border animate-in slide-in-from-right-4 duration-200"
            style={{ background: cfg.bg, borderColor: cfg.border }}
          >
            <div className="h-0.5" style={{ background: cfg.bar }} />
            <div className="flex items-start gap-3 px-4 py-3">
              <span className="text-base shrink-0 mt-0.5">{cfg.icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-zepto-dark leading-snug">{t.title}</p>
                {t.body && (
                  <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed truncate">{t.body}</p>
                )}
              </div>
              <button
                onClick={() => removeToast(t.id)}
                className="shrink-0 text-gray-400 hover:text-gray-600 transition-colors mt-0.5"
              >
                <X size={13} />
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
