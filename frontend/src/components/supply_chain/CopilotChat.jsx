import React, { useState, useRef, useEffect } from 'react'
import { supplyChainApi } from '../../api/supplyChainApi'

// ── Star rating helper ────────────────────────────────────────────
function StarRating({ rating }) {
  const full = Math.floor(rating)
  const half = rating % 1 >= 0.5
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <svg key={i} className={`w-3 h-3 ${i <= full ? 'text-amber-400' : i === full + 1 && half ? 'text-amber-300' : 'text-gray-200'}`} fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
      <span className="text-xs text-gray-500 ml-1">{rating.toFixed(1)}</span>
    </span>
  )
}

// ── Country flag emoji lookup ─────────────────────────────────────
const COUNTRY_FLAGS = {
  'Sri Lanka': '🇱🇰', 'India': '🇮🇳', 'Bangladesh': '🇧🇩',
  'Turkey': '🇹🇷', 'Pakistan': '🇵🇰', 'China': '🇨🇳',
  'Vietnam': '🇻🇳', 'Indonesia': '🇮🇩',
}

// ── Supplier selection card ───────────────────────────────────────
function SupplierCard({ supplier, requirements, onSelect, disabled }) {
  const total = supplier.estimated_total ?? (requirements.qty * (supplier.price_per_unit || 260))
  const pricePerUnit = supplier.price_per_unit || 260
  return (
    <button
      onClick={() => onSelect(supplier)}
      disabled={disabled}
      className="w-full text-left bg-white border border-gray-200 rounded-xl p-3 hover:border-amber-400 hover:shadow-md transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed group relative"
    >
      {/* Badges */}
      <div className="absolute top-2 right-2 flex gap-1">
        {supplier.badge_best_price && (
          <span className="text-[9px] font-bold bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full border border-emerald-200">💚 Best Price</span>
        )}
        {supplier.badge_fastest && (
          <span className="text-[9px] font-bold bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full border border-blue-200">⚡ Fastest</span>
        )}
      </div>
      <div className="flex items-start justify-between gap-2 pr-16">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-gray-800 text-sm truncate group-hover:text-amber-700">
            {COUNTRY_FLAGS[supplier.country] || '🏭'} {supplier.name}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">{supplier.country}</p>
          <StarRating rating={supplier.rating} />
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-xs text-gray-400">Lead time</p>
          <p className="text-sm font-semibold text-gray-700">{supplier.lead_time_days}d</p>
        </div>
      </div>
      {/* Per-supplier pricing row */}
      <div className="mt-2 pt-2 border-t border-gray-100 flex items-center justify-between">
        <span className="text-xs text-gray-400">LKR {pricePerUnit.toLocaleString()}/unit</span>
        <span className="text-sm font-bold text-emerald-700">Total: LKR {total.toLocaleString()}</span>
      </div>
    </button>
  )
}

