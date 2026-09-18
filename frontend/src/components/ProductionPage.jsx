import { useEffect, useState } from 'react'

const API_BASE_URL = 'http://127.0.0.1:8000'


// ============================================================
// STATUS STYLING
// ============================================================

const VERDICT_STYLES = {
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
        fetch(`${API_BASE_URL}/production/lines`),
        fetch(`${API_BASE_URL}/production/orders`),
        fetch(`${API_BASE_URL}/production/kpis`),
        fetch(`${API_BASE_URL}/production/products`),
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
      const response = await fetch(`${API_BASE_URL}/production/feasibility`, {
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
      <div className="p-8">

        <h1 className="text-2xl font-semibold text-slate-900">
          Production agent
        </h1>

        <p className="text-sm text-slate-500 mt-1">
          Line capacity, bottlenecks and order feasibility
        </p>

        <div className="mt-10 text-slate-500">
          Loading production data...
        </div>

      </div>
    )
  }


  const verdict = result ? (VERDICT_STYLES[result.status] || VERDICT_STYLES.NOT_FOUND) : null


  // --------------------------------------------------
  // Main page
  // --------------------------------------------------

  return (
    <div className="p-8">

      {/* ================================================ */}
      {/* HEADER */}
      {/* ================================================ */}

      <div className="flex items-start justify-between mb-6">

        <div>

          <div className="inline-flex items-center gap-2 rounded-full bg-[#1f3a36] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#f3e8d3] mb-3">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
            Production intelligence
          </div>

          <h1 className="text-3xl font-semibold text-slate-900 tracking-tight">
            Line planning
          </h1>

          <p className="text-sm text-[#86612b] mt-2">
            Capacity, bottlenecks and order feasibility across every production line
          </p>

        </div>

        <button
          onClick={loadProduction}
          className="
            px-4
            py-2.5
            rounded-xl
            bg-white
            border
            border-slate-200
            text-sm
            text-slate-700
            shadow-sm
            hover:bg-slate-50
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
      {/* KPI HERO */}
      {/* ================================================ */}

      {kpis && (
        <div className="mb-6 rounded-2xl border border-[#e7dcc7] bg-gradient-to-r from-[#1f3a36] via-[#2d4a46] to-[#2e3d4f] p-5 text-white shadow-[0_18px_40px_rgba(31,58,54,0.18)]">

          <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">

            <div>
              <p className="text-[11px] uppercase tracking-[0.2em] text-[#d7c9ae]">
                Factory capacity
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                {kpis.average_utilization}% average utilization
              </h2>
              <p className="mt-1 text-xs text-[#d7c9ae]">
                {formatNumber(kpis.spare_capacity_per_day)} of{' '}
                {formatNumber(kpis.total_capacity_per_day)} units/day still free
              </p>
            </div>

            <div className="flex items-center gap-3 flex-wrap">

              <div className="rounded-xl bg-white/10 px-3 py-2 text-right">
                <div className="text-[10px] uppercase tracking-[0.2em] text-[#d7c9ae]">
                  Active lines
                </div>
                <div className="mt-1 text-lg font-semibold">
                  {kpis.active_lines} / {kpis.total_lines}
                </div>
              </div>

              <div className="rounded-xl bg-amber-500/20 px-3 py-2 text-right border border-amber-300/20">
                <div className="text-[10px] uppercase tracking-[0.2em] text-amber-100">
                  Bottlenecks
                </div>
                <div className="mt-1 text-lg font-semibold">
                  {kpis.bottleneck_count}
                </div>
              </div>

              <div className="rounded-xl bg-emerald-500/20 px-3 py-2 text-right border border-emerald-300/20">
                <div className="text-[10px] uppercase tracking-[0.2em] text-emerald-100">
                  Orders on track
                </div>
                <div className="mt-1 text-lg font-semibold">
                  {kpis.on_track_percentage}%
                </div>
              </div>

            </div>

          </div>

        </div>
      )}


      {/* ================================================ */}
      {/* FEASIBILITY CHECKER */}
      {/* ================================================ */}

      <div className="mb-4 bg-white border border-slate-200 rounded-2xl p-5 shadow-[0_10px_25px_rgba(15,23,42,0.03)]">

        <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
          Order feasibility
        </p>

        <h2 className="mt-2 text-lg font-semibold text-slate-900">
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
              bg-[#1f3a36]
              hover:bg-[#274a44]
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

              <h3 className="mt-3 text-lg font-semibold text-slate-900">
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
                            <span className={`rounded-full px-2 py-1 text-[10px] font-medium ${
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
                      className="rounded-lg bg-[#1f3a36] px-3 py-2 text-xs font-medium text-white hover:bg-[#274a44]"
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
                        <span className="ml-2 text-xs text-slate-400">{option.line_id}</span>
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
      {/* LINE UTILIZATION + ORDERS */}
      {/* ================================================ */}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">

        {/* LINES */}

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-[0_10px_25px_rgba(15,23,42,0.03)]">

          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
            Capacity
          </p>

          <h2 className="mt-2 text-lg font-semibold text-slate-900 mb-4">
            Line utilization
          </h2>

          <div className="space-y-4">
            {lines.map((line) => (
              <div key={line.line_id}>

                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <div className="text-xs text-slate-700">
                    {line.name}
                    <span className="ml-2 text-slate-400">{line.line_id}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      LINE_STYLES[line.status] || LINE_STYLES.OFFLINE
                    }`}>
                      {line.status}
                    </span>
                    <span className="text-xs text-slate-600">
                      {line.current_utilization}%
                    </span>
                  </div>
                </div>

                <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full ${
                      line.status === 'BOTTLENECK' ? 'bg-[#d9a441]' : 'bg-[#1f3a36]'
                    }`}
                    style={{ width: `${line.current_utilization}%` }}
                  />
                </div>

                <div className="mt-1 text-[11px] text-slate-400">
                  {formatNumber(line.spare_capacity_per_day)} of{' '}
                  {formatNumber(line.capacity_per_day)} units/day free ·
                  builds {line.supported_skus?.join(', ')}
                </div>

              </div>
            ))}
          </div>

        </div>


        {/* ORDERS */}

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-[0_10px_25px_rgba(15,23,42,0.03)]">

          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
            Workload
          </p>

          <h2 className="mt-2 text-lg font-semibold text-slate-900 mb-4">
            Production orders
          </h2>

          <div className="space-y-3">
            {orders.map((order) => (
              <div
                key={order.production_order_id}
                className="rounded-xl border border-slate-200 p-3"
              >

                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="text-sm text-slate-800">
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
                    className="h-full rounded-full bg-[#2e7d6b]"
                    style={{ width: `${order.completion_percentage}%` }}
                  />
                </div>

                <div className="mt-1.5 text-[11px] text-slate-500">
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
  )
}


export default ProductionPage
