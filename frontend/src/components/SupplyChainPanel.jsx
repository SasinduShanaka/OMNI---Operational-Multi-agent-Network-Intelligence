import React, { useState, useEffect } from 'react'
import SuppliersTab from './supply_chain/SuppliersTab'
import PurchaseOrdersTab from './supply_chain/PurchaseOrdersTab'
import ShipmentsTab from './supply_chain/ShipmentsTab'
import CopilotChat from './supply_chain/CopilotChat'
import { supplyChainApi } from '../api/supplyChainApi'
import { ScenePage, SkeletonCard, SkeletonTable } from './FactoryScene'
import { Donut, Meter, SegmentedBar } from './metrics/MetricVisuals'
import { SERIES } from './metrics/metricColors'
import OmniMark from './OmniMark'

// ------------------------------------------------------------------
// Metric Card — matches the Dashboard MetricCard style exactly
// ------------------------------------------------------------------
const ACCENT = {
  amber:  { bg: 'bg-amber-50',   text: 'text-amber-700',   dot: 'bg-amber-400',   border: 'border-amber-100' },
  green:  { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-400', border: 'border-emerald-100' },
  blue:   { bg: 'bg-blue-50',    text: 'text-blue-700',    dot: 'bg-blue-400',    border: 'border-blue-100' },
  orange: { bg: 'bg-orange-50',  text: 'text-orange-700',  dot: 'bg-orange-400',  border: 'border-orange-100' },
}

function MetricCard({ title, value, subtitle, accent = 'amber', icon }) {
  const a = ACCENT[accent]
  return (
    <div className={`rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)] flex flex-col gap-2`}>
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">{title}</p>
        <span className={`w-7 h-7 rounded-lg ${a.bg} ${a.border} border flex items-center justify-center`}>
          {icon}
        </span>
      </div>
      <div>
        <p className="text-[18px] font-semibold tracking-tight tabular-nums text-slate-900">{value}</p>
        <p className="mt-1 text-[11px] text-slate-400">{subtitle}</p>
      </div>
    </div>
  )
}

const TABS = [
  {
    id: 'suppliers',
    label: 'Suppliers',
    icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>,
  },
  {
    id: 'purchase-orders',
    label: 'Purchase Orders',
    icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
  },
  {
    id: 'shipments',
    label: 'Shipments',
    icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>,
  },
]

export default function SupplyChainPanel({ initialQuery, clearQuery, setActivePage }) {
  const [activeTab, setActiveTab] = useState('suppliers')
  const [copilotOpen, setCopilotOpen] = useState(false)
  const [prefillSupplier, setPrefillSupplier] = useState(null)
  
  // Global Data State
  const [suppliersData, setSuppliersData] = useState([])
  const [posData, setPosData] = useState([])
  const [shipmentsData, setShipmentsData] = useState([])
  const [loadingData, setLoadingData] = useState(true)

  const [metrics, setMetrics] = useState({ suppliers: '—', pendingPos: '—', activeShipments: '—', delayed: '—' })

  const loadAllData = (showLoader = true) => {
    if (showLoader) {
      setLoadingData(true)
    }

    Promise.allSettled([
      supplyChainApi.getSuppliers(),
      supplyChainApi.getPurchaseOrders(),
      supplyChainApi.getShipments(),
    ]).then((results) => {
      const [suppliersResult, posResult, shipmentsResult] = results
      const suppliers = suppliersResult.status === 'fulfilled' ? suppliersResult.value : []
      const pos = posResult.status === 'fulfilled' ? posResult.value : []
      const shipments = shipmentsResult.status === 'fulfilled' ? shipmentsResult.value : []

      results.forEach((result, index) => {
        if (result.status === 'rejected') {
          console.error(['Suppliers', 'Purchase orders', 'Shipments'][index] + ' failed to load:', result.reason)
        }
      })

      setSuppliersData(suppliers)
      setPosData(pos)
      setShipmentsData(shipments)
      setMetrics({
        suppliers: suppliers.length,
        pendingPos: pos.filter(p => p.status === 'pending_approval').length,
        activeShipments: shipments.filter(s => s.status !== 'delivered').length,
        delayed: shipments.filter(s => s.status === 'delayed').length,
      })
      if (showLoader) {
        setLoadingData(false)
      }
    })
  }

  // If initialQuery comes in from operations agent routing, open copilot
  useEffect(() => {
    if (initialQuery) {
      setCopilotOpen(true)
    }
  }, [initialQuery])

  // Initial load & Auto-update
  useEffect(() => {
    loadAllData(true)
    const intervalId = setInterval(() => {
      loadAllData(false)
    }, 5000)
    return () => clearInterval(intervalId)
  }, [])

  // --- figures behind the pulse visuals ---------------------------------
  const poStages = {
    draft:    posData.filter((order) => order.status === 'draft').length,
    pending:  posData.filter((order) => order.status === 'pending_approval').length,
    approved: posData.filter((order) => ['approved', 'ordered', 'received'].includes(order.status)).length,
    total:    posData.length,
  }

  const freight = (() => {
    const late = shipmentsData.filter((shipment) => (shipment.status || '').toLowerCase().includes('delay')).length
    const onTime = Math.max(0, shipmentsData.length - late)
    return {
      onTime,
      onTimePct: shipmentsData.length ? Math.round((onTime / shipmentsData.length) * 100) : 0,
    }
  })()

  const supplierMix = {
    fast:     suppliersData.filter((supplier) => Number(supplier.lead_time_days) <= 14).length,
    standard: suppliersData.filter((supplier) => Number(supplier.lead_time_days) > 14 && Number(supplier.lead_time_days) <= 21).length,
    slow:     suppliersData.filter((supplier) => Number(supplier.lead_time_days) > 21).length,
    total:    suppliersData.length,
  }

  const totalSpend = posData
    .filter(po => po.status === 'approved')
    .reduce((sum, po) => sum + (Number(po.total_value) || 0), 0)

  const avgRating = suppliersData.length
    ? (suppliersData.reduce((sum, s) => sum + Number(s.rating), 0) / suppliersData.length).toFixed(1)
    : '0.0'


  const handleRequestSupply = (supplier) => {
    setPrefillSupplier(supplier)
    setCopilotOpen(true)
  }

  const handlePipelineComplete = () => {
    setActiveTab('purchase-orders')
    loadAllData()
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <ScenePage
        scene="supplier"
        banner={
          <div className="mx-auto flex w-full max-w-[1280px] flex-wrap items-end justify-between gap-3 px-5 pb-6">

            <div className="rounded-xl border border-white/60 bg-white/80 px-4 py-3 backdrop-blur-xl">
              <span className="inline-flex items-center gap-2 rounded-full bg-[#1d4ed8] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#e2e8f0]">
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
                Procurement live
              </span>
              <h1 className="mt-2 text-[22px] font-semibold tracking-tight text-slate-900">Supply chain overview</h1>
              <p className="mt-1 text-[12px] text-[#64748b]">
                Supplier sourcing, purchase orders, and freight logistics · powered by Omni agents
              </p>
            </div>

            <button
              onClick={() => { setPrefillSupplier(null); setCopilotOpen(true) }}
              className="flex items-center gap-2 rounded-lg bg-[#0f172a] px-3.5 py-2 text-[13px] font-semibold text-white shadow-[0_10px_24px_rgba(15,23,42,0.4)] transition-colors hover:bg-[#334155]"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
              </svg>
              New Request
            </button>

          </div>
        }
      >

      <div className="mx-auto w-full max-w-[1280px] flex-shrink-0 px-5">

        {/* Metric cards row — same pattern as dashboard */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-3">
          <MetricCard
            title="Supplier network"
            value={metrics.suppliers}
            subtitle="ERP-registered vendors"
            accent="amber"
            icon={<svg className="w-3.5 h-3.5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5" /></svg>}
          />
          <MetricCard
            title="Pending approvals"
            value={metrics.pendingPos}
            subtitle="POs awaiting sign-off"
            accent="orange"
            icon={<svg className="w-3.5 h-3.5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <MetricCard
            title="Active shipments"
            value={metrics.activeShipments}
            subtitle="In-transit logistics"
            accent="blue"
            icon={<svg className="w-3.5 h-3.5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>}
          />
          <MetricCard
            title="Shipment delays"
            value={metrics.delayed}
            subtitle="Requiring attention"
            accent={metrics.delayed > 0 ? 'orange' : 'green'}
            icon={<svg className="w-3.5 h-3.5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <MetricCard
            title="Total Spend"
            value={`LKR ${(totalSpend / 1000).toFixed(1)}k`}
            subtitle="Approved Purchase Value"
            accent="green"
            icon={<svg className="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <MetricCard
            title="Supplier Quality"
            value={`${avgRating} / 5.0`}
            subtitle="Average Network Rating"
            accent="blue"
            icon={<svg className="w-3.5 h-3.5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg>}
          />
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 rounded-xl border border-slate-200/80 bg-white px-1.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`my-1.5 flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-[13px] font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-[#1d4ed8] text-white shadow-[0_6px_14px_-6px_rgba(29,78,216,0.8)]'
                  : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Tab Content ── */}
      <div className="mx-auto w-full max-w-[1280px] flex-1 px-5 py-4">
        {loadingData ? (
           <div>
             <SkeletonCard className="mb-3" lines={1} />
             <SkeletonTable rows={8} columns={4} />
           </div>
        ) : (
          <>
            {activeTab === 'suppliers' && (
              <SuppliersTab suppliers={suppliersData} onUpdate={loadAllData} onRequestSupply={handleRequestSupply} />
            )}
            {activeTab === 'purchase-orders' && (
              <PurchaseOrdersTab orders={posData} onUpdate={loadAllData} />
            )}
            {activeTab === 'shipments' && (
              <ShipmentsTab shipments={shipmentsData} onUpdate={loadAllData} />
            )}
          </>
        )}
      </div>

      </ScenePage>

      {/* ── Floating Copilot ── */}
      <CopilotChat
        isOpen={copilotOpen}
        onClose={() => { setCopilotOpen(false); setPrefillSupplier(null) }}
        onPipelineComplete={handlePipelineComplete}
        prefillSupplier={prefillSupplier}
        prefillQuery={initialQuery}
        clearQuery={clearQuery}
      />

      {!copilotOpen && (
        <button
          onClick={() => setActivePage?.('operations')}
          className="group fixed bottom-6 right-6 z-30 flex items-center gap-2.5 rounded-full bg-gradient-to-br from-[#1e3a8a] to-[#111f4d] py-2 pl-2 pr-3 text-white shadow-[0_18px_36px_-12px_rgba(29,78,216,0.85)] transition hover:pr-4 hover:shadow-[0_22px_44px_-12px_rgba(29,78,216,0.95)]"
          aria-label="Ask Omni"
        >
          <span className="relative flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-white shadow-[0_2px_8px_-2px_rgba(15,23,42,0.4)]">
            <OmniMark size={26} />
            <span className="absolute -right-0.5 -top-0.5 flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-70" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-[#111f4d]" />
            </span>
          </span>

          <span className="max-w-0 overflow-hidden whitespace-nowrap text-[13px] font-medium opacity-0 transition-all duration-300 group-hover:max-w-[120px] group-hover:opacity-100">
            Ask Omni
          </span>
        </button>
      )}
    </div>
  )
}
