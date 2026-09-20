import React, { useState } from 'react'
import { supplyChainApi } from '../api/supplyChainApi'

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function OperationsAgent({ chatState, setChatState, setActivePage, setScQuery }) {
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID())
  const { draft, messages, isAsking, error } = chatState

  function updateChatState(patch) {
    setChatState((previous) => ({
      ...previous,
      ...patch,
    }))
  }

  async function handleSend(actionText = null, payload = null) {
    const userMessage = typeof actionText === 'string' ? actionText : draft.trim()
    if (!userMessage || isAsking) {
      return
    }

    updateChatState({
      messages: [
        ...messages,
        {
          type: 'user',
          text: userMessage,
        },
      ],
      draft: '',
      isAsking: true,
      error: '',
    })

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
          payload: payload
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data?.detail?.message || data?.detail || `Request failed: ${response.status}`
        )
      }
      
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id)
      }

      updateChatState({
        messages: [
          ...messages,
          {
            type: 'user',
            text: userMessage,
          },
          {
            type: 'agent',
            data,
          },
        ],
        isAsking: false,
      })
    } catch (requestError) {
      console.error(requestError)

      updateChatState({
        error: requestError.message ||
          'I could not connect to the Operations Agent. Please make sure the backend is running.',
        isAsking: false,
      })
    }
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter') {
      event.preventDefault()
      handleSend()
    }
  }

  const suggestedQuestions = [
    'Show me the full fabric stock list',
    'Which materials are below safety stock?',
    'How much Black Cotton Fabric is available?',
    'Forecast demand for GAR-003 next month',
  ]

  return (
    <section className="w-full h-full flex flex-col p-8">

      {/* Header */}
      <div className="mb-5 flex-shrink-0">
        <div className="inline-flex items-center gap-2 rounded-full bg-[#1d4ed8] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#e2e8f0] mb-3">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
          Factory assistant
        </div>
        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">
          Ask Omni
        </h2>

        <p className="text-sm text-[#64748b] mt-2">
          Factory operations assistant for stock, sourcing, and production planning
        </p>
      </div>


      {/* Chat container */}
      <div className="flex-1 min-h-0 bg-white border border-slate-200 rounded-2xl shadow-[0_12px_30px_rgba(15,23,42,0.06)] overflow-hidden flex flex-col">

        {/* Conversation */}
        <div className="flex-1 min-h-0 p-6 overflow-y-auto">

          {messages.length === 0 && (
            <div className="flex items-center justify-center min-h-[400px]">

              <div className="text-center max-w-md">

                <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-[#eff6ff] border border-[#bfdbfe] flex items-center justify-center shadow-sm">
                  <span className="text-xl text-[#0369a1]">
                    ✦
                  </span>
                </div>

                <h3 className="text-lg font-semibold text-slate-800">
                  How can I help today?
                </h3>

                <p className="text-sm text-slate-500 mt-2 leading-6">
                  Ask about demand forecasts, raw material availability,
                  production shortages, line constraints,
                  or replenishment timing.
                </p>

              </div>

            </div>
          )}


          <div className="space-y-6">

            {messages.map((item, index) => (

              <div key={index}>

                {item.type === 'user' && (
                  <UserMessage text={item.text} />
                )}

                {item.type === 'agent' && (
                  <AgentResponse 
                    data={item.data} 
                    setActivePage={setActivePage} 
                    setScQuery={setScQuery}
                    handleSend={handleSend}
                  />
                )}

              </div>

            ))}


            {isAsking && (
              <div>

                <p className="text-xs font-medium text-slate-500 mb-2">
                  Ask Omni
                </p>

                <div className="inline-flex items-center gap-2 bg-[#f1f5f9] text-[#475569] rounded-xl px-4 py-3 text-sm border border-[#cbd5e1]">

                  <span className="w-2 h-2 rounded-full bg-[#3b82f6] animate-pulse"></span>

                  Checking factory data and supplier status...

                </div>

              </div>
            )}

          </div>


          {error && (
            <div className="mt-5 p-4 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm">
              {error}
            </div>
          )}

        </div>


        {/* Suggested questions */}
        {messages.length === 0 && (
          <div className="px-6 pb-5 flex-shrink-0 border-t border-slate-100 pt-4">

            <p className="text-xs text-slate-400 mb-2">
              Try asking
            </p>

            <div className="flex flex-wrap gap-2">

              {suggestedQuestions.map((question) => (
                <button
                  key={question}
                  onClick={() => updateChatState({ draft: question })}
                  className="px-3 py-2 rounded-lg border border-[#cbd5e1] bg-[#ffffff] text-xs text-[#475569] hover:border-[#3b82f6] hover:bg-[#dbeafe] transition"
                >
                  {question}
                </button>
              ))}

            </div>

          </div>
        )}


        {/* Input */}
        <div className="border-t border-slate-100 p-4 flex-shrink-0">

          <div className="flex gap-3">

            <input
              type="text"
              value={draft}
              onChange={(event) => updateChatState({ draft: event.target.value })}
              onKeyDown={handleKeyDown}
              disabled={isAsking}
              placeholder="Ask about demand, fabric, shortages, or production planning..."
              className="flex-1 px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-800 placeholder-slate-400 outline-none focus:bg-white focus:border-[#2563eb] focus:ring-2 focus:ring-[#3b82f6]/20 transition"
            />

            <button
              onClick={handleSend}
              disabled={isAsking || !draft.trim()}
              className="px-5 py-3 rounded-xl bg-[#1d4ed8] hover:bg-[#1e40af] text-white text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAsking ? '...' : 'Send'}
            </button>

          </div>

        </div>

      </div>

    </section>
  )
}


