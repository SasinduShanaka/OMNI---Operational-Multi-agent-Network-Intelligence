import React, { useState, useEffect, useRef } from 'react'
import { supplyChainApi } from '../api/supplyChainApi'

// ------------------------------------------------------------------
// Sub-components: Beautiful UI Cards for Business Data
// ------------------------------------------------------------------

function PurchaseOrderCard({ po, onApprove, onReject, isLoading }) {
  return (
    <div className="bg-white rounded-xl shadow-md border border-gray-100 p-5 mt-3 max-w-lg animate-fade-in-up">
      <div className="flex items-center justify-between border-b pb-3 mb-3">
        <h3 className="text-lg font-bold text-gray-800 flex items-center">
          <span className="text-amber-500 mr-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          </span>
          Purchase Order #{po.po_id}
        </h3>
        <span className="bg-amber-100 text-amber-800 text-xs px-2 py-1 rounded-full font-semibold uppercase tracking-wider">
          Review Needed
        </span>
      </div>

      <div className="space-y-2 text-sm text-gray-600 mb-4">
        <div className="flex justify-between"><span className="font-medium text-gray-500">Supplier:</span> <span className="font-semibold text-gray-800">{po.supplier} ({po.country})</span></div>
        <div className="flex justify-between"><span className="font-medium text-gray-500">Quantity:</span> <span className="font-semibold text-gray-800">{po.qty} meters</span></div>
        <div className="flex justify-between"><span className="font-medium text-gray-500">Total Value:</span> <span className="font-semibold text-gray-800">LKR {po.total_value.toLocaleString()}</span></div>
        
        <div className="mt-3 p-3 bg-green-50 border border-green-100 rounded-lg text-xs text-green-800">
          <p className="font-bold mb-1 flex items-center">
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
            Compliance Verified
          </p>
          <p className="text-green-700 italic">"{po.proof}"</p>
        </div>
      </div>

      <div className="flex space-x-3 pt-2">
        <button 
          onClick={onApprove}
          disabled={isLoading}
          className="flex-1 bg-gradient-to-r from-[#d9a441] to-[#b87d39] text-white py-2 px-4 rounded-lg text-sm font-bold shadow-md hover:shadow-lg transition-all transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Processing...' : 'Authorize PO'}
        </button>
        <button 
          onClick={onReject}
          disabled={isLoading}
          className="flex-1 bg-white border border-gray-300 text-gray-700 py-2 px-4 rounded-lg text-sm font-bold hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Reject
        </button>
      </div>
    </div>
  )
}

function ShipmentCard({ shipment }) {
  return (
    <div className="bg-white rounded-xl shadow-md border border-gray-100 p-5 mt-3 max-w-lg animate-fade-in-up">
      <div className="flex items-center justify-between border-b pb-3 mb-3">
        <h3 className="text-lg font-bold text-gray-800 flex items-center">
          <span className="text-blue-500 mr-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
          </span>
          Logistics Booked
        </h3>
        <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-semibold uppercase tracking-wider">
          #{shipment.shipment_id}
        </span>
      </div>

      <div className="space-y-2 text-sm text-gray-600 mb-4">
        <div className="flex justify-between"><span className="font-medium text-gray-500">Carrier:</span> <span className="font-semibold text-gray-800">{shipment.carrier} ({shipment.mode.toUpperCase()})</span></div>
        <div className="flex justify-between"><span className="font-medium text-gray-500">Route:</span> <span className="font-semibold text-gray-800">{shipment.origin} → {shipment.destination}</span></div>
        <div className="flex justify-between"><span className="font-medium text-gray-500">Arrival ETA:</span> <span className="font-semibold text-gray-800">{shipment.eta}</span></div>
      </div>

      <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700 italic border-l-4 border-l-blue-500">
        "{shipment.summary}"
      </div>
    </div>
  )
}

