import { useState, useEffect } from 'react'
import { getDashboard } from '../api'
import { AlertTriangle, CheckCircle2, Clock, Brain, TrendingUp } from 'lucide-react'

const CASE_TYPE_COLORS = {
  AMOUNT_MISMATCH: 'bg-purple-500',
  MISSING_SETTLEMENT: 'bg-blue-500',
  DUPLICATE_REFUND: 'bg-red-500',
  CHARGEBACK_RISK: 'bg-orange-500',
}

const CASE_TYPE_LABELS = {
  AMOUNT_MISMATCH: 'Amount Mismatch',
  MISSING_SETTLEMENT: 'Missing Settlement',
  DUPLICATE_REFUND: 'Duplicate Refund',
  CHARGEBACK_RISK: 'Chargeback Risk',
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch(() => setError('Failed to load dashboard'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
          <p style={{ color: 'var(--text-muted)' }} className="text-sm">Loading dashboard…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
        <p className="text-red-400">{error}</p>
      </div>
    )
  }

  const maxCount = data?.cases_by_type
    ? Math.max(...Object.values(data.cases_by_type), 1)
    : 1

  const statCards = [
    {
      label: 'Open Cases',
      value: data?.open_cases ?? 0,
      icon: AlertTriangle,
      color: 'text-blue-400',
      accent: 'from-blue-500/20 to-blue-600/5',
      border: 'border-blue-500/20',
    },
    {
      label: 'Pending Approval',
      value: data?.pending_approval ?? 0,
      icon: Clock,
      color: 'text-yellow-400',
      accent: 'from-yellow-500/20 to-yellow-600/5',
      border: 'border-yellow-500/20',
    },
    {
      label: 'Disputes Due <24h',
      value: data?.disputes_due_24h ?? 0,
      icon: AlertTriangle,
      color: (data?.disputes_due_24h ?? 0) > 0 ? 'text-red-400' : 'text-slate-400',
      accent:
        (data?.disputes_due_24h ?? 0) > 0
          ? 'from-red-500/20 to-red-600/5'
          : 'from-slate-500/10 to-slate-600/5',
      border:
        (data?.disputes_due_24h ?? 0) > 0 ? 'border-red-500/30' : 'border-slate-500/20',
      urgent: (data?.disputes_due_24h ?? 0) > 0,
    },
    {
      label: 'Avg AI Confidence',
      value:
        data?.avg_confidence != null
          ? `${(data.avg_confidence * 100).toFixed(0)}%`
          : 'N/A',
      icon: Brain,
      color: 'text-emerald-400',
      accent: 'from-emerald-500/20 to-emerald-600/5',
      border: 'border-emerald-500/20',
    },
  ]

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gradient mb-1">Operations Dashboard</h1>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Real-time overview of reconciliation health and dispute exposure
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => {
          const Icon = card.icon
          return (
            <div
              key={card.label}
              className={`card p-5 bg-gradient-to-br ${card.accent} border ${card.border} ${
                card.urgent ? 'animate-pulse-soft' : ''
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <span className="stat-label">{card.label}</span>
                <Icon className={`w-4 h-4 ${card.color}`} />
              </div>
              <p className={`text-3xl font-bold font-mono ${card.color}`}>{card.value}</p>
            </div>
          )
        })}
      </div>

      {/* Resolution Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-6">
          <div className="section-title flex items-center gap-2">
            <TrendingUp className="w-3.5 h-3.5" />
            Today's Resolution Activity
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)' }}>
              <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Auto-Resolved</p>
              <p className="text-2xl font-bold text-brand-400">{data?.auto_resolved_today ?? 0}</p>
            </div>
            <div className="p-4 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)' }}>
              <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Manually Resolved</p>
              <p className="text-2xl font-bold text-emerald-400">{data?.manually_resolved_today ?? 0}</p>
            </div>
          </div>
        </div>

        {/* Cases by Type */}
        <div className="card p-6">
          <div className="section-title">Cases by Type</div>
          <div className="space-y-3">
            {Object.entries(data?.cases_by_type || {}).map(([type, count]) => (
              <div key={type}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                    {CASE_TYPE_LABELS[type] || type}
                  </span>
                  <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
                    {count}
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                  <div
                    className={`h-full rounded-full ${CASE_TYPE_COLORS[type] || 'bg-slate-500'} opacity-80 transition-all duration-700`}
                    style={{ width: maxCount > 0 ? `${(count / maxCount) * 100}%` : '0%' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
