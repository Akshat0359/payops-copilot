const TYPE_CONFIG = {
  AMOUNT_MISMATCH: { label: 'Amount Mismatch', bg: 'bg-purple-500/15', text: 'text-purple-300', border: 'border-purple-500/30' },
  MISSING_SETTLEMENT: { label: 'Missing Settlement', bg: 'bg-blue-500/15', text: 'text-blue-300', border: 'border-blue-500/30' },
  DUPLICATE_REFUND: { label: 'Duplicate Refund', bg: 'bg-red-500/15', text: 'text-red-300', border: 'border-red-500/30' },
  CHARGEBACK_RISK: { label: 'Chargeback Risk', bg: 'bg-orange-500/15', text: 'text-orange-300', border: 'border-orange-500/30' },
}

export default function CaseTypeBadge({ type }) {
  const config = TYPE_CONFIG[type] || { label: type, bg: 'bg-slate-500/15', text: 'text-slate-300', border: 'border-slate-500/30' }
  return (
    <span className={`badge ${config.bg} ${config.text} border ${config.border}`}>
      {config.label}
    </span>
  )
}