/* ============================================================
   USER MESSAGE
============================================================ */

function UserMessage({ text }) {
  return (
    <div className="flex justify-end">

      <div className="max-w-[78%]">

        <p className="text-xs text-slate-400 text-right mb-1">
          You
        </p>

        <div className="bg-[#1d4ed8] text-white rounded-2xl rounded-tr-md px-4 py-3 text-sm leading-6 shadow-sm">
          {text}
        </div>

      </div>

    </div>
  )
}


/* ============================================================
   AGENT RESPONSE
============================================================ */

function AgentResponse({ data, setActivePage, setScQuery, handleSend }) {
  if (!data) {
    return null
  }

  return (
    <div className="max-w-[92%]">

      <p className="text-xs font-medium text-slate-500 mb-2">
        Ops chat agent
      </p>


      {/* ======================================================
          WORKFLOW
      ====================================================== */}

      {data.workflow && data.workflow.length > 0 && (

        <div className="mb-3">

          <div className="flex flex-wrap items-center gap-2">

            {data.workflow.map((agent, index) => (

              <React.Fragment key={`${agent}-${index}`}>

                <span className="inline-flex items-center px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-medium text-slate-600">

                  {index === 0 ? 'Operations Agent' : agent}

                </span>

                {index < data.workflow.length - 1 && (
                  <span className="text-slate-300">
                    →
                  </span>
                )}

              </React.Fragment>

            ))}

          </div>

        </div>

      )}


      {/* ======================================================
          ANSWER
      ====================================================== */}

      {data.answer && (

        <div className="bg-slate-100 text-slate-800 rounded-2xl rounded-tl-md px-5 py-4 text-sm leading-7">

          {data.answer}

        </div>

      )}

      {/* ======================================================
          SHADE SELECTION
      ====================================================== */}

      {data.status === 'needs_shade_selection' && (
        <div className="mt-4 p-4 border border-[#e2e8f0] rounded-xl bg-white shadow-sm max-w-sm">
          <ColorPalette 
            question={data.answer} 
            onSelect={(shade) => handleSend && handleSend(shade)} 
          />
        </div>
      )}

      {/* ======================================================
          SELECTING (SUPPLIERS)
      ====================================================== */}

      {data.status === 'selecting' && data.suppliers && (
        <div className="mt-4 max-w-md space-y-2">
          {data.suppliers.map((sup, idx) => (
            <SupplierCard 
              key={idx} 
              supplier={sup} 
              onSelect={(supplier) => handleSend && handleSend(`Selected supplier: ${supplier.name}`, { supplier })}
            />
          ))}
        </div>
      )}

      {/* ======================================================
          PROCUREMENT
      ====================================================== */}

      {data.intent === 'procurement' && data.data && (
        <OmniProcurementCard data={data.data} />
      )}

      {/* ======================================================
          DEMAND FORECAST
      ====================================================== */}

      {data.intent === 'demand_forecast' && data.result && (
        <ForecastCard result={data.result} />
      )}

      {data.intent === 'demand_forecast' && data.results && (
        <ForecastList results={data.results} />
      )}


      {/* ======================================================
          INVENTORY LIST
      ====================================================== */}

      {data.intent === 'inventory_list' &&
        data.results && (

          <InventoryList
            results={data.results}
          />

        )}


      {/* ======================================================
          LOW STOCK
      ====================================================== */}

      {data.intent === 'low_stock' &&
        data.results && (

          <LowStockList
            results={data.results}
          />

        )}


      {/* ======================================================
          OUT OF STOCK
      ====================================================== */}

      {data.intent === 'out_of_stock' &&
        data.results && (

          <LowStockList
            results={data.results}
            outOfStock
          />

        )}


      {/* ======================================================
          HEALTHY STOCK
      ====================================================== */}

      {data.intent === 'healthy_stock' &&
        data.results && (

          <HealthyStockList
            results={data.results}
          />

        )}


      {/* ======================================================
          REORDER
      ====================================================== */}

      {data.intent === 'reorder_requirements' &&
        data.results && (

          <ReorderList
            results={data.results}
          />

        )}


      {/* ======================================================
          MATERIAL STATUS
      ====================================================== */}

      {data.intent === 'material_status' &&
        data.result && (

          <MaterialCard
            result={data.result}
          />

        )}


      {/* ======================================================
          INVENTORY REQUIREMENT
      ====================================================== */}

      {data.intent === 'inventory_requirement' &&
        data.result && (

          <RequirementCard
            result={data.result}
          />

        )}


      {/* ======================================================
          INVENTORY SUMMARY
      ====================================================== */}

      {data.intent === 'inventory_summary' &&
        data.result && (

          <SummaryCard
            result={data.result}
          />

        )}


      {/* ======================================================
          TOTAL STOCK
      ====================================================== */}

      {data.intent === 'total_stock' &&
        data.result && (

          <TotalStockCard
            result={data.result}
          />

        )}


      {/* ======================================================
          KPI
      ====================================================== */}

      {data.intent === 'inventory_kpis' &&
        data.result && (

          <KpiCard
            result={data.result}
          />

        )}


      {/* ======================================================
          METADATA
      ====================================================== */}

      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 text-xs text-slate-400">

        {data.intent && (
          <span>
            Intent: {formatIntent(data.intent)}
          </span>
        )}

        {data.delegated_to && (
          <span>
            Delegated to: {data.delegated_to}
          </span>
        )}

        {data.status && (
          <span className={
            data.status === 'success'
              ? 'text-emerald-600'
              : 'text-amber-600'
          }>
            {formatStatus(data.status)}
          </span>
        )}

      </div>

    </div>
  )
}


