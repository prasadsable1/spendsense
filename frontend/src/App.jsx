import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import {
  Activity, ArrowDownLeft, ArrowLeft, ArrowRight, ArrowUpRight, BarChart3, Bell, CalendarDays,
  Check, ChevronDown, ChevronLeft, ChevronRight, CircleHelp, CreditCard, Database, Download,
  FileDown, FileSpreadsheet, Filter, LayoutDashboard, Lightbulb, LoaderCircle, Menu, MoreHorizontal,
  Plus, Search, Settings as SettingsIcon, ShieldAlert, Sparkles, Target, Trash2, TrendingDown,
  TrendingUp, Upload, Wallet, X, Utensils, Plane, ShoppingBag, Receipt, GraduationCap, HeartPulse,
  Clapperboard, House, Carrot, CircleEllipsis, BriefcaseBusiness, Zap,
} from 'lucide-react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import api, { apiDocsUrl, errorMessage } from './api.js'

const isPublicDemo = import.meta.env.VITE_PUBLIC_DEMO === 'true'
const money = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(value || 0))
const today = new Date()
const currentYear = today.getFullYear()
const currentMonth = today.getMonth() + 1
const monthName = (month) => new Date(2026, month - 1, 1).toLocaleString('en', { month: 'long' })
const categoryIcons = { Food: Utensils, Travel: Plane, Shopping: ShoppingBag, Bills: Receipt, Education: GraduationCap, Healthcare: HeartPulse, Entertainment: Clapperboard, Rent: House, Groceries: Carrot, Other: CircleEllipsis }
const navGroups = [
  { title: 'OVERVIEW', items: [{ to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard }, { to: '/transactions', label: 'Transactions', icon: CreditCard }, { to: '/analytics', label: 'Analytics', icon: BarChart3 }] },
  { title: 'MANAGE', items: [{ to: '/add-expense', label: 'Add expense', icon: Plus }, { to: '/import', label: 'Import CSV', icon: FileSpreadsheet }, { to: '/categories', label: 'Categories', icon: Wallet }, { to: '/budgets', label: 'Monthly budgets', icon: Target }] },
  { title: 'INTELLIGENCE', items: [{ to: '/predictions', label: 'ML predictions', icon: Sparkles }, { to: '/unusual', label: 'Unusual expenses', icon: ShieldAlert }, { to: '/reports', label: 'Reports', icon: FileDown }] },
]

function useApiData(path, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: '' })
  const refresh = useCallback(async () => {
    setState((old) => ({ ...old, loading: true, error: '' }))
    try { setState({ data: (await api.get(path)).data, loading: false, error: '' }) }
    catch (error) { setState({ data: null, loading: false, error: errorMessage(error) }) }
  // Path and explicitly supplied dependencies define the request identity.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps])
  useEffect(() => { refresh() }, [refresh])
  return { ...state, refresh }
}

function PageTitle({ eyebrow, title, subtitle, action }) {
  return <div className="page-title"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{action}</div>
}

function Notice({ children, kind = 'error', onClose }) {
  if (!children) return null
  return <div className={`notice ${kind}`} role="status">{children}{onClose && <button className="icon-button" onClick={onClose} aria-label="Dismiss"><X size={15} /></button>}</div>
}

function EnvironmentBadge() {
  return <span className="local-badge"><span /> {isPublicDemo ? 'PUBLIC DEMO' : 'LOCAL & PRIVATE'}</span>
}

function Loading({ label = 'Loading your financial data…' }) {
  return <div className="loading"><LoaderCircle className="spin" size={22} />{label}</div>
}

function LoginScreen({ onLogin }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const { data } = await api.post('/auth/login', { password })
      sessionStorage.setItem('spendsense_token', data.access_token)
      onLogin()
    } catch (loginError) {
      setError(errorMessage(loginError))
    } finally {
      setBusy(false)
      setPassword('')
    }
  }
  return <main className="login-screen"><form className="card login-card" onSubmit={submit}><Link to="/" className="brand"><span className="brand-mark"><Activity size={19} /></span><span>spend<span className="brand-accent">sense</span><small>PERSONAL FINANCE</small></span></Link><h1>Your finances, protected.</h1><p>Enter your SpendSense password to continue.</p><Notice>{error}</Notice><label className="field-label">Password<input className="field-input" type="password" autoComplete="current-password" required maxLength={1024} value={password} onChange={(event) => setPassword(event.target.value)} autoFocus /></label><button className="button primary full-button" disabled={busy}>{busy ? <LoaderCircle className="spin" size={15} /> : <ShieldAlert size={15} />} Sign in</button><div className="login-privacy"><ShieldAlert size={14} /> Your financial data is private to your account.</div></form></main>
}

function AuthGate({ children }) {
  const [auth, setAuth] = useState({ loading: true, required: false, authenticated: false })
  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get('/auth/status')
      if (!data.required) {
        setAuth({ loading: false, required: false, authenticated: true })
        return
      }
      if (!sessionStorage.getItem('spendsense_token')) {
        setAuth({ loading: false, required: true, authenticated: false })
        return
      }
      await api.get('/auth/me')
      setAuth({ loading: false, required: true, authenticated: true })
    } catch {
      sessionStorage.removeItem('spendsense_token')
      setAuth({ loading: false, required: true, authenticated: false })
    }
  }, [])
  useEffect(() => {
    refresh()
    const expire = () => setAuth({ loading: false, required: true, authenticated: false })
    window.addEventListener('spendsense:auth-required', expire)
    return () => window.removeEventListener('spendsense:auth-required', expire)
  }, [refresh])
  if (auth.loading) return <Loading label="Checking your secure session…" />
  if (auth.required && !auth.authenticated) return <LoginScreen onLogin={() => setAuth({ loading: false, required: true, authenticated: true })} />
  return children
}

function Empty({ title, text, action }) {
  return <div className="empty"><span className="empty-icon"><Activity size={21} /></span><strong>{title}</strong><p>{text}</p>{action}</div>
}

function StatCard({ label, value, note, icon: Icon, tone = 'blue', trend }) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span><span className={`stat-icon ${tone}`}><Icon size={18} /></span></div><strong className="stat-value">{value}</strong><div className="stat-note">{trend && <span className={trend > 0 ? 'negative' : 'positive'}>{trend > 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}{Math.abs(trend)}%</span>}{note}</div></div>
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return <div className="chart-tooltip"><strong>{label}</strong>{payload.map((item) => <div key={item.dataKey} className="tooltip-line"><i style={{ background: item.color }} />{item.name}: {money(item.value)}</div>)}</div>
}

