import React, { useState, useRef, useEffect } from 'react'
import { supplyChainApi } from '../../api/supplyChainApi'

// ── Star rating helper ─────────────────────────────────────────────
function StarRating({ rating }) {
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <svg key={i} className={`w-3 h-3 ${i <= Math.round(rating) ? 'text-amber-400' : 'text-gray-200'}`} fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
      <span className="text-xs text-gray-500 ml-1">{Number(rating).toFixed(1)}</span>
    </span>
  )
}

const FLAGS = {
  'Sri Lanka': '🇱🇰', 'India': '🇮🇳', 'Bangladesh': '🇧🇩',
  'Turkey': '🇹🇷', 'Pakistan': '🇵🇰', 'China': '🇨🇳',
  'Vietnam': '🇻🇳', 'Indonesia': '🇮🇩',
}

// ── Predefined colour palette ──────────────────────────────────────
const COLOUR_PALETTE = [
  { name: 'Ivory White',       hex: '#FFFFF0', base: 'White' },
  { name: 'Natural White',     hex: '#F5F5DC', base: 'White' },
  { name: 'Optical White',     hex: '#F8F8FF', base: 'White' },
  { name: 'Light Grey',        hex: '#D3D3D3', base: 'Grey' },
  { name: 'Stone Grey',        hex: '#A9A9A9', base: 'Grey' },
  { name: 'Charcoal',          hex: '#36454F', base: 'Grey' },
  { name: 'Black',             hex: '#111111', base: 'Black' },
  { name: 'Sky Blue',          hex: '#87CEEB', base: 'Blue' },
  { name: 'Royal Blue',        hex: '#4169E1', base: 'Blue' },
  { name: 'Navy Blue',         hex: '#1E3A8A', base: 'Blue' },
  { name: 'Midnight Blue',     hex: '#191970', base: 'Blue' },
  { name: 'Teal',              hex: '#008080', base: 'Green' },
  { name: 'Mint Green',        hex: '#98FF98', base: 'Green' },
  { name: 'Olive Green',       hex: '#6B8E23', base: 'Green' },
  { name: 'Forest Green',      hex: '#228B22', base: 'Green' },
  { name: 'Dark Green',        hex: '#006400', base: 'Green' },
  { name: 'Burgundy',          hex: '#800020', base: 'Red' },
  { name: 'Rose Red',          hex: '#FF007F', base: 'Red' },
  { name: 'Tomato Red',        hex: '#FF6347', base: 'Red' },
  { name: 'Coral',             hex: '#FF7F50', base: 'Orange' },
  { name: 'Orange',            hex: '#FF8C00', base: 'Orange' },
  { name: 'Mustard Yellow',    hex: '#FFDB58', base: 'Yellow' },
  { name: 'Sand Beige',        hex: '#F5DEB3', base: 'Brown' },
  { name: 'Caramel Brown',     hex: '#C68642', base: 'Brown' },
  { name: 'Chocolate Brown',   hex: '#7B3F00', base: 'Brown' },
  { name: 'Lavender',          hex: '#E6E6FA', base: 'Purple' },
  { name: 'Purple',            hex: '#800080', base: 'Purple' },
  { name: 'Fuchsia',           hex: '#FF00FF', base: 'Purple' },
  { name: 'Dusty Rose',        hex: '#DCAE96', base: 'Pink' },
  { name: 'Natural / Undyed',  hex: '#EDE0C8', base: 'Other' },
]

function generateShades(baseName) {
  const hues = {
    red: 0, orange: 30, yellow: 60, green: 120, teal: 180,
    blue: 215, navy: 230, purple: 270, pink: 330, brown: 25,
    olive: 80, mint: 150
  };
  
  const b = baseName.toLowerCase();
  let hue = 215; // default to blue
  let isAchromatic = false;
  
  if (b.includes('white') || b.includes('grey') || b.includes('gray') || b.includes('black')) {
    isAchromatic = true;
  } else {
    for (const [k, v] of Object.entries(hues)) {
      if (b.includes(k)) { hue = v; break; }
    }
  }

  const shades = [];
  const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  const baseDisplay = b.split(' ').map(capitalize).join(' ');
  
  if (isAchromatic) {
    for (let i = 0; i < 25; i++) {
      const l = 98 - (i * 3.8); // 98 down to ~6.8
      let name = `Monochrome Shade ${i+1}`;
      if (i === 0) name = 'Pure White';
      else if (i === 12) name = 'Medium Grey';
      else if (i === 24) name = 'Deep Black';
      else if (i < 5) name = `Light Grey ${i}`;
      else if (i > 20) name = `Dark Grey ${i}`;
      shades.push({ name, hex: `hsl(0, 0%, ${l.toFixed(1)}%)` });
    }
  } else {
    const l_vals = [85, 70, 50, 35, 20];
    const s_vals = [20, 40, 60, 80, 100];
    const l_names = ['Very Light', 'Light', 'Medium', 'Dark', 'Very Dark'];
    const s_names = ['Muted', 'Soft', 'Standard', 'Vibrant', 'Neon'];
    
    for (let i = 0; i < 5; i++) {
      for (let j = 0; j < 5; j++) {
        let l = l_vals[i];
        let s = s_vals[j];
        if (b.includes('brown')) l = l * 0.7; // Brown needs to be darker
        let name = `${l_names[i]} ${s_names[j]} ${baseDisplay}`;
        shades.push({ name, hex: `hsl(${hue}, ${s}%, ${l}%)` });
      }
    }
  }
  return shades;
}

