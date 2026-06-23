import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCases, analyzeCase } from '../api'
import PriorityBadge from '../components/PriorityBadge'
import CaseTypeBadge from '../components/CaseTypeBadge'
import { RefreshCw, Zap, AlertCircle, ChevronRight } from 'lucide-react'

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleString('en-IN', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function formatAmount(paise) {
  if (!paise) return '—'
  return `₹${(paise / 100).toFixed(2)}`
}

function StatusBadge({ status }) {
  const cfg = {
    open: { label: 'Open', cls: 'bg-blue-500/15 text-blue-300 border-blue-500/30' },
    pending_approval: { label: 'Pending Approval', cls: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30' },
    manually_resolved: { label: 'Resolved', cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
    auto_resolved: { label: 'Auto-resolved', cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  }[status] || { label: status, cls: 'bg-slate-500/15 text-slate-300 border-slate-500/30' }
  return <span className={`badge border ${cfg.cls}`}>{cfg.label}</span>
}

export default function CaseInbox() {
  const [cases, setCases] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [analyzingIds, setAnalyzingIds] = useState(new Set())
  const navigate = useNavigate()
  const intervalRef = useRef(null)

  const loadCases = useCallback(() => {
    getCases({ status: 'open', limit: 50 })
      .then((data) => {
        setCases(data.items || [])
        setError(null)
      })
      .catch(() => setError('Failed to load cases'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadCases()
    intervalRef.current = setInterval(loadCases, 30_000)
    return () => clearInterval(intervalRef.current)
  }, [loadCases])

  const handleAnalyze = async (e, caseId) => {
    e.stopPropagation()
    setAnalyzingIds((prev) => new Set([...prev, caseId]))
    try {
      const updated = await analyzeCase(caseId)
      setCases((prev) => prev.map((c) => (c.id === caseId ? { ...c, ...updated } : c)))
    } catch (err) {
      console.error('Analysis failed', err)
    } finally {
      setAnalyzingIds((prev) => {
        const next = new Set(prev)
        next.delete(caseId)
        return next
      })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient mb-1">Case Inbox</h1>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {cases.length} open case{cases.length !== 1 ? 's' : ''} · auto-refreshes every 30s
          </p>
        </div>
        <button id="btn-refresh-cases" onClick={loadCases} className="btn-ghost">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="card p-4 border-red-500/30 flex items-center gap-3">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {cases.length === 0 && !error && (
        <div className="card p-12 text-center">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
            <Zap className="w-6 h-6 text-emerald-400" />
          </div>
          <p className="font-medium mb-1" style={{ color: 'var(--text-primary)' }}>All clear!</p>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No open cases right now.</p>
        </div>
      )}

      {cases.length > 0 && (
        <div className="card overflow-hidden">
          {/* Table header */}
          <div
            className="grid gap-3 px-5 py-3 text-[11px] font-semibold uppercase tracking-wider"
            style={{
              gridTemplateColumns: '100px 160px 120px 110px 130px 140px 120px',
              borderBottom: '1px solid var(--border)',
              color: 'var(--text-muted)',
            }}
          >
            <span>Priority</span>
            <span>Type</span>
            <span>Merchant</span>
            <span>Amount</span>
            <span>Status</span>
            <span>Created</span>
            <span>Action</span>
          </div>

          {/* Rows */}
          <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
            {cases.map((c) => {
              const isAnalyzing = analyzingIds.has(c.id)
              return (
                <div
                  key={c.id}
                  id={`case-row-${c.id}`}
                  className="grid gap-3 px-5 py-4 items-center table-row-hover cursor-pointer"
                  style={{ gridTemplateColumns: '100px 160px 120px 110px 130px 140px 120px' }}
                  onClick={() => navigate(`/cases/${c.id}`)}
                >
                  <PriorityBadge score={c.priority_score} />
                  <CaseTypeBadge type={c.case_type} />
                  <span className="text-sm font-mono truncate" style={{ color: 'var(--text-secondary)' }}>
                    {c.merchant_id}
                  </span>
                  <span className="text-sm font-mono font-medium" style={{ color: 'var(--text-primary)' }}>
                    {formatAmount(c.discrepancy_paise)}
                  </span>
                  <StatusBadge status={c.status} />
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {formatDate(c.created_at)}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      id={`btn-analyze-${c.id}`}
                      disabled={isAnalyzing || c.status !== 'open'}
                      onClick={(e) => handleAnalyze(e, c.id)}
                      className={`btn-primary py-1.5 px-3 text-xs ${
                        c.status !== 'open' ? 'opacity-40 cursor-not-allowed' : ''
                      }`}
                    >
                      {isAnalyzing ? (
                        <>
                          <span className="spinner w-3 h-3" />
                          Running…
                        </>
                      ) : (
                        <>
                          <Zap className="w-3 h-3" />
                          Analyze
                        </>
                      )}
                    </button>
                    <ChevronRight className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