function Layout() {
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const title = navGroups.flatMap((group) => group.items).find((item) => location.pathname.startsWith(item.to))?.label || (location.pathname === '/settings' ? 'Settings' : 'Dashboard')
  const signOut = () => {
    sessionStorage.removeItem('spendsense_token')
    window.dispatchEvent(new Event('spendsense:auth-required'))
  }
  return <div className="app-shell">
    <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
      <Link to="/dashboard" className="brand"><span className="brand-mark"><Activity size={19} /></span><span>spend<span className="brand-accent">sense</span><small>PERSONAL FINANCE</small></span></Link>
      <div className="profile-card"><div className="avatar">S</div><div><strong>My finances</strong><small>Personal workspace</small></div><ChevronDown size={15} className="muted" /></div>
      <nav className="side-nav">{navGroups.map((group) => <div className="nav-group" key={group.title}><div className="nav-label">{group.title}</div>{group.items.map(({ to, label, icon: Icon }) => <NavLink onClick={() => setMobileOpen(false)} to={to} key={to} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Icon size={17} /><span>{label}</span>{label === 'Unusual expenses' && <span className="nav-dot" />}</NavLink>)}</div>)}</nav>
      <div className="sidebar-bottom"><div className="upgrade-card"><span className="upgrade-icon"><Sparkles size={16} /></span><strong>Clarity, every day.</strong><p>Your finances. Your data. Your decisions.</p><Link to="/analytics">Explore insights <ArrowRight size={13} /></Link></div><NavLink to="/settings" className={({ isActive }) => `nav-link settings-link ${isActive ? 'active' : ''}`}><SettingsIcon size={17} /><span>Settings</span></NavLink><div className="sidebar-foot">SpendSense v1.0 · {isPublicDemo ? 'Public demo' : 'Local workspace'}</div></div>
    </aside>
    {mobileOpen && <button className="mobile-backdrop" onClick={() => setMobileOpen(false)} aria-label="Close menu" />}
    <main className="main-panel"><header className="topbar"><button className="icon-button mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open menu"><Menu size={19} /></button><div className="breadcrumb">Workspace <span>/</span> <strong>{title}</strong></div><div className="topbar-right"><EnvironmentBadge />{sessionStorage.getItem('spendsense_token') && <button className="icon-button" title="Sign out" aria-label="Sign out" onClick={signOut}><ShieldAlert size={18} /></button>}<button className="icon-button" title="Help"><CircleHelp size={18} /></button><span className="avatar small">S</span></div></header><div className="page-content"><Outlet /></div></main>
  </div>
}

function PeriodPicker({ year, month, onChange }) {
  const change = (delta) => { const date = new Date(year, month - 1 + delta, 1); onChange(date.getFullYear(), date.getMonth() + 1) }
  return <div className="period-picker"><button className="icon-button" onClick={() => change(-1)} aria-label="Previous month"><ChevronLeft size={17} /></button><span>{monthName(month)} {year}</span><button className="icon-button" onClick={() => change(1)} aria-label="Next month"><ChevronRight size={17} /></button></div>
}

