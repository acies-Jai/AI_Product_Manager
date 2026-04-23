import { useStore } from '../store'

export default function Hero() {
  const chunksIndexed = useStore(s => s.chunksIndexed)

  return (
    <div
      className="rounded-2xl px-8 py-7 flex items-center justify-between"
      style={{ background: 'linear-gradient(135deg, #5E17EB 0%, #7C3AED 60%, #9F67FA 100%)' }}
    >
      <div>
        <p className="text-[11px] font-semibold tracking-[2px] uppercase text-white/60 mb-1">
          ⚡ Zepto — Insights on Demand
        </p>
        <h1 className="text-2xl font-extrabold text-white leading-tight">
          Product Manager Assistant
        </h1>
        <p className="text-sm text-white/60 mt-1.5">
          Charter: Customer App &amp; Checkout Experience
        </p>
      </div>
      <div className="text-right flex flex-col gap-2 items-end shrink-0">
        <div className="bg-white/15 rounded-full px-4 py-1.5 text-white text-xs font-semibold">
          🗄️ {chunksIndexed} sources live
        </div>
        <p className="text-white/40 text-[10px] font-medium tracking-wide">
          Insights delivered in seconds
        </p>
      </div>
    </div>
  )
}
