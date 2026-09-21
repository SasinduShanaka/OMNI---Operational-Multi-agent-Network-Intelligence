import { useCallback, useEffect, useState } from 'react'
import ManagementReport, { ReportStatus } from './ManagementReport'
import { reportDate } from './reportFormatting'
import { createChatReportPreview } from './chatReports'
import ForecastPdfPreview from './ForecastPdfPreview'
import { ScenePage, SkeletonCard } from './FactoryScene'
import { apiFetch } from '../api/http'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const domains = [['inventory', 'Inventory'], ['forecast', 'Demand forecast'], ['production', 'Production'], ['supply_chain', 'Supply chain']]
const button = 'rounded-lg bg-[#1d4ed8] px-3.5 py-2 text-[13px] font-medium text-white transition hover:bg-[#1e40af] disabled:opacity-50'
const field = 'mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 focus:border-blue-400 focus:outline-none'

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
  return <ScenePage
    scene="overview"
    banner={
      <div className="mx-auto w-full max-w-[1280px] px-5 pb-6">
        <div className="rounded-xl border border-white/60 bg-white/80 px-4 py-3 backdrop-blur-xl">
          <span className="inline-flex items-center gap-2 rounded-full bg-[#1d4ed8] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#e2e8f0]">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
            Report agent
          </span>
          <h1 className="mt-2 text-[22px] font-semibold tracking-tight text-slate-900">Your factory, in focus</h1>
          <p className="mt-1 max-w-2xl text-[12px] text-[#64748b]">Inventory, demand, production and supply chain findings in one management brief — on demand or on a schedule.</p>
        </div>
      </div>
    }
  ><section className="mx-auto w-full max-w-[1280px] space-y-4 px-5 pb-10">
    {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-800">{error}</p>}
    {notice && <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-[12px] text-emerald-800">{notice}</p>}
    <div className="grid items-start gap-4 lg:grid-cols-2">
      <section className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">
        <h2 className="text-[13px] font-semibold text-slate-900">Build a management report</h2>
        <label className="mt-4 block text-[12px] text-slate-600">Report title<input className={field} value={title} maxLength={100} onChange={(e) => setTitle(e.target.value)} /></label>
        <fieldset className="mt-4"><legend className="text-[12px] text-slate-600">Include these areas</legend><div className="mt-3 flex flex-wrap gap-3">{domains.map(([id, name]) => <label key={id} className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700"><input type="checkbox" checked={selected.includes(id)} onChange={(e) => setSelected(e.target.checked ? [...selected, id] : selected.filter((item) => item !== id))} />{name}</label>)}</div></fieldset>
        {selected.includes('forecast') && <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="text-[12px] text-slate-600">Forecast product codes<input className={field} placeholder="All products, or GAR-003, GAR-004" value={skus} onChange={(e) => setSkus(e.target.value)} /></label>
          <label className="text-[12px] text-slate-600">Forecast horizon<select className={field} value={periods} onChange={(e) => setPeriods(e.target.value)}>{[1, 3, 6, 12].map((n) => <option key={n} value={n}>{n} month{n > 1 ? 's' : ''}</option>)}</select></label>
        </div>}
        <p className="mt-3 text-[11px] leading-5 text-slate-400">Reports capture current conditions. Daily and monthly schedules control when snapshots are created; they do not calculate historical period totals.</p>
        <button className={`${button} mt-4`} disabled={!!busy || !valid} onClick={() => action('generate', async () => {
          const saved = await request('/generate', { method: 'POST', body: JSON.stringify(scope()) })
          setReport(saved); setNotice('Report generated and saved to history.'); await refresh()
        })}>{busy === 'generate' ? 'Collecting agent results...' : 'Generate & save report'}</button>
      </section>
      <section className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">
        <h2 className="text-[13px] font-semibold text-slate-900">Make it a routine</h2>
        <p className="mt-1 text-[12px] leading-5 text-slate-500">Use the selected report scope for an automatic daily or monthly brief.</p>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <label className="text-[12px] text-slate-600">Frequency<select className={field} value={frequency} onChange={(e) => setFrequency(e.target.value)}><option value="daily">Daily</option><option value="monthly">Monthly</option></select></label>
          <label className="text-[12px] text-slate-600">Time (Sri Lanka)<input type="time" className={field} value={time} onChange={(e) => setTime(e.target.value)} /></label>
          {frequency === 'monthly' && <label className="text-[12px] text-slate-600">Day of month<select className={field} value={day} onChange={(e) => setDay(Number(e.target.value))}>{Array.from({ length: 28 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}</select></label>}
        </div>
        <p className="mt-3 text-[11px] leading-5 text-slate-400">The backend must be running. After downtime, one current snapshot is generated for missed runs. Reports are saved here for download; files are not downloaded automatically.</p>
        <button className={`${button} mt-4`} disabled={!!busy || !valid || !time} onClick={() => action('schedule', async () => {
          await request('/schedules', { method: 'POST', body: JSON.stringify({ scope: scope(), frequency, time, day_of_month: day }) })
          setNotice('Schedule saved. Its next run is shown below.'); await refresh()
        })}>{busy === 'schedule' ? 'Saving schedule...' : 'Create schedule'}</button>
      </section>
    </div>
    <section className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">
      <h2 className="text-[13px] font-semibold text-slate-900">Scheduled briefs</h2>
      {!schedules.length && (loading
        ? <div className="mt-3 space-y-2"><SkeletonCard lines={2} /><SkeletonCard lines={2} /></div>
        : <p className="mt-2 text-[12px] text-slate-500">No schedules yet. Create one above.</p>)}
      <div className="mt-3 space-y-3">{schedules.map((item) => <div key={item._id} className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-200/80 p-3">
        <div><p className="font-semibold text-slate-800">{item.scope.title}</p><p className="mt-1 text-[12px] text-slate-600">{item.frequency === 'daily' ? 'Daily' : `Monthly, day ${item.day_of_month}`} at {item.time} · Sri Lanka time · {item.enabled ? 'Active' : 'Paused'}</p><p className="mt-1 text-xs text-slate-500">{item.scope.domains.join(', ')} · Next: {item.enabled ? reportDate(item.next_run) : 'Paused'}</p><p className="mt-1 text-xs text-slate-500">Last run: {reportDate(item.last_run)} · {item.last_status.replaceAll('_', ' ')}</p>{item.last_error && <p className="mt-2 text-xs text-red-700">{item.last_error}</p>}</div>
        <div className="flex gap-2">{item.last_report_id && <button className={button} disabled={!!busy} onClick={() => action('open', async () => setReport(await request(`/${encodeURIComponent(item.last_report_id)}`)))}>View latest</button>}<button className="rounded-lg border border-slate-300 px-4 py-2 text-sm disabled:opacity-50" disabled={!!busy} onClick={() => action('toggle', async () => { await request(`/schedules/${item._id}`, { method: 'PATCH', body: JSON.stringify({ enabled: !item.enabled }) }); await refresh() })}>{item.enabled ? 'Pause' : 'Resume'}</button></div>
      </div>)}</div>
    </section>
    <section className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">
      <div className="flex items-center justify-between gap-3"><h2 className="text-[13px] font-semibold text-slate-900">Report history <span className="text-sm font-normal text-slate-500">({total})</span></h2><button className="text-sm font-semibold text-[#1d4ed8] disabled:opacity-50" disabled={!!busy} onClick={() => action('refresh', refresh)}>Refresh</button></div>
      {!history.length && (loading
        ? <div className="mt-3 space-y-2"><SkeletonCard lines={1} /><SkeletonCard lines={1} /><SkeletonCard lines={1} /></div>
        : <p className="mt-2 text-[12px] text-slate-500">Saved reports will appear here.</p>)}
      <div className="mt-4 divide-y divide-slate-100">{history.map((item) => <div key={item._id} className="flex flex-wrap items-center justify-between gap-4 py-4">
        <div><p className="font-semibold text-slate-800">{item.title}</p><p className="mt-1 text-xs text-slate-500">{reportDate(item.generated_at)} · {item.schedule_id ? 'Scheduled' : 'On demand'} · Sri Lanka time</p></div><div className="flex items-center gap-3"><ReportStatus status={item.status} /><button className={button} disabled={!!busy} onClick={() => action('open', async () => setReport(await request(`/${encodeURIComponent(item._id)}`)))}>Open report</button></div>
      </div>)}</div>
      <div className="mt-4 flex items-center justify-end gap-4 text-sm"><button disabled={page === 0 || !!busy} className="disabled:opacity-40" onClick={() => setPage(page - 1)}>Previous</button><span>Page {page + 1}</span><button disabled={(page + 1) * 10 >= total || !!busy} className="disabled:opacity-40" onClick={() => setPage(page + 1)}>Next</button></div>
    </section>
    {report && <section className="space-y-4" aria-label="Selected report">
      <div className="flex items-center justify-between"><h2 className="text-[13px] font-semibold text-slate-900">Report preview</h2><button className={button} disabled={!!busy} onClick={() => action('download', async () => setPdfPreview(await createChatReportPreview(report)))}>{busy === 'download' ? 'Preparing PDF...' : 'Download PDF'}</button></div>
      <ManagementReport report={report} />
    </section>}
    {pdfPreview && <ForecastPdfPreview report={pdfPreview} onClose={() => setPdfPreview(null)} />}
  </section></ScenePage>
}
