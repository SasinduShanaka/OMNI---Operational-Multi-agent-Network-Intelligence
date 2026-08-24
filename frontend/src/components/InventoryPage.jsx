import { useEffect, useState } from 'react'

const API_BASE_URL = 'http://127.0.0.1:8000'

function InventoryPage() {
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // --------------------------------------------------
  // Get inventory from backend
  // --------------------------------------------------

  async function loadInventory() {
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/inventory`)

      if (!response.ok) {
        throw new Error('Failed to load inventory')
      }

      const data = await response.json()

      setInventory(data)
    } catch (err) {
      console.error(err)
      setError('Could not load inventory from the backend.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInventory()
  }, [])

  // --------------------------------------------------
  // Calculate dashboard metrics
  // --------------------------------------------------

  const totalSKUs = inventory.length

  const lowStockItems = inventory.filter(
    (item) => item.status === 'LOW_STOCK'
  )

  const stockoutEvents = inventory.filter(
    (item) => Number(item.current_stock) === 0
  ).length

  const healthyItems = inventory.filter(
    (item) => item.status === 'STOCK_OK'
  ).length

  const fillRate =
    totalSKUs > 0
      ? ((healthyItems / totalSKUs) * 100).toFixed(1)
      : '0.0'

  // --------------------------------------------------
  // Status helper
  // --------------------------------------------------

  function getStatus(item) {
    if (item.current_stock === 0) {
      return {
        label: 'Critical',
        className: 'bg-red-100 text-red-600',
      }
    }

    if (item.status === 'LOW_STOCK') {
      return {
        label: 'Low',
        className: 'bg-amber-100 text-amber-600',
      }
    }

    return {
      label: 'Healthy',
      className: 'bg-emerald-100 text-emerald-600',
    }
  }

  // --------------------------------------------------
  // Loading state
  // --------------------------------------------------

  if (loading) {
    return (
      <div className="p-8">

        <h1 className="text-2xl font-semibold text-slate-900">
          Inventory agent
        </h1>

        <p className="text-sm text-slate-500 mt-1">
          Real-time stock levels, thresholds and inventory analysis
        </p>

        <div className="mt-10 text-slate-500">
          Loading inventory...
        </div>

      </div>
    )
  }

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
            Inventory intelligence
          </div>

          <h1 className="text-3xl font-semibold text-slate-900 tracking-tight">
            Fabric stock control
          </h1>

          <p className="text-sm text-[#86612b] mt-2">
            Real-time stock levels, thresholds and ABC classification across the supply chain
          </p>

        </div>

        <button
          className="
            px-4
            py-2.5
            rounded-xl
            bg-[#1f3a36]
            hover:bg-[#274a44]
            text-white
            text-sm
            font-medium
            transition
            shadow-sm
          "
        >
          + Manual reorder
        </button>

      </div>

      <div className="mb-6 rounded-2xl border border-[#e7dcc7] bg-gradient-to-r from-[#fff9f0] via-[#f9f2e8] to-[#eef3f2] p-5 shadow-[0_10px_25px_rgba(31,58,54,0.06)]">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Stock health</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">{fillRate}% fill rate</h2>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-white px-3 py-2 border border-slate-200">
              <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Critical</div>
              <div className="mt-1 text-lg font-semibold text-slate-900">{stockoutEvents}</div>
            </div>
            <div className="rounded-xl bg-emerald-50 px-3 py-2 border border-emerald-100">
              <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-700">Healthy</div>
              <div className="mt-1 text-lg font-semibold text-emerald-700">{healthyItems}</div>
            </div>
          </div>
        </div>
      </div>


      {/* ================================================ */}
      {/* ERROR */}
      {/* ================================================ */}

      {error && (

        <div className="
          mb-6
          p-4
          rounded-lg
          bg-red-50
          border
          border-red-200
          text-red-600
          text-sm
        ">
          {error}
        </div>

      )}


      {/* ================================================ */}
      {/* METRICS */}
      {/* ================================================ */}

      <div className="
        grid
        grid-cols-1
        md:grid-cols-2
        xl:grid-cols-4
        gap-4
        mb-4
      ">

        {/* Total SKUs */}

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-[0_10px_25px_rgba(15,23,42,0.03)]">

          <div className="inline-flex rounded-lg border border-[#f4d9a8] bg-[#fff7ea] px-2 py-1 text-[10px] font-medium uppercase tracking-[0.16em] text-[#a76913]">
            Total SKUs
          </div>

          <p className="text-3xl font-semibold text-slate-900 mt-4 tracking-tight">
            {totalSKUs}
          </p>

        </div>


        {/* Stockout */}

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-[0_10px_25px_rgba(15,23,42,0.03)]">

          <div className="inline-flex rounded-lg border border-[#f3c3c3] bg-[#fff1f1] px-2 py-1 text-[10px] font-medium uppercase tracking-[0.16em] text-[#b63f3f]">
            Stockouts (30d)
          </div>

          <p className="text-3xl font-semibold text-slate-900 mt-4 tracking-tight">
            {stockoutEvents}
          </p>

        </div>


        {/* Fill rate */}

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-[0_10px_25px_rgba(15,23,42,0.03)]">

          <div className="inline-flex rounded-lg border border-[#bfe5cf] bg-[#edfaf4] px-2 py-1 text-[10px] font-medium uppercase tracking-[0.16em] text-[#1d6a4a]">
            Avg. fill rate
          </div>

          <p className="text-3xl font-semibold text-slate-900 mt-4 tracking-tight">
            {fillRate}%
          </p>

        </div>


        {/* Carrying cost */}

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-[0_10px_25px_rgba(15,23,42,0.03)]">

          <div className="inline-flex rounded-lg border border-[#dfe3ea] bg-[#f3f4f6] px-2 py-1 text-[10px] font-medium uppercase tracking-[0.16em] text-[#425466]">
            Carrying cost
          </div>

          <p className="text-3xl font-semibold text-slate-900 mt-4 tracking-tight">
            —
          </p>

          <p className="text-xs text-slate-500 mt-2">
            Not available yet
          </p>

        </div>

      </div>


      {/* ================================================ */}
      {/* LOW STOCK SUMMARY */}
      {/* ================================================ */}

      {lowStockItems.length > 0 && (

        <div className="
          mb-4
          px-4
          py-3
          bg-red-50
          border
          border-red-100
          rounded-xl
          text-sm
        ">

          <span className="text-red-600 font-medium">
            ▼ {lowStockItems.length} item
            {lowStockItems.length !== 1 ? 's' : ''} below reorder point
          </span>

        </div>

      )}


      {/* ================================================ */}
      {/* REORDER WATCHLIST */}
      {/* ================================================ */}

      <div className="
        bg-white
        border
        border-slate-200
        rounded-2xl
        overflow-hidden
        shadow-[0_10px_25px_rgba(15,23,42,0.03)]
      ">

        <div className="px-5 pt-5 pb-3">

          <h2 className="text-[10px] uppercase tracking-[0.2em] font-medium text-slate-500">
            Reorder watchlist
          </h2>

        </div>


        {/* Table header */}

        <div className="
          grid
          grid-cols-7
          px-5
          py-3
          border-t
          border-b
          border-slate-200
          text-xs
          text-slate-400
        ">

          <span>SKU</span>

          <span className="col-span-2">
            ITEM
          </span>

          <span>CLASS</span>

          <span>ON HAND</span>

          <span>REORDER PT.</span>

          <span>STATUS</span>

        </div>


        {/* Inventory rows */}

        {inventory.map((item) => {

          const status = getStatus(item)

          return (

            <div
              key={item.material_code}
              className="
                grid
                grid-cols-7
                items-center
                px-5
                py-4
                border-b
                border-slate-200
                last:border-b-0
                text-sm
                hover:bg-slate-50
                transition
              "
            >

              {/* SKU */}

              <div className="text-slate-900">
                {item.material_code}
              </div>


              {/* Item */}

              <div className="col-span-2 text-slate-900">
                {item.material_name}
              </div>


              {/* Class */}

              <div>

                <span className="
                  inline-flex
                  items-center
                  justify-center
                  w-7
                  h-7
                  rounded-full
                  bg-slate-100
                  text-slate-600
                  text-xs
                ">
                  {item.classification || 'B'}
                </span>

              </div>


              {/* On hand */}

              <div className="text-slate-900">
                {item.current_stock?.toLocaleString()}
              </div>


              {/* Reorder point */}

              <div className="text-slate-900">
                {item.reorder_level?.toLocaleString()}
              </div>


              {/* Status */}

              <div>

                <span
                  className={`
                    inline-flex
                    px-3
                    py-1
                    rounded-full
                    text-xs
                    font-medium
                    ${status.className}
                  `}
                >
                  {status.label}
                </span>

              </div>

            </div>

          )

        })}


        {/* Empty inventory */}

        {inventory.length === 0 && !error && (

          <div className="p-10 text-center text-slate-400">
            No inventory items found.
          </div>

        )}

      </div>


      {/* ================================================ */}
      {/* REFRESH */}
      {/* ================================================ */}

      <div className="flex justify-end mt-4">

        <button
          onClick={loadInventory}
          className="
            px-4
            py-2
            rounded-lg
            border
            border-slate-200
            bg-white
            text-slate-700
            text-sm
            hover:bg-slate-50
            transition
          "
        >
          ↻ Refresh
        </button>

      </div>

    </div>
  )
}

export default InventoryPage