import { useEffect, useId, useRef, useState } from 'react'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function DemandDataQuality({ sku, result }) {
  const [quality, setQuality] = useState(null)
  const [issuesOpen, setIssuesOpen] = useState(false)
  const issuesRef = useRef(null)
  const issuesId = useId()
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!sku) return
    const controller = new AbortController()
    setLoading(true)
    setQuality(null)
    setError('')
    async function check() {
      try {
        const response = await fetch(`${API}/forecast/data-quality/${encodeURIComponent(sku)}`, { signal: controller.signal })
        const data = await response.json()
        if (!response.ok) throw new Error(data?.detail?.message || 'Data-quality check failed.')
        setQuality(data)
        setIssuesOpen(data.status === 'blocked')
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure.message)
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    check()
    return () => controller.abort()
  }, [sku, revision, result])
  const labels = { passed: 'Checks passed', needs_review: 'Needs review', blocked: 'Forecast blocked' }
  return <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" aria-label="Demand data quality">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-widest text-emerald-700">Input validation / {sku || 'Select a product'}</p><h2 className="mt-1 text-lg font-bold text-slate-900">Data quality</h2></div><div className="flex items-center gap-3">{quality && (quality.issues.length > 0 ? <button type="button" aria-expanded={issuesOpen} aria-controls={issuesId} onClick={() => {
      setIssuesOpen(true)
      const details = issuesRef.current
      if (details) {
        details.open = true
        details.querySelector('summary')?.focus({ preventScroll: true })
        details.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }
    }} className={`rounded-full px-3 py-1 text-xs font-semibold transition hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600 ${quality.status === 'blocked' ? 'bg-rose-50 text-rose-800' : 'bg-amber-50 text-amber-800'}`}>{labels[quality.status]} <span aria-hidden="true">?</span></button> : <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">{labels[quality.status]}</span>)}<button type="button" disabled={!sku || loading} onClick={() => setRevision((value) => value + 1)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 disabled:opacity-50">{loading ? 'Checking...' : 'Check again'}</button></div></div>
    {error && <p role="alert" className="mt-3 text-sm text-rose-700">{error}</p>}
    {loading && <p role="status" className="mt-3 text-sm text-slate-500">Checking MongoDB demand records...</p>}
    {quality && <>
      <dl className="my-4 grid grid-cols-2 gap-3 sm:grid-cols-4">{[['Records checked', quality.records_checked], ['Usable records', quality.valid_records], ['Excluded records', quality.invalid_records], ['Usable months', quality.usable_months]].map(([label, value]) => <div key={label} className="rounded-xl bg-slate-50 p-3"><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-1 text-xl font-bold text-slate-800">{value}</dd></div>)}</dl>
      <p className="text-xs leading-5 text-slate-600">{quality.can_forecast ? 'Enough continuous monthly history is available. Review any issues below before using the forecast.' : 'Correct missing months or add at least three usable months before forecasting.'} No records are changed by this check.</p>
      {quality.issues.length > 0 && <details ref={issuesRef} id={issuesId} className="mt-4" open={issuesOpen} onToggle={(event) => setIssuesOpen(event.currentTarget.open)}><summary className="cursor-pointer text-sm font-semibold text-slate-700">View {quality.issues.length} issue{quality.issues.length === 1 ? '' : 's'}</summary><div className="mt-3 max-h-80 space-y-3 overflow-auto">{quality.issues.map((issue, index) => <div key={index} className="rounded-xl border border-slate-200 p-3"><p className="text-xs font-bold uppercase text-slate-500">{issue.severity}{issue.month ? ` / ${issue.month}` : ''}</p><p className="mt-1 text-sm text-slate-700">{issue.message}</p>{issue.record_ids.length > 0 && <details className="mt-2 text-xs text-slate-500"><summary className="cursor-pointer">MongoDB document IDs</summary><p className="mt-1 break-all font-mono">{issue.record_ids.join(', ')}</p></details>}</div>)}</div></details>}
      <p className="mt-3 text-[10px] text-slate-400">Checked {new Date(quality.checked_at).toLocaleString()}. Data quality does not measure forecast accuracy. Run forecast again after correcting records.</p>
    </>}
  </section>
}
