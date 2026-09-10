import { useId, useState } from 'react'

const number = (value) => Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })
const month = (date) => new Date(`${date.slice(0, 10)}T00:00:00`).toLocaleDateString(undefined, { month: 'short', year: '2-digit' })

export default function ForecastChart({ history, predictions }) {
  const gradient = useId().replace(/:/g, '')
  const [range, setRange] = useState(24)
  const [activeDate, setActiveDate] = useState(null)
  const actual = history.slice(-range).map((point) => ({ ...point, type: 'Actual' }))
  const future = predictions.map((point) => ({ ...point, type: 'Forecast' }))
  const points = [...actual, ...future]
  if (!points.length) return <div className="grid h-80 place-items-center rounded-2xl bg-slate-50 text-sm text-slate-500" role="status">Loading demand history…</div>

  const width = 840
  const left = 62
  const right = 28
  const top = 44
  const bottom = 280
  const plotWidth = width - left - right
  const highest = Math.max(1, ...points.map((point) => Number(point.quantity)))
  const roughStep = highest * 1.15 / 4
  const magnitude = 10 ** Math.floor(Math.log10(roughStep))
  const step = Math.ceil(roughStep / magnitude) * magnitude
  const maximum = step * 4
  const x = (index) => left + index / Math.max(1, points.length - 1) * plotWidth
  const y = (quantity) => bottom - Number(quantity) / maximum * (bottom - top)
  const path = (items, offset = 0) => items.map((point, index) => `${index ? 'L' : 'M'} ${x(index + offset)} ${y(point.quantity)}`).join(' ')
  const actualPath = path(actual)
  const projected = actual.length ? [actual.at(-1), ...future] : future
  const forecastPath = path(projected, Math.max(0, actual.length - 1))
  const boundary = actual.length && future.length ? (x(actual.length - 1) + x(actual.length)) / 2 : left
  const activeIndex = Math.max(0, points.findIndex((point) => point.date === activeDate))
  const selected = activeDate && points.some((point) => point.date === activeDate) ? points[activeIndex] : (future[0] || actual.at(-1))
  const selectedIndex = points.indexOf(selected)
  const average = actual.length ? actual.reduce((sum, point) => sum + Number(point.quantity), 0) / actual.length : null
  const labelInterval = Math.max(1, Math.ceil((points.length - 1) / 6))

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs text-slate-500">{month(points[0].date)} — {month(points.at(-1).date)}</p>
          <p className="mt-1 text-xs text-slate-400">Monthly demand · units</p>
        </div>
        <div className="inline-flex gap-1 rounded-xl bg-slate-100 p-1" role="group" aria-label="Historical time range">
          {[6, 12, 24].map((value) => <button key={value} type="button" aria-pressed={range === value} onClick={() => { setRange(value); setActiveDate(null) }} className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600 ${range === value ? 'bg-white text-emerald-800 shadow-sm' : 'text-slate-500 hover:text-slate-900'}`}>{value}M</button>)}
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-slate-100 bg-slate-50/70 px-4 py-3" aria-live="polite" aria-atomic="true">
        <span className={`h-2 w-2 rounded-full ${selected.type === 'Actual' ? 'bg-emerald-700' : 'bg-amber-500'}`} />
        <span className="text-xs font-medium text-slate-600">{month(selected.date)} <span className="px-1 text-slate-300">/</span> {selected.type}</span>
        <span className="ml-auto text-lg font-bold tabular-nums text-slate-900">{number(selected.quantity)} <span className="text-xs font-normal text-slate-500">units</span></span>
      </div>

      <div className="overflow-x-auto rounded-xl" tabIndex={0} role="region" aria-label="Demand chart. Scroll horizontally on small screens.">
        <svg viewBox={`0 0 ${width} 330`} className="block w-full min-w-[580px]" role="group" aria-labelledby={`${gradient}-title ${gradient}-description`}>
          <title id={`${gradient}-title`}>Actual demand and Holt forecast</title>
          <desc id={`${gradient}-description`}>Solid emerald line shows history; dashed amber line shows projected demand. Focus a point for its month and quantity. The shaded forecast area marks future months, not a confidence interval.</desc>
          <defs>
            <linearGradient id={`${gradient}-actual`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#059669" stopOpacity="0.2" /><stop offset="100%" stopColor="#059669" stopOpacity="0.01" /></linearGradient>
            <linearGradient id={`${gradient}-future`} x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#fffbeb" /><stop offset="100%" stopColor="#fef3c7" stopOpacity="0.5" /></linearGradient>
          </defs>
          {future.length > 0 && <rect x={boundary} y={top - 18} width={width - right - boundary} height={bottom - top + 18} rx="10" fill={`url(#${gradient}-future)`} />}
          {[0, 1, 2, 3, 4].map((tick) => <g key={tick}><line x1={left} x2={width - right} y1={y(tick * step)} y2={y(tick * step)} stroke="#e2e8f0" strokeDasharray={tick ? '3 5' : undefined} /><text x={left - 14} y={y(tick * step) + 4} textAnchor="end" fontSize="11" fill="#64748b">{number(tick * step)}</text></g>)}
          {actual.length > 1 && <path d={`${actualPath} L ${x(actual.length - 1)} ${bottom} L ${left} ${bottom} Z`} fill={`url(#${gradient}-actual)`} />}
          {average !== null && <line x1={left} x2={width - right} y1={y(average)} y2={y(average)} stroke="#94a3b8" strokeDasharray="2 6" />}
          {actual.length > 0 && <path d={actualPath} fill="none" stroke="#047857" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />}
          {future.length > 0 && <>
            <line x1={boundary} x2={boundary} y1={top - 18} y2={bottom} stroke="#d97706" strokeOpacity="0.4" strokeDasharray="4 5" />
            <text x={width - right} y="16" textAnchor="end" fill="#b45309" fontSize="10" fontWeight="600" letterSpacing="1.5">FORECAST →</text>
            <path d={forecastPath} fill="none" stroke="#d97706" strokeWidth="3" strokeDasharray="7 6" strokeLinecap="round" />
          </>}
          <line x1={x(selectedIndex)} x2={x(selectedIndex)} y1={top} y2={bottom} stroke="#64748b" strokeOpacity="0.35" strokeDasharray="3 4" />
          {points.map((point, index) => <g key={`${point.type}-${point.date}`}>
            {point === selected && <circle cx={x(index)} cy={y(point.quantity)} r="10" fill={point.type === 'Actual' ? '#059669' : '#f59e0b'} fillOpacity="0.13" />}
            <circle cx={x(index)} cy={y(point.quantity)} r={point === selected ? 5 : 3.5} fill="white" stroke={point.type === 'Actual' ? '#047857' : '#d97706'} strokeWidth="2" />
            <circle cx={x(index)} cy={y(point.quantity)} r="12" fill="transparent" tabIndex={0} role="img" aria-label={`${month(point.date)}, ${point.type}, ${number(point.quantity)} units`} onMouseEnter={() => setActiveDate(point.date)} onFocus={() => setActiveDate(point.date)} onClick={() => setActiveDate(point.date)} className="cursor-crosshair focus:outline-none focus:stroke-slate-500">
              <title>{month(point.date)}: {number(point.quantity)} units ({point.type})</title>
            </circle>
            {(index % labelInterval === 0 && index < points.length - 2 || index === points.length - 1) && <text x={x(index)} y={bottom + 26} textAnchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'} fill="#64748b" fontSize="11">{month(point.date)}</text>}
          </g>)}
        </svg>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4">
        <div><p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Historical average</p><p className="mt-1 text-sm font-semibold text-slate-700">{average === null ? '—' : `${number(average)} units`} <span className="ml-1 inline-block w-5 border-t border-dotted border-slate-400 align-middle" /></p></div>
        <div className="text-right"><p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Forecast horizon</p><p className="mt-1 text-sm font-semibold text-amber-700">{future.length} month{future.length !== 1 ? 's' : ''} ahead</p></div>
      </div>
      <details className="mt-4 text-xs text-slate-500"><summary className="w-fit cursor-pointer rounded py-1 focus-visible:outline-emerald-600">View chart data</summary><div className="mt-2 max-h-48 overflow-auto"><table className="w-full text-left"><caption className="sr-only">Monthly demand values for the selected time range</caption><thead><tr><th scope="col" className="py-2">Month</th><th scope="col">Series</th><th scope="col" className="text-right">Units</th></tr></thead><tbody>{points.map((point) => <tr key={`${point.type}-${point.date}`} className="border-t border-slate-100"><td className="py-2">{month(point.date)}</td><td>{point.type}</td><td className="text-right tabular-nums">{number(point.quantity)}</td></tr>)}</tbody></table></div></details>
    </div>
  )
}
