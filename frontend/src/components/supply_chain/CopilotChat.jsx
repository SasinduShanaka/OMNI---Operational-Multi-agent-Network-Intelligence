import React, { useState, useRef, useEffect } from 'react'
import { supplyChainApi } from '../../api/supplyChainApi'

function isSupplyRequest(text) {
  const t = text.toLowerCase()
  return t.includes('need') || t.includes('buy') || t.includes('order') || t.includes('get') || t.includes('source')
}

export default function CopilotChat({ isOpen, onClose, onPipelineComplete, prefillSupplier, prefillQuery, clearQuery }) {
  const [messages, setMessages] = useState([
    { role: 'omni', type: 'text', content: 'Hi! I am your procurement assistant. Tell me what materials you need — for example: "I need 400 meters of organic cotton for our SS26 line."' }
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [typingText, setTypingText] = useState('')
  const messagesEndRef = useRef(null)

  // Pre-fill if opened from a supplier row
  useEffect(() => {
    if (prefillSupplier && isOpen) {
      setInput(`I need to order from ${prefillSupplier.name}`)
    }
  }, [prefillSupplier, isOpen])

  // Pre-fill and auto-send if opened from operations routing
  useEffect(() => {
    if (prefillQuery && isOpen && !isTyping) {
      // Simulate typing and submit the query directly via handleSend
      const mockEvent = { preventDefault: () => {} };
      
      // We must bypass state input so we pass it directly to handleSend equivalent
      submitQuery(prefillQuery);
      
      if (clearQuery) clearQuery();
    }
  }, [prefillQuery, isOpen])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const submitQuery = async (userMsg) => {
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setIsTyping(true)
    setTypingText('Analyzing request...')
    await new Promise(r => setTimeout(r, 800))

    if (!isSupplyRequest(userMsg)) {
      setIsTyping(false)
      setMessages(prev => [...prev, {
        role: 'omni', type: 'text',
        content: 'I can help you source and procure materials. Try: "We need 500 meters of organic cotton fabric."'
      }])
      return
    }

    setTypingText('Analyzing request with Agent...')

    try {
      const result = await supplyChainApi.chatPipeline({ message: userMsg })

      if (result.status === 'unrelated') {
        setIsTyping(false)
        setMessages(prev => [...prev, {
          role: 'omni', type: 'text',
          content: result.message
        }])
        return
      }

      setIsTyping(false)
      setMessages(prev => [...prev, {
        role: 'omni',
        type: 'po_card',
        content: `I found a compliant supplier and drafted a Purchase Order. Please review and authorize below.`,
        data: result
      }])
    } catch (err) {
      setIsTyping(false)
      setMessages(prev => [...prev, { role: 'omni', type: 'error', content: `Error: ${err.message}` }])
    }
  }

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim()) return
    const userMsg = input.trim()
    setInput('')
    submitQuery(userMsg)
  }

  const handleApprove = async (runId, poId) => {
    setIsTyping(true)
    setTypingText('Authorizing PO & booking logistics...')
    setMessages(prev => prev.map(m =>
      (m.type === 'po_card' && m.data.run_id === runId) ? { ...m, type: 'po_card_done', approved: true } : m
    ))
    try {
      const result = await supplyChainApi.approvePo(runId, 'Human Manager')
      setIsTyping(false)
      setMessages(prev => [...prev, {
        role: 'omni', type: 'shipment_card',
        content: 'PO authorized! Freight booked and shipment is underway.',
        data: result
      }])
      if (onPipelineComplete) onPipelineComplete()
    } catch (err) {
      setIsTyping(false)
      setMessages(prev => [...prev, { role: 'omni', type: 'error', content: `Logistics error: ${err.message}` }])
    }
  }

  const handleReject = async (runId) => {
    setMessages(prev => prev.map(m =>
      (m.type === 'po_card' && m.data.run_id === runId) ? { ...m, type: 'po_card_done', approved: false } : m
    ))
    try {
      await supplyChainApi.rejectPo(runId)
      setMessages(prev => [...prev, { role: 'omni', type: 'text', content: 'Purchase Order cancelled. The pipeline has been stopped.' }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'omni', type: 'error', content: `Error: ${err.message}` }])
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed bottom-6 right-6 z-40 w-[400px] h-[580px] flex flex-col rounded-2xl shadow-2xl bg-white border border-gray-200 animate-fade-in-up overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 bg-[#1a2430] text-white flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#d9a441] to-[#7d5d2f] flex items-center justify-center text-sm font-bold shadow">O</div>
          <div>
            <div className="font-bold text-sm">Omni Copilot</div>
            <div className="text-xs text-white/60">Procurement Assistant</div>
          </div>
        </div>
        <button onClick={onClose} className="p-1.5 hover:bg-white/10 rounded-lg transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#f9f8f6]">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} items-end gap-2`}>
            {msg.role === 'omni' && (
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#d9a441] to-[#7d5d2f] flex-shrink-0 flex items-center justify-center text-white text-xs font-bold">O</div>
            )}
            <div className={`max-w-[85%] ${msg.role === 'user' ? 'bg-[#1a2430] text-white rounded-2xl rounded-br-sm px-4 py-2.5 text-sm' : ''}`}>
              {msg.role !== 'user' && <p className="text-sm text-gray-700 leading-relaxed">{msg.content}</p>}
              {msg.role === 'user' && <p className="text-[13px]">{msg.content}</p>}

              {/* PO Card */}
              {msg.type === 'po_card' && (
                <div className="mt-2 bg-white rounded-xl border border-gray-200 shadow-sm p-4 text-sm">
                  <div className="space-y-1.5 mb-3">
                    <div className="flex justify-between"><span className="text-gray-500">Supplier</span><span className="font-semibold text-gray-800">{msg.data.supplier?.supplier_name}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">PO #</span><span className="font-mono font-semibold text-gray-800">#{msg.data.po?.po_id}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">Value</span><span className="font-semibold text-gray-800">LKR {msg.data.po?.total_value?.toLocaleString()}</span></div>
                    <div className="mt-2 p-2 bg-green-50 rounded-lg text-xs text-green-700 border border-green-100">✓ Compliance verified</div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleApprove(msg.data.run_id, msg.data.po?.po_id)} disabled={isTyping} className="flex-1 bg-gradient-to-r from-[#d9a441] to-[#b87d39] text-white text-xs font-bold py-2 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50">Authorize</button>
                    <button onClick={() => handleReject(msg.data.run_id)} disabled={isTyping} className="flex-1 border border-gray-300 text-gray-700 text-xs font-bold py-2 rounded-lg hover:bg-gray-50 disabled:opacity-50">Reject</button>
                  </div>
                </div>
              )}

              {msg.type === 'po_card_done' && (
                <div className={`mt-2 text-xs font-semibold px-3 py-2 rounded-lg border ${msg.approved ? 'bg-green-50 text-green-800 border-green-200' : 'bg-red-50 text-red-700 border-red-200'}`}>
                  {msg.approved ? '✓ PO Authorized' : '✗ PO Cancelled'}
                </div>
              )}

              {msg.type === 'shipment_card' && (
                <div className="mt-2 bg-white rounded-xl border border-gray-200 shadow-sm p-4 text-sm space-y-1.5">
                  <div className="flex justify-between"><span className="text-gray-500">Shipment</span><span className="font-mono font-semibold text-gray-800">#{msg.data.shipment?.shipment_id}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Carrier</span><span className="font-semibold text-gray-800">{msg.data.shipment?.carrier}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">ETA</span><span className="font-semibold text-gray-800">{msg.data.shipment?.eta}</span></div>
                  <div className="mt-2 p-2 bg-blue-50 rounded-lg text-xs text-blue-800 italic border border-blue-100">"{msg.data.shipment?.summary}"</div>
                </div>
              )}

              {msg.type === 'error' && (
                <div className="mt-2 p-2 bg-red-50 text-red-700 rounded-lg border border-red-200 text-xs">{msg.content}</div>
              )}
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
          disabled={isTyping}
          placeholder="e.g. Need 300m of organic cotton..."
          className="flex-1 bg-gray-50 border border-gray-200 text-sm rounded-xl px-4 py-2.5 focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isTyping || !input.trim()}
          className="w-9 h-9 bg-[#1a2430] text-white rounded-xl flex items-center justify-center hover:bg-[#2c3e50] transition-colors disabled:opacity-40"
        >
          <svg className="w-4 h-4 transform rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
        </button>
      </form>
    </div>
  )
}