function ColorPalette({ onSelect, disabled, question }) {
  const [hovered, setHovered] = useState(null)
  
  let baseColor = null;
  const match = (question || "").match(/shade of ([a-zA-Z\s]+)/i);
  if (match) {
    baseColor = match[1].trim();
  }
  
  const displayColors = baseColor ? generateShades(baseColor) : COLOUR_PALETTE;

  return (
    <div className="mt-2">
      <p className="text-xs text-gray-400 mb-2">Click to select a colour:</p>
      <div className={`grid gap-1.5 ${baseColor ? 'grid-cols-5' : 'grid-cols-6'}`}>
        {displayColors.map(c => (
          <button
            key={c.name}
            title={c.name}
            disabled={disabled}
            onClick={() => onSelect(c.name)}
            onMouseEnter={() => setHovered(c.name)}
            onMouseLeave={() => setHovered(null)}
            className="w-full aspect-square rounded-md border-2 border-transparent hover:border-gray-700 transition-all duration-100 relative focus:outline-none focus:ring-2 focus:ring-amber-400 disabled:cursor-not-allowed"
            style={{ backgroundColor: c.hex }}
          />
        ))}
      </div>
      {hovered && (
        <p className="text-xs text-gray-500 mt-1.5 text-center">{hovered}</p>
      )}
    </div>
  )
}

