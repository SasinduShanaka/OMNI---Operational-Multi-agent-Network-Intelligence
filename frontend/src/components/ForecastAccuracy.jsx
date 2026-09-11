const number = (value) => value == null ? 'N/A' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })
const month = (value) => new Date(`${value.slice(0, 10)}T00:00:00`).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })

export default function ForecastAccuracy({ accuracy, sku }) {
  const rows = accuracy?.comparisons || []
  const hasComparisonData = Array.isArray(accuracy?.comparisons)
  const maximum = Math.ceil(Math.max(1, ...rows.flatMap((row) => [row.actual, row.forecast])) / 400) * 400
  const x = (index) => rows.length === 1 ? 390 : 60 + index / (rows.length - 1) * 660
  const y = (value) => 210 - value / maximum * 170
  return <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
    <p className="mb-1 text-[10px] font-bold uppercase tracking-[.18em] text-emerald-700">03 / Forecast performance</p>
    <h2 className="text-xl font-bold tracking-tight">Forecast accuracy {sku && <span className="text-sm font-normal text-slate-500">{sku}</span>}</h2>
    <p className="mt-2 text-xs leading-6 text-slate-500">Compare simulated one-month-ahead predictions with actual demand in completed months.</p>
    {!hasComparisonData ? <p role="status" className="mt-5 text-sm text-amber-800">The forecast service has not loaded the accuracy update yet. Restart the backend, then run the forecast again.</p> : !rows.length ? <p role="status" className="mt-5 text-sm text-slate-500">Awaiting enough completed demand history. At least three completed months are needed.</p> : <>
      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        {[['Accuracy score', accuracy.accuracy_percent == null ? 'N/A' : `${number(accuracy.accuracy_percent)}%`, 'Derived score: max(0, 100 − WAPE)'], ['Forecast error (WAPE)', accuracy.wape_percent == null ? 'N/A' : `${number(accuracy.wape_percent)}%`, 'Total absolute error / total actual demand'], ['Average error (MAE)', `${number(accuracy.mae)} units`, `${rows.length} evaluated months · lower error is better`]].map(([label, value, detail]) => <div key={label} className="rounded-xl border border-slate-100 bg-slate-50/80 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-2xl font-semibold tracking-tight text-emerald-800">{value}</p><p className="mt-2 text-[10px] leading-4 text-slate-500">{detail}</p></div>)}
      </div>
      {accuracy.wape_percent == null && <p className="mt-3 rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-[11px] text-amber-800">WAPE and the accuracy score are unavailable because total actual demand is zero.</p>}
      {rows.length < 6 && <p className="mt-3 rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-[11px] text-amber-800">Limited validation history: treat this score as preliminary.</p>}
      <p className="mt-5 text-xs text-slate-500">{month(rows[0].date)} – {month(rows.at(-1).date)} · Units · <span className="text-emerald-800">Actual (solid)</span> / <span className="text-amber-700">Backtest forecast (dashed)</span></p>
      <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Monthly forecast accuracy chart">
      <svg viewBox="0 0 760 250" className="mt-2 block w-full min-w-[460px] max-h-[260px]" role="img" aria-label="Actual demand versus historical backtest forecasts. Exact monthly values follow in the table.">
        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => <g key={fraction}><line x1="60" x2="720" y1={y(maximum * fraction)} y2={y(maximum * fraction)} stroke="#e2e8f0" /><text x="52" y={y(maximum * fraction) + 4} textAnchor="end" fontSize="11" fill="#64748b">{number(maximum * fraction)}</text></g>)}
        {['actual', 'forecast'].map((key) => <g key={key}><polyline points={rows.map((row, index) => `${x(index)},${y(row[key])}`).join(' ')} fill="none" stroke={key === 'actual' ? '#047857' : '#b45309'} strokeWidth="2" strokeDasharray={key === 'forecast' ? '6 4' : undefined} />{rows.map((row, index) => <circle key={row.date} cx={x(index)} cy={y(row[key])} r="3" fill={key === 'actual' ? '#047857' : '#b45309'}><title>{month(row.date)}: {key} {number(row[key])} units</title></circle>)}</g>)}
        {rows.map((row, index) => (index % Math.max(1, Math.ceil(rows.length / 6)) === 0 && index < rows.length - 1 || index === rows.length - 1) && <text key={row.date} x={x(index)} y="240" textAnchor={index === 0 ? 'start' : index === rows.length - 1 ? 'end' : 'middle'} fontSize="10" fill="#64748b">{month(row.date)}</text>)}
      </svg>
      </div>
      <details className="mt-3 border-t border-slate-100 pt-3 text-xs text-slate-500"><summary className="w-fit cursor-pointer rounded py-1 font-medium focus-visible:outline-emerald-600">Monthly comparison & calculation details</summary><p className="mt-2 leading-5">Each backtest uses only earlier months. These are simulated historical forecasts, not previously saved outcomes. The score is not a probability of future accuracy. WAPE is total absolute error divided by total actual demand; MAE is the average absolute error in units.</p><div className="mt-3 max-h-64 overflow-auto"><table className="w-full text-left text-sm"><caption className="sr-only">Monthly historical forecast accuracy for {sku}</caption><thead className="sticky top-0 bg-slate-50 text-xs text-slate-500"><tr>{['Month', 'Forecast units', 'Actual units', 'Absolute error'].map((heading) => <th key={heading} scope="col" className="px-3 py-3">{heading}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row.date} className="border-t border-slate-100"><th scope="row" className="px-3 py-3 font-medium">{month(row.date)}</th><td className="px-3 py-3">{number(row.forecast)}</td><td className="px-3 py-3">{number(row.actual)}</td><td className="px-3 py-3">{number(row.absolute_error)}</td></tr>)}</tbody></table></div></details>
    </>}
  </section>
}
