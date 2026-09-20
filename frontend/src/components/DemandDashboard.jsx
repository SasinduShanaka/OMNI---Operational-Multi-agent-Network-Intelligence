import DemandDataQuality from './DemandDataQuality'
import { useState } from 'react'
import { createForecastPdf } from './exportForecastReport'
import ForecastPdfPreview from './ForecastPdfPreview'
import ForecastChart from './ForecastChart'
import ForecastAccuracy from './ForecastAccuracy'
import { SceneStage } from './FactoryScene'

const number = (value) => value == null ? 'N/A' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 })
const month = (value) => value ? new Date(`${value.slice(0, 10)}T00:00:00`).toLocaleDateString(undefined, { month: 'short', year: 'numeric' }) : '—'

export default function DemandDashboard({ sku, setSku, periods, setPeriods, products, result, isLoading, error, requestForecast, setActivePage }) {
  const [exportError, setExportError] = useState('')
  const [pdfReport, setPdfReport] = useState(null)
  const [isExporting, setIsExporting] = useState(false)
  const accuracy = result?.accuracy
  const total = result?.predictions.reduce((sum, point) => sum + point.quantity, 0)
  const last = result?.history.at(-1)?.quantity
  const change = last > 0 ? (result.forecast - last) / last * 100 : null
  const maxPrediction = Math.max(1, ...(result?.predictions.map((point) => point.quantity) || []))
  const pending = result && (sku !== result.sku || periods !== result.forecast_horizon_months)
  const selectedName = products.find((product) => product.sku === sku)?.product_name

  async function exportForecast() {
    setExportError('')
    setIsExporting(true)
    try {
      const pdf = await createForecastPdf(result)
      setPdfReport({ pdf, filename: `${result.sku}-demand-forecast.pdf` })
    } catch {
      setExportError('Unable to prepare the PDF preview. Please try again.')
    } finally {
      setIsExporting(false)
    }
  }

  return <SceneStage scene="forecast"><main className="min-h-full px-4 py-5 text-slate-800 sm:px-5">
    {pdfReport && <ForecastPdfPreview report={pdfReport} onClose={() => setPdfReport(null)} />}
    <div className="mx-auto w-full max-w-[1280px] space-y-3">
      <header className="flex flex-wrap items-end justify-between gap-3 pt-4">
          <div className="rounded-2xl border border-white/60 bg-white/80 px-4 py-3 backdrop-blur-xl"><p className="mb-2 text-[10px] font-bold uppercase tracking-[.24em] text-blue-700">OMNI / Intelligence / Planning</p><h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Demand outlook<span className="text-blue-500">.</span></h1><p className="mt-2 text-sm text-slate-500">Understand the past. Plan what comes next.</p></div>
          <div className="flex items-center gap-2"><button type="button" onClick={() => setActivePage('operations')} className="rounded-xl border border-white/70 bg-white/85 px-4 py-2.5 text-xs font-semibold backdrop-blur-md transition hover:border-blue-400 focus-visible:outline-blue-600">✦ Ask Omni</button><button type="button" disabled={!result || isLoading || isExporting} onClick={exportForecast} className="rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-semibold text-white shadow-[0_10px_24px_rgba(15,23,42,0.4)] transition hover:bg-blue-900 disabled:opacity-40 focus-visible:outline-blue-600">↓ {isExporting ? 'Preparing PDF...' : 'Export PDF'}</button></div>
      </header>

      <form onSubmit={(event) => { event.preventDefault(); requestForecast() }} className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">
        <label className="min-w-0 flex-[2] basis-56 text-[10px] font-bold uppercase tracking-wider text-slate-500">Product
          <select value={sku} disabled={isLoading || !products.length} onChange={(event) => setSku(event.target.value)} className="mt-2 block w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-medium tracking-normal text-slate-800 focus:outline-blue-600">
            {!products.length && <option value="">No products loaded</option>}{products.map((product) => <option key={product.sku} value={product.sku}>{product.sku} · {product.product_name}</option>)}
          </select>
        </label>
        <label className="flex-1 basis-36 text-[10px] font-bold uppercase tracking-wider text-slate-500">Forecast horizon
          <select value={periods} disabled={isLoading} onChange={(event) => setPeriods(Number(event.target.value))} className="mt-2 block w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-medium tracking-normal text-slate-800 focus:outline-blue-600">{[1, 3, 6, 12].map((value) => <option key={value} value={value}>{value} month{value > 1 ? 's' : ''} ahead</option>)}</select>
        </label>
        <button disabled={isLoading || !sku} className="rounded-xl bg-blue-800 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-900 disabled:cursor-wait disabled:opacity-50 focus-visible:outline-blue-600">{isLoading ? 'Calculating…' : 'Run forecast →'}</button>
      </form>
      {exportError && <p role="alert" className="text-sm text-amber-800">{exportError}</p>}
      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}
      {pending && <p role="status" className="text-sm text-amber-800">Selection changed. Run forecast to update the results below.</p>}

      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#1e3a8a] to-blue-950 p-4 text-white shadow-[0_18px_44px_rgba(15,23,42,0.22)]">
        <div aria-hidden="true" className="pointer-events-none absolute -right-16 -top-36 h-96 w-96 rounded-full border-[48px] border-blue-400/5" />
        <div className="relative grid gap-4 lg:grid-cols-[1.2fr_1fr]">
          <div><div className="flex flex-wrap items-center gap-3"><span className="rounded-md border border-white/20 px-2 py-1 text-[10px] font-semibold tracking-widest text-blue-200">{result?.sku || sku || 'PRODUCT'}</span><p className="text-sm text-blue-50/80">{result?.product_name || selectedName || 'Select a product'}</p></div>
            <p className="mt-6 text-[10px] font-semibold uppercase tracking-[.2em] text-blue-200/70">Next month · {month(result?.forecast_period)}</p>
            <div className="mt-2 flex items-baseline gap-3"><strong className="text-4xl font-semibold tracking-tight sm:text-5xl">{result ? number(result.forecast) : '—'}</strong><span className="text-sm text-blue-100/60">units forecast</span></div>
            <p className="mt-4 text-xs text-blue-100/80">{change !== null ? `${change >= 0 ? '+' : ''}${number(change)}% vs. last observed month` : isLoading ? 'Reading demand history…' : 'Run a forecast to see your demand outlook.'}</p>
          </div>
          <div className="flex flex-col justify-between rounded-2xl border border-white/10 bg-white/5 p-4"><div><p className="text-[10px] font-bold uppercase tracking-[.18em] text-blue-300">✦ Planning brief</p><p className="mt-3 text-sm leading-7 text-blue-50">{result?.recommendation || (isLoading ? 'Preparing your demand plan…' : 'A planning recommendation will appear after a successful forecast.')}</p></div><div className="mt-5 flex flex-wrap justify-between gap-2 border-t border-white/10 pt-4 text-[11px] text-blue-100/60"><span>{result ? `${result.history_points} observed months` : 'Awaiting history'}</span><span>{result ? `Trend: ${result.trend}` : 'Holt linear trend model'}</span></div></div>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Horizon demand" value={result ? number(total) : '—'} unit="units" detail={result ? `Total across ${result.predictions.length} projected months` : 'Total projected demand'} color="primary" />
        <Stat label="Historical average" value={result ? number(result.average_historical_demand) : '—'} unit="units / month" detail="Baseline across available history" color="blue" />
        <Stat label="Backtest error" value={accuracy ? `${number(accuracy.mape_percent)}%` : '—'} detail="MAPE · lower is better; excludes zero actuals" color="amber" />
        <Stat label="Validation coverage" value={accuracy ? number(accuracy.test_points) : '—'} unit="predictions" detail="Historical one-month-ahead tests" color="violet" />
      </div>

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-5">
        <section className="min-w-0 rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-[.18em] text-blue-700">01 / Demand trajectory</p><h2 className="mt-2 text-[13px] font-semibold tracking-tight">History meets forecast</h2></div><div className="flex gap-4 text-[11px] text-slate-500"><span className="flex items-center gap-2"><i className="w-5 border-t-2 border-blue-700" />Actual</span><span className="flex items-center gap-2"><i className="w-5 border-t-2 border-dashed border-amber-600" />Forecast</span></div></div>
          {result ? <ForecastChart history={result.history} predictions={result.predictions} /> : <div role="status" className="grid h-80 place-items-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 text-center text-sm text-slate-500">{isLoading ? 'Building your demand trajectory…' : 'No forecast to display. Run a forecast above.'}</div>}
        </section>
        {result && <ForecastAccuracy accuracy={accuracy} sku={result.sku} />}
        </div>
        <aside className="min-w-0 space-y-5">
        <DemandDataQuality sku={sku} result={result} />

      <section className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]"><p className="text-[10px] font-bold uppercase tracking-[.18em] text-blue-700">02 / Production outlook</p><div className="mt-2 flex items-center justify-between gap-2"><h2 className="text-[13px] font-semibold tracking-tight">Monthly plan</h2><span className="rounded-lg bg-amber-50 px-2 py-1 text-[10px] font-bold text-amber-700">{result?.predictions.length || 0} MONTHS</span></div>
          <div className="mt-5 max-h-[280px] space-y-5 overflow-y-auto pr-1">{result?.predictions.map((point, index) => <div key={point.date}><div className="mb-2 flex items-center justify-between gap-3"><span className="text-xs text-slate-500"><span className="mr-2 text-[10px] text-slate-400">{String(index + 1).padStart(2, '0')}</span>{month(point.date)}</span><span className="text-sm font-bold tabular-nums">{number(point.quantity)} <span className="text-[10px] font-normal text-slate-400">units</span></span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-gradient-to-r from-blue-800 to-blue-400" style={{ width: `${point.quantity / maxPrediction * 100}%` }} /></div></div>) || <p className="py-8 text-sm text-slate-400">Your monthly plan will appear here.</p>}</div>
          <div className="mt-6 flex justify-between border-t border-slate-100 pt-4 text-sm"><span className="text-slate-500">Total planned demand</span><strong>{result ? number(total) : '—'}</strong></div>
        </section>
        <section className="grid gap-4 rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">
        <div><p className="text-[10px] font-bold uppercase tracking-[.18em] text-blue-700">Model / Method & validation</p><h2 className="mt-2 text-[13px] font-semibold tracking-tight">Behind the forecast</h2><p className="mt-3 text-xs leading-6 text-slate-500">Holt’s model follows the demand level and trend. Historical backtests measure past performance, not the probability of a correct future prediction.</p></div>
        <div className="space-y-3"><Gauge label="Level response · alpha" value={result?.smoothing_parameters.alpha} /><Gauge label="Trend response · beta" value={result?.smoothing_parameters.beta} /><p className="text-[11px] text-slate-400">Larger values respond faster to recent changes.</p></div>
        <div className="rounded-2xl bg-slate-50 p-4"><p className="text-xs font-bold text-slate-700">Validation notes</p><p className="mt-2 text-xs leading-6 text-slate-500">{accuracy ? `${accuracy.test_points} backtest prediction${accuracy.test_points === 1 ? '' : 's'} evaluated. ${accuracy.test_points < 6 ? 'Limited validation history: treat these metrics as preliminary.' : 'Review errors alongside the demand history.'}` : 'Run a forecast to inspect model validation.'}</p>{accuracy && <p className="mt-2 text-xs font-medium text-slate-600">RMSE {number(accuracy.rmse)} units · MAE {number(accuracy.mae)} units</p>}</div>
      </section>
        </aside>
      </div>
      <footer className="flex flex-wrap justify-between gap-2 pb-2 text-[10px] text-slate-500"><span>Source: MongoDB demand history · Monthly aggregation</span><span>{result ? `Generated ${new Date(result.generated_at).toLocaleString()} · Audit ${result.audit_saved ? 'recorded' : 'not recorded'}` : 'Waiting for a forecast'}</span></footer>
    </div>
  </main></SceneStage>
}

function Stat({ label, value, unit, detail, color }) {
  const colors = { primary: 'bg-blue-500', blue: 'bg-sky-500', amber: 'bg-amber-400', violet: 'bg-violet-400' }
  return <section className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]"><div className="flex items-center justify-between gap-3"><h2 className="text-xs font-medium text-slate-500">{label}</h2><span className={`h-2 w-2 rounded-full ${colors[color]}`} /></div><p className="mt-1.5 text-[19px] font-semibold tracking-tight tabular-nums text-slate-900">{value} <span className="text-[11px] font-normal tracking-normal text-slate-400">{unit}</span></p><p className="mt-3 text-[11px] leading-5 text-slate-500">{detail}</p></section>
}

function Gauge({ label, value }) {
  return <div><div className="mb-2 flex justify-between text-xs"><span className="text-slate-600">{label}</span><strong>{value ?? '—'}</strong></div><div className="h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-blue-600" style={{ width: `${Math.max(0, Math.min(1, value || 0)) * 100}%` }} /></div></div>
}
