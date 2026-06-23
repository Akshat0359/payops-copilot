function formatTime(dateStr) {
  return new Date(dateStr).toLocaleString('en-IN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function AuditLog({ entries }) {
  if (!entries || entries.length === 0) {
    return (
      <p className="text-xs italic py-3 text-center" style={{ color: 'var(--text-muted)' }}>
        No audit activity yet
      </p>
    )
  }

  return (
    <div className="scrollable space-y-2 pr-1">
      {entries.map((entry) => (
        <div
          key={entry.id}
          className="flex items-start gap-3 py-2 px-3 rounded-lg"
          style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}
        >
          {/* Actor badge */}
          {entry.actor_type === 'agent' ? (
            <span className="badge bg-blue-500/20 text-blue-300 border border-blue-500/30 shrink-0 text-[10px] mt-0.5">
              AGENT
            </span>
          ) : (
            <span className="badge bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shrink-0 text-[10px] mt-0.5">
              HUMAN
            </span>
          )}

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium capitalize" style={{ color: 'var(--text-primary)' }}>
                {entry.action.replace(/_/g, ' ')}
              </span>
              <span className="text-[10px] shrink-0 font-mono" style={{ color: 'var(--text-muted)' }}>
                {formatTime(entry.created_at)}
              </span>
            </div>
            {entry.reasoning && (
              <p className="text-[11px] mt-0.5 truncate" style={{ color: 'var(--text-secondary)' }}>
                {entry.reasoning}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