// ── Supplier card (clickable) ──────────────────────────────────────
function SupplierCard({ supplier, onSelect, disabled, selected }) {
  return (
    <button
      onClick={() => onSelect(supplier)}
      disabled={disabled}
      className={`w-full text-left rounded-xl p-3 border transition-all duration-150 group
        ${selected
          ? 'border-amber-400 bg-amber-50 shadow-md'
          : disabled
            ? 'border-gray-100 opacity-40 cursor-not-allowed'
            : 'border-gray-200 bg-white hover:border-amber-400 hover:shadow-md'
        }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
            <span className="font-semibold text-sm text-gray-800 group-hover:text-amber-700">
              {FLAGS[supplier.country] || '🏭'} {supplier.name}
            </span>
            {selected && <span className="text-amber-600 text-xs font-semibold">✓ Selected</span>}
            {supplier.badge_fastest && !selected && (
              <span className="text-[9px] font-bold bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">⚡ Fastest</span>
            )}
            {supplier.badge_best_price && !selected && (
              <span className="text-[9px] font-bold bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">💰 Best Price</span>
            )}
          </div>
          <p className="text-xs text-gray-400">{supplier.country}</p>
          <StarRating rating={supplier.rating} />
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-xs text-gray-400">Lead time</p>
          <p className="text-sm font-semibold text-gray-700">{supplier.lead_time_days}d</p>
          {supplier.price_per_unit && (
            <p className="text-xs text-gray-400 mt-0.5">LKR {Number(supplier.price_per_unit).toLocaleString()}/unit</p>
          )}
          {supplier.estimated_total && (
            <p className="text-xs font-bold text-emerald-700">LKR {Number(supplier.estimated_total).toLocaleString()}</p>
          )}
        </div>
      </div>
    </button>
  )
}

// ── Main component ─────────────────────────────────────────────────
export default function CopilotChat({ isOpen, onClose, onPipelineComplete, prefillSupplier, prefillQuery, clearQuery }) {
  /**
   * Phases:
   *   gathering  — bot asks questions one-by-one until requirements are complete
   *   selecting  — bot shows ranked supplier list; user clicks one
   *   ordering   — /run called; bot shows PO card
   *   approving  — user clicks Authorize or Reject
   *   done       — pipeline complete
   */
  const [phase, setPhase] = useState('gathering')
  const [messages, setMessages] = useState([{
    role: 'omni', type: 'text',
    content: 'Hi! I\'m your procurement assistant. What materials do you need? For example: "I need cotton fabric" or "500 navy blue zippers".'
  }])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [typingText, setTypingText] = useState('')
  const [history, setHistory] = useState([])       // sent to /gather each turn
  const [requirements, setRequirements] = useState(null)
  const [selectedSupplier, setSelectedSupplier] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  useEffect(() => {
    if (prefillSupplier && isOpen) setInput(`I need to order from ${prefillSupplier.name}`)
  }, [prefillSupplier, isOpen])

  useEffect(() => {
    if (prefillQuery && isOpen && !isTyping) {
      sendMessage(prefillQuery)
      if (clearQuery) clearQuery()
    }
  }, [prefillQuery, isOpen])

  const pushOmni = (type, content, data = null) =>
    setMessages(prev => [...prev, { role: 'omni', type, content, ...(data ? { data } : {}) }])

  // ── Main send handler ───────────────────────────────────────────
  const sendMessage = async (text) => {
    const userMsg = text?.trim()
    if (!userMsg || isTyping) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', type: 'text', content: userMsg }])
    const newHistory = [...history, { role: 'user', content: userMsg }]
    setHistory(newHistory)

    setIsTyping(true)
    setTypingText('Thinking...')

    try {
      if (phase === 'gathering') {
        const result = await supplyChainApi.gatherRequirements(newHistory)

        if (result.status === 'ready') {
          // ── All requirements collected; search real DB ──────────
          setRequirements(result)
          const assistantMsg = 'Requirements complete! Searching for the best suppliers...'
          setHistory(h => [...h, { role: 'assistant', content: assistantMsg }])
          setTypingText(`Searching ${result.material_type.replace('_', ' ')} suppliers...`)

          const { suppliers } = await supplyChainApi.findSuppliers({
            material_type: result.material_type,
            qty: result.qty,
            color_spec: result.color_spec,
            compliance_keywords: result.compliance_keywords,
          })

          setIsTyping(false)

          const summary = `Got it — **${result.qty} ${result.unit}** of **${result.material_name}** (${result.color_spec}) to **${result.destination}**.`

          if (!suppliers || suppliers.length === 0) {
            pushOmni('text', summary + '\n\nNo matching suppliers found in the database for this category.')
          } else {
            pushOmni('text', summary + `\n\nFound **${suppliers.length}** supplier(s) ranked by rating. Click one to select:`)
            pushOmni('supplier_list', null, { suppliers, requirements: result })
            setPhase('selecting')
          }

        } else {
          // ── Still gathering; bot asks next question ─────────────
          const question = result.question || result.message || 'Could you provide more details?'
          setHistory(h => [...h, { role: 'assistant', content: question }])
          setIsTyping(false)
          pushOmni('text', question)
          
          const qLower = question.toLowerCase()
          if (qLower.includes('color') || qLower.includes('colour') || qLower.includes('shade')) {
            pushOmni('colour_palette', question)
          }
        }
      }
    } catch (err) {
      setIsTyping(false)
      pushOmni('error', `Error: ${err.message}`)
    }
  }

  // ── User selects a supplier ─────────────────────────────────────
  const handleSelectSupplier = async (supplier) => {
    if (phase !== 'selecting' || isTyping) return
    setSelectedSupplier(supplier)

    // Freeze the supplier list visually
    setMessages(prev => prev.map(m =>
      m.type === 'supplier_list' ? { ...m, type: 'supplier_list_done', selectedId: supplier.supplier_id } : m
    ))

    pushOmni('text', `Great choice! Creating a Purchase Order with **${supplier.name}** (⭐ ${supplier.rating}, ${supplier.lead_time_days}d lead time)...`)

    setIsTyping(true)
    setTypingText('Drafting Purchase Order...')
    setPhase('ordering')

    try {
      const result = await supplyChainApi.startPipeline({
        material_type: requirements.material_type,
        requirement_id: requirements.requirement_id,
        qty: requirements.qty,
        total_value: supplier.estimated_total || requirements.total_value,
        compliance_keywords: requirements.compliance_keywords?.length
          ? requirements.compliance_keywords
          : [],
        destination: requirements.destination,
        // Pass full po_details so material_name, color_spec, unit are saved to DB
        po_details: {
          material_name:       requirements.material_name,
          color_spec:          requirements.color_spec,
          unit:                requirements.unit,
          compliance_keywords: requirements.compliance_keywords || [],
          destination:         requirements.destination,
        },
      })


      setIsTyping(false)

      if (!result.run_id) {
        pushOmni('error', `Pipeline failed: ${result.error || 'Unknown error'}`)
        setPhase('selecting')
        return
      }

      pushOmni('text', 'I found a compliant supplier and drafted a Purchase Order. Please review and authorize below.')
      pushOmni('po_card', null, { ...result, _supplier: supplier, _requirements: requirements })
      setPhase('approving')

    } catch (err) {
      setIsTyping(false)
      pushOmni('error', `Order error: ${err.message}`)
      setPhase('selecting')
    }
  }

  // ── Authorize PO ────────────────────────────────────────────────
  const handleApprove = async (runId) => {
    setIsTyping(true)
    setTypingText('Authorizing PO & booking logistics...')
    setMessages(prev => prev.map(m =>
      m.type === 'po_card' && m.data?.run_id === runId
        ? { ...m, type: 'po_card_done', approved: true }
        : m
    ))
    try {
      const result = await supplyChainApi.approvePo(runId, 'Human Manager')
      setIsTyping(false)
      pushOmni('shipment_card', 'PO authorized! Freight booked and shipment is underway.', result)
      setPhase('done')
      if (onPipelineComplete) onPipelineComplete()
    } catch (err) {
      setIsTyping(false)
      pushOmni('error', `Logistics error: ${err.message}`)
    }
  }

  // ── Reject PO ───────────────────────────────────────────────────
  const handleReject = async (runId) => {
    setMessages(prev => prev.map(m =>
      m.type === 'po_card' && m.data?.run_id === runId
        ? { ...m, type: 'po_card_done', approved: false }
        : m
    ))
    try {
      await supplyChainApi.rejectPo(runId)
      pushOmni('text', 'Purchase Order cancelled. The pipeline has been stopped.')
      setPhase('done')
    } catch (err) {
      pushOmni('error', `Error: ${err.message}`)
    }
  }

  const handleReset = () => {
    setPhase('gathering')
    setHistory([])
    setRequirements(null)
    setSelectedSupplier(null)
    setMessages([{
      role: 'omni', type: 'text',
      content: 'Hi! I\'m your procurement assistant. What materials do you need? For example: "I need cotton fabric" or "500 navy blue zippers".'
    }])
  }

  const handleSend = (e) => { e.preventDefault(); sendMessage(input) }

  // ── Render a single message ─────────────────────────────────────
  const renderMsg = (msg, idx) => {
    if (msg.type === 'text') {
      const html = (msg.content || '').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>')
      return <p className="text-sm text-gray-700 leading-relaxed" dangerouslySetInnerHTML={{ __html: html }} />
    }

    if (msg.type === 'colour_palette') {
      return (
        <ColorPalette 
          question={msg.content}
          onSelect={(color) => {
            if (isTyping || phase !== 'gathering') return;
            // Send the selected color name as a user message
            sendMessage(color);
          }} 
          disabled={isTyping || phase !== 'gathering' || idx !== messages.length - 1} 
        />
      )
    }

    if (msg.type === 'supplier_list') {
      return (
        <div className="mt-2 space-y-2 w-full">
          {msg.data.suppliers.map(s => (
            <SupplierCard
              key={s.supplier_id}
              supplier={s}
              onSelect={handleSelectSupplier}
              disabled={isTyping}
              selected={false}
            />
          ))}
        </div>
      )
    }

    if (msg.type === 'supplier_list_done') {
      return (
        <div className="mt-2 space-y-2 w-full">
          {msg.data.suppliers.map(s => (
            <SupplierCard
              key={s.supplier_id}
              supplier={s}
              onSelect={() => {}}
              disabled={true}
              selected={s.supplier_id === msg.selectedId}
            />
          ))}
        </div>
      )
    }

    if (msg.type === 'po_card') {
      const d = msg.data || {}
      const sup = d._supplier || {}
      const req = d._requirements || {}
      return (
        <div className="mt-2 bg-white rounded-xl border border-gray-200 shadow-sm p-4 text-sm">
          <div className="space-y-1.5 mb-3">
            <div className="flex justify-between">
              <span className="text-gray-500">Supplier</span>
              <span className="font-semibold text-gray-800">{sup.name || d.supplier || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Country</span>
              <span className="font-semibold text-gray-800">{FLAGS[sup.country] || ''} {sup.country || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">PO #</span>
              <span className="font-mono font-semibold text-gray-800">#{d.po_id || d.po?.po_id || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Quantity</span>
              <span className="font-semibold text-gray-800">{Number(d.qty || req.qty || 0).toLocaleString()} {req.unit || ''}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Total Value</span>
              <span className="font-bold text-gray-900">LKR {Number(d.total_value || sup.estimated_total || req.total_value || 0).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Lead Time</span>
              <span className="font-semibold text-gray-800">{sup.lead_time_days || '—'} days</span>
            </div>
            <div className="mt-2 p-2 bg-green-50 rounded-lg text-xs text-green-700 border border-green-100">
              ✓ Compliance verified · {req.compliance_keywords?.join(', ') || 'Standard'}
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

    if (msg.type === 'po_card_done') {
      return (
        <div className={`mt-2 text-xs font-semibold px-3 py-2 rounded-lg border ${msg.approved ? 'bg-green-50 text-green-800 border-green-200' : 'bg-red-50 text-red-700 border-red-200'}`}>
          {msg.approved ? '✓ PO Authorized' : '✗ PO Cancelled'}
        </div>
      )
    }

    if (msg.type === 'shipment_card') {
      const d = msg.data || {}
      return (
        <div className="mt-2 bg-white rounded-xl border border-gray-200 shadow-sm p-4 text-sm space-y-1.5">
          <p className="text-sm text-gray-700 font-medium mb-2">{msg.content}</p>
          <div className="flex justify-between"><span className="text-gray-500">Shipment #</span><span className="font-mono font-semibold">#{d.shipment_id || '—'}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Carrier</span><span className="font-semibold">{d.carrier || '—'}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Mode</span><span className="font-semibold">{d.mode || '—'}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">ETA</span><span className="font-semibold">{d.eta || '—'}</span></div>
          {d.summary && <div className="mt-2 p-2 bg-blue-50 rounded-lg text-xs text-blue-800 italic border border-blue-100">"{d.summary}"</div>}
        </div>
      )
    }

    if (msg.type === 'error') {
      return <div className="mt-1 p-2 bg-red-50 text-red-700 rounded-lg border border-red-200 text-xs">{msg.content}</div>
    }

    return null
  }

  const inputLocked = isTyping || phase === 'selecting' || phase === 'approving' || phase === 'done'

  if (!isOpen) return null

  return (
    <div className="fixed bottom-6 right-6 z-40 w-[420px] h-[620px] flex flex-col rounded-2xl shadow-2xl bg-white border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 bg-[#1a2430] text-white flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#d9a441] to-[#7d5d2f] flex items-center justify-center text-sm font-bold">O</div>
          <div>
            <div className="font-bold text-sm">Omni Copilot</div>
            <div className="text-xs text-white/60">Procurement Assistant</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[9px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full ${
            phase === 'gathering'  ? 'bg-blue-500/30 text-blue-200' :
            phase === 'selecting'  ? 'bg-amber-500/30 text-amber-200' :
            phase === 'ordering' || phase === 'approving' ? 'bg-orange-500/30 text-orange-200' :
            'bg-green-500/30 text-green-200'
          }`}>
            {phase === 'gathering'  ? '● Gathering info' :
             phase === 'selecting'  ? '● Pick a supplier' :
             phase === 'ordering'   ? '● Creating PO' :
             phase === 'approving'  ? '● Review PO' : '✓ Done'}
          </span>
          {phase === 'done' && (
            <button onClick={handleReset} className="text-xs text-white/60 hover:text-white px-2 py-1 hover:bg-white/10 rounded-lg transition-colors">
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
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#d9a441] to-[#7d5d2f] flex-shrink-0 flex items-center justify-center text-white text-xs font-bold self-start mt-1">O</div>
            )}
            <div className={`max-w-[88%] ${msg.role === 'user' ? 'bg-[#1a2430] text-white rounded-2xl rounded-br-sm px-4 py-2.5 text-sm' : 'w-full'}`}>
              {msg.role === 'user'
                ? <p className="text-[13px]">{msg.content}</p>
                : renderMsg(msg, idx)
              }
            </div>
          </div>
        ))}

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
          disabled={inputLocked}
          placeholder={
            phase === 'selecting'  ? 'Click a supplier card above to select...' :
            phase === 'approving'  ? 'Authorize or Reject the PO above...' :
            phase === 'done'       ? 'Click "New" to start another request...' :
            'e.g. I need 500 meters of navy blue cotton fabric...'
          }
          className="flex-1 bg-gray-50 border border-gray-200 text-sm rounded-xl px-4 py-2.5 focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={inputLocked || !input.trim()}
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