/* ============================================================
   FORECAST RESULTS
============================================================ */

function ForecastCard({ result }) {
  return (
    <div className="mt-4 rounded-xl border border-[#3b82f6]/30 bg-[#ffffff] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-800">{result.product_name}</p>
          <p className="mt-1 text-xs text-slate-500">{result.sku} · {result.model}</p>
        </div>
        <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">{result.trend}</span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4">
        <div><p className="text-xs text-slate-500">Next-month forecast</p><p className="mt-1 text-lg font-semibold text-slate-900">{Number(result.forecast).toLocaleString()} units</p></div>
        <div><p className="text-xs text-slate-500">History analyzed</p><p className="mt-1 text-lg font-semibold text-slate-900">{result.history_points} periods</p></div>
      </div>
    </div>
  )
}


function ForecastList({ results }) {
  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="border-b border-slate-100 px-4 py-3"><p className="text-sm font-semibold text-slate-800">Demand Forecast Agent results</p></div>
      <div className="divide-y divide-slate-100">
        {results.map((result) => (
          <div key={result.sku} className="flex items-center justify-between gap-4 px-4 py-3">
            <div><p className="text-sm font-medium text-slate-800">{result.product_name}</p><p className="mt-1 text-xs text-slate-500">{result.sku} · {result.trend}</p></div>
            <div className="text-right"><p className="text-sm font-semibold text-slate-900">{Number(result.forecast).toLocaleString()} units</p><p className="mt-1 text-xs text-slate-500">next month</p></div>
          </div>
        ))}
      </div>
    </div>
  )
}