// ── Confirmation card (order summary before PO creation) ──────────
function ConfirmationCard({ supplier, requirements, onConfirm, onBack, disabled }) {
  const total = supplier.estimated_total ?? (requirements.qty * (supplier.price_per_unit || 260))
  const dims = requirements.dimensions || {}
  return (
    <div className="mt-2 bg-white border-2 border-amber-300 rounded-xl p-4 text-sm shadow-md">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-5 h-5 bg-amber-100 rounded-full flex items-center justify-center text-amber-600 font-bold text-xs">!</div>
        <p className="font-bold text-gray-800 text-xs uppercase tracking-wide">Order Summary — Please Confirm</p>
      </div>
      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-500">Supplier</span>
          <span className="font-semibold">{COUNTRY_FLAGS[supplier.country] || '🏭'} {supplier.name} ⭐{supplier.rating}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Material</span>
          <span className="font-semibold">{requirements.material_name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Colour</span>
          <span className="font-semibold">{requirements.color_spec}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Quantity</span>
          <span className="font-semibold">{requirements.qty?.toLocaleString()} {requirements.unit}</span>
        </div>
        {Object.entries(dims).slice(0, 3).map(([k, v]) => (
          <div key={k} className="flex justify-between">
            <span className="text-gray-500">{k.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</span>
            <span className="font-semibold">{v}</span>
          </div>
        ))}
        <div className="flex justify-between">
          <span className="text-gray-500">Lead Time</span>
          <span className="font-semibold">{supplier.lead_time_days} days</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Destination</span>
          <span className="font-semibold">{requirements.destination}</span>
        </div>
        <div className="flex justify-between pt-1 border-t border-amber-100 mt-1">
          <span className="text-gray-700 font-bold">Total Value</span>
          <span className="font-extrabold text-amber-700 text-sm">LKR {total.toLocaleString()}</span>
        </div>
      </div>
      <div className="flex gap-2 mt-3">
        <button
          onClick={onConfirm}
          disabled={disabled}
          className="flex-1 bg-gradient-to-r from-[#d9a441] to-[#b87d39] text-white text-xs font-bold py-2.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          ✓ Confirm &amp; Place Order
        </button>
        <button
          onClick={onBack}
          disabled={disabled}
          className="flex-shrink-0 border border-gray-300 text-gray-600 text-xs font-semibold py-2.5 px-3 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          ← Back
        </button>
      </div>
    </div>
  )
}

// ── Main CopilotChat component ────────────────────────────────────
export default function CopilotChat({ isOpen, onClose, onPipelineComplete, prefillSupplier, prefillQuery, clearQuery }) {
  // Conversation phases: 'gathering' | 'selecting' | 'confirming' | 'ordering' | 'approving' | 'done'
  const [phase, setPhase] = useState('gathering')
  const [messages, setMessages] = useState([
    {
      role: 'omni', type: 'text',
      content: 'Hi! I\'m your procurement assistant. Tell me what materials you need — for example: "I need cotton fabric" or "We need 500 zippers".'
    }
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [typingText, setTypingText] = useState('')
  const messagesEndRef = useRef(null)

  // conversation_history sent to backend (only user+assistant turns, no system)
  const [history, setHistory] = useState([])
  const [requirements, setRequirements] = useState(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  // Pre-fill if opened from a supplier row
  useEffect(() => {
    if (prefillSupplier && isOpen) {
      setInput(`I need to order from ${prefillSupplier.name}`)
    }
  }, [prefillSupplier, isOpen])

  // Auto-send if prefillQuery is set (routed from Operations Agent)
  useEffect(() => {
    if (prefillQuery && isOpen && !isTyping) {
      sendMessage(prefillQuery)
      if (clearQuery) clearQuery()
    }
  }, [prefillQuery, isOpen])

  const addOmniMessage = (type, content, data = null) => {
    setMessages(prev => [...prev, { role: 'omni', type, content, ...(data ? { data } : {}) }])
  }

  const sendMessage = async (text) => {
    if (!text.trim() || isTyping) return

    const userMsg = text.trim()
    setInput('')

    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', type: 'text', content: userMsg }])

    // Update history
    const newHistory = [...history, { role: 'user', content: userMsg }]
    setHistory(newHistory)

    setIsTyping(true)
    setTypingText('Thinking...')

    try {
      // ── Phase: GATHERING ─────────────────────────────────────
      if (phase === 'gathering') {
        const result = await supplyChainApi.gatherRequirements(newHistory)

        if (result.status === 'needs_more_info') {
          const assistantReply = result.question
          setHistory(prev => [...prev, { role: 'assistant', content: assistantReply }])
          setIsTyping(false)
          addOmniMessage('text', assistantReply)
        } else if (result.status === 'needs_shade_selection') {
          const assistantReply = result.question
          setHistory(prev => [...prev, { role: 'assistant', content: assistantReply }])
          setIsTyping(false)
          addOmniMessage('text', assistantReply)
          addOmniMessage('shade_list', null, { shades: result.shades })

        } else if (result.status === 'ready') {
          // Requirements complete — now search for suppliers
          setRequirements(result)
          setHistory(prev => [...prev, { role: 'assistant', content: 'Requirements complete! Searching for the best suppliers...' }])

          setTypingText(`Searching for ${result.material_type.replace('_', ' ')} suppliers...`)

          const suppliersResult = await supplyChainApi.findSuppliers({
            material_type: result.material_type,
            qty: result.qty,
            color_spec: result.color_spec,
            compliance_keywords: result.compliance_keywords,
            dimensions: result.dimensions || {},
          })

          setIsTyping(false)

          const summary = `Got it! I need **${result.qty} ${result.unit}** of **${result.material_name}** (${result.color_spec}) delivered to **${result.destination}**.`

          if (!suppliersResult.suppliers || suppliersResult.suppliers.length === 0) {
            addOmniMessage('text', summary + '\n\nUnfortunately, I could not find any matching suppliers in the database for this material type.')
          } else {
            addOmniMessage('text', summary + `\n\nI found **${suppliersResult.suppliers.length}** matching supplier(s). Select one to proceed:`)
            addOmniMessage('supplier_list', null, {
              suppliers: suppliersResult.suppliers,
              requirements: result,
            })
            setPhase('selecting')
          }
        }
      }
    } catch (err) {
      setIsTyping(false)
      addOmniMessage('error', `Error: ${err.message}`)
    }
  }

  const handleSelectSupplier = (supplier) => {
    if (phase !== 'selecting' || isTyping) return
    // Freeze the supplier list visually
    setMessages(prev => prev.map(m =>
      m.type === 'supplier_list' ? { ...m, type: 'supplier_list_pending', selectedId: supplier.supplier_id } : m
    ))
    // Show confirmation card
    addOmniMessage('confirmation_card', null, { supplier, requirements })
    setPhase('confirming')
  }

  const handleBackToSuppliers = () => {
    // Restore supplier list to selectable state
    setMessages(prev => {
      const filtered = prev.filter(m => m.type !== 'confirmation_card')
      return filtered.map(m =>
        m.type === 'supplier_list_pending' ? { ...m, type: 'supplier_list', selectedId: null } : m
      )
    })
    setPhase('selecting')
  }

  const handleConfirmSupplier = async (supplier) => {
    if (isTyping) return
    // Freeze confirmation card
    setMessages(prev => prev.map(m =>
      m.type === 'confirmation_card' ? { ...m, type: 'confirmation_card_done' } : m
    ))
    // Also freeze supplier list
    setMessages(prev => prev.map(m =>
      m.type === 'supplier_list_pending' ? { ...m, type: 'supplier_list_done', selectedId: supplier.supplier_id } : m
    ))

    setIsTyping(true)
    setTypingText('Drafting Purchase Order...')
    setPhase('ordering')

    try {
      const result = await supplyChainApi.startPipeline({
        material_type: requirements.material_type,
        requirement_id: requirements.requirement_id,
        qty: requirements.qty,
        total_value: supplier.estimated_total || requirements.total_value,
        compliance_keywords: [],          // RAG skipped — user already chose supplier
        destination: requirements.destination,
        targeted_supplier: supplier.name, // Lock to user-chosen supplier
      })

      setIsTyping(false)

      if (result.status === 'failed' || !result.run_id) {
        addOmniMessage('error', `Pipeline failed: ${result.error || 'Unknown error'}`)
        setPhase('selecting')
        return
      }

      addOmniMessage('text', 'Purchase Order drafted. Please review all details and authorize below.')
      addOmniMessage('po_card', null, {
        ...result,
        supplier: { ...result.supplier, supplier_name: supplier.name },
        selected_supplier: supplier,
        requirements,
      })
      setPhase('approving')

    } catch (err) {
      setIsTyping(false)
      addOmniMessage('error', `Order error: ${err.message}`)
      setPhase('confirming')
    }
  }

  const handleApprove = async (runId) => {
    setIsTyping(true)
    setTypingText('Authorizing PO & notifying supplier...')
    setMessages(prev => prev.map(m =>
      (m.type === 'po_card' && m.data?.run_id === runId) ? { ...m, type: 'po_card_done', approved: true } : m
    ))

    try {
      const result = await supplyChainApi.approvePo(runId, 'Human Manager')
      setIsTyping(false)
      addOmniMessage('shipment_card', 'PO authorized! Freight booked and shipment is underway.', result)
      setPhase('done')
      if (onPipelineComplete) onPipelineComplete()
    } catch (err) {
      setIsTyping(false)
      addOmniMessage('error', `Logistics error: ${err.message}`)
    }
  }

  const handleReject = async (runId) => {
    setMessages(prev => prev.map(m =>
      (m.type === 'po_card' && m.data?.run_id === runId) ? { ...m, type: 'po_card_done', approved: false } : m
    ))
    try {
      await supplyChainApi.rejectPo(runId)
      addOmniMessage('text', 'Purchase Order cancelled. The pipeline has been stopped.')
      setPhase('done')
    } catch (err) {
      addOmniMessage('error', `Error: ${err.message}`)
    }
  }

  const handleReset = () => {
    setPhase('gathering')
    setHistory([])
    setRequirements(null)
    setMessages([{
      role: 'omni', type: 'text',
      content: 'Hi! I\'m your procurement assistant. Tell me what materials you need — for example: "I need cotton fabric" or "We need 500 zippers".'
    }])
  }

  const handleSend = (e) => {
    e.preventDefault()
    sendMessage(input)
  }

  // Render message body
  const renderMessage = (msg, idx) => {
    // Simple text
    if (msg.type === 'text') {
      const formatted = msg.content?.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') || ''
      return (
        <p
          className="text-sm text-gray-700 leading-relaxed"
          dangerouslySetInnerHTML={{ __html: formatted }}
        />
      )
    }

    // Shade List (Color Confirmation)
    if (msg.type === 'shade_list') {
      return (
        <div className="mt-3 grid grid-cols-11 gap-1">
          {msg.data.shades.map(shade => (
            <button
              key={shade.name}
              onClick={() => sendMessage(shade.name)}
              disabled={isTyping}
              className="group relative h-10 w-full rounded-sm shadow-sm transition-transform hover:scale-110 focus:outline-none disabled:opacity-50"
              style={{ backgroundColor: shade.hex }}
              title={shade.name}
            >
              <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block whitespace-nowrap bg-gray-800 text-white text-[10px] px-2 py-1 rounded shadow-lg z-10 pointer-events-none">
                <span className="font-bold">{shade.name}</span><br />
                <span className="opacity-75">{shade.hex.toUpperCase()}</span>
              </span>
            </button>
          ))}
        </div>
      )
    }

    // Supplier list (selectable)
    if (msg.type === 'supplier_list') {
      return (
        <div className="mt-2 space-y-2 w-full">
          {msg.data.suppliers.map(s => (
            <SupplierCard
              key={s.supplier_id}
              supplier={s}
              requirements={msg.data.requirements}
              onSelect={handleSelectSupplier}
              disabled={isTyping}
            />
          ))}
        </div>
      )
    }

    // Supplier list (pending confirmation — visually frozen but shows selected)
    if (msg.type === 'supplier_list_pending') {
      return (
        <div className="mt-2 space-y-2 w-full opacity-70">
          {msg.data.suppliers.map(s => (
            <div
              key={s.supplier_id}
              className={`w-full text-left bg-white border rounded-xl p-3 transition-all duration-150 ${
                s.supplier_id === msg.selectedId
                  ? 'border-amber-400 shadow-md bg-amber-50'
                  : 'border-gray-100 opacity-40'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-800 text-sm truncate">
                    {COUNTRY_FLAGS[s.country] || '🏭'} {s.name}
                    {s.supplier_id === msg.selectedId && <span className="ml-2 text-amber-600 text-xs">✓ Selected</span>}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">{s.country}</p>
                  <StarRating rating={s.rating} />
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-semibold text-gray-700">{s.lead_time_days}d</p>
                  <p className="text-xs text-emerald-700 font-bold">LKR {(s.estimated_total || 0).toLocaleString()}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )
    }

    // Confirmation card (pre-PO order summary)
    if (msg.type === 'confirmation_card') {
      const { supplier, requirements: req } = msg.data
      return (
        <ConfirmationCard
          supplier={supplier}
          requirements={req}
          onConfirm={() => handleConfirmSupplier(supplier)}
          onBack={handleBackToSuppliers}
          disabled={isTyping}
        />
      )
    }

    // Confirmation card done (frozen)
    if (msg.type === 'confirmation_card_done') {
      const { supplier } = msg.data
      return (
        <div className="mt-2 text-xs font-semibold px-3 py-2 rounded-lg border bg-amber-50 text-amber-800 border-amber-200">
          ✓ Order confirmed with {supplier.name} — creating PO...
        </div>
      )
    }


    // PO Card
    if (msg.type === 'po_card') {
      const d = msg.data || {}
      const req = d.requirements || requirements || {}
      const supplierName = d.selected_supplier?.name || d.supplier?.supplier_name || d.supplier || '—'
      const dims = req.dimensions || {}
      return (
        <div className="mt-2 bg-white rounded-xl border border-gray-200 shadow-sm p-4 text-sm">
          <div className="space-y-1.5 mb-3">
            <div className="flex justify-between">
              <span className="text-gray-500">Supplier</span>
              <span className="font-semibold text-gray-800">{supplierName}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">PO #</span>
              <span className="font-mono font-semibold text-gray-800">#{d.po_id || d.po?.po_id || '—'}</span>
            </div>
            {req.material_name && (
              <div className="flex justify-between">
                <span className="text-gray-500">Material</span>
                <span className="font-semibold text-gray-800">{req.material_name}</span>
              </div>
            )}
            {req.color_spec && (
              <div className="flex justify-between">
                <span className="text-gray-500">Colour</span>
                <span className="font-semibold text-gray-800">{req.color_spec}</span>
              </div>
            )}
            {/* Dynamic dimension rows */}
            {Object.entries(dims).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-gray-500">{k.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</span>
                <span className="font-semibold text-gray-800">{v}</span>
              </div>
            ))}
            <div className="flex justify-between">
              <span className="text-gray-500">Quantity</span>
              <span className="font-semibold text-gray-800">{d.qty?.toLocaleString() || req.qty?.toLocaleString() || '—'} {req.unit || ''}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Unit Price</span>
              <span className="font-semibold text-gray-800">LKR {(d.selected_supplier?.price_per_unit || 260).toLocaleString()}/unit</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Total Value</span>
              <span className="font-bold text-amber-700">LKR {(d.total_value || req.total_value || 0).toLocaleString()}</span>
            </div>
            {d.selected_supplier?.lead_time_days && (
              <div className="flex justify-between">
                <span className="text-gray-500">Lead time</span>
                <span className="font-semibold text-gray-800">{d.selected_supplier.lead_time_days} days</span>
              </div>
            )}
            <div className="mt-2 p-2 bg-green-50 rounded-lg text-xs text-green-700 border border-green-100">
              ✓ Compliance verified · {req.compliance_keywords?.join(', ') || 'Standard checks'}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleApprove(d.run_id)}
              disabled={isTyping}
              className="flex-1 bg-gradient-to-r from-[#d9a441] to-[#b87d39] text-white text-xs font-bold py-2.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              Authorize
            </button>
            <button
              onClick={() => handleReject(d.run_id)}
              disabled={isTyping}
              className="flex-1 border border-gray-300 text-gray-700 text-xs font-bold py-2.5 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Reject
            </button>
          </div>
        </div>
      )
    }



    // PO done
    if (msg.type === 'po_card_done') {
      return (
        <div className={`mt-2 text-xs font-semibold px-3 py-2 rounded-lg border ${msg.approved ? 'bg-green-50 text-green-800 border-green-200' : 'bg-red-50 text-red-700 border-red-200'}`}>
          {msg.approved ? '✓ PO Authorized' : '✗ PO Cancelled'}
        </div>
      )
    }

    // Shipment card (includes auto-email result)
    if (msg.type === 'shipment_card') {
      const d = msg.data || {}
      const emailSent = d.email_sent
      const emailRecipient = d.email_recipient
      const emailError = d.email_error
      return (
        <div className="mt-2 bg-white rounded-xl border border-gray-200 shadow-sm p-4 text-sm space-y-1.5">
          {/* Status banner */}
          <div className="flex items-center gap-2 p-2.5 bg-green-50 rounded-lg border border-green-200 mb-2">
            <span className="text-green-600 text-base">✅</span>
            <div>
              <p className="text-xs font-bold text-green-800">PO #{String(d.po_id || '').padStart(4,'0')} Authorized & Processed</p>
              {emailSent
                ? <p className="text-xs text-green-600">✉ Email sent → {emailRecipient}</p>
                : <p className="text-xs text-amber-600">⚠ Email skipped — {emailError || 'configure Brevo credentials'}</p>
              }
            </div>
          </div>
          <div className="flex justify-between"><span className="text-gray-500">Shipment #</span><span className="font-mono font-semibold text-gray-800">#{d.shipment_id || '—'}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Carrier</span><span className="font-semibold text-gray-800">{d.carrier || '—'}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Mode</span><span className="font-semibold text-gray-800">{d.mode || '—'}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">ETA</span><span className="font-semibold text-gray-800">{d.eta || '—'}</span></div>
          {d.summary && (
            <div className="mt-2 p-2 bg-blue-50 rounded-lg text-xs text-blue-800 italic border border-blue-100">"{d.summary}"</div>
          )}
        </div>
      )
    }

    // Error
    if (msg.type === 'error') {
      return (
        <div className="mt-2 p-2 bg-red-50 text-red-700 rounded-lg border border-red-200 text-xs">{msg.content}</div>
      )
    }

    return null
  }

  const inputDisabled = isTyping || phase === 'selecting' || phase === 'confirming' || phase === 'approving' || phase === 'done'

  if (!isOpen) return null

  return (
    <div className="fixed bottom-6 right-6 z-40 w-[420px] h-[620px] flex flex-col rounded-2xl shadow-2xl bg-white border border-gray-200 animate-fade-in-up overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 bg-[#1a2430] text-white flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#d9a441] to-[#7d5d2f] flex items-center justify-center text-sm font-bold shadow">O</div>
          <div>
            <div className="font-bold text-sm">Omni Copilot</div>
            <div className="text-xs text-white/60">Procurement Assistant</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Phase pill */}
          <span className={`text-[9px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full ${
            phase === 'gathering'  ? 'bg-blue-500/30 text-blue-200' :
            phase === 'selecting'  ? 'bg-amber-500/30 text-amber-200' :
            phase === 'confirming' ? 'bg-yellow-500/30 text-yellow-200' :
            phase === 'ordering' || phase === 'approving' ? 'bg-orange-500/30 text-orange-200' :
            'bg-green-500/30 text-green-200'
          }`}>
            {phase === 'gathering'  ? '● Gathering' :
             phase === 'selecting'  ? '● Select supplier' :
             phase === 'confirming' ? '● Confirm order' :
             phase === 'ordering' || phase === 'approving' ? '● Review PO' :
             '✓ Complete'}
          </span>
          {phase === 'done' && (
            <button
              onClick={handleReset}
              title="Start new request"
              className="p-1.5 hover:bg-white/10 rounded-lg transition-colors text-xs text-white/60 hover:text-white"
            >
              New
            </button>
          )}
          <button onClick={onClose} className="p-1.5 hover:bg-white/10 rounded-lg transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#f9f8f6]">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} items-end gap-2`}>
            {msg.role === 'omni' && (
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#d9a441] to-[#7d5d2f] flex-shrink-0 flex items-center justify-center text-white text-xs font-bold">O</div>
            )}
            <div className={`max-w-[88%] ${msg.role === 'user' ? 'bg-[#1a2430] text-white rounded-2xl rounded-br-sm px-4 py-2.5 text-sm' : 'w-full'}`}>
              {msg.role === 'user'
                ? <p className="text-[13px]">{msg.content}</p>
                : renderMessage(msg, idx)
              }
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#d9a441] to-[#7d5d2f] flex-shrink-0 flex items-center justify-center text-white text-xs font-bold">O</div>
            <div className="flex items-center gap-2 text-xs text-gray-400 bg-white rounded-xl px-4 py-2.5 shadow-sm border border-gray-100">
              <svg className="animate-spin w-3 h-3 text-amber-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              {typingText}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="flex-shrink-0 p-3 bg-white border-t border-gray-100 flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={inputDisabled}
          placeholder={
            phase === 'selecting'  ? 'Click a supplier above to select...' :
            phase === 'confirming' ? 'Review the order summary above and confirm...' :
            phase === 'approving'  ? 'Review and authorize or reject the PO above...' :
            phase === 'done'       ? 'Click "New" to start another request...' :
            'e.g. Need 500m of navy blue organic cotton...'
          }
          className="flex-1 bg-gray-50 border border-gray-200 text-sm rounded-xl px-4 py-2.5 focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={inputDisabled || !input.trim()}
          className="w-9 h-9 bg-[#1a2430] text-white rounded-xl flex items-center justify-center hover:bg-[#2c3e50] transition-colors disabled:opacity-40"
        >
          <svg className="w-4 h-4 transform rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </form>
    </div>
  )
}
