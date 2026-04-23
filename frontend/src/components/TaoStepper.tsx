import type { TaoStep } from '../types'

export default function TaoStepper({ steps }: { steps: TaoStep[] }) {
  if (!steps.length) return null

  return (
    <div className="bg-white rounded-xl border border-zepto-muted px-4 py-3 space-y-0 my-2">
      <p className="text-[10px] font-bold uppercase tracking-[1.5px] text-gray-400 mb-2">⚡ On it…</p>
      {steps.map((step, i) => (
        <div
          key={step.id}
          className="flex items-start gap-3 relative"
          style={{ paddingLeft: '18px', paddingBottom: i < steps.length - 1 ? '10px' : '0' }}
        >
          {/* vertical connector */}
          {i < steps.length - 1 && (
            <div
              className="absolute left-[7px] top-[14px] w-[2px]"
              style={{ background: `${step.color}30`, bottom: 0 }}
            />
          )}
          {/* dot */}
          <div
            className="absolute left-[3px] top-[5px] w-2 h-2 rounded-full shrink-0"
            style={{ background: step.color, boxShadow: `0 0 0 3px ${step.color}20` }}
          />
          <div>
            <p className="text-xs font-bold leading-none" style={{ color: step.color }}>
              {step.icon} {step.label}
            </p>
            <p className="text-[11px] text-gray-400 mt-0.5">{step.detail}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
