import React, { useState, useEffect, useCallback } from 'react'
import { supplyChainApi } from '../../api/supplyChainApi'

// Status badge
function StatusBadge({ status }) {
  const styles = {
    booked:     'bg-blue-100 text-blue-800 border-blue-200',
    in_transit: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    delayed:    'bg-orange-100 text-orange-800 border-orange-200 animate-pulse-slow',
    delivered:  'bg-green-100 text-green-800 border-green-200',
  }
  const labels = {
    booked:     '🔵 Booked',
    in_transit: '🚀 In Transit',
    delayed:    '⚠ Delayed',
    delivered:  '✓ Delivered',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles[status] || 'bg-gray-100 text-gray-600'}`}>
      {labels[status] || status}
    </span>
  )
}

// Mode icon
function ModeIcon({ mode }) {
  if (mode === 'air') return <span title="Air Freight" className="text-lg">✈️</span>
  if (mode === 'road') return <span title="Road Freight" className="text-lg">🚚</span>
  return <span title="Sea Freight" className="text-lg">🚢</span>
}

// Tracking slide-out panel
function TrackingPanel({ shipment, onClose }) {
  const [trackData, setTrackData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    supplyChainApi.trackShipment(shipment.shipment_id)
      .then(d => { setTrackData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [shipment.shipment_id])

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="flex-1 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      {/* Panel */}
      <div className="w-[420px] h-full bg-white shadow-2xl flex flex-col animate-fade-in-up overflow-y-auto">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between bg-[#1a2430] text-white">
          <div>
            <h3 className="font-bold text-lg">Live Tracking</h3>
            <p className="text-sm text-white/70">Shipment #{shipment.shipment_id}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 flex-1">
          {/* Static DB data */}
          <div className="space-y-3 mb-6">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Carrier</span>
              <span className="font-semibold text-gray-800">{shipment.carrier_name}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Mode</span>
              <span className="font-semibold text-gray-800 flex items-center gap-1"><ModeIcon mode={shipment.mode} />{shipment.mode.toUpperCase()}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Route</span>
              <span className="font-semibold text-gray-800">{shipment.origin} → {shipment.destination}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">ETA</span>
              <span className="font-semibold text-gray-800">{shipment.eta}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Status</span>
              <StatusBadge status={shipment.status} />
            </div>
          </div>

          {/* AI Agent Summary */}
          <div className="border-t border-gray-100 pt-5">
            <h4 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-gradient-to-br from-[#d9a441] to-[#7d5d2f] flex items-center justify-center text-white text-xs font-bold">O</span>
              Omni Tracking Summary
            </h4>
            {loading && (
              <div className="flex items-center gap-2 text-gray-400 text-sm animate-pulse">
                <svg className="animate-spin w-4 h-4 text-amber-500" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Fetching live status...
              </div>
            )}
            {error && <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg border border-red-200">Could not reach tracking agent: {error}</div>}
            {trackData && (
              <div className="bg-[#f5f1ea] border border-amber-100 rounded-xl p-4 text-sm text-gray-700 italic leading-relaxed">
                "{trackData.summary}"
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ShipmentsTab() {
  const [shipments, setShipments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState('all')
  const [trackingShipment, setTrackingShipment] = useState(null)

  const fetchShipments = useCallback(() => {
    setLoading(true)
    supplyChainApi.getShipments()
      .then(data => { setShipments(data); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  useEffect(() => { fetchShipments() }, [fetchShipments])

  const filtered = statusFilter === 'all' ? shipments : shipments.filter(s => s.status === statusFilter)
  const delayedCount = shipments.filter(s => s.status === 'delayed').length

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-gray-400">
      <svg className="animate-spin w-6 h-6 mr-2 text-amber-500" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      Loading shipments...
    </div>
  )

  if (error) return <div className="p-6 text-red-600 bg-red-50 rounded-xl border border-red-200">Error: {error}</div>

  return (
    <div className="animate-fade-in-up">
      {/* Tracking panel overlay */}
      {trackingShipment && (
        <TrackingPanel shipment={trackingShipment} onClose={() => setTrackingShipment(null)} />
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Shipment Tracking</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {shipments.length} shipments
            {delayedCount > 0 && (
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-orange-100 text-orange-800">
                ⚠ {delayedCount} delayed
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:border-amber-400"
          >
            <option value="all">All Statuses</option>
            <option value="booked">Booked</option>
            <option value="in_transit">In Transit</option>
            <option value="delayed">Delayed</option>
            <option value="delivered">Delivered</option>
          </select>
          <button
            onClick={fetchShipments}
            className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors text-gray-500"
            title="Refresh"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-5 py-3.5 font-semibold text-gray-600 text-xs uppercase tracking-wider">ID</th>
              <th className="text-left px-5 py-3.5 font-semibold text-gray-600 text-xs uppercase tracking-wider">Mode</th>
              <th className="text-left px-5 py-3.5 font-semibold text-gray-600 text-xs uppercase tracking-wider">Carrier</th>
              <th className="text-left px-5 py-3.5 font-semibold text-gray-600 text-xs uppercase tracking-wider">Route</th>
              <th className="text-left px-5 py-3.5 font-semibold text-gray-600 text-xs uppercase tracking-wider">ETA</th>
              <th className="text-left px-5 py-3.5 font-semibold text-gray-600 text-xs uppercase tracking-wider">Status</th>
              <th className="px-5 py-3.5"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map(s => (
              <tr
                key={s.shipment_id}
                className={`transition-colors ${s.status === 'delayed' ? 'bg-orange-50/40 hover:bg-orange-50' : 'hover:bg-gray-50'}`}
              >
                <td className="px-5 py-4 font-mono font-semibold text-gray-700">#{s.shipment_id}</td>
                <td className="px-5 py-4"><ModeIcon mode={s.mode} /></td>
                <td className="px-5 py-4">
                  <div className="font-medium text-gray-800">{s.carrier_name}</div>
                  <div className="text-xs text-gray-400">LKR {s.rate_per_unit}/unit</div>
                </td>
                <td className="px-5 py-4 text-gray-600">
                  <span>{s.origin}</span>
                  <span className="text-gray-300 mx-1">→</span>
                  <span>{s.destination}</span>
                </td>
                <td className="px-5 py-4">
                  <div className="font-medium text-gray-800">{s.eta}</div>
                  {s.actual_arrival && <div className="text-xs text-green-600">Arrived: {s.actual_arrival}</div>}
                </td>
                <td className="px-5 py-4"><StatusBadge status={s.status} /></td>
                <td className="px-5 py-4">
                  {s.status !== 'delivered' && (
                    <button
                      onClick={() => setTrackingShipment(s)}
                      className="text-xs font-semibold text-[#1a2430] border border-gray-300 px-3 py-1.5 rounded-lg hover:bg-[#1a2430] hover:text-white transition-colors"
                    >
                      Track Live
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-400 text-sm">No shipments found.</div>
        )}
      </div>
    </div>
  )
}