function Dashboard() {
  const [period, setPeriod] = useState({ year: currentYear, month: currentMonth })
  const { data, loading, error } = useApiData(`/dashboard?year=${period.year}&month=${period.month}`, [period.year, period.month])
  return <>
    <PageTitle eyebrow="YOUR FINANCIAL OVERVIEW" title="Good to see you." subtitle="Here's what's happening with your money." action={<PeriodPicker {...period} onChange={(year, month) => setPeriod({ year, month })} />} />
    <Notice>{error}</Notice>
    {loading ? <Loading /> : data && <>
      <div className="stat-grid">
        <StatCard label="Total expenses" value={money(data.total_expenses)} icon={ArrowUpRight} tone="violet" note={`${monthName(data.month)} spending`} />
        <StatCard label="Total income" value={money(data.total_income)} icon={ArrowDownLeft} tone="green" note="Recorded this month" />
        <StatCard label="Remaining budget" value={data.remaining_budget == null ? '—' : money(data.remaining_budget)} icon={Target} tone="amber" note={data.budgets.length ? 'Across your active budgets' : 'Set a budget to track'} />
        <StatCard label="Daily average" value={money(data.daily_average)} icon={Zap} tone="blue" note="Average per day" />
      </div>
      <div className="dashboard-grid">
        <section className="card chart-card"><div className="card-heading"><div><h2>Spending overview</h2><p>Your monthly expenses over time</p></div><button className="subtle-tag"><CalendarDays size={13} /> Last 6 months</button></div>
          <div className="chart-area">{data.monthly_trend.some((item) => item.amount > 0) ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={data.monthly_trend} margin={{ top: 10, right: 9, left: -14, bottom: 0 }}><defs><linearGradient id="spendFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7488ff" stopOpacity={0.28} /><stop offset="100%" stopColor="#7488ff" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#272b39" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="month" tickFormatter={(value) => value.slice(5)} tickLine={false} axisLine={false} tick={{ fill: '#858a9d', fontSize: 11 }} /><YAxis tickFormatter={(value) => `$${value}`} tickLine={false} axisLine={false} tick={{ fill: '#858a9d', fontSize: 11 }} /><Tooltip content={<ChartTooltip />} /><Area type="monotone" dataKey="amount" name="Expenses" stroke="#8595ff" strokeWidth={2.5} fill="url(#spendFill)" /></AreaChart></ResponsiveContainer> : <Empty title="Your spending story starts here" text="Add a transaction to see your monthly trend." action={<Link className="text-link" to="/add-expense">Add an expense <ArrowRight size={14} /></Link>} />}</div>
        </section>
        <section className="card category-card"><div className="card-heading"><div><h2>Where it goes</h2><p>Spending by category</p></div><Link to="/analytics" className="icon-button" aria-label="View analytics"><ArrowRight size={17} /></Link></div>
          {data.categories.length ? <><div className="donut-wrap"><ResponsiveContainer width="100%" height={194}><PieChart><Pie data={data.categories} dataKey="amount" nameKey="name" innerRadius={61} outerRadius={84} paddingAngle={4} stroke="none">{data.categories.map((row, i) => <Cell key={row.name} fill={['#8794ff', '#be87f2', '#54c9a5', '#efa965', '#ef8392', '#5db9d2'][i % 6]} />)}</Pie><Tooltip content={<ChartTooltip />} /></PieChart></ResponsiveContainer><div className="donut-center"><strong>{money(data.total_expenses)}</strong><small>Total spent</small></div></div><div className="category-legend">{data.categories.slice(0, 4).map((row, i) => <div className="legend-row" key={row.name}><span><i style={{ background: ['#8794ff', '#be87f2', '#54c9a5', '#efa965'][i] }} />{row.name}</span><strong>{money(row.amount)}</strong></div>)}</div></> : <Empty title="No categories yet" text="Your category breakdown will appear after you add expenses." />}
        </section>
        <section className="card transactions-card"><div className="card-heading"><div><h2>Recent transactions</h2><p>Your latest money movements</p></div><Link to="/transactions" className="text-link">View all <ArrowRight size={14} /></Link></div>
          {data.recent_transactions.length ? <TransactionTable rows={data.recent_transactions.slice(0, 5)} compact /> : <Empty title="No transactions yet" text="Add your first expense to get started." action={<Link className="text-link" to="/add-expense">Add transaction <ArrowRight size={14} /></Link>} />}
        </section>
        <section className="card budget-card"><div className="card-heading"><div><h2>Budget check-in</h2><p>A little awareness goes a long way</p></div><Link className="icon-button" to="/budgets" aria-label="View budgets"><ArrowRight size={17} /></Link></div>
          {data.budgets.length ? <div className="budget-list">{data.budgets.slice(0, 4).map((budget) => <BudgetProgress key={budget.id} budget={budget} />)}</div> : <Empty title="Make a plan for your money" text="Create a monthly budget to keep your goals in sight." action={<Link className="text-link" to="/budgets">Set a budget <ArrowRight size={14} /></Link>} />}
        </section>
      </div>
    </>}
  </>
}

function BudgetProgress({ budget, onDelete }) {
  const percent = Math.min(100, budget.percent_used)
  const status = budget.status
  return <div className="budget-progress"><div className="budget-progress-top"><div><strong>{budget.category_name || 'Overall budget'}</strong><small>{money(budget.spent)} <span>of {money(budget.amount)}</span></small></div><span className={`budget-pct ${status}`}>{budget.percent_used}%</span></div><div className="progress-track"><div className={`progress-fill ${status}`} style={{ width: `${percent}%` }} /></div><div className="budget-progress-bottom"><span className={status === 'exceeded' ? 'negative' : status === 'warning' ? 'warning-text' : ''}>{status === 'exceeded' ? 'Over budget' : status === 'warning' ? 'Near your limit' : `${money(Math.max(0, budget.remaining))} remaining`}</span>{onDelete && <button className="icon-button danger-quiet" onClick={onDelete} aria-label="Delete budget"><Trash2 size={14} /></button>}</div></div>
}

const paymentIcons = { Card: CreditCard, Cash: Wallet, Transfer: ArrowDownLeft }
function TransactionTable({ rows, compact = false, onEdit, onDelete }) {
  return <div className="table-scroll"><table className="data-table"><thead><tr><th>Transaction</th><th>Category</th><th>Date</th><th>Payment</th><th className="align-right">Amount</th>{(onEdit || onDelete) && <th />}</tr></thead><tbody>{rows.map((row) => {
    const Icon = categoryIcons[row.category?.name] || categoryIcons.Other
    const category = row.category?.name || row.category || 'Other'
    const PaymentIcon = paymentIcons[row.payment_method] || CreditCard
    return <tr key={row.id}><td><div className="transaction-name"><span className="category-icon"><Icon size={15} /></span><div><strong>{row.description}</strong><small>{row.merchant || category}</small></div></div></td><td><span className="category-pill">{category}</span></td><td className="date-cell">{new Date(`${row.date}T12:00:00`).toLocaleDateString('en', { month: 'short', day: 'numeric', year: 'numeric' })}</td><td className="payment-cell"><PaymentIcon size={14} /> {row.payment_method}</td><td className={`align-right amount-cell ${row.type === 'income' ? 'income' : ''}`}>{row.type === 'income' ? '+' : '−'}{money(row.amount)}</td>{(onEdit || onDelete) && <td className="row-actions">{onEdit && <button className="icon-button" onClick={() => onEdit(row)} title="Edit"><MoreHorizontal size={17} /></button>}{onDelete && <button className="icon-button danger-quiet" onClick={() => onDelete(row)} title="Delete"><Trash2 size={15} /></button>}</td>}</tr>
  })}</tbody></table></div>
}

function Transactions() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState({ category_id: '', type: '' })
  const [offset, setOffset] = useState(0)
  const [sort, setSort] = useState('date')
  const [sortOrder, setSortOrder] = useState('desc')
  const [categories, setCategories] = useState([])
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null)
  const pageSize = 10
  const refresh = useCallback(async () => {
    setBusy(true); setError('')
    try {
      const params = new URLSearchParams({ offset, limit: pageSize, sort, order: sortOrder })
      if (search.trim()) params.set('search', search.trim())
      if (filter.category_id) params.set('category_id', filter.category_id)
      if (filter.type) params.set('type', filter.type)
      const countParams = new URLSearchParams()
      if (search.trim()) countParams.set('search', search.trim())
      if (filter.category_id) countParams.set('category_id', filter.category_id)
      if (filter.type) countParams.set('type', filter.type)
      const [tx, cats, count] = await Promise.all([api.get(`/transactions?${params}`), api.get('/categories'), api.get(`/transactions/count?${countParams}`)])
      setRows(tx.data); setCategories(cats.data); setTotal(count.data.count)
    } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) }
  }, [offset, sort, sortOrder, search, filter])
  useEffect(() => { refresh() }, [refresh])
  const remove = async (row) => {
    if (!window.confirm(`Delete "${row.description}"? This cannot be undone.`)) return
    try { await api.delete(`/transactions/${row.id}`); refresh() } catch (e) { setError(errorMessage(e)) }
  }
  const exportUrl = `${api.defaults.baseURL}/reports/export`
  return <>
    <PageTitle eyebrow="YOUR MONEY, IN MOTION" title="Transactions" subtitle="Every transaction, all in one place." action={<Link className="button primary" to="/add-expense"><Plus size={16} /> Add expense</Link>} />
    <Notice>{error}</Notice>
    <section className="card table-card"><div className="table-toolbar"><div className="search-field"><Search size={16} /><input placeholder="Search transactions…" value={search} onChange={(e) => { setSearch(e.target.value); setOffset(0) }} /></div><div className="filter-tools"><label className="select-wrap"><Filter size={15} /><select value={filter.category_id} onChange={(e) => { setFilter({ ...filter, category_id: e.target.value }); setOffset(0) }}><option value="">All categories</option>{categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}</select></label><select className="filter-select" value={filter.type} onChange={(e) => { setFilter({ ...filter, type: e.target.value }); setOffset(0) }}><option value="">All types</option><option value="expense">Expenses</option><option value="income">Income</option></select><select className="filter-select" value={sort} onChange={(e) => setSort(e.target.value)}><option value="date">Date</option><option value="amount">Amount</option><option value="description">Description</option></select><button className="icon-button" title="Download CSV" onClick={() => window.open(exportUrl, '_blank')}><Download size={17} /></button></div></div>
      {busy ? <Loading /> : rows.length ? <TransactionTable rows={rows} onEdit={setEditing} onDelete={remove} /> : <Empty title="Nothing to see here yet" text="Try changing your filters or add your first transaction." action={<Link className="text-link" to="/add-expense">Add transaction <ArrowRight size={14} /></Link>} />}
      <div className="pagination"><span>Showing {rows.length ? offset + 1 : 0}–{offset + rows.length} of {total} transactions</span><div><button className="icon-button" disabled={offset === 0 || busy} onClick={() => setOffset(Math.max(0, offset - pageSize))} aria-label="Previous page"><ChevronLeft size={16} /></button><button className="icon-button" disabled={offset + rows.length >= total || busy} onClick={() => setOffset(offset + pageSize)} aria-label="Next page"><ChevronRight size={16} /></button></div></div>
    </section>
    {editing && <TransactionModal categories={categories} transaction={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); refresh() }} />}
  </>
}

