export default function PriorityBadge({ score }) {
  const getConfig = () => {
    if (score >= 80) return { label: 'P1 CRITICAL', bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/40', dot: 'bg-red-400' }
    if (score >= 60) return { label: 'P2 HIGH', bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/40', dot: 'bg-orange-400' }
    if (score >= 40) return { label: 'P3 MEDIUM', bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/40', dot: 'bg-yellow-400' }
    return { label: 'P4 LOW', bg: 'bg-slate-500/20', text: 'text-slate-400', border: 'border-slate-500/40', dot: 'bg-slate-400' }
  }

  const { label, bg, text, border, dot } = getConfig()

  return (
    <span className={`badge ${bg} ${text} border ${border} gap-1.5`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot} ${score >= 80 ? 'animate-pulse' : ''}`} />
      {label}
      <span className="ml-0.5 opacity-60 text-[10px]">{score}</span>
    </span>
  )
}
