export default function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100)

  const getColor = () => {
    if (value < 0.5) return 'from-red-500 to-red-400'
    if (value < 0.75) return 'from-yellow-500 to-amber-400'
    return 'from-emerald-500 to-green-400'
  }

  const getTextColor = () => {
    if (value < 0.5) return 'text-red-400'
    if (value < 0.75) return 'text-yellow-400'
    return 'text-emerald-400'
  }

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          AI Confidence
        </span>
        <span className={`text-xs font-bold font-mono ${getTextColor()}`}>
          {pct}%
        </span>
      </div>
      <div
        className="w-full h-2 rounded-full overflow-hidden"
        style={{ background: 'rgba(255,255,255,0.06)' }}
      >
        <div
          className={`h-full rounded-full bg-gradient-to-r ${getColor()} transition-all duration-700 ease-out`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