/* ============================================================
   INVENTORY LIST
============================================================ */

function InventoryList({ results }) {

  return (
    <div className="mt-4 border border-slate-200 rounded-xl overflow-hidden bg-white">

      <div className="px-4 py-3 border-b border-slate-100">

        <h3 className="font-semibold text-slate-800 text-sm">
          Inventory details
        </h3>

        <p className="text-xs text-slate-400 mt-1">
          {results.length} materials currently recorded
        </p>

      </div>


      <div className="divide-y divide-slate-100">

        {results.map((item) => (

          <InventoryRow
            key={item.material_code}
            item={item}
          />

        ))}

      </div>

    </div>
  )
}


/* ============================================================
   INVENTORY ROW
============================================================ */

function InventoryRow({ item }) {

  const lowStock = item.status === 'LOW_STOCK'
  const outOfStock = item.status === 'OUT_OF_STOCK'

  return (
    <div className="px-4 py-4">

      <div className="flex items-center justify-between gap-4">

        <div>

          <p className="text-sm font-medium text-slate-800">
            {item.material_name}
          </p>

          <p className="text-xs text-slate-400 mt-1">
            {item.material_code}
          </p>

        </div>


        <span className={

          outOfStock
            ? 'px-2.5 py-1 rounded-full bg-red-50 text-red-600 text-xs font-medium'
            : lowStock
              ? 'px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 text-xs font-medium'
              : 'px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 text-xs font-medium'

        }>

          {outOfStock
            ? 'Out of stock'
            : lowStock
              ? 'Low stock'
              : 'Healthy'}

        </span>

      </div>


      <div className="grid grid-cols-3 gap-4 mt-4">

        <Detail
          label="Current stock"
          value={`${item.current_stock} ${item.unit}`}
        />

        <Detail
          label="Reorder level"
          value={`${item.reorder_level} ${item.unit}`}
        />

        <Detail
          label="Shortage"
          value={`${item.shortage} ${item.unit}`}
          danger={lowStock || outOfStock}
        />

      </div>

    </div>
  )
}


/* ============================================================
   LOW STOCK
============================================================ */

function LowStockList({ results, outOfStock = false }) {

  if (results.length === 0) {

    return (
      <div className="mt-4 p-4 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-700 text-sm">
        {outOfStock
          ? 'There are currently no materials completely out of stock.'
          : 'Good news — there are currently no materials below their reorder levels.'
        }
      </div>
    )

  }


  return (
    <div className="mt-4 space-y-2">

      {results.map((item) => (

        <InventoryRow
          key={item.material_code}
          item={item}
        />

      ))}

    </div>
  )
}


/* ============================================================
   HEALTHY STOCK
============================================================ */

function HealthyStockList({ results }) {

  return (
    <div className="mt-4 border border-emerald-100 rounded-xl overflow-hidden">

      <div className="px-4 py-3 bg-emerald-50">

        <p className="text-sm font-semibold text-emerald-700">
          Healthy inventory
        </p>

        <p className="text-xs text-emerald-600 mt-1">
          {results.length} materials are currently at or above
          their reorder levels.
        </p>

      </div>

      {results.map((item) => (

        <InventoryRow
          key={item.material_code}
          item={item}
        />

      ))}

    </div>
  )
}


/* ============================================================
   REORDER LIST
============================================================ */

