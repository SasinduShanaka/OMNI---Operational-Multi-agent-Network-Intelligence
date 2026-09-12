import React, { useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function OperationsAgent({ chatState, setChatState }) {
  const { draft, messages, isAsking, error } = chatState

  function updateChatState(patch) {
    setChatState((previous) => ({
      ...previous,
      ...patch,
    }))
  }

  async function handleSend() {
    if (!draft.trim() || isAsking) {
      return
    }

    const userMessage = draft.trim()

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
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data?.detail?.message || data?.detail || `Request failed: ${response.status}`
        )
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
    <section className="w-full h-[calc(100vh-32px)] flex flex-col">

      {/* Header */}
      <div className="mb-5 flex-shrink-0">
        <div className="inline-flex items-center gap-2 rounded-full bg-[#1f3a36] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#f3e8d3] mb-3">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
          Factory assistant
        </div>
        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">
          Ask Omni
        </h2>

        <p className="text-sm text-[#86612b] mt-2">
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

                <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-[#fff4dc] border border-[#f4d9a8] flex items-center justify-center shadow-sm">
                  <span className="text-xl text-[#a76913]">
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
                  <AgentResponse data={item.data} />
                )}

              </div>

            ))}


            {isAsking && (
              <div>

                <p className="text-xs font-medium text-slate-500 mb-2">
                  Ask Omni
                </p>

                <div className="inline-flex items-center gap-2 bg-[#f7f1e7] text-[#5e4a2e] rounded-xl px-4 py-3 text-sm border border-[#ebdcb4]">

                  <span className="w-2 h-2 rounded-full bg-[#d9a441] animate-pulse"></span>

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
                  className="px-3 py-2 rounded-lg border border-[#eadcc0] bg-[#fffaf2] text-xs text-[#5e4a2e] hover:border-[#d9a441] hover:bg-[#fff3d6] transition"
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
              className="flex-1 px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-800 placeholder-slate-400 outline-none focus:bg-white focus:border-[#b87d39] focus:ring-2 focus:ring-[#d9a441]/20 transition"
            />

            <button
              onClick={handleSend}
              disabled={isAsking || !draft.trim()}
              className="px-5 py-3 rounded-xl bg-[#1f3a36] hover:bg-[#274a44] text-white text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
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

        <div className="bg-[#1f3a36] text-white rounded-2xl rounded-tr-md px-4 py-3 text-sm leading-6 shadow-sm">
          {text}
        </div>

      </div>

    </div>
  )
}


/* ============================================================
   AGENT RESPONSE
============================================================ */

function AgentResponse({ data }) {
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
    <div className="mt-4 rounded-xl border border-[#d9a441]/30 bg-[#fffaf2] p-4">
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


export default OperationsAgent