// ------------------------------------------------------------------
// Main Component: Omni Copilot
// ------------------------------------------------------------------

export default function SupplyChainPanel() {
  const [messages, setMessages] = useState([
    { role: 'omni', type: 'text', content: 'Hello! I am Omni, your supply chain copilot. How can I assist you with procurement today?' }
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [typingText, setTypingText] = useState('')
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  // Simple NLP Parsing for demo purposes
  const parseIntent = (text) => {
    const t = text.toLowerCase()
    const isCotton = t.includes('cotton') || t.includes('fabric') || t.includes('meters')
    const isTrim = t.includes('button') || t.includes('zipper') || t.includes('trim')

    let qty = 500
    const numbers = t.match(/\d+/)
    if (numbers) qty = parseInt(numbers[0])

    if (isTrim) return { material_type: 'trim_vendor', qty, total_value: qty * 15 } // Mock calculation
    return { material_type: 'fabric_mill', qty, total_value: qty * 260 } // Mock calculation
  }

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    
    // Simulate thinking delay
    setIsTyping(true)
    setTypingText('Analyzing request...')
    await new Promise(r => setTimeout(r, 1000))

    const params = parseIntent(userMsg)
    
    // Check if it's a procurement request
    if (userMsg.toLowerCase().includes('need') || userMsg.toLowerCase().includes('buy') || userMsg.toLowerCase().includes('order')) {
      setTypingText('Searching for compliant suppliers...')
      
      try {
        const payload = {
          material_type: params.material_type,
          requirement_id: Math.floor(Math.random() * 100) + 1,
          qty: params.qty,
          total_value: params.total_value,
          compliance_keywords: ['Organic Cotton', 'Child-Labor Free'],
          destination: 'Colombo, LK'
        }

        const result = await supplyChainApi.startPipeline(payload)
        
        setIsTyping(false)
        setMessages(prev => [...prev, { 
          role: 'omni', 
          type: 'po_card', 
          content: `I've found a highly-rated, fully compliant supplier and drafted the Purchase Order. Please review the details below.`,
          data: result
        }])
      } catch (err) {
        setIsTyping(false)
        setMessages(prev => [...prev, { role: 'omni', type: 'error', content: `Error: ${err.message}` }])
      }
    } else {
      setIsTyping(false)
      setMessages(prev => [...prev, { role: 'omni', type: 'text', content: "I can help you procure materials. Try asking me something like: 'We need 500 meters of organic cotton fabric.'" }])
    }
  }

  const handleApprove = async (runId) => {
    setIsTyping(true)
    setTypingText('Authorizing PO and booking logistics...')
    
    // Optimistically hide the card's buttons
    setMessages(prev => prev.map(m => 
      (m.type === 'po_card' && m.data.run_id === runId) 
        ? { ...m, type: 'po_card_approved' } 
        : m
    ))

    try {
      const result = await supplyChainApi.approvePo(runId, 'System Admin')
      
      setIsTyping(false)
      setMessages(prev => [...prev, { 
        role: 'omni', 
        type: 'shipment_card', 
        content: `Purchase Order authorized! I've gone ahead and booked the logistics.`,
        data: result
      }])
    } catch (err) {
      setIsTyping(false)
      setMessages(prev => [...prev, { role: 'omni', type: 'error', content: `Logistics Error: ${err.message}` }])
    }
  }

  const handleReject = async (runId) => {
    setIsTyping(true)
    setTypingText('Cancelling pipeline...')
    
    setMessages(prev => prev.map(m => 
      (m.type === 'po_card' && m.data.run_id === runId) 
        ? { ...m, type: 'po_card_rejected' } 
        : m
    ))

    try {
      await supplyChainApi.rejectPo(runId)
      setIsTyping(false)
      setMessages(prev => [...prev, { role: 'omni', type: 'text', content: `The Purchase Order has been cancelled. Let me know if you need anything else.` }])
    } catch (err) {
      setIsTyping(false)
      setMessages(prev => [...prev, { role: 'omni', type: 'error', content: `Cancellation Error: ${err.message}` }])
    }
  }

  return (
    <div className="flex flex-col h-full bg-[#f5f1ea] font-sans relative overflow-hidden">
      
      {/* Header */}
      <div className="flex-shrink-0 px-8 py-6 border-b border-gray-200 bg-white/50 backdrop-blur-sm z-10">
        <h1 className="text-2xl font-bold text-gray-800 tracking-tight">Omni Procurement Copilot</h1>
        <p className="text-sm text-gray-500 mt-1">AI-assisted sourcing, purchasing, and logistics management.</p>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            
            {msg.role === 'omni' && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#d9a441] to-[#7d5d2f] flex items-center justify-center text-white font-bold text-sm shadow-md mr-3 flex-shrink-0 mt-1">
                O
              </div>
            )}

            <div className={`max-w-[75%] ${msg.role === 'user' ? 'bg-[#1a2430] text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-sm' : ''}`}>
              
              {/* Text Content */}
              {msg.role === 'user' ? (
                <p className="text-[15px] leading-relaxed">{msg.content}</p>
              ) : (
                <div className="text-[15px] text-gray-800 leading-relaxed pt-1">
                  {msg.content}
                </div>
              )}

              {/* Dynamic Business Cards */}
              {msg.type === 'po_card' && (
                <PurchaseOrderCard 
                  po={msg.data} 
                  onApprove={() => handleApprove(msg.data.run_id)} 
                  onReject={() => handleReject(msg.data.run_id)} 
                  isLoading={isTyping}
                />
              )}

              {msg.type === 'po_card_approved' && (
                <div className="mt-3 p-3 border border-green-200 bg-green-50 rounded-lg text-sm text-green-800 font-medium inline-block">
                  ✓ Purchase Order #{msg.data.po_id} Authorized
                </div>
              )}

              {msg.type === 'po_card_rejected' && (
                <div className="mt-3 p-3 border border-red-200 bg-red-50 rounded-lg text-sm text-red-800 font-medium inline-block">
                  ✗ Purchase Order Cancelled
                </div>
              )}

              {msg.type === 'shipment_card' && (
                <ShipmentCard shipment={msg.data} />
              )}

              {msg.type === 'error' && (
                <div className="mt-2 p-3 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">
                  {msg.content}
                </div>
              )}

            </div>
          </div>
        ))}

        {/* Loading Indicator */}
        {isTyping && (
          <div className="flex justify-start items-center">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#d9a441] to-[#7d5d2f] flex items-center justify-center text-white font-bold text-sm shadow-md mr-3 flex-shrink-0">
              O
            </div>
            <div className="text-sm text-gray-500 flex items-center font-medium animate-pulse-slow">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-[#d9a441]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {typingText}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-6 bg-white border-t border-gray-200">
        <form onSubmit={handleSend} className="relative max-w-4xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isTyping}
            placeholder="E.g., 'We need 500 meters of organic cotton fabric for the summer line...'"
            className="w-full bg-[#f8f9fa] border border-gray-300 text-gray-800 text-[15px] rounded-full pl-6 pr-14 py-4 focus:outline-none focus:border-[#d9a441] focus:ring-1 focus:ring-[#d9a441] shadow-sm transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isTyping || !input.trim()}
            className="absolute right-2 top-2 bottom-2 w-10 h-10 bg-[#1a2430] text-white rounded-full flex items-center justify-center hover:bg-[#2c3e50] transition-colors disabled:opacity-50 disabled:hover:bg-[#1a2430]"
          >
            <svg className="w-5 h-5 transform rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
          </button>
        </form>
        <div className="text-center mt-3 text-xs text-gray-400 font-medium">
          Omni AI Procurement & Logistics Agent · Beta Version
        </div>
      </div>
    </div>
  )
}