function ReorderList({ results }) {

  return (
    <div className="mt-4 border border-slate-200 rounded-xl overflow-hidden">

      <div className="px-4 py-3 bg-slate-50 border-b border-slate-100">

        <p className="text-sm font-semibold text-slate-800">
          Replenishment requirements
        </p>

      </div>


      <div className="divide-y divide-slate-100">

        {results.map((item) => (

          <div
            key={item.material_code}
            className="px-4 py-4"
          >

            <p className="text-sm font-medium text-slate-800">
              {item.material_name}
            </p>

            <div className="grid grid-cols-3 gap-4 mt-3">

              <Detail
                label="Current"
                value={`${item.current_stock} ${item.unit}`}
              />

              <Detail
                label="Reorder level"
                value={`${item.reorder_level} ${item.unit}`}
              />

              <Detail
                label="Replenish"
                value={`${item.reorder_quantity} ${item.unit}`}
                danger
              />

            </div>

          </div>

        ))}

      </div>

    </div>
  )
}


/* ============================================================
   MATERIAL CARD
============================================================ */

function MaterialCard({ result }) {

  const lowStock = result.status === 'LOW_STOCK'
  const outOfStock = result.status === 'OUT_OF_STOCK'

  return (
    <div className="mt-4 border border-slate-200 rounded-xl p-4">

      <div className="flex justify-between items-start gap-3 mb-4">

        <div>

          <h3 className="text-sm font-semibold text-slate-800">
            {result.material_name}
          </h3>

          <p className="text-xs text-slate-400 mt-1">
            {result.material_code}
          </p>

        </div>


        <span className={
          outOfStock
            ? 'px-2.5 py-1 rounded-full bg-red-50 text-red-600 text-xs'
            : lowStock
              ? 'px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 text-xs'
              : 'px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 text-xs'
        }>
          {outOfStock
            ? 'Out of stock'
            : lowStock
              ? 'Low stock'
              : 'Healthy'
          }
        </span>

      </div>


      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        <Detail
          label="Current stock"
          value={`${result.current_stock} ${result.unit}`}
        />

        <Detail
          label="Reorder level"
          value={`${result.reorder_level} ${result.unit}`}
        />

        <Detail
          label="Shortage"
          value={`${result.shortage} ${result.unit}`}
          danger={lowStock || outOfStock}
        />

        <Detail
          label="Recommendation"
          value={result.recommendation}
        />

      </div>

    </div>
  )
}


/* ============================================================
   REQUIREMENT CARD
============================================================ */

function RequirementCard({ result }) {

  const shortage = result.status === 'SHORTAGE'

  return (
    <div className="mt-4 border border-slate-200 rounded-xl p-4">

      <div className="flex justify-between items-center mb-4">

        <h3 className="text-sm font-semibold text-slate-800">
          Inventory requirement
        </h3>

        <span className={
          shortage
            ? 'px-2.5 py-1 rounded-full bg-red-50 text-red-600 text-xs font-medium'
            : 'px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 text-xs font-medium'
        }>
          {shortage ? 'Shortage' : 'Sufficient stock'}
        </span>

      </div>


      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        <Detail
          label="Material"
          value={result.material_name}
        />

        <Detail
          label="Available"
          value={`${result.available_quantity} ${result.unit}`}
        />

        <Detail
          label="Required"
          value={`${result.required_quantity} ${result.unit}`}
        />

        <Detail
          label="Shortage"
          value={`${result.shortage} ${result.unit}`}
          danger={shortage}
        />

      </div>


      {result.message && (
        <div className={
          shortage
            ? 'mt-4 p-3 rounded-lg bg-red-50 text-red-600 text-sm'
            : 'mt-4 p-3 rounded-lg bg-emerald-50 text-emerald-700 text-sm'
        }>
          {result.message}
        </div>
      )}

    </div>
  )
}


/* ============================================================
   SUMMARY CARD
============================================================ */

