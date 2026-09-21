import { useCallback, useEffect, useState } from 'react'
import ManagementReport, { ReportStatus } from './ManagementReport'
import { reportDate } from './reportFormatting'
import { createChatReportPreview } from './chatReports'
import ForecastPdfPreview from './ForecastPdfPreview'
import { apiFetch } from '../api/http'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const domains = [['inventory', 'Inventory'], ['forecast', 'Demand forecast'], ['production', 'Production'], ['supply_chain', 'Supply chain']]
const button = 'rounded-lg bg-[#193e36] px-4 py-2 text-sm font-semibold text-white hover:bg-[#285448] disabled:opacity-50'
const field = 'mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900'

async function request(path, options = {}) {
  const response = await apiFetch(`${API}/reports${path}`, { ...options, headers: { 'Content-Type': 'application/json' } })
  const data = await response.json()
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : data.detail?.map((item) => item.msg).join('; ')
    throw new Error(detail || 'The report request failed. Please try again.')
  }
  return data
}

export default function ReportsPage() {
  const [selected, setSelected] = useState(domains.map(([id]) => id))
  const [title, setTitle] = useState('Factory management report')
  const [skus, setSkus] = useState('')
  const [periods, setPeriods] = useState(3)
  const [frequency, setFrequency] = useState('daily')
  const [time, setTime] = useState('08:00')
  const [day, setDay] = useState(1)
  const [history, setHistory] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [schedules, setSchedules] = useState([])
  const [report, setReport] = useState(null)
  const [pdfPreview, setPdfPreview] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async (signal) => {
    const [saved, scheduled] = await Promise.all([request(`?limit=10&skip=${page * 10}`, { signal }), request('/schedules', { signal })])
    if (signal?.aborted) return
    setHistory(saved.reports)
    setTotal(saved.total)
    setSchedules(scheduled.schedules)
  }, [page])

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    const load = () => refresh(controller.signal).catch((e) => { if (active) setError(e.message) }).finally(() => { if (active) setLoading(false) })
    load()
    const interval = setInterval(load, 30000)
    return () => { active = false; controller.abort(); clearInterval(interval) }
  }, [refresh])

  function scope() {
    return { title: title.trim(), domains: selected, skus: skus.split(',').map((sku) => sku.trim().toUpperCase()).filter(Boolean), periods: Number(periods) }
  }

  async function action(name, work) {
    if (busy) return
    setBusy(name); setError(''); setNotice('')
    try { await work() } catch (e) { setError(e.message || 'Unable to complete the report action.') }
    finally { setBusy('') }
  }

  const valid = selected.length > 0 && title.trim()
  return <section className="mx-auto max-w-7xl space-y-6 p-6 md:p-8">
    <header className="rounded-2xl bg-[#193e36] p-7 text-white">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#dfbf83]">Report Agent</p>
      <h1 className="mt-3 text-3xl font-semibold">Your factory, in focus.</h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-emerald-100">Bring inventory, demand, production, and supply chain findings into one management brief. Save a snapshot now or let a schedule prepare the next one.</p>
    </header>
    {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</p>}
    {notice && <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</p>}
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="rounded-2xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900">Build a management report</h2>
        <label className="mt-4 block text-sm text-slate-600">Report title<input className={field} value={title} maxLength={100} onChange={(e) => setTitle(e.target.value)} /></label>
        <fieldset className="mt-4"><legend className="text-sm text-slate-600">Include these areas</legend><div className="mt-3 flex flex-wrap gap-3">{domains.map(([id, name]) => <label key={id} className="flex items-center gap-2 rounded-lg bg-[#f1f6f3] px-3 py-2 text-sm text-slate-700"><input type="checkbox" checked={selected.includes(id)} onChange={(e) => setSelected(e.target.checked ? [...selected, id] : selected.filter((item) => item !== id))} />{name}</label>)}</div></fieldset>
        {selected.includes('forecast') && <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="text-sm text-slate-600">Forecast product codes<input className={field} placeholder="All products, or GAR-003, GAR-004" value={skus} onChange={(e) => setSkus(e.target.value)} /></label>
          <label className="text-sm text-slate-600">Forecast horizon<select className={field} value={periods} onChange={(e) => setPeriods(e.target.value)}>{[1, 3, 6, 12].map((n) => <option key={n} value={n}>{n} month{n > 1 ? 's' : ''}</option>)}</select></label>
        </div>}
        <p className="mt-4 text-xs leading-5 text-slate-500">Reports capture current conditions. Daily and monthly schedules control when snapshots are created; they do not calculate historical period totals.</p>
        <button className={`${button} mt-5`} disabled={!!busy || !valid} onClick={() => action('generate', async () => {
          const saved = await request('/generate', { method: 'POST', body: JSON.stringify(scope()) })
          setReport(saved); setNotice('Report generated and saved to history.'); await refresh()
        })}>{busy === 'generate' ? 'Collecting agent results...' : 'Generate & save report'}</button>
      </section>
      <section className="rounded-2xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900">Make it a routine</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">Use the selected report scope for an automatic daily or monthly brief.</p>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <label className="text-sm text-slate-600">Frequency<select className={field} value={frequency} onChange={(e) => setFrequency(e.target.value)}><option value="daily">Daily</option><option value="monthly">Monthly</option></select></label>
          <label className="text-sm text-slate-600">Time (Sri Lanka)<input type="time" className={field} value={time} onChange={(e) => setTime(e.target.value)} /></label>
          {frequency === 'monthly' && <label className="text-sm text-slate-600">Day of month<select className={field} value={day} onChange={(e) => setDay(Number(e.target.value))}>{Array.from({ length: 28 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}</select></label>}
        </div>
        <p className="mt-4 text-xs leading-5 text-slate-500">The backend must be running. After downtime, one current snapshot is generated for missed runs. Reports are saved here for download; files are not downloaded automatically.</p>
        <button className={`${button} mt-5`} disabled={!!busy || !valid || !time} onClick={() => action('schedule', async () => {
          await request('/schedules', { method: 'POST', body: JSON.stringify({ scope: scope(), frequency, time, day_of_month: day }) })
          setNotice('Schedule saved. Its next run is shown below.'); await refresh()
        })}>{busy === 'schedule' ? 'Saving schedule...' : 'Create schedule'}</button>
      </section>
    </div>
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-semibold text-slate-900">Scheduled briefs</h2>
      {!schedules.length && <p className="mt-3 text-sm text-slate-500">{loading ? 'Loading schedules...' : 'No schedules yet. Create one above.'}</p>}
      <div className="mt-3 space-y-3">{schedules.map((item) => <div key={item._id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 p-4">
        <div><p className="font-semibold text-slate-800">{item.scope.title}</p><p className="mt-1 text-sm text-slate-600">{item.frequency === 'daily' ? 'Daily' : `Monthly, day ${item.day_of_month}`} at {item.time} · Sri Lanka time · {item.enabled ? 'Active' : 'Paused'}</p><p className="mt-1 text-xs text-slate-500">{item.scope.domains.join(', ')} · Next: {item.enabled ? reportDate(item.next_run) : 'Paused'}</p><p className="mt-1 text-xs text-slate-500">Last run: {reportDate(item.last_run)} · {item.last_status.replaceAll('_', ' ')}</p>{item.last_error && <p className="mt-2 text-xs text-red-700">{item.last_error}</p>}</div>
        <div className="flex gap-2">{item.last_report_id && <button className={button} disabled={!!busy} onClick={() => action('open', async () => setReport(await request(`/${encodeURIComponent(item.last_report_id)}`)))}>View latest</button>}<button className="rounded-lg border border-slate-300 px-4 py-2 text-sm disabled:opacity-50" disabled={!!busy} onClick={() => action('toggle', async () => { await request(`/schedules/${item._id}`, { method: 'PATCH', body: JSON.stringify({ enabled: !item.enabled }) }); await refresh() })}>{item.enabled ? 'Pause' : 'Resume'}</button></div>
      </div>)}</div>
    </section>
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="flex items-center justify-between gap-3"><h2 className="text-lg font-semibold text-slate-900">Report history <span className="text-sm font-normal text-slate-500">({total})</span></h2><button className="text-sm font-semibold text-[#193e36] disabled:opacity-50" disabled={!!busy} onClick={() => action('refresh', refresh)}>Refresh</button></div>
      {!history.length && <p className="mt-3 text-sm text-slate-500">{loading ? 'Loading reports...' : 'Saved reports will appear here.'}</p>}
      <div className="mt-4 divide-y divide-slate-100">{history.map((item) => <div key={item._id} className="flex flex-wrap items-center justify-between gap-4 py-4">
        <div><p className="font-semibold text-slate-800">{item.title}</p><p className="mt-1 text-xs text-slate-500">{reportDate(item.generated_at)} · {item.schedule_id ? 'Scheduled' : 'On demand'} · Sri Lanka time</p></div><div className="flex items-center gap-3"><ReportStatus status={item.status} /><button className={button} disabled={!!busy} onClick={() => action('open', async () => setReport(await request(`/${encodeURIComponent(item._id)}`)))}>Open report</button></div>
      </div>)}</div>
      <div className="mt-4 flex items-center justify-end gap-4 text-sm"><button disabled={page === 0 || !!busy} className="disabled:opacity-40" onClick={() => setPage(page - 1)}>Previous</button><span>Page {page + 1}</span><button disabled={(page + 1) * 10 >= total || !!busy} className="disabled:opacity-40" onClick={() => setPage(page + 1)}>Next</button></div>
    </section>
    {report && <section className="space-y-4" aria-label="Selected report">
      <div className="flex items-center justify-between"><h2 className="text-lg font-semibold text-slate-900">Report preview</h2><button className={button} disabled={!!busy} onClick={() => action('download', async () => setPdfPreview(await createChatReportPreview(report)))}>{busy === 'download' ? 'Preparing PDF...' : 'Download PDF'}</button></div>
      <ManagementReport report={report} />
    </section>}
    {pdfPreview && <ForecastPdfPreview report={pdfPreview} onClose={() => setPdfPreview(null)} />}
  </section>
}
