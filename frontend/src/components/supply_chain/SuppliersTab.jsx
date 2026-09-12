import React, { useState, useEffect } from 'react'
import { supplyChainApi } from '../../api/supplyChainApi'

// Star rating renderer
function StarRating({ rating }) {
  const full = Math.floor(rating)
  const half = rating - full >= 0.5
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <svg key={i} className={`w-3.5 h-3.5 ${i <= full ? 'text-amber-400' : i === full + 1 && half ? 'text-amber-300' : 'text-slate-200'}`} fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
      <span className="ml-1.5 text-xs font-semibold text-slate-500">{rating.toFixed(1)}</span>
    </span>
  )
}

// Lead time badge — matches dashboard's color coding
function LeadTimeBadge({ days }) {
  const { cls, label } =
    days <= 14 ? { cls: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: `${days}d · Fast` } :
    days <= 21 ? { cls: 'bg-amber-50 text-amber-700 border-amber-200',   label: `${days}d · Standard` } :
                  { cls: 'bg-red-50 text-red-700 border-red-200',         label: `${days}d · Slow` }
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold border ${cls}`}>
      {label}
    </span>
  )
}

// Category pill
const CATEGORY_META = {
  fabric_mill:  { label: 'Fabric Mill',  cls: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  trim_vendor:  { label: 'Trim Vendor',  cls: 'bg-purple-50 text-purple-700 border-purple-200' },
  dye_house:    { label: 'Dye House',    cls: 'bg-teal-50 text-teal-700 border-teal-200' },
}

const COUNTRY_FLAGS = {
  'Bangladesh': '🇧🇩', 'Sri Lanka': '🇱🇰', 'India': '🇮🇳',
  'Turkey': '🇹🇷', 'Pakistan': '🇵🇰', 'China': '🇨🇳',
}

export default function SuppliersTab({ suppliers, onUpdate, onRequestSupply }) {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')

  // Edit state
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({})

  const filtered = suppliers.filter(s => {
    const matchSearch = s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.country.toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === 'all' || s.category === filter
    return matchSearch && matchFilter
  })

  const handleEditClick = (s) => {
    setEditingId(s.supplier_id)
    setEditForm({
      category: s.category,
      rating: s.rating,
      lead_time_days: s.lead_time_days
    })
  }

  const handleSaveEdit = async (id) => {
    try {
      await supplyChainApi.updateSupplier(id, editForm)
      if (onUpdate) onUpdate()
      setEditingId(null)
    } catch (err) {
      alert('Failed to update supplier: ' + err.message)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this supplier?')) return
    try {
      await supplyChainApi.deleteSupplier(id)
      if (onUpdate) onUpdate()
    } catch (err) {
      alert('Failed to delete supplier: ' + err.message)
    }
  }



  return (
    <div>
      {/* Controls */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Supplier Directory</h2>
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400 mt-0.5">{suppliers.length} ERP-registered vendors</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search suppliers..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-8 pr-4 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 bg-white shadow-sm"
            />
          </div>
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="text-sm border border-slate-200 rounded-xl px-3 py-2 bg-white shadow-sm focus:outline-none focus:border-amber-400"
          >
            <option value="all">All Categories</option>
            <option value="fabric_mill">Fabric Mills</option>
            <option value="trim_vendor">Trim Vendors</option>
            <option value="dye_house">Dye Houses</option>
          </select>
        </div>
      </div>

      {/* Table — matches dashboard's white card with shadow */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-[0_10px_25px_rgba(15,23,42,0.03)] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="text-left px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">Supplier</th>
              <th className="text-left px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">Category</th>
              <th className="text-left px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">Rating</th>
              <th className="text-left px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">Lead Time</th>
              <th className="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filtered.map((s, idx) => {
              const cat = CATEGORY_META[s.category] || { label: s.category, cls: 'bg-slate-100 text-slate-600 border-slate-200' }
              const isEditing = editingId === s.supplier_id

              return (
                <tr
                  key={s.supplier_id}
                  className="hover:bg-amber-50/30 transition-colors group"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      {/* Color avatar for each supplier */}
                      <div
                        className="w-9 h-9 rounded-xl flex items-center justify-center text-white text-sm font-bold flex-shrink-0 shadow-sm"
                        style={{ background: `hsl(${(s.supplier_id * 47) % 360}, 55%, 45%)` }}
                      >
                        {s.name.charAt(0)}
                      </div>
                      <div>
                        <div className="font-semibold text-slate-800">{s.name}</div>
                        <div className="text-xs text-slate-400">{COUNTRY_FLAGS[s.country] || '🌍'} {s.country}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {isEditing ? (
                      <select
                        value={editForm.category}
                        onChange={e => setEditForm({ ...editForm, category: e.target.value })}
                        className="text-xs border border-slate-300 rounded px-2 py-1 focus:outline-none focus:border-amber-400"
                      >
                        <option value="fabric_mill">Fabric Mill</option>
                        <option value="trim_vendor">Trim Vendor</option>
                        <option value="dye_house">Dye House</option>
                      </select>
                    ) : (
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold border ${cat.cls}`}>
                        {cat.label}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="5"
                        value={editForm.rating}
                        onChange={e => setEditForm({ ...editForm, rating: parseFloat(e.target.value) })}
                        className="w-16 text-xs border border-slate-300 rounded px-2 py-1 focus:outline-none focus:border-amber-400"
                      />
                    ) : (
                      <StarRating rating={s.rating} />
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {isEditing ? (
                      <input
                        type="number"
                        value={editForm.lead_time_days}
                        onChange={e => setEditForm({ ...editForm, lead_time_days: parseInt(e.target.value, 10) })}
                        className="w-16 text-xs border border-slate-300 rounded px-2 py-1 focus:outline-none focus:border-amber-400"
                      />
                    ) : (
                      <LeadTimeBadge days={s.lead_time_days} />
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {isEditing ? (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setEditingId(null)}
                          className="bg-white border border-slate-300 text-slate-600 text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-slate-50 shadow-sm"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSaveEdit(s.supplier_id)}
                          className="bg-emerald-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-emerald-700 shadow-sm"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-all">
                        <button
                          onClick={() => handleEditClick(s)}
                          className="bg-white border border-slate-300 text-slate-700 text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-slate-50 shadow-sm"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(s.supplier_id)}
                          className="bg-red-50 border border-red-200 text-red-700 text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-red-100 shadow-sm"
                        >
                          Delete
                        </button>
                        <button
                          onClick={() => onRequestSupply(s)}
                          className="bg-[#1a2430] text-white text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-[#2c3e50] shadow-sm"
                        >
                          Request Supply
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-16 text-slate-400 text-sm">No suppliers match your search.</div>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-5 mt-4 text-xs text-slate-400">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span>Fast ≤ 14 days</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-400 inline-block"></span>Standard 15–21 days</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-400 inline-block"></span>Slow &gt; 21 days</span>
      </div>
    </div>
  )
}
