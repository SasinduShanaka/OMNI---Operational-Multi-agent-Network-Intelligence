import { useEffect, useState } from 'react'

import { SceneStage } from './FactoryScene'
import { apiFetch } from '../api/http'

const API_BASE_URL = 'http://127.0.0.1:8000'


// ============================================================
// STATUS STYLING
// ============================================================

const VERDICT_STYLES = {
  NO_BOM: {
    label: 'Bill of materials missing',
    badge: 'bg-amber-100 text-amber-800',
    panel: 'border-amber-200 bg-amber-50',
  },
  FEASIBLE: {
    label: 'Feasible',
    badge: 'bg-emerald-100 text-emerald-700',
    panel: 'border-emerald-200 bg-emerald-50',
  },
  AT_RISK: {
    label: 'At risk',
    badge: 'bg-amber-100 text-amber-700',
    panel: 'border-amber-200 bg-amber-50',
  },
  INFEASIBLE: {
    label: 'Infeasible',
    badge: 'bg-red-100 text-red-700',
    panel: 'border-red-200 bg-red-50',
  },
  NO_LINE: {
    label: 'No line',
    badge: 'bg-slate-200 text-slate-700',
    panel: 'border-slate-200 bg-slate-50',
  },
  NOT_FOUND: {
    label: 'Not found',
    badge: 'bg-slate-200 text-slate-700',
    panel: 'border-slate-200 bg-slate-50',
  },
}

const LINE_STYLES = {
  AVAILABLE: 'bg-emerald-100 text-emerald-700',
  BOTTLENECK: 'bg-amber-100 text-amber-700',
  OFFLINE: 'bg-slate-200 text-slate-600',
}

const ORDER_STYLES = {
  COMPLETED: 'bg-emerald-100 text-emerald-700',
  ON_TRACK: 'bg-sky-100 text-sky-700',
  BEHIND_SCHEDULE: 'bg-amber-100 text-amber-700',
}


function formatNumber(value) {
  if (value === null || value === undefined) {
    return '—'
  }

  return Number(value).toLocaleString()
}


// ============================================================
// CIRCULAR STAT GAUGE — used in the hero stat row
// ============================================================

function CircularStat({ label, value, sublabel, accent }) {
  const radius = 30
  const circumference = 2 * Math.PI * radius
  const pct = Math.max(0, Math.min(100, Number(value) || 0))
  const offset = circumference * (1 - pct / 100)

  return (
    <div className="flex items-center gap-4 rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">
      <svg width="72" height="72" viewBox="0 0 72 72" className="shrink-0 -rotate-90">
        <circle cx="36" cy="36" r={radius} fill="none" stroke="#f1f5f9" strokeWidth="7" />
        <circle
          cx="36"
          cy="36"
          r={radius}
          fill="none"
          stroke={accent}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div>
        <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">{label}</p>
        <p className="mt-1 text-xl font-semibold text-slate-900">{sublabel}</p>
      </div>
    </div>
  )
}


// ============================================================
// PRODUCTION PAGE
// ============================================================

