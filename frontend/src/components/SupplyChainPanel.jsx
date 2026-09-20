import React, { useState, useRef, useEffect } from 'react'
import SuppliersTab from './supply_chain/SuppliersTab'
import PurchaseOrdersTab from './supply_chain/PurchaseOrdersTab'
import ShipmentsTab from './supply_chain/ShipmentsTab'
import CopilotChat from './supply_chain/CopilotChat'
import { supplyChainApi } from '../api/supplyChainApi'
import { SceneStage } from './FactoryScene'

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
    <div className={`rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)] flex flex-col gap-2.5`}>
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">{title}</p>
        <span className={`w-7 h-7 rounded-lg ${a.bg} ${a.border} border flex items-center justify-center`}>
          {icon}
        </span>
      </div>
      <div>
        <p className="text-[20px] font-semibold tracking-tight tabular-nums text-slate-900">{value}</p>
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

export default function SupplyChainPanel({ initialQuery, clearQuery }) {
  const [activeTab, setActiveTab] = useState('suppliers')
  const [copilotOpen, setCopilotOpen] = useState(false)
  const [prefillSupplier, setPrefillSupplier] = useState(null)
  
  // Global Data State
  const [suppliersData, setSuppliersData] = useState([])
  const [posData, setPosData] = useState([])
  const [shipmentsData, setShipmentsData] = useState([])
  const [loadingData, setLoadingData] = useState(true)

  const [metrics, setMetrics] = useState({ suppliers: '—', pendingPos: '—', activeShipments: '—', delayed: '—' })

  const loadAllData = () => {
    setLoadingData(true)

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
      setLoadingData(false)
    })
  }

  // If initialQuery comes in from operations agent routing, open copilot
  useEffect(() => {
    if (initialQuery) {
      setCopilotOpen(true)
    }
  }, [initialQuery])

  // Initial load
  useEffect(() => {
    loadAllData()
  }, [])

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
      <SceneStage scene="supplier">

      {/* ── Hero Banner ── matches Dashboard's dark gradient banner */}
      <div className="mx-auto w-full max-w-[1280px] flex-shrink-0 px-5 pt-5">

        {/* Header — sits straight on the inbound yard scene */}
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3 pt-4">

            <div className="rounded-2xl border border-white/60 bg-white/80 px-4 py-3 backdrop-blur-xl">
              <span className="inline-flex items-center gap-2 rounded-full bg-[#1d4ed8] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#e2e8f0]">
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
                Procurement live
              </span>
              <h1 className="mt-3 text-3xl font-semibold text-slate-900 tracking-tight">Supply chain overview</h1>
              <p className="text-sm text-[#64748b] mt-2">
                Supplier sourcing, purchase orders, and freight logistics · powered by Omni agents
              </p>
            </div>

            <button
              onClick={() => { setPrefillSupplier(null); setCopilotOpen(true) }}
              className="flex items-center gap-2 bg-[#0f172a] text-white px-4 py-2.5 rounded-xl text-sm font-semibold shadow-[0_10px_24px_rgba(15,23,42,0.4)] hover:bg-[#334155] transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
              </svg>
              New Request
            </button>

        </div>

        {/* Dark gradient hero — same style as dashboard's production pulse */}
        <div className="rounded-2xl border border-[#e2e8f0] bg-gradient-to-r from-[#1d4ed8] via-[#2563eb] to-[#1e40af] p-4 text-white shadow-[0_18px_44px_rgba(15,23,42,0.22)] mb-4">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <p className="text-[11px] uppercase tracking-[0.2em] text-[#cbd5e1]">Procurement pulse</p>
              <h2 className="mt-1.5 text-lg font-semibold tracking-tight">
                {metrics.pendingPos > 0
                  ? `${metrics.pendingPos} purchase order${metrics.pendingPos > 1 ? 's' : ''} awaiting your approval`
                  : 'All purchase orders are up to date'}
              </h2>
              <p className="text-sm text-white/60 mt-1">
                {metrics.suppliers} active suppliers · {metrics.activeShipments} shipments in transit
                {metrics.delayed > 0 && <span className="text-orange-300"> · {metrics.delayed} delayed</span>}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-white/10 px-3 py-1.5 text-right">
                <div className="text-[10px] uppercase tracking-[0.2em] text-[#cbd5e1]">Suppliers</div>
                <div className="mt-1 text-lg font-semibold">{metrics.suppliers}</div>
              </div>
              <div className="rounded-xl bg-emerald-500/20 px-3 py-1.5 text-right border border-emerald-300/20">
                <div className="text-[10px] uppercase tracking-[0.2em] text-emerald-100">Active ships</div>
                <div className="mt-1 text-lg font-semibold">{metrics.activeShipments}</div>
              </div>
              {metrics.delayed > 0 && (
                <div className="rounded-xl bg-orange-500/20 px-3 py-1.5 text-right border border-orange-300/20">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-orange-200">Delayed</div>
                  <div className="mt-1 text-lg font-semibold">{metrics.delayed}</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Metric cards row — same pattern as dashboard */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-4">
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
           <div className="flex items-center justify-center h-64 text-slate-400">Loading modules...</div>
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

      </SceneStage>

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
          onClick={() => { setPrefillSupplier(null); setCopilotOpen(true) }}
          className="fixed bottom-6 right-6 z-30 w-14 h-14 bg-gradient-to-br from-[#3b82f6] to-[#2563eb] text-white rounded-full shadow-xl flex items-center justify-center hover:scale-105 transition-transform"
          title="Open Omni Copilot"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </button>
      )}
    </div>
  )
}