function SummaryCard({ result }) {

  const critical = result.inventory_health === 'CRITICAL'
  const needsAttention = result.inventory_health === 'NEEDS_ATTENTION'

  return (
    <div className="mt-4 border border-slate-200 rounded-xl p-4">

      <div className="flex justify-between items-center mb-4">

        <h3 className="text-sm font-semibold text-slate-800">
          Inventory health
        </h3>

        <span className={
          critical
            ? 'px-2.5 py-1 rounded-full bg-red-50 text-red-600 text-xs'
            : needsAttention
              ? 'px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 text-xs'
              : 'px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 text-xs'
        }>
          {result.inventory_health}
        </span>

      </div>


      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        <Detail
          label="Total materials"
          value={result.total_materials}
        />

        <Detail
          label="Healthy"
          value={result.healthy_materials}
        />

        <Detail
          label="Low stock"
          value={result.low_stock_materials}
          danger={result.low_stock_materials > 0}
        />

        <Detail
          label="Out of stock"
          value={result.out_of_stock_materials}
          danger={result.out_of_stock_materials > 0}
        />

      </div>

    </div>
  )
}


/* ============================================================
   TOTAL STOCK CARD
============================================================ */

function TotalStockCard({ result }) {

  const units = result.units?.join(', ') || ''

  return (
    <div className="mt-4 border border-slate-200 rounded-xl p-4">

      <h3 className="text-sm font-semibold text-slate-800 mb-4">
        Total inventory
      </h3>

      <div className="grid grid-cols-2 gap-4">

        <Detail
          label="Total stock"
          value={`${result.total_stock} ${units}`}
        />

        <Detail
          label="Materials"
          value={result.material_count}
        />

      </div>

    </div>
  )
}


/* ============================================================
   KPI CARD
============================================================ */

function KpiCard({ result }) {

  return (
    <div className="mt-4 border border-slate-200 rounded-xl p-4">

      <h3 className="text-sm font-semibold text-slate-800 mb-4">
        Inventory KPIs
      </h3>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        <Detail
          label="Total materials"
          value={result.total_materials}
        />

        <Detail
          label="Healthy"
          value={`${result.healthy_percentage}%`}
        />

        <Detail
          label="Low stock"
          value={`${result.low_stock_percentage}%`}
        />

        <Detail
          label="Out of stock"
          value={`${result.out_of_stock_percentage}%`}
          danger={result.out_of_stock_percentage > 0}
        />

      </div>

    </div>
  )
}


/* ============================================================
   DETAIL
============================================================ */

function Detail({
  label,
  value,
  danger = false,
}) {

  return (
    <div>

      <p className="text-xs text-slate-400 mb-1">
        {label}
      </p>

      <p className={
        danger
          ? 'text-sm font-semibold text-red-600'
          : 'text-sm font-medium text-slate-800'
      }>
        {value}
      </p>

    </div>
  )
}


/* ============================================================
   HELPERS
============================================================ */

function formatIntent(intent) {

  return intent
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}


function formatStatus(status) {

  return status
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}


/* ============================================================
   OMNI PROCUREMENT CARD

   NOTE: this component was left unfinished on the dev branch — the
   file ended mid-comment here with no implementation, and
   OmniProcurementCard was referenced above without ever being
   imported or defined. This is a minimal fallback so a procurement
   response renders instead of crashing with a ReferenceError.
   Replace with the real UI once the intended design is available.
============================================================ */