function TransactionForm({ categories, initial, onSave, onCancel, saving, compact = false }) {
  const [form, setForm] = useState(initial || { date: today.toISOString().slice(0, 10), amount: '', type: 'expense', description: '', merchant: '', payment_method: 'Card', category_id: categories[0]?.id || '' })
  const [error, setError] = useState('')
  useEffect(() => { if (!initial && !form.category_id && categories.length) setForm((value) => ({ ...value, category_id: categories[0].id })) }, [categories, initial, form.category_id])
  const update = (key, value) => setForm((valueNow) => ({ ...valueNow, [key]: value }))
  const submit = async (event) => {
    event.preventDefault(); setError('')
    try {
      await onSave({ ...form, amount: Number(form.amount), category_id: Number(form.category_id) })
    } catch (e) { setError(errorMessage(e)) }
  }
  return <form className={`transaction-form ${compact ? 'compact-form' : ''}`} onSubmit={submit}>
    <Notice>{error}</Notice>
    <div className="type-switch"><button type="button" className={form.type === 'expense' ? 'selected expense' : ''} onClick={() => update('type', 'expense')}><ArrowUpRight size={15} /> Expense</button><button type="button" className={form.type === 'income' ? 'selected income' : ''} onClick={() => update('type', 'income')}><ArrowDownLeft size={15} /> Income</button></div>
    <label className="field-label">Amount <div className="amount-input"><span>$</span><input type="number" step="0.01" min="0.01" required placeholder="0.00" value={form.amount} onChange={(e) => update('amount', e.target.value)} /></div></label>
    <div className="form-grid"><label className="field-label">Date<input className="field-input" type="date" required value={form.date} onChange={(e) => update('date', e.target.value)} /></label><label className="field-label">Category<select className="field-input" required value={form.category_id} onChange={(e) => update('category_id', e.target.value)}><option value="">Choose category</option>{categories.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label></div>
    <label className="field-label">Description<input className="field-input" required maxLength={240} placeholder="What was this for?" value={form.description} onChange={(e) => update('description', e.target.value)} /></label>
    <div className="form-grid"><label className="field-label">Merchant <span className="optional">Optional</span><input className="field-input" maxLength={120} placeholder="Store or business" value={form.merchant} onChange={(e) => update('merchant', e.target.value)} /></label><label className="field-label">Payment method<select className="field-input" value={form.payment_method} onChange={(e) => update('payment_method', e.target.value)}>{['Card', 'Cash', 'Transfer', 'Other'].map((v) => <option key={v}>{v}</option>)}</select></label></div>
    <div className="form-actions"><button type="button" className="button secondary" onClick={onCancel}>Cancel</button><button className="button primary" disabled={saving || !categories.length}>{saving ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />}{initial ? 'Save changes' : 'Save transaction'}</button></div>
  </form>
}

function TransactionModal({ categories, transaction, onClose, onSaved }) {
  const [saving, setSaving] = useState(false)
  const save = async (payload) => {
    setSaving(true)
    try { await api.put(`/transactions/${transaction.id}`, payload); onSaved() } finally { setSaving(false) }
  }
  return <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><div className="modal-card"><div className="modal-heading"><div><h2>Edit transaction</h2><p>Update your transaction details.</p></div><button className="icon-button" onClick={onClose}><X size={18} /></button></div><TransactionForm categories={categories} initial={{ ...transaction, category_id: transaction.category.id, date: transaction.date }} onSave={save} onCancel={onClose} saving={saving} compact /></div></div>
}

function AddExpense() {
  const navigate = useNavigate()
  const [categories, setCategories] = useState([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => { api.get('/categories').then(({ data }) => setCategories(data)).catch((e) => setError(errorMessage(e))) }, [])
  const save = async (payload) => {
    setSaving(true)
    try { await api.post('/transactions', payload); navigate('/transactions', { state: { saved: true } }) }
    catch (e) { throw e } finally { setSaving(false) }
  }
  return <><PageTitle eyebrow="CAPTURE THE DETAILS" title="Add a transaction" subtitle="Small details make your financial picture clearer." /><Notice>{error}</Notice><div className="form-layout"><section className="card form-card"><div className="card-heading"><div><h2>Transaction details</h2><p>Enter the details exactly as they happened.</p></div></div><TransactionForm categories={categories} onSave={save} onCancel={() => navigate('/transactions')} saving={saving} /></section><aside className="form-aside"><div className="insight-card"><span className="insight-orb"><Lightbulb size={19} /></span><h3>A little context goes a long way</h3><p>A clear description and merchant name make it easier to find transactions and understand your habits later.</p></div><div className="privacy-note"><ShieldAlert size={16} /><span><strong>{isPublicDemo ? 'Public demo data.' : 'Your data stays yours.'}</strong><br />{isPublicDemo ? 'Anyone with the link can see and change these records. Use sample data only.' : 'Transactions are stored in your local MySQL database.'}</span></div></aside></div></>
}

const mapFields = ['date', 'description', 'amount', 'debit', 'credit', 'type', 'merchant', 'category']
function ImportCsv() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [mapping, setMapping] = useState({})
  const [categoryId, setCategoryId] = useState('')
  const [categories, setCategories] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [summary, setSummary] = useState(null)
  const [dragging, setDragging] = useState(false)
  useEffect(() => { api.get('/categories').then(({ data }) => setCategories(data)).catch((e) => setError(errorMessage(e))) }, [])
  const loadFile = async (nextFile) => {
    if (!nextFile) return
    setFile(nextFile); setSummary(null); setError('')
    if (!nextFile.name.toLowerCase().endsWith('.csv')) { setError('Choose a CSV file.'); return }
    if (nextFile.size > 5 * 1024 * 1024) { setError('CSV files are limited to 5 MB.'); return }
    const body = new FormData(); body.append('file', nextFile)
    setBusy(true)
    try { const { data } = await api.post('/imports/preview', body); setPreview(data); setMapping(data.suggested_mapping) }
    catch (e) { setError(errorMessage(e)); setPreview(null) } finally { setBusy(false) }
  }
  const confirm = async () => {
    if (!file) return
    setBusy(true); setError('')
    const body = new FormData(); body.append('file', file); body.append('mapping', JSON.stringify(mapping))
    if (categoryId) body.append('category_id', categoryId)
    try { const { data } = await api.post('/imports/confirm', body); setSummary(data); setPreview(null); setFile(null) }
    catch (e) { setError(errorMessage(e)) } finally { setBusy(false) }
  }
  return <>
    <PageTitle eyebrow="BRING YOUR DATA TOGETHER" title="Import transactions" subtitle="Import a CSV export from your bank. No bank credentials needed." />
    <Notice>{error}</Notice>
    <div className="import-layout"><section className="card import-card"><div className="card-heading"><div><h2>Upload a CSV file</h2><p>Your file is checked before any transactions are imported.</p></div><span className="step-count">STEP 01</span></div>
      <label className={`drop-zone ${dragging ? 'dragging' : ''}`} onDragOver={(e) => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(e) => { e.preventDefault(); setDragging(false); loadFile(e.dataTransfer.files[0]) }}><input type="file" accept=".csv,text/csv" onChange={(e) => loadFile(e.target.files[0])} /><span className="upload-icon"><Upload size={19} /></span><strong>{file ? file.name : 'Drop your CSV file here'}</strong><p>{file ? `${(file.size / 1024).toFixed(1)} KB · ${preview?.row_count || 0} transactions` : 'or click to browse your files'}</p><small>CSV format · Max 5 MB · Up to 10,000 rows</small></label>
      {busy && <Loading label="Reading your CSV…" />}
      {summary && <div className="import-success"><span><Check size={19} /></span><div><strong>Import complete</strong><p>{summary.imported} imported · {summary.duplicates} duplicate{summary.duplicates === 1 ? '' : 's'} skipped · {summary.total_rows} rows checked</p></div><Link className="text-link" to="/transactions">View transactions <ArrowRight size={14} /></Link></div>}
      {preview && <div className="mapping-section"><div className="mapping-heading"><span className="step-count">STEP 02</span><div><h3>Match your columns</h3><p>We made a best guess. Review every field before importing.</p></div></div><div className="mapping-grid">{mapFields.map((field) => <label className="field-label" key={field}>{field.charAt(0).toUpperCase() + field.slice(1)}{['date', 'description'].includes(field) && <span className="required-mark"> *</span>}<select className="field-input" value={mapping[field] || ''} onChange={(e) => setMapping({ ...mapping, [field]: e.target.value || null })}><option value="">Not mapped</option>{preview.columns.map((column) => <option key={column} value={column}>{column}</option>)}</select></label>)}</div><label className="field-label fallback-category">Fallback category <span className="optional">Used if the CSV category is blank or unrecognized</span><select className="field-input" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}><option value="">Use “Other”</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <div className="preview-table-wrap"><div className="preview-label">PREVIEW · FIRST {preview.preview.length} OF {preview.row_count} ROWS</div><div className="table-scroll"><table className="data-table preview-table"><thead><tr>{preview.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{preview.preview.map((row, index) => <tr key={index}>{preview.columns.map((column) => <td key={column}>{row[column]}</td>)}</tr>)}</tbody></table></div></div><button className="button primary" disabled={busy || !mapping.date || !mapping.description || (!mapping.amount && !mapping.debit && !mapping.credit)} onClick={confirm}><Check size={15} /> Confirm import</button>
      </div>}
    </section><aside className="import-aside"><div className="card tips-card"><div className="tips-icon"><FileSpreadsheet size={19} /></div><h3>Every bank is different</h3><p>SpendSense lets you match columns before importing, so your bank’s format does not have to match ours.</p><div className="tips-list"><span><Check size={14} /> Date, description & amount</span><span><Check size={14} /> Debit and credit columns</span><span><Check size={14} /> Optional merchant & category</span><span><Check size={14} /> Duplicate transactions skipped</span></div></div><div className="privacy-note"><ShieldAlert size={16} /><span><strong>Private by design</strong><br />CSV files are parsed in memory, never saved to disk, and are not sent to any external service.</span></div></aside></div>
  </>
}

function Categories() {
  const { data: categories, loading, error, refresh } = useApiData('/categories')
  const [form, setForm] = useState({ name: '', color: '#7186ff' })
  const [notice, setNotice] = useState('')
  const [working, setWorking] = useState(false)
  const add = async (e) => { e.preventDefault(); setNotice(''); setWorking(true); try { await api.post('/categories', form); setForm({ name: '', color: '#7186ff' }); refresh() } catch (err) { setNotice(errorMessage(err)) } finally { setWorking(false) } }
  const remove = async (category) => { if (!window.confirm(`Delete ${category.name}?`)) return; setNotice(''); try { await api.delete(`/categories/${category.id}`); refresh() } catch (e) { setNotice(errorMessage(e)) } }
  return <><PageTitle eyebrow="ORGANIZE YOUR SPENDING" title="Categories" subtitle="Give every transaction a place to belong." /><Notice>{error || notice}</Notice><div className="categories-layout"><section className="card category-list-card"><div className="card-heading"><div><h2>Your categories</h2><p>Default and custom categories</p></div><span className="count-pill">{categories?.length || 0}</span></div>{loading ? <Loading /> : categories?.length ? <div className="categories-list">{categories.map((category) => { const Icon = categoryIcons[category.name] || CircleEllipsis; return <div className="category-row" key={category.id}><span className="category-icon large" style={{ color: category.color, background: `${category.color}20` }}><Icon size={17} /></span><strong>{category.name}</strong><span className="category-default">{['Food','Travel','Shopping','Bills','Education','Healthcare','Entertainment','Rent','Groceries','Other'].includes(category.name) ? 'DEFAULT' : 'CUSTOM'}</span><button className="icon-button danger-quiet" onClick={() => remove(category)} title="Delete category"><Trash2 size={15} /></button></div> })}</div> : <Empty title="Categories unavailable" text="Could not load categories." />}</section><section className="card add-category-card"><div className="card-heading"><div><h2>Create a category</h2><p>Make it personal to the way you spend.</p></div></div><form onSubmit={add}><label className="field-label">Category name<input className="field-input" maxLength={60} required placeholder="e.g. Pet care" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label><label className="field-label">Category color<div className="color-control"><input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} /><span>{form.color.toUpperCase()}</span></div></label><button className="button primary full-button" disabled={working}><Plus size={15} /> Create category</button></form></section></div></>
}

