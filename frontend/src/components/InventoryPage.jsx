import { useEffect, useMemo, useState } from 'react'

import { SceneStage } from './FactoryScene'

const API_BASE_URL = 'http://127.0.0.1:8000'

function InventoryPage() {
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [sortBy, setSortBy] = useState('risk')
  const [showOnlyLowStock, setShowOnlyLowStock] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [formData, setFormData] = useState({
    material_code: '',
    material_name: '',
    current_stock: '',
    reorder_level: '',
    unit: 'meters',
    classification: 'B',
  })

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

  const totalShortage = lowStockItems.reduce(
    (sum, item) => sum + Number(item.shortage || 0),
    0
  )

  const uniqueUnits = Array.from(
    new Set(inventory.map((item) => item.unit).filter(Boolean))
  )

  const filteredInventory = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()

    return inventory
      .filter((item) => {
        const matchesSearch =
          !query ||
          item.material_name?.toLowerCase().includes(query) ||
          item.material_code?.toLowerCase().includes(query)

        const matchesStatus =
          statusFilter === 'ALL' || item.status === statusFilter

        const matchesLowStock =
          !showOnlyLowStock || item.status === 'LOW_STOCK' || Number(item.current_stock) === 0

        return matchesSearch && matchesStatus && matchesLowStock
      })
      .sort((a, b) => {
        if (sortBy === 'name') {
          return String(a.material_name).localeCompare(String(b.material_name))
        }

        if (sortBy === 'stock') {
          return Number(a.current_stock || 0) - Number(b.current_stock || 0)
        }

        if (sortBy === 'shortage') {
          return Number(b.shortage || 0) - Number(a.shortage || 0)
        }

        const riskRank = {
          OUT_OF_STOCK: 0,
          LOW_STOCK: 1,
          STOCK_OK: 2,
        }

        return (riskRank[a.status] ?? 3) - (riskRank[b.status] ?? 3)
      })
  }, [inventory, searchTerm, statusFilter, sortBy, showOnlyLowStock])

  function resetFilters() {
    setSearchTerm('')
    setStatusFilter('ALL')
    setSortBy('risk')
    setShowOnlyLowStock(false)
  }

  function updateFormField(field, value) {
    setFormData((current) => ({
      ...current,
      [field]: value,
    }))
  }

  function resetAddForm() {
    setFormData({
      material_code: '',
      material_name: '',
      current_stock: '',
      reorder_level: '',
      unit: 'meters',
      classification: 'B',
    })
    setFormError('')
  }

  async function submitInventoryItem(event) {
    event.preventDefault()
    setFormError('')

    if (!formData.material_name.trim()) {
      setFormError('Material name is required.')
      return
    }

    if (formData.current_stock === '' || formData.reorder_level === '') {
      setFormError('Current stock and reorder level are required.')
      return
    }

    setIsSaving(true)

    try {
      const response = await fetch(`${API_BASE_URL}/inventory`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          material_code: formData.material_code.trim() || null,
          material_name: formData.material_name.trim(),
          current_stock: Number(formData.current_stock),
          reorder_level: Number(formData.reorder_level),
          unit: formData.unit,
          classification: formData.classification,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data?.detail || 'Failed to save material')
      }

      await loadInventory()
      setSearchTerm(data.item?.material_name || formData.material_name)
      setStatusFilter('ALL')
      setShowOnlyLowStock(false)
      setShowAddForm(false)
      resetAddForm()
    } catch (err) {
      console.error(err)
      setFormError(err.message || 'Could not save inventory material.')
    } finally {
      setIsSaving(false)
    }
  }

  function exportCsv() {
    const headers = [
      'Material Code',
      'Material Name',
      'Status',
      'Current Stock',
      'Reorder Level',
      'Shortage',
      'Unit',
      'Recommendation',
    ]

    const rows = filteredInventory.map((item) => [
      item.material_code,
      item.material_name,
      item.status,
      item.current_stock,
      item.reorder_level,
      item.shortage,
      item.unit,
      item.recommendation,
    ])

    const csv = [headers, ...rows]
      .map((row) =>
        row
          .map((value) => `"${String(value ?? '').replaceAll('"', '""')}"`)
          .join(',')
      )
      .join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `inventory-${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

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
      <SceneStage scene="fabric">
      <div className="mx-auto w-full max-w-[1280px] px-5 pb-8 pt-5">

        <div className="inline-block rounded-2xl border border-white/60 bg-white/80 px-4 py-3 backdrop-blur-xl">

          <h1 className="text-xl font-semibold tracking-tight text-slate-900">
            Inventory agent
          </h1>

          <p className="mt-1 text-[11px] text-slate-500">
            Real-time stock levels, thresholds and inventory analysis
          </p>

          <p className="mt-3 flex items-center gap-2 text-[12px] text-slate-500">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#1d4ed8]" />
            Loading inventory...
          </p>

        </div>

      </div>
      </SceneStage>
    )
  }

  // --------------------------------------------------
  // Main page
  // --------------------------------------------------

  return (
    <SceneStage scene="fabric">
    <div className="mx-auto w-full max-w-[1280px] px-5 pb-8">

      {/* ================================================ */}
      {/* HEADER — over the fabric store scene */}
      {/* ================================================ */}

      <div className="mb-4 flex flex-wrap items-end justify-between gap-3 pt-5">

          <div className="rounded-2xl border border-white/60 bg-white/80 px-4 py-3 backdrop-blur-xl">

            <div className="inline-flex items-center gap-2 rounded-full bg-[#1d4ed8] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#e2e8f0] mb-3">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
              Inventory intelligence
            </div>

            <h1 className="text-3xl font-semibold text-slate-900 tracking-tight">
              Fabric stock control
            </h1>

            <p className="text-sm text-[#64748b] mt-2">
              Real-time stock levels, thresholds and ABC classification across the supply chain
            </p>

          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setShowAddForm((current) => !current)}
              className="
                px-4
                py-2.5
                rounded-xl
                bg-slate-900
                hover:bg-slate-700
                text-white
                text-sm
                font-medium
                transition
                shadow-[0_10px_24px_rgba(15,23,42,0.2)]
              "
            >
              Add material
            </button>

            <button
              onClick={() => setShowOnlyLowStock(true)}
              className="
                px-4
                py-2.5
                rounded-xl
                bg-[#1d4ed8]
                hover:bg-[#1e40af]
                text-white
                text-sm
                font-medium
                transition
                shadow-[0_10px_24px_rgba(29,78,216,0.35)]
              "
            >
              View reorder needs
            </button>
          </div>

      </div>

      <div className="mb-4 rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Stock health</p>
            <h2 className="mt-1.5 text-lg font-semibold text-slate-900">{fillRate}% fill rate</h2>
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
            <div className="rounded-xl bg-amber-50 px-3 py-2 border border-amber-100">
              <div className="text-[10px] uppercase tracking-[0.16em] text-amber-700">Shortage</div>
              <div className="mt-1 text-lg font-semibold text-amber-700">
                {totalShortage.toLocaleString()}
              </div>
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
      {/* ADD MATERIAL */}
      {/* ================================================ */}

      {showAddForm && (
        <form
          onSubmit={submitInventoryItem}
          className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_10px_25px_rgba(15,23,42,0.04)]"
        >
          <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">
                Inventory entry
              </p>
              <h2 className="mt-1 text-base font-semibold text-slate-900">
                Add or update material
              </h2>
            </div>
            <button
              type="button"
              onClick={() => {
                setShowAddForm(false)
                resetAddForm()
              }}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <label className="xl:col-span-2">
              <span className="mb-1 block text-xs font-medium text-slate-500">Material name</span>
              <input
                value={formData.material_name}
                onChange={(event) => updateFormField('material_name', event.target.value)}
                placeholder="Red Cotton Fabric"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-[#1d4ed8] focus:bg-white focus:ring-2 focus:ring-blue-100"
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-medium text-slate-500">Code</span>
              <input
                value={formData.material_code}
                onChange={(event) => updateFormField('material_code', event.target.value)}
                placeholder="Auto"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm uppercase text-slate-800 outline-none transition focus:border-[#1d4ed8] focus:bg-white focus:ring-2 focus:ring-blue-100"
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-medium text-slate-500">Current stock</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={formData.current_stock}
                onChange={(event) => updateFormField('current_stock', event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-[#1d4ed8] focus:bg-white focus:ring-2 focus:ring-blue-100"
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-medium text-slate-500">Reorder level</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={formData.reorder_level}
                onChange={(event) => updateFormField('reorder_level', event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-[#1d4ed8] focus:bg-white focus:ring-2 focus:ring-blue-100"
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-medium text-slate-500">Unit</span>
              <select
                value={formData.unit}
                onChange={(event) => updateFormField('unit', event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-[#1d4ed8] focus:ring-2 focus:ring-blue-100"
              >
                <option value="meters">meters</option>
                <option value="pieces">pieces</option>
                <option value="spools">spools</option>
                <option value="rolls">rolls</option>
                <option value="kg">kg</option>
                <option value="units">units</option>
              </select>
            </label>

            <label>
              <span className="mb-1 block text-xs font-medium text-slate-500">Class</span>
              <select
                value={formData.classification}
                onChange={(event) => updateFormField('classification', event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-[#1d4ed8] focus:ring-2 focus:ring-blue-100"
              >
                <option value="A">A</option>
                <option value="B">B</option>
                <option value="C">C</option>
              </select>
            </label>
          </div>

          {formError && (
            <p className="mt-3 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">
              {formError}
            </p>
          )}

          <div className="mt-4 flex justify-end">
            <button
              type="submit"
              disabled={isSaving}
              className="rounded-xl bg-[#1d4ed8] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#1e40af] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSaving ? 'Saving...' : 'Save material'}
            </button>
          </div>
        </form>
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

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
            Total SKUs
          </p>

          <p className="mt-1.5 text-[20px] font-semibold tracking-tight tabular-nums text-slate-900">
            {totalSKUs}
          </p>

        </div>


        {/* Stockout */}

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
            Stockouts (30d)
          </p>

          <p className="mt-1.5 text-[20px] font-semibold tracking-tight tabular-nums text-slate-900">
            {stockoutEvents}
          </p>

        </div>


        {/* Fill rate */}

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
            Avg. fill rate
          </p>

          <p className="mt-1.5 text-[20px] font-semibold tracking-tight tabular-nums text-slate-900">
            {fillRate}%
          </p>

        </div>


        {/* Carrying cost */}

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
            Carrying cost
          </p>

          <p className="mt-1.5 text-[20px] font-semibold tracking-tight tabular-nums text-slate-900">
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
      {/* CONTROLS */}
      {/* ================================================ */}

      <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-3.5 shadow-[0_10px_25px_rgba(15,23,42,0.03)]">
        <div className="grid gap-3 lg:grid-cols-[1.5fr_1fr_1fr_auto_auto]">
          <input
            type="search"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search material or code..."
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-[#1d4ed8] focus:bg-white focus:ring-2 focus:ring-blue-100"
          />

          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-[#1d4ed8] focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">All statuses</option>
            <option value="LOW_STOCK">Low stock</option>
            <option value="OUT_OF_STOCK">Out of stock</option>
            <option value="STOCK_OK">Healthy</option>
          </select>

          <select
            value={sortBy}
            onChange={(event) => setSortBy(event.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-[#1d4ed8] focus:ring-2 focus:ring-blue-100"
          >
            <option value="risk">Sort by risk</option>
            <option value="shortage">Sort by shortage</option>
            <option value="stock">Sort by stock</option>
            <option value="name">Sort by name</option>
          </select>

          <button
            onClick={() => setShowOnlyLowStock((current) => !current)}
            className={`rounded-xl border px-3 py-2 text-sm font-medium transition ${
              showOnlyLowStock
                ? 'border-amber-200 bg-amber-50 text-amber-700'
                : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            Reorder only
          </button>

          <button
            onClick={exportCsv}
            disabled={filteredInventory.length === 0}
            className="rounded-xl bg-slate-900 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Export CSV
          </button>
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <span>
            Showing {filteredInventory.length} of {inventory.length} materials
            {uniqueUnits.length > 0 ? ` across ${uniqueUnits.join(', ')}` : ''}
          </span>
          <button
            onClick={resetFilters}
            className="font-medium text-[#1d4ed8] transition hover:text-[#1e40af]"
          >
            Reset filters
          </button>
        </div>
      </div>


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
            {filteredInventory.length} items
          </span>

        </div>


        {/* Table header */}

        <div className="
          grid
          grid-cols-8
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

          <span>SHORTAGE</span>

          <span>STATUS</span>

        </div>


        {/* Inventory rows */}

        {filteredInventory.map((item) => {

          const status = getStatus(item)

          return (

            <div
              key={item.material_code}
              className="
                grid
                grid-cols-8
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
                {item.current_stock?.toLocaleString()} {item.unit}
              </div>


              {/* Reorder point */}

              <div className="tabular-nums text-slate-500">
                {item.reorder_level?.toLocaleString()} {item.unit}
              </div>


              {/* Shortage */}

              <div className={`tabular-nums ${item.shortage > 0 ? 'font-medium text-red-600' : 'text-slate-400'}`}>
                {item.shortage > 0
                  ? `${item.shortage?.toLocaleString()} ${item.unit}`
                  : '-'}
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

        {filteredInventory.length === 0 && !error && (

          <div className="p-10 text-center text-slate-400">
            {inventory.length === 0
              ? 'No inventory items found.'
              : 'No materials match the current filters.'}
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
    </SceneStage>
  )
}

export default InventoryPage
