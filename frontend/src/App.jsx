import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { LayoutDashboard, Inbox, AlertTriangle, Zap } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import CaseInbox from './pages/CaseInbox'
import CaseDetail from './pages/CaseDetail'
import { getDisputes } from './api'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/cases', label: 'Case Inbox', icon: Inbox },
  { to: '/disputes', label: 'Disputes', icon: AlertTriangle },
]

function Sidebar() {
  return (
    <aside
      className="w-64 shrink-0 flex flex-col border-r"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)', minHeight: '100vh' }}
    >
      {/* Logo */}
      <div
        className="px-5 py-5 border-b flex items-center gap-3"
        style={{ borderColor: 'var(--border)' }}
      >
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <div>
          <p className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
            PayOps Copilot
          </p>
          <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>AI Operations Platform</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <p className="px-4 py-2 text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
          Navigation
        </p>
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            id={`nav-${label.toLowerCase().replace(/\s+/g, '-')}`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t" style={{ borderColor: 'var(--border)' }}>
        <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
          Powered by Claude · Razorpay
        </p>
      </div>
    </aside>
  )
}

function DisputesPage() {
  const [disputes, setDisputes] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDisputes().then(setDisputes).finally(() => setLoading(false))
  }, [])

  const formatDate = (d) =>
    d ? new Date(d).toLocaleString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-gradient mb-1">Open Disputes</h1>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Chargebacks sorted by respond-by deadline (soonest first)
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40">
          <div className="w-7 h-7 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
        </div>
      ) : disputes.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="font-medium mb-1" style={{ color: 'var(--text-primary)' }}>No open disputes</p>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>All chargebacks are resolved.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {disputes.map((d) => {
            const urgent = d.hours_until_deadline != null && d.hours_until_deadline < 24
            const warning = d.hours_until_deadline != null && d.hours_until_deadline < 48
            return (
              <div
                key={d.id}
                className={`card p-5 border ${urgent ? 'border-red-500/40' : warning ? 'border-orange-500/30' : ''}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-mono text-xs font-bold" style={{ color: 'var(--text-muted)' }}>
                        {d.id}
                      </span>
                      {urgent && (
                        <span className="badge bg-red-500/20 text-red-300 border border-red-500/40 animate-pulse">
                          <AlertTriangle className="w-3 h-3" /> CRITICAL
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                      {d.reason_description || d.reason_code || 'No description'}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      Payment: {d.payment_id} · Amount: ₹{(d.amount_paise / 100).toFixed(2)}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Respond by</p>
                    <p className={`text-sm font-mono font-bold ${urgent ? 'text-red-400' : warning ? 'text-orange-400' : ''}`} style={!urgent && !warning ? { color: 'var(--text-primary)' } : {}}>
                      {formatDate(d.respond_by)}
                    </p>
                    {d.hours_until_deadline != null && (
                      <p className={`text-xs mt-0.5 ${urgent ? 'text-red-400 font-bold' : 'text-slate-400'}`}>
                        {d.hours_until_deadline.toFixed(0)}h remaining
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8 overflow-auto" style={{ background: 'var(--bg-primary)' }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/cases" element={<CaseInbox />} />
            <Route path="/cases/:id" element={<CaseDetail />} />
            <Route path="/disputes" element={<DisputesPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
