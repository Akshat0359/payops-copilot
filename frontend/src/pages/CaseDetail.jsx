import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCase, analyzeCase, approveCase, rejectCase } from '../api'
import PriorityBadge from '../components/PriorityBadge'
import CaseTypeBadge from '../components/CaseTypeBadge'
import ConfidenceBar from '../components/ConfidenceBar'
import AuditLog from '../components/AuditLog'
import {
  ArrowLeft, Zap, CheckCircle2, XCircle, CreditCard,
  Clock, AlertTriangle, Building2, Hash,
} from 'lucide-react'

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('en-IN', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatAmount(paise) {
  if (!paise && paise !== 0) return '—'
  return `₹${(paise / 100).toFixed(2)}`
}

function Toast({ message, type, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3000)
    return () => clearTimeout(t)
  }, [onClose])

  return (
    <div className={type === 'success' ? 'toast-success' : 'toast-error'}>
      {type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
      {message}
    </div>
  )
}

function Modal({ title, placeholder, confirmLabel, confirmClass, onConfirm, onClose }) {
  const [text, setText] = useState('')
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
          {title}
        </h3>
        <textarea
          id="modal-textarea"
          className="input-field h-28 resize-none mb-4"
          placeholder={placeholder}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="flex gap-3 justify-end">
          <button id="modal-cancel" onClick={onClose} className="btn-ghost">Cancel</button>
          <button
            id="modal-confirm"
            onClick={() => onConfirm(text)}
            className={confirmClass}
            disabled={!text.trim()}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

function PaymentCard({ payment }) {
  if (!payment) return null
  const fields = [
    { icon: Hash, label: 'Payment ID', value: payment.id },
    { icon: CreditCard, label: 'Amount', value: formatAmount(payment.amount_paise) },
    { icon: CreditCard, label: 'Method', value: payment.method || '—' },
    { icon: Building2, label: 'Bank', value: payment.bank || '—' },
    { icon: CheckCircle2, label: 'Status', value: payment.status },
    { icon: Clock, label: 'Created', value: formatDate(payment.created_at) },
  ]
  return (
    <div className="space-y-2">
      {fields.map(({ icon: Icon, label, value }) => (
        <div
          key={label}
          className="flex items-center justify-between py-2 px-3 rounded-lg"
          style={{ background: 'rgba(255,255,255,0.03)' }}
        >
          <div className="flex items-center gap-2">
            <Icon className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</span>
          </div>
          <span className="text-xs font-mono font-medium truncate max-w-[160px]" style={{ color: 'var(--text-primary)' }}>
            {value}
          </span>
        </div>
      ))}
    </div>
  )
}

function ChargebackCard({ chargeback }) {
  if (!chargeback) return null
  const urgent = chargeback.hours_until_deadline != null && chargeback.hours_until_deadline < 24
  return (
    <div className={`rounded-lg p-4 space-y-2 border ${urgent ? 'border-red-500/40 bg-red-500/5' : 'border-orange-500/20 bg-orange-500/5'}`}>
      {urgent && (
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-4 h-4 text-red-400 animate-pulse" />
          <span className="text-xs font-bold text-red-400">
            DEADLINE CRITICAL — {chargeback.hours_until_deadline?.toFixed(0)}h remaining
          </span>
        </div>
      )}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <p style={{ color: 'var(--text-muted)' }}>Reason Code</p>
          <p className="font-mono font-medium mt-0.5" style={{ color: 'var(--text-primary)' }}>{chargeback.reason_code || '—'}</p>
        </div>
        <div>
          <p style={{ color: 'var(--text-muted)' }}>Amount</p>
          <p className="font-mono font-medium mt-0.5" style={{ color: 'var(--text-primary)' }}>{formatAmount(chargeback.amount_paise)}</p>
        </div>
        <div className="col-span-2">
          <p style={{ color: 'var(--text-muted)' }}>Description</p>
          <p className="font-medium mt-0.5" style={{ color: 'var(--text-primary)' }}>{chargeback.reason_description || '—'}</p>
        </div>
        <div>
          <p style={{ color: 'var(--text-muted)' }}>Respond By</p>
          <p className="font-mono font-medium mt-0.5" style={{ color: urgent ? '#f87171' : 'var(--text-primary)' }}>
            {formatDate(chargeback.respond_by)}
          </p>
        </div>
      </div>
    </div>
  )
}

export default function CaseDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [caseData, setCaseData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [modal, setModal] = useState(null) // 'approve' | 'reject' | null
  const [toast, setToast] = useState(null)

  useEffect(() => {
    setLoading(true)
    getCase(id).then(setCaseData).finally(() => setLoading(false))
  }, [id])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const updated = await analyzeCase(id)
      setCaseData(updated)
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Analysis failed. Check GEMINI_API_KEY in backend/.env'
      setToast({ message: msg, type: 'error' })
    } finally {
      setAnalyzing(false)
    }
  }

  const handleApprove = async (note) => {
    const updated = await approveCase(id, note)
    setCaseData(updated)
    setModal(null)
    setToast({ message: 'Case approved and resolved!', type: 'success' })
    setTimeout(() => navigate('/cases'), 1500)
  }

  const handleReject = async (reason) => {
    const updated = await rejectCase(id, reason)
    setCaseData(updated)
    setModal(null)
    setToast({ message: 'Analysis rejected. Case reopened.', type: 'error' })
    setTimeout(() => navigate('/cases'), 1500)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
      </div>
    )
  }

  if (!caseData) return null

  const hasAnalysis = !!caseData.ai_root_cause

  const resolutionSteps = caseData.ai_resolution_steps
    ? caseData.ai_resolution_steps.split('\n').filter((l) => l.trim())
    : []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Breadcrumb + Title */}
      <div>
        <button
          id="btn-back"
          onClick={() => navigate('/cases')}
          className="flex items-center gap-1.5 text-sm mb-4 transition-colors"
          style={{ color: 'var(--text-muted)' }}
          onMouseOver={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
          onMouseOut={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
        >
          <ArrowLeft className="w-4 h-4" /> Back to Cases
        </button>

        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
            Case #{caseData.id}
          </h1>
          <PriorityBadge score={caseData.priority_score} />
          <CaseTypeBadge type={caseData.case_type} />
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* LEFT — 40% */}
        <div className="lg:col-span-2 space-y-5">
          {/* Payment Details */}
          <div className="card p-5">
            <div className="section-title flex items-center gap-2">
              <CreditCard className="w-3.5 h-3.5" /> Payment Details
            </div>
            <PaymentCard payment={caseData.payment} />
          </div>

          {/* Chargeback (if any) */}
          {caseData.chargeback && (
            <div className="card p-5">
              <div className="section-title flex items-center gap-2">
                <AlertTriangle className="w-3.5 h-3.5" /> Chargeback Details
              </div>
              <ChargebackCard chargeback={caseData.chargeback} />
            </div>
          )}

          {/* Audit Log */}
          <div className="card p-5">
            <div className="section-title">Audit Trail</div>
            <AuditLog entries={caseData.audit_log || []} />
          </div>
        </div>

        {/* RIGHT — 60% */}
        <div className="lg:col-span-3 space-y-5">
          {/* AI Analysis */}
          <div className="card p-6">
            <div className="section-title flex items-center gap-2">
              <Zap className="w-3.5 h-3.5" /> AI Analysis
            </div>

            {!hasAnalysis ? (
              <div className="text-center py-8">
                <div className="w-14 h-14 rounded-full bg-brand-500/10 flex items-center justify-center mx-auto mb-4">
                  <Zap className="w-7 h-7 text-brand-400" />
                </div>
                <p className="font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                  Not yet analyzed
                </p>
                <p className="text-sm mb-5" style={{ color: 'var(--text-muted)' }}>
                  Run the AI agent to get root cause and resolution steps
                </p>
                <button
                  id="btn-run-analysis"
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="btn-primary mx-auto"
                >
                  {analyzing ? (
                    <><span className="spinner" /> Analyzing…</>
                  ) : (
                    <><Zap className="w-4 h-4" /> Run Analysis</>
                  )}
                </button>
              </div>
            ) : (
              <div className="space-y-5">
                {/* Root Cause */}
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                    Root Cause
                  </p>
                  <div className="root-cause-box">
                    <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                      {caseData.ai_root_cause}
                    </p>
                  </div>
                </div>

                {/* Resolution Steps */}
                {resolutionSteps.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                      Resolution Steps
                    </p>
                    <ol className="space-y-2">
                      {resolutionSteps.map((step, i) => (
                        <li key={i} className="flex gap-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
                          <span
                            className="shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold mt-0.5"
                            style={{ background: 'rgba(99,102,241,0.2)', color: '#a5bafb' }}
                          >
                            {i + 1}
                          </span>
                          <span className="leading-relaxed">{step.replace(/^\d+\.\s*/, '')}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Confidence Bar */}
                <ConfidenceBar value={caseData.ai_confidence || 0} />

                {/* HITL Actions */}
                {caseData.status === 'pending_approval' && (
                  <div className="flex gap-3 pt-2 border-t" style={{ borderColor: 'var(--border)' }}>
                    <button
                      id="btn-approve"
                      onClick={() => setModal('approve')}
                      className="btn-success flex-1 justify-center"
                    >
                      <CheckCircle2 className="w-4 h-4" /> Approve
                    </button>
                    <button
                      id="btn-reject"
                      onClick={() => setModal('reject')}
                      className="btn-danger flex-1 justify-center"
                    >
                      <XCircle className="w-4 h-4" /> Reject
                    </button>
                  </div>
                )}

                {/* Re-analyze button for open cases */}
                {caseData.status === 'open' && (
                  <button
                    id="btn-reanalyze"
                    onClick={handleAnalyze}
                    disabled={analyzing}
                    className="btn-primary w-full justify-center"
                  >
                    {analyzing ? <><span className="spinner" /> Analyzing…</> : <><Zap className="w-4 h-4" /> Re-analyze</>}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      {modal === 'approve' && (
        <Modal
          title="Approve Resolution"
          placeholder="Add a note about this resolution decision…"
          confirmLabel="Approve & Resolve"
          confirmClass="btn-success"
          onConfirm={handleApprove}
          onClose={() => setModal(null)}
        />
      )}
      {modal === 'reject' && (
        <Modal
          title="Reject AI Analysis"
          placeholder="Why is this analysis incorrect or incomplete?"
          confirmLabel="Reject Analysis"
          confirmClass="btn-danger"
          onConfirm={handleReject}
          onClose={() => setModal(null)}
        />
      )}

      {/* Toast */}
      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  )
}