function ProductionPage() {

  const [lines, setLines] = useState([])
  const [orders, setOrders] = useState([])
  const [kpis, setKpis] = useState(null)
  const [products, setProducts] = useState([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Feasibility form
  const [sku, setSku] = useState('')
  const [quantity, setQuantity] = useState(10000)
  const [requiredDate, setRequiredDate] = useState('')

  const [checking, setChecking] = useState(false)
  const [checkError, setCheckError] = useState('')
  const [result, setResult] = useState(null)

  // Human-in-the-loop decision on the reallocation proposal
  const [decision, setDecision] = useState(null)


  // --------------------------------------------------
  // Load production data from the backend
  // --------------------------------------------------

  async function loadProduction() {
    setLoading(true)
    setError('')

    try {
      const [linesRes, ordersRes, kpisRes, productsRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/production/lines`),
        apiFetch(`${API_BASE_URL}/production/orders`),
        apiFetch(`${API_BASE_URL}/production/kpis`),
        apiFetch(`${API_BASE_URL}/production/products`),
      ])

      if (!linesRes.ok || !ordersRes.ok || !kpisRes.ok || !productsRes.ok) {
        throw new Error('Failed to load production data')
      }

      const productList = await productsRes.json()

      setLines(await linesRes.json())
      setOrders(await ordersRes.json())
      setKpis(await kpisRes.json())
      setProducts(productList)

      if (productList.length > 0) {
        setSku((current) => current || productList[0].sku)
      }
    } catch (err) {
      console.error(err)
      setError('Could not load production data from the backend.')
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    loadProduction()

    // Default the required date to 30 days out
    const target = new Date()
    target.setDate(target.getDate() + 30)
    setRequiredDate(target.toISOString().slice(0, 10))
  }, [])


  // --------------------------------------------------
  // Run a feasibility check
  // --------------------------------------------------

  async function handleCheck(event) {
    event.preventDefault()

    if (!sku || !requiredDate || Number(quantity) <= 0) {
      setCheckError('Choose a product, a quantity above zero and a required date.')
      return
    }

    setChecking(true)
    setCheckError('')
    setResult(null)
    setDecision(null)

    try {
      const response = await apiFetch(`${API_BASE_URL}/production/feasibility`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sku: sku,
          quantity: Number(quantity),
          required_date: requiredDate,
        }),
      })

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`)
      }

      setResult(await response.json())
    } catch (err) {
      console.error(err)
      setCheckError('The Production Agent could not assess this order.')
    } finally {
      setChecking(false)
    }
  }


  // --------------------------------------------------
  // Loading state
  // --------------------------------------------------

  if (loading) {
    return (
      <SceneStage scene="production">
      <div className="mx-auto w-full max-w-[1280px] px-5 pb-8 pt-5">

        <div className="inline-block rounded-2xl border border-white/60 bg-white/80 px-4 py-3 backdrop-blur-xl">

          <h1 className="text-xl font-semibold tracking-tight text-slate-900">
            Production agent
          </h1>

          <p className="mt-1 text-[11px] text-slate-500">
            Line capacity, bottlenecks and order feasibility
          </p>

          <p className="mt-3 flex items-center gap-2 text-[12px] text-slate-500">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#1d4ed8]" />
            Loading production data...
          </p>

        </div>

      </div>
      </SceneStage>
    )
  }


  const verdict = result ? (VERDICT_STYLES[result.status] || VERDICT_STYLES.NOT_FOUND) : null
  const bottleneckLine = lines.find((line) => line.status === 'BOTTLENECK')
  const offlineCount = lines.filter((line) => line.status === 'OFFLINE').length


  // --------------------------------------------------
  // Main page
  // --------------------------------------------------

  return (
    <SceneStage scene="production">
    <div className="mx-auto w-full max-w-[1280px] px-5 pb-8">

      {/* ================================================ */}
      {/* HEADER */}
      {/* ================================================ */}

      <div className="flex flex-wrap items-end justify-between gap-3 mb-4 pt-6">

        <div className="rounded-2xl border border-white/60 bg-white/80 px-4 py-3 backdrop-blur-xl">

          <div className="inline-flex items-center gap-2 rounded-full bg-[#1d4ed8] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#e2e8f0] mb-3">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
            Production intelligence
          </div>

          <h1 className="text-3xl font-semibold text-slate-900 tracking-tight">
            Line planning
          </h1>

          <p className="text-sm text-[#64748b] mt-2">
            Capacity, bottlenecks and order feasibility across every production line
          </p>

        </div>

        <button
          onClick={loadProduction}
          className="
            px-4
            py-2.5
            rounded-xl
            bg-white/85
            border
            border-white/70
            text-sm
            text-slate-700
            backdrop-blur-md
            shadow-[0_8px_20px_rgba(15,23,42,0.12)]
            hover:bg-white
            transition
          "
        >
          ↻ Refresh
        </button>

      </div>


      {/* ================================================ */}
      {/* ERROR */}
      {/* ================================================ */}

      {error && (
        <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
        </div>
      )}


      {/* ================================================ */}
      {/* FACTORY FLOOR HERO — status rail + isometric visual */}
      {/* ================================================ */}

      {kpis && (
        <div className="mb-4 grid grid-cols-1 gap-3 xl:grid-cols-[360px_1fr]">

          {/* STATUS RAIL */}

          <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
              Factory status
            </p>
            <h2 className="mt-1.5 text-[13px] font-semibold text-slate-900">
              Line overview
            </h2>

            <div className="mt-4 flex gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-100 px-2.5 py-1 text-[11px] font-medium text-emerald-700">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {kpis.active_lines} active
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-100 px-2.5 py-1 text-[11px] font-medium text-amber-700">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                {kpis.bottleneck_count} bottleneck
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
                {offlineCount} offline
              </span>
            </div>

            <div className="mt-5 space-y-3 max-h-[340px] overflow-y-auto pr-1">
              {lines.map((line) => (
                <div key={line.line_id} className="rounded-xl border border-slate-100 p-3">

                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <div className="text-xs font-medium text-slate-700 truncate">
                      {line.name}
                    </div>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      LINE_STYLES[line.status] || LINE_STYLES.OFFLINE
                    }`}>
                      {line.current_utilization}%
                    </span>
                  </div>

                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-full rounded-full ${
                        line.status === 'BOTTLENECK' ? 'bg-[#f59e0b]' : 'bg-[#1d4ed8]'
                      }`}
                      style={{ width: `${line.current_utilization}%` }}
                    />
                  </div>

                  <div className="mt-1 text-[10px] text-slate-400 truncate">
                    {line.line_id} · builds {line.supported_skus?.join(', ')}
                  </div>

                </div>
              ))}
            </div>

          </div>


          {/* ISOMETRIC FACTORY VISUAL */}

          <div className="relative min-h-[420px]">

            {/* Floating capacity card */}

            <div className="absolute left-5 top-5 max-w-[240px] p-4 rounded-xl border border-white/70 bg-white/85 backdrop-blur-md shadow-[0_10px_30px_-12px_rgba(15,23,42,0.45)]">
              <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
                Factory capacity
              </p>
              <h3 className="mt-1 text-[22px] font-semibold tracking-tight tabular-nums text-slate-900">
                {kpis.average_utilization}%
              </h3>
              <p className="mt-1 text-[11px] text-slate-500">
                {formatNumber(kpis.spare_capacity_per_day)} of{' '}
                {formatNumber(kpis.total_capacity_per_day)} units/day free
              </p>
            </div>

            {/* Floating bottleneck callout */}

            {bottleneckLine && (
              <div className="absolute right-5 top-5 max-w-[220px] p-4 rounded-xl border border-white/70 bg-white/85 backdrop-blur-md shadow-[0_10px_30px_-12px_rgba(15,23,42,0.45)] !border-amber-200">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-amber-500" />
                  <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-amber-700">
                    Bottleneck
                  </p>
                </div>
                <h3 className="mt-1.5 text-[13px] font-semibold text-slate-900">
                  {bottleneckLine.name}
                </h3>
                <p className="mt-1 text-[11px] text-slate-500">
                  {bottleneckLine.current_utilization}% utilized · {bottleneckLine.line_id}
                </p>
              </div>
            )}

            {/* Floating orders-on-track card */}

            <div className="absolute bottom-5 left-5 px-4 py-3 rounded-xl border border-white/70 bg-white/85 backdrop-blur-md shadow-[0_10px_30px_-12px_rgba(15,23,42,0.45)]">
              <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
                Orders on track
              </p>
              <p className="mt-1 text-[18px] font-semibold tabular-nums text-slate-900">
                {kpis.on_track_percentage}%
              </p>
            </div>

          </div>

        </div>
      )}


      {/* ================================================ */}
      {/* STAT GAUGES */}
      {/* ================================================ */}

      {kpis && (
        <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <CircularStat
            label="Average utilization"
            value={kpis.average_utilization}
            sublabel={`${kpis.average_utilization}%`}
            accent="#1d4ed8"
          />
          <CircularStat
            label="Orders on track"
            value={kpis.on_track_percentage}
            sublabel={`${kpis.on_track_percentage}%`}
            accent="#3b82f6"
          />
          <CircularStat
            label="Bottlenecks"
            value={kpis.total_lines ? (kpis.bottleneck_count / kpis.total_lines) * 100 : 0}
            sublabel={`${kpis.bottleneck_count} / ${kpis.total_lines} lines`}
            accent="#f59e0b"
          />
        </div>
      )}


      {/* ================================================ */}
      {/* FEASIBILITY CHECKER */}
      {/* ================================================ */}

      <div className="mb-4 rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

        <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
          Order feasibility
        </p>

        <h2 className="mt-1.5 text-[13px] font-semibold text-slate-900">
          Can we make it?
        </h2>

        <p className="mt-1 text-xs text-slate-500">
          The Production Agent checks line capacity, then asks the Inventory Agent
          whether the materials exist.
        </p>

        <form onSubmit={handleCheck} className="mt-4 flex flex-wrap items-end gap-3">

          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
              Product
            </span>
            <select
              value={sku}
              onChange={(event) => setSku(event.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 min-w-[240px]"
            >
              {products.map((product) => (
                <option key={product.sku} value={product.sku}>
                  {product.name} ({product.sku})
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
              Quantity
            </span>
            <input
              type="number"
              min="1"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 w-[140px]"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
              Required by
            </span>
            <input
              type="date"
              value={requiredDate}
              onChange={(event) => setRequiredDate(event.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
            />
          </label>

          <button
            type="submit"
            disabled={checking}
            className="
              rounded-xl
              bg-[#1d4ed8]
              hover:bg-[#1e40af]
              disabled:opacity-50
              px-4
              py-2.5
              text-sm
              font-medium
              text-white
              shadow-sm
              transition
            "
          >
            {checking ? 'Assessing...' : 'Assess order'}
          </button>

        </form>

        {checkError && (
          <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
            {checkError}
          </div>
        )}

      </div>


      {/* ================================================ */}
      {/* VERDICT */}
      {/* ================================================ */}

      {result && verdict && (
        <div className={`mb-4 rounded-2xl border p-5 ${verdict.panel}`}>

          {/* VERDICT HEADER */}

          <div className="flex items-start justify-between gap-4 flex-wrap">

            <div>
              <div className="flex items-center gap-3">
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${verdict.badge}`}>
                  {verdict.label}
                </span>
                <span className="text-xs text-slate-500">
                  {result.workflow?.join(' → ')}
                </span>
              </div>

              <h3 className="mt-2 text-[13px] font-semibold text-slate-900">
                {formatNumber(result.required_quantity)} × {result.product_name}
              </h3>

              <p className="mt-1 text-sm text-slate-600">
                {result.message}
              </p>
            </div>

            {result.capacity?.line_name && (
              <div className="rounded-xl bg-white/70 border border-white px-3 py-2 text-right">
                <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
                  Assigned line
                </div>
                <div className="mt-1 text-sm font-semibold text-slate-900">
                  {result.capacity.line_name}
                </div>
                <div className="text-[11px] text-slate-500">
                  {result.capacity.line_id} · {result.capacity.current_utilization}% used
                </div>
              </div>
            )}

          </div>


          {/* EXPLAINABILITY — EVIDENCE PANEL */}

          <div className="mt-5 rounded-xl bg-white/70 border border-white p-4">

            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
              Why — evidence behind this verdict
            </p>

            <ul className="mt-3 space-y-1.5">
              {result.factors?.map((factor, index) => (
                <li key={index} className="text-sm text-slate-700 flex gap-2">
                  <span className="text-slate-400">•</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>

          </div>


          {/* AGENT-TO-AGENT MESSAGE LOG */}

          {result.materials?.length > 0 && (
            <div className="mt-4 rounded-xl bg-white/70 border border-white p-4">

              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                Material check · Production Agent → Inventory Agent
              </p>

              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-left text-sm">

                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="pb-2 pr-4 font-medium text-slate-600">Message</th>
                      <th className="pb-2 pr-4 font-medium text-slate-600">Material</th>
                      <th className="pb-2 pr-4 font-medium text-slate-600">Required</th>
                      <th className="pb-2 pr-4 font-medium text-slate-600">Available</th>
                      <th className="pb-2 font-medium text-slate-600">Reply</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100">
                    {result.materials.map((check, index) => {

                      const isShort = check.response.status === 'SHORTAGE'

                      return (
                        <tr key={index}>
                          <td className="py-2 pr-4 font-mono text-[11px] text-slate-500">
                            {check.request.message_type}
                          </td>
                          <td className="py-2 pr-4 text-slate-800">
                            {check.response.material_name || check.request.material_code}
                          </td>
                          <td className="py-2 pr-4 text-slate-700">
                            {formatNumber(check.request.required_quantity)}{' '}
                            {check.response.unit || ''}
                          </td>
                          <td className="py-2 pr-4 text-slate-700">
                            {formatNumber(check.response.available_quantity)}
                          </td>
                          <td className="py-2">
                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                              isShort
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-emerald-100 text-emerald-700'
                            }`}>
                              {check.response.status}
                              {isShort && ` · short ${formatNumber(check.response.shortage)}`}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>

                </table>
              </div>

            </div>
          )}


          {/* HUMAN-IN-THE-LOOP — REALLOCATION APPROVAL */}

          {result.reallocation && result.reallocation.options.length > 0 && (
            <div className="mt-4 rounded-xl bg-white/70 border border-white p-4">

              <div className="flex items-start justify-between gap-4 flex-wrap">

                <div>
                  <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    Proposed action · requires approval
                  </p>

                  <h4 className="mt-2 text-sm font-semibold text-slate-900">
                    Reallocate {formatNumber(result.reallocation.shortfall)} units to lines with spare capacity
                  </h4>

                  <p className="mt-1 text-xs text-slate-500">
                    {result.reallocation.fully_recoverable
                      ? 'This fully covers the shortfall.'
                      : `Only ${formatNumber(result.reallocation.total_absorbable)} units can be absorbed elsewhere.`}
                  </p>
                </div>

                {!decision && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => setDecision('APPROVED')}
                      className="rounded-lg bg-[#1d4ed8] px-3 py-2 text-xs font-medium text-white hover:bg-[#1e40af]"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => setDecision('REJECTED')}
                      className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                    >
                      Reject
                    </button>
                  </div>
                )}

                {decision && (
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    decision === 'APPROVED'
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-slate-200 text-slate-700'
                  }`}>
                    {decision === 'APPROVED' ? 'Approved' : 'Rejected'} · logged
                  </span>
                )}

              </div>

              <div className="mt-4 space-y-2">
                {result.reallocation.options.map((option) => (
                  <div
                    key={option.line_id}
                    className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white px-3 py-2"
                  >
                    <div>
                      <div className="text-sm text-slate-800">
                        {option.line_name}
                        <span className="ml-2 text-[11px] font-normal text-slate-400">{option.line_id}</span>
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {option.current_utilization}% utilized
                        {option.requires_retooling && ' · requires retooling'}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-sm font-semibold text-slate-900">
                        {formatNumber(option.absorbable_quantity)}
                      </div>
                      <div className="text-[11px] text-slate-500">units absorbable</div>
                    </div>
                  </div>
                ))}
              </div>

            </div>
          )}

        </div>
      )}


      {/* ================================================ */}
      {/* PRODUCTION ORDERS */}
      {/* ================================================ */}

      <div className="grid grid-cols-1 gap-4">

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
            Workload
          </p>

          <h2 className="mt-1.5 text-[13px] font-semibold text-slate-900 mb-3">
            Production orders
          </h2>

          <div className="space-y-3">
            {orders.map((order) => (
              <div
                key={order.production_order_id}
                className="rounded-lg border border-slate-200/80 px-3 py-2.5"
              >

                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <div className="text-[13px] font-medium text-slate-800">
                    {order.production_order_id}
                    <span className="ml-2 text-xs text-slate-400">
                      {order.sku} · {order.line_id}
                    </span>
                  </div>

                  <span className={`rounded-full px-2 py-1 text-[10px] font-medium ${
                    ORDER_STYLES[order.status] || ORDER_STYLES.ON_TRACK
                  }`}>
                    {order.status.replace('_', ' ')}
                  </span>
                </div>

                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-[#3b82f6]"
                    style={{ width: `${order.completion_percentage}%` }}
                  />
                </div>

                <div className="mt-1.5 text-[11px] text-slate-400">
                  {formatNumber(order.completed_quantity)} of{' '}
                  {formatNumber(order.planned_quantity)} units ·{' '}
                  {order.completion_percentage}% complete
                </div>

              </div>
            ))}
          </div>

        </div>

      </div>

    </div>
    </SceneStage>
  )
}


export default ProductionPage