function Budgets() {
  const [period, setPeriod] = useState({ year: currentYear, month: currentMonth })
  const [items, setItems] = useState([])
  const [categories, setCategories] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ category_id: '', amount: '' })
  const [saving, setSaving] = useState(false)
  const refresh = useCallback(async () => {
    setLoading(true)
    try { const [budgets, cats] = await Promise.all([api.get(`/budgets?year=${period.year}&month=${period.month}`), api.get('/categories')]); setItems(budgets.data); setCategories(cats.data); setError('') }
    catch (e) { setError(errorMessage(e)) } finally { setLoading(false) }
  }, [period])
  useEffect(() => { refresh() }, [refresh])
  const save = async (e) => { e.preventDefault(); setSaving(true); setError(''); try { await api.post('/budgets', { ...period, amount: Number(form.amount), category_id: form.category_id ? Number(form.category_id) : null }); setForm({ category_id: '', amount: '' }); refresh() } catch (err) { setError(errorMessage(err)) } finally { setSaving(false) } }
  const remove = async (budget) => { if (!window.confirm('Delete this monthly budget?')) return; try { await api.delete(`/budgets/${budget.id}`); refresh() } catch (e) { setError(errorMessage(e)) } }
  const overall = items.find((item) => item.category_id == null)
  const allocation = overall ? [overall] : items
  const total = allocation.reduce((sum, item) => sum + Number(item.amount), 0)
  const spent = allocation.reduce((sum, item) => sum + Number(item.spent), 0)
  return <><PageTitle eyebrow="INTENTIONAL SPENDING" title="Monthly budgets" subtitle="A plan is not a restriction. It's a way to make room for what matters." action={<PeriodPicker {...period} onChange={(year, month) => setPeriod({ year, month })} />} /><Notice>{error}</Notice><div className="budget-summary-grid"><StatCard label="Budgeted" value={money(total)} icon={Target} tone="blue" note={`${items.length} active budget${items.length === 1 ? '' : 's'}`} /><StatCard label="Spent so far" value={money(spent)} icon={CreditCard} tone="violet" note={`In ${monthName(period.month)}`} /><StatCard label="Left to spend" value={money(total - spent)} icon={Wallet} tone="green" note={total ? `${Math.max(0, Math.round((total - spent) / total * 100))}% of budget left` : 'Add a budget to start'} /></div><div className="budget-layout"><section className="card budget-list-card"><div className="card-heading"><div><h2>Budget health</h2><p>{monthName(period.month)} {period.year}</p></div></div>{loading ? <Loading /> : items.length ? <div className="budget-list expanded">{items.map((item) => <div key={item.id} className="budget-item"><BudgetProgress budget={item} onDelete={() => remove(item)} /></div>)}</div> : <Empty title="Start with one simple goal" text="Set an overall limit or a goal for one category." />}</section><section className="card add-budget-card"><div className="card-heading"><div><h2>Set a budget</h2><p>Choose an overall or category limit.</p></div></div><form onSubmit={save}><label className="field-label">Budget type<select className="field-input" value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}><option value="">Overall monthly budget</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="field-label">Monthly limit<div className="amount-input compact-amount"><span>$</span><input type="number" min="0.01" step="0.01" required placeholder="0.00" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></div></label><div className="budget-date-note"><CalendarDays size={15} /> Applies to {monthName(period.month)} {period.year}</div><button className="button primary full-button" disabled={saving}><Plus size={15} /> Save budget</button></form></section></div></>
}