function OmniProcurementCard({ data }) {
  const supplier = data.supplier || {}
  const po = data.po || {}
  const [status, setStatus] = useState(data.status || 'unknown')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [actionResult, setActionResult] = useState(null)
  const [actionError, setActionError] = useState('')
  const isAwaitingApproval = status === 'awaiting_approval'

  async function handleApprove() {
    if (!data.run_id || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setActionError('')

    try {
      const result = await supplyChainApi.approvePo(data.run_id, 'Human Manager')
      setStatus('completed')
      setActionResult({
        type: 'approved',
        message: 'Approved. Freight booking has been started for this purchase order.',
        details: result,
      })
    } catch (error) {
      setActionError(error.message || 'Could not approve this purchase order.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleReject() {
    if (!data.run_id || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setActionError('')

    try {
      await supplyChainApi.rejectPo(data.run_id)
      setStatus('rejected')
      setActionResult({
        type: 'rejected',
        message: 'Rejected. I stopped this procurement pipeline.',
      })
    } catch (error) {
      setActionError(error.message || 'Could not reject this purchase order.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mt-4 overflow-hidden rounded-2xl border border-[#e2e8f0] bg-white text-sm text-slate-700 shadow-sm">
      <div className="flex items-start justify-between gap-3 border-b border-slate-100 bg-[#ffffff] px-4 py-3">
        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-[#0369a1]">Procurement run</p>
          <p className="mt-1 font-semibold text-slate-900">
            {supplier.supplier_name || 'Supplier selected'}
          </p>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
          isAwaitingApproval
            ? 'bg-amber-100 text-amber-700'
            : status === 'failed'
              ? 'bg-red-100 text-red-700'
              : 'bg-emerald-100 text-emerald-700'
        }`}>
          {formatStatus(status)}
        </span>
      </div>

      <div className="grid gap-3 p-4 md:grid-cols-2">
        <Detail label="Run ID" value={data.run_id || '-'} />
        <Detail label="Material Type" value={formatStatus(data.material_type || 'unknown')} />
        <Detail label="Supplier" value={supplier.supplier_name || '-'} />
        <Detail label="Country" value={supplier.country || '-'} />
        <Detail label="Rating" value={supplier.rating !== undefined ? Number(supplier.rating).toFixed(1) : '-'} />
        <Detail label="Lead Time" value={supplier.lead_time_days ? `${supplier.lead_time_days} days` : '-'} />
        <Detail label="PO ID" value={po.po_id ? `#${po.po_id}` : '-'} />
        <Detail label="PO Status" value={formatStatus(po.status || status)} />
        <Detail label="Quantity" value={data.qty ? Number(data.qty).toLocaleString() : po.qty ? Number(po.qty).toLocaleString() : '-'} />
        <Detail label="Total Value" value={data.total_value ? `LKR ${Number(data.total_value).toLocaleString()}` : '-'} />
      </div>

      {supplier.compliance_proof && (
        <div className="border-t border-slate-100 px-4 py-3">
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Compliance proof</p>
          <p className="mt-1 text-xs leading-5 text-slate-600">{supplier.compliance_proof}</p>
        </div>
      )}

      {isAwaitingApproval && (
        <div className="border-t border-slate-100 bg-[#ffffff] px-4 py-4">
          <p className="text-sm font-semibold text-slate-900">
            Ready for your approval
          </p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Authorize this PO to continue with freight booking, or reject it to stop the pipeline.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleApprove}
              disabled={isSubmitting}
              className="rounded-lg bg-[#1d4ed8] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#1e40af] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? 'Working...' : 'Authorize PO'}
            </button>
            <button
              type="button"
              onClick={handleReject}
              disabled={isSubmitting}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {actionResult && (
        <div className={`border-t px-4 py-3 text-xs ${
          actionResult.type === 'approved'
            ? 'border-emerald-100 bg-emerald-50 text-emerald-800'
            : 'border-red-100 bg-red-50 text-red-700'
        }`}>
          <p className="font-semibold">{actionResult.message}</p>
          {actionResult.details?.shipment_id && (
            <p className="mt-1">
              Shipment #{actionResult.details.shipment_id}
              {actionResult.details.carrier ? ` with ${actionResult.details.carrier}` : ''}
              {actionResult.details.eta ? `, ETA ${actionResult.details.eta}` : ''}.
            </p>
          )}
        </div>
      )}

      {actionError && (
        <div className="border-t border-red-100 bg-red-50 px-4 py-3 text-xs text-red-700">
          {actionError}
        </div>
      )}

      {data.error && (
        <div className="border-t border-red-100 bg-red-50 px-4 py-3 text-xs text-red-700">
          {data.error}
        </div>
      )}
    </div>
  )
}

export default OperationsAgent

// ── Shared Supplier UI Components ──────────────────────────────────────

const FLAGS = {
  'Sri Lanka': '🇱🇰', 'India': '🇮🇳', 'Bangladesh': '🇧🇩',
  'Turkey': '🇹🇷', 'Pakistan': '🇵🇰', 'China': '🇨🇳',
  'Vietnam': '🇻🇳', 'Indonesia': '🇮🇩',
}

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
          {supplier.rating !== undefined && (
            <div className="flex items-center gap-1 mt-1">
              <span className="text-xs font-medium text-amber-500">★ {Number(supplier.rating).toFixed(1)}</span>
            </div>
          )}
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
