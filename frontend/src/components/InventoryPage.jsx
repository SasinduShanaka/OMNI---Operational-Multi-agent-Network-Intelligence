import { useEffect, useState } from 'react'

import { ScenePage, SkeletonCard, SkeletonStatRow, SkeletonTable } from './FactoryScene'

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
      <ScenePage
        scene="fabric"
        banner={
          <div className="mx-auto w-full max-w-[1280px] px-5 pb-6">

            <div className="inline-block rounded-xl border border-white/60 bg-white/80 px-4 py-3 backdrop-blur-xl">

              <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
                Fabric stock control
              </h1>

              <p className="mt-1 flex items-center gap-2 text-[12px] text-slate-500">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#1d4ed8]" />
                Loading inventory...
              </p>

            </div>

          </div>
        }
      >
        <div className="mx-auto w-full max-w-[1280px] px-5 pb-10">

          <SkeletonCard className="mb-3" lines={1} />

          <div className="mb-3">
            <SkeletonStatRow count={4} />
          </div>

          <SkeletonTable rows={8} columns={6} />

        </div>
      </ScenePage>
    )
  }

  // --------------------------------------------------
  // Main page
  // --------------------------------------------------

  return (
    <ScenePage
      scene="fabric"
      banner={
        <div className="mx-auto flex w-full max-w-[1280px] flex-wrap items-end justify-between gap-3 px-5 pb-6">

          <div className="rounded-xl border border-white/60 bg-white/80 px-4 py-3 backdrop-blur-xl">

            <div className="inline-flex items-center gap-2 rounded-full bg-[#1d4ed8] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#e2e8f0] mb-2">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
              Inventory intelligence
            </div>

            <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
              Fabric stock control
            </h1>

            <p className="mt-1 text-[12px] text-[#64748b]">
              Real-time stock levels, thresholds and ABC classification across the supply chain
            </p>

          </div>

          <button
            className="
              rounded-lg
              bg-[#1d4ed8]
              px-3.5
              py-2
              text-[13px]
              font-medium
              text-white
              shadow-[0_10px_24px_rgba(29,78,216,0.35)]
              transition
              hover:bg-[#1e40af]
            "
          >
            + Manual reorder
          </button>

        </div>
      }
    >
    <div className="mx-auto w-full max-w-[1280px] px-5 pb-10">

      <div className="mb-4 rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Stock health</p>
            <h2 className="mt-1 text-[18px] font-semibold tracking-tight text-slate-900">{fillRate}% fill rate</h2>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5">
              <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Critical</div>
              <div className="mt-0.5 text-[16px] font-semibold tabular-nums text-slate-900">{stockoutEvents}</div>
            </div>
            <div className="rounded-lg border border-emerald-100 bg-emerald-50 px-2.5 py-1.5">
              <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-700">Healthy</div>
              <div className="mt-0.5 text-[16px] font-semibold tabular-nums text-emerald-700">{healthyItems}</div>
            </div>
          </div>
        </div>
      </div>


      {/* ================================================ */}
      {/* ERROR */}
      {/* ================================================ */}

      {error && (

        <div className="
          mb-3
          px-3
          py-2
          rounded-lg
          bg-red-50
          border
          border-red-200
          text-red-600
          text-[12px]
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
        mb-3
      ">

        {/* Total SKUs */}

        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
            Total SKUs
          </p>

          <p className="mt-1.5 text-[18px] font-semibold tracking-tight tabular-nums text-slate-900">
            {totalSKUs}
          </p>

        </div>


        {/* Stockout */}

        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
            Stockouts (30d)
          </p>

          <p className="mt-1.5 text-[18px] font-semibold tracking-tight tabular-nums text-slate-900">
            {stockoutEvents}
          </p>

        </div>


        {/* Fill rate */}

        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
            Avg. fill rate
          </p>

          <p className="mt-1.5 text-[18px] font-semibold tracking-tight tabular-nums text-slate-900">
            {fillRate}%
          </p>

        </div>


        {/* Carrying cost */}

        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
            Carrying cost
          </p>

          <p className="mt-1.5 text-[18px] font-semibold tracking-tight tabular-nums text-slate-900">
            —
          </p>

          <p className="mt-1 text-[11px] text-slate-400">
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
          inline-flex
          items-center
          gap-2
          rounded-lg
          border
          border-red-100
          bg-red-50
          px-3
          py-1.5
        ">

          <span className="text-[12px] font-medium text-red-600">
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

        <div className="flex items-center justify-between px-4 pb-2 pt-3">

          <h2 className="text-[13px] font-semibold text-slate-900">
            Reorder watchlist
          </h2>

          <span className="text-[11px] text-slate-400">
            {inventory.length} items
          </span>

        </div>


        {/* Table header */}

        <div className="
          grid
          grid-cols-7
          items-center
          gap-3
          border-y
          border-slate-200/70
          bg-slate-50/70
          px-4
          py-1.5
          text-[10px]
          font-medium
          uppercase
          tracking-[0.12em]
          text-slate-500
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
                gap-3
                border-b
                border-slate-100
                px-4
                py-2
                text-[13px]
                last:border-b-0
                hover:bg-slate-50/70
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
                  h-5
                  w-5
                  items-center
                  justify-center
                  rounded-md
                  bg-slate-100
                  text-[10px]
                  font-medium
                  text-slate-600
                ">
                  {item.classification || 'B'}
                </span>

              </div>


              {/* On hand */}

              <div className="tabular-nums text-slate-900">
                {item.current_stock?.toLocaleString()}
              </div>


              {/* Reorder point */}

              <div className="tabular-nums text-slate-500">
                {item.reorder_level?.toLocaleString()}
              </div>


              {/* Status */}

              <div>

                <span
                  className={`
                    inline-flex
                    rounded-full
                    px-2
                    py-0.5
                    text-[10px]
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
    </ScenePage>
  )
}

export default InventoryPage