function Analytics() {
  const { data, loading, error } = useApiData('/analytics')
  const { data: dashboard, loading: dashLoading } = useApiData(`/dashboard?year=${currentYear}&month=${currentMonth}`, [currentYear, currentMonth])
  return <><PageTitle eyebrow="PATTERNS, MADE VISIBLE" title="Spending analytics" subtitle="A clearer picture of where your money is going." /><Notice>{error}</Notice>{loading || dashLoading ? <Loading /> : data && <><div className="stat-grid analytics-stats"><StatCard label="Total expenses" value={money(data.total_expenses)} icon={ArrowUpRight} tone="violet" note="Across all recorded time" /><StatCard label="Average daily spend" value={money(data.average_daily_spending)} icon={Activity} tone="blue" note="On days with transactions" /><StatCard label="Median transaction" value={money(data.median_transaction)} icon={CreditCard} tone="amber" note="Typical expense size" /><StatCard label="Savings estimate" value={money(data.savings_estimate)} icon={Wallet} tone="green" note="Income minus expenses" /></div><div className="analytics-grid"><section className="card analytics-chart-card"><div className="card-heading"><div><h2>Monthly spending</h2><p>Actual expenses recorded each month</p></div></div>{data.monthly.length ? <div className="large-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.monthly} margin={{ top: 12, right: 8, left: -12, bottom: 0 }}><CartesianGrid stroke="#272b39" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="month" tickFormatter={(v) => v.slice(2)} tickLine={false} axisLine={false} tick={{ fill: '#858a9d', fontSize: 10 }} /><YAxis tickFormatter={(v) => `$${v}`} tickLine={false} axisLine={false} tick={{ fill: '#858a9d', fontSize: 10 }} /><Tooltip content={<ChartTooltip />} /><Bar dataKey="amount" name="Expenses" fill="#8794ff" radius={[4, 4, 0, 0]} maxBarSize={32} /></BarChart></ResponsiveContainer></div> : <Empty title="Not enough history yet" text="Add transactions to see your monthly spending." />}</section><section className="card analytics-category-card"><div className="card-heading"><div><h2>Category breakdown</h2><p>All recorded expenses</p></div></div>{data.categories.length ? <div className="analytics-category-list">{data.categories.map((item, index) => <div className="analytics-category" key={item.category}><div className="analytics-cat-top"><span><i style={{ background: ['#8794ff', '#be87f2', '#54c9a5', '#efa965', '#ef8392'][index % 5] }} />{item.category}</span><strong>{money(item.amount)}</strong></div><div className="progress-track"><div className="progress-fill" style={{ width: `${data.total_expenses ? item.amount / data.total_expenses * 100 : 0}%`, background: ['#8794ff', '#be87f2', '#54c9a5', '#efa965', '#ef8392'][index % 5] }} /></div></div>)}</div> : <Empty title="No category data yet" text="Your category breakdown will appear once expenses are recorded." />}</section><section className="card comparison-card"><div className="card-heading"><div><h2>Month-to-month changes</h2><p>How spending shifts over time</p></div></div>{data.comparisons.length ? <div className="comparison-list">{data.comparisons.slice(-6).reverse().map((item) => <div className="comparison-row" key={item.month}><div><strong>{item.month}</strong><small>vs. {item.previous_month}</small></div><strong>{money(item.amount)}</strong><span className={item.change > 0 ? 'negative' : 'positive'}>{item.change > 0 ? '+' : ''}{money(item.change)}{item.change_percent != null ? ` (${item.change_percent > 0 ? '+' : ''}${item.change_percent}%)` : ''}</span></div>)}</div> : <Empty title="One month at a time" text="Month-to-month comparisons appear after you have transactions in multiple months." />}</section><section className="card weekly-card"><div className="card-heading"><div><h2>Weekly rhythm</h2><p>Your spending by week</p></div></div>{data.weekly.length ? <div className="weekly-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.weekly.slice(-8)}><CartesianGrid stroke="#272b39" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="week" tickFormatter={(v) => v.slice(5)} tickLine={false} axisLine={false} tick={{ fill: '#858a9d', fontSize: 10 }} /><YAxis tickFormatter={(v) => `$${v}`} tickLine={false} axisLine={false} tick={{ fill: '#858a9d', fontSize: 10 }} /><Tooltip content={<ChartTooltip />} /><Area type="monotone" dataKey="amount" name="Expenses" stroke="#56c9a3" fill="#56c9a322" /></AreaChart></ResponsiveContainer></div> : <Empty title="Weekly view needs more data" text="Weekly spending appears when transactions are available." />}</section></div></>}</>
}

function Predictions() {
  const { data, loading, error } = useApiData('/predictions')
  return <><PageTitle eyebrow="A THOUGHTFUL LOOK AHEAD" title="Spending forecast" subtitle="A simple model, grounded in your own transaction history." /><Notice>{error}</Notice>{loading ? <Loading /> : data && (data.available ? <><div className="forecast-hero"><div className="forecast-copy"><span className="forecast-badge"><Sparkles size={13} /> LINEAR REGRESSION</span><p>Estimated spending for {data.next_month}</p><strong>{money(data.predicted_spending)}</strong><small>{data.explanation}</small></div><div className="forecast-orbit"><div className="orbit-ring ring-one" /><div className="orbit-ring ring-two" /><span><TrendingUp size={29} /></span></div></div><div className="prediction-grid"><section className="card prediction-chart-card"><div className="card-heading"><div><h2>Monthly history & forecast</h2><p>Actuals and a held-out model evaluation</p></div></div><div className="large-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={[...data.historical.slice(-9).map((item) => ({ month: item.month, Actual: item.actual })), ...data.evaluation.map((item) => ({ month: item.month, Actual: item.actual, Predicted: item.predicted }))]} margin={{ top: 12, right: 8, left: -12, bottom: 0 }}><CartesianGrid stroke="#272b39" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="month" tickFormatter={(v) => v.slice(2)} tickLine={false} axisLine={false} tick={{ fill: '#858a9d', fontSize: 10 }} /><YAxis tickFormatter={(v) => `$${v}`} tickLine={false} axisLine={false} tick={{ fill: '#858a9d', fontSize: 10 }} /><Tooltip content={<ChartTooltip />} /><Bar dataKey="Actual" fill="#8794ff" radius={[4, 4, 0, 0]} /><Bar dataKey="Predicted" fill="#54c9a5" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div></section><section className="card model-card"><div className="card-heading"><div><h2>Model evaluation</h2><p>Tested on months kept out of training</p></div></div><div className="model-metric"><span>Mean absolute error</span><strong>{money(data.mae)}</strong><small>Typical difference between model and actual monthly spend.</small></div><div className="model-metric"><span>R² score</span><strong>{data.r_squared == null ? 'N/A' : data.r_squared}</strong><small>{data.r_squared == null ? 'Not statistically meaningful with this test sample.' : 'Fit on the held-out test months; values near 1 indicate a closer fit.'}</small></div><div className="model-disclaimer"><Lightbulb size={15} /><span>This is a trend-based estimate, not financial advice. It cannot anticipate changes in your plans.</span></div></section></div></> : <section className="card forecast-empty-card"><span className="forecast-empty-icon"><Activity size={24} /></span><h2>More history, more insight</h2><p>{data.reason}</p><div className="history-requirement"><span>HISTORICAL MONTHS</span><strong>{data.historical?.length || 0} <small>/ 6 required</small></strong><div className="progress-track"><div className="progress-fill" style={{ width: `${Math.min(100, (data.historical?.length || 0) / 6 * 100)}%` }} /></div></div><Link className="button primary" to="/transactions"><CreditCard size={15} /> Add transaction history</Link></section>)}</>
}

function Unusual() {
  const { data, loading, error } = useApiData('/anomalies')
  return <><PageTitle eyebrow="A GENTLE HEADS-UP" title="Unusual expenses" subtitle="Spending patterns that might be worth a second look — never a fraud verdict." /><Notice>{error}</Notice>{loading ? <Loading /> : data && <><div className="notice info"><ShieldAlert size={16} /><span><strong>Context, not a conclusion.</strong> Unusual spending is identified with historical statistical patterns. It is not a fraud detection system.</span></div><div className="anomaly-grid"><section className="card anomaly-card"><div className="card-heading"><div><h2>Transactions to review</h2><p>Outliers compared with your usual spending</p></div><span className="count-pill">{data.transactions.length}</span></div>{data.transactions.length ? <div className="anomaly-list">{data.transactions.map((item) => <div className="anomaly-row" key={item.id}><span className="anomaly-icon"><ShieldAlert size={16} /></span><div className="anomaly-details"><strong>{item.description}</strong><small>{item.category} · {new Date(`${item.date}T12:00:00`).toLocaleDateString()}</small><p>{item.reason}</p></div><strong className="amount-cell">{money(item.amount)}</strong></div>)}</div> : <Empty title="Nothing stands out" text="No expense amounts are outside your historical IQR ranges." />}</section><section className="card anomaly-card"><div className="card-heading"><div><h2>Spending changes</h2><p>Month-over-month increases</p></div><TrendingUp size={17} className="muted" /></div>{data.spending_increases.length ? <div className="anomaly-list">{data.spending_increases.map((item) => <div className="increase-row" key={item.month}><span className="increase-icon"><TrendingUp size={16} /></span><div><strong>{item.month} expenses rose</strong><p>{money(item.previous_amount)} → {money(item.amount)}</p><small>{item.reason}</small></div><b className="negative">+{money(item.increase)}</b></div>)}</div> : <Empty title="No increase to call out" text="A comparison appears once expense activity exists across consecutive months." />}</section></div></>}</>
}

function Reports() {
  const [period, setPeriod] = useState({ year: currentYear, month: currentMonth })
  const { data, loading, error } = useApiData(`/reports/monthly?year=${period.year}&month=${period.month}`, [period.year, period.month])
  const { data: all, loading: allLoading } = useApiData('/analytics')
  const download = () => window.open(`${api.defaults.baseURL}/reports/export?year=${period.year}&month=${period.month}`, '_blank')
  return <><PageTitle eyebrow="YOUR DATA, YOUR WAY" title="Reports" subtitle="A clear monthly snapshot and exports for your records." action={<PeriodPicker {...period} onChange={(year, month) => setPeriod({ year, month })} />} /><Notice>{error}</Notice>{loading || allLoading ? <Loading /> : data && all && <><div className="report-actions"><button className="button primary" onClick={download}><Download size={15} /> Download monthly CSV</button><button className="button secondary" onClick={() => window.open(`${api.defaults.baseURL}/reports/export`, '_blank')}><FileDown size={15} /> Full transaction history</button></div><div className="report-summary"><div className="report-heading"><div className="report-symbol"><FileSpreadsheet size={19} /></div><div><span>MONTHLY REPORT</span><h2>{monthName(period.month)} {period.year}</h2></div></div><div className="report-totals"><div><small>Total expenses</small><strong>{money(data.summary.total_expenses)}</strong></div><div><small>Total income</small><strong className="positive">{money(data.summary.total_income)}</strong></div><div><small>Net savings estimate</small><strong>{money(data.summary.savings_estimate)}</strong></div>  <div><small>Transactions</small><strong>{data.transaction_count}</strong></div></div><div className="report-category"><h3>Category breakdown</h3>{data.categories.length ? data.categories.map((row) => <div className="report-category-row" key={row.name}><span>{row.name}</span><div className="progress-track"><div className="progress-fill" style={{ width: `${data.summary.total_expenses ? row.amount / data.summary.total_expenses * 100 : 0}%` }} /></div><strong>{money(row.amount)}</strong></div>) : <p className="muted">No expenses recorded this month.</p>}</div></div><section className="card report-history"><div className="card-heading"><div><h2>All-time overview</h2><p>Based on your recorded transactions</p></div></div><div className="report-totals compact-totals"><div><small>Lifetime expenses</small><strong>{money(all.total_expenses)}</strong></div><div><small>Lifetime income</small><strong>{money(all.total_income)}</strong></div><div><small>Highest expense</small><strong>{money(all.highest_transaction)}</strong></div><div><small>Average per active day</small><strong>{money(all.average_daily_spending)}</strong></div></div></section></>}</>
}

function Settings() {
  const { data, loading, error, refresh } = useApiData('/health')
  const database = isPublicDemo ? 'SQLite' : 'MySQL'
  return <>
    <PageTitle eyebrow="YOUR SPACE, YOUR SETTINGS" title="Settings" subtitle={isPublicDemo ? 'Public demo. Anyone with this link can access and change its data.' : 'Your data is stored locally. You stay in control.'} />
    <Notice>{error}</Notice>
    <div className="settings-layout">
      <section className="card settings-card">
        <div className="card-heading"><div><h2>Database connection</h2><p>{isPublicDemo ? 'Hosted demo database on Render.' : 'SpendSense uses your configured local MySQL database.'}</p></div><Database size={18} className="muted" /></div>
        {loading ? <Loading /> : <div className={`connection-status ${data?.status === 'ok' ? 'connected' : 'disconnected'}`}><span /><div><strong>{data?.status === 'ok' ? `Connected to ${database}` : 'Not connected'}</strong><small>{data?.database === 'connected' ? 'Database connection is healthy.' : data?.database || 'Check backend configuration and restart the API.'}</small></div><button className="button secondary small-button" onClick={refresh}>Check again</button></div>}
        <div className="setting-item"><div><strong>Storage mode</strong><small>{isPublicDemo ? 'Temporary hosted SQLite · data may reset on restart or redeploy' : 'Local MySQL · no cloud sync'}</small></div><span className="setting-chip">{isPublicDemo ? 'DEMO' : 'LOCAL'}</span></div>
        <div className="setting-item"><div><strong>{isPublicDemo ? 'Public access' : 'Privacy'}</strong><small>{isPublicDemo ? 'Anyone with the URL can view, add, edit, or delete demo records.' : 'No bank connection or third-party analytics.'}</small></div><ShieldAlert size={17} className={isPublicDemo ? 'muted' : 'green-icon'} /></div>
        <div className="setting-item"><div><strong>CSV uploads</strong><small>Files parsed in memory, 5 MB maximum.</small></div><FileSpreadsheet size={17} className="muted" /></div>
      </section>
      <section className="card settings-card">
        <div className="card-heading"><div><h2>Application details</h2><p>About this SpendSense workspace.</p></div></div>
        <div className="setting-item"><div><strong>Version</strong><small>SpendSense Personal Expense Intelligence</small></div><span className="setting-chip">1.0.0</span></div>
        <div className="setting-item"><div><strong>API documentation</strong><small>Explore available endpoints and schemas.</small></div><a className="text-link" href={apiDocsUrl} target="_blank" rel="noreferrer">Open Swagger <ArrowRight size={14} /></a></div>
        <div className="setting-item"><div><strong>Data export</strong><small>Download all transactions as a CSV.</small></div><button className="icon-button" title="Export transactions" onClick={() => window.open(`${api.defaults.baseURL}/reports/export`, '_blank')}><Download size={16} /></button></div>
      </section>
    </div>
  </>
}

function Landing() {
  const { data, loading } = useApiData('/health')
  return <div className="landing">
    <nav className="landing-nav">
      <Link className="brand" to="/"><span className="brand-mark"><Activity size={19} /></span><span>spend<span className="brand-accent">sense</span><small>PERSONAL FINANCE</small></span></Link>
      <div><EnvironmentBadge /><Link className="button primary" to="/dashboard">Open dashboard <ArrowRight size={15} /></Link></div>
    </nav>
    <section className="landing-hero">
      <div className="hero-copy">
        <span className="hero-kicker"><span /> A clearer relationship with money</span>
        <h1>Your money.<br /><span>Your understanding.</span></h1>
        <p>See your spending for what it is. Find patterns, build better habits, and make your next decision with confidence.</p>
        <div className="hero-actions"><Link className="button primary large-button" to="/dashboard">Explore your dashboard <ArrowRight size={16} /></Link><Link className="button secondary large-button" to="/add-expense"><Plus size={16} /> Add your first expense</Link></div>
        <div className="hero-trust"><ShieldAlert size={15} /><span>{isPublicDemo ? 'Public demo: anyone with this link can view or change the shared demo data.' : 'Private by design. Your data stays in your local MySQL database.'}</span></div>
      </div>
      <div className="hero-art">
        <div className="hero-glow" />
        <div className="hero-float float-one"><span className="float-icon purple"><BarChart3 size={15} /></span><div><small>MONTHLY SPENDING</small><strong>Understand every dollar</strong></div><TrendingDown size={17} className="positive" /></div>
        <div className="hero-dashboard-card"><div className="mock-top"><span>MONTHLY OVERVIEW</span><MoreHorizontal size={15} /></div><strong className="mock-amount">A clearer picture.</strong><span className="mock-caption">Your transactions, thoughtfully organized.</span><div className="mock-bars"><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /></div><div className="mock-legend"><span><i /> Spending insights</span><span><i /> Your real data</span></div></div>
        <div className="hero-float float-two"><span className="float-icon green"><Check size={15} /></span><div><strong>{isPublicDemo ? 'Shared demo data' : 'Your data stays yours'}</strong><small>{isPublicDemo ? 'Anyone with the link can access it.' : 'Private. Always.'}</small></div></div>
        <div className="hero-spark spark-one">✳</div><div className="hero-spark spark-two">✦</div>
      </div>
    </section>
    <section className="feature-strip">
      <div><span><BarChart3 size={17} /></span><strong>See your patterns</strong><small>Thoughtful analytics from your actual transactions.</small></div>
      <div><span><Target size={17} /></span><strong>Spend with intention</strong><small>Budgets that keep your priorities in view.</small></div>
      <div><span><Sparkles size={17} /></span><strong>Look ahead</strong><small>Clear, honest forecasts from your history.</small></div>
      <div><span><ShieldAlert size={17} /></span><strong>{isPublicDemo ? 'Demo data only' : 'Stay in control'}</strong><small>{isPublicDemo ? 'Avoid sensitive financial records.' : 'Local storage. No bank links. No surprises.'}</small></div>
    </section>
    <footer className="landing-footer"><span>SpendSense · Personal Expense Intelligence</span><span>{loading ? 'Checking API…' : data?.status === 'ok' ? '● API connected' : '○ API not connected yet'}</span></footer>
  </div>
}

function NotFound() { return <div className="not-found"><strong>404</strong><h1>That page isn't here.</h1><Link className="button primary" to="/dashboard">Back to dashboard</Link></div> }

export default function App() {
  return <AuthGate><Routes><Route path="/" element={<Landing />} /><Route element={<Layout />}><Route path="/dashboard" element={<Dashboard />} /><Route path="/transactions" element={<Transactions />} /><Route path="/add-expense" element={<AddExpense />} /><Route path="/import" element={<ImportCsv />} /><Route path="/categories" element={<Categories />} /><Route path="/budgets" element={<Budgets />} /><Route path="/analytics" element={<Analytics />} /><Route path="/predictions" element={<Predictions />} /><Route path="/unusual" element={<Unusual />} /><Route path="/reports" element={<Reports />} /><Route path="/settings" element={<Settings />} /></Route><Route path="*" element={<NotFound />} /></Routes></AuthGate>
}
