import { useState } from 'react'
import FeatureCard from './components/FeatureCard'
import MetricsGrid from './components/MetricsGrid'
import StatusBadge from './components/StatusBadge'
import { capabilities, metrics } from './data/omniData'
import { useSystemTime } from './hooks/useSystemTime'

import {
  fetchSystemHealth,
  askOperationsAgent,
  fetchInventoryStatus,
} from './services/systemApi'


function App() {

  // ----------------------------------------
  // System status
  // ----------------------------------------

  const [status, setStatus] = useState('online')
  const [healthMessage, setHealthMessage] =
    useState('No health checks yet')

  const [isChecking, setIsChecking] =
    useState(false)


  // ----------------------------------------
  // Operations Agent
  // ----------------------------------------

  const [userMessage, setUserMessage] =
    useState('')

  const [agentResponse, setAgentResponse] =
    useState(null)

  const [isAsking, setIsAsking] =
    useState(false)

  const [agentError, setAgentError] =
    useState('')


  // ----------------------------------------
  // Inventory
  // ----------------------------------------

  const [inventoryData, setInventoryData] =
    useState(null)

  const [isLoadingInventory, setIsLoadingInventory] =
    useState(false)


  const systemTime = useSystemTime()


  // ========================================
  // Backend health check
  // ========================================

  async function handleHealthCheck() {

    setIsChecking(true)

    try {

      const health = await fetchSystemHealth()

      setStatus('online')

      setHealthMessage(
        health?.message ?? 'System healthy'
      )

    } catch (error) {

      console.error(error)

      setStatus('degraded')

      setHealthMessage(
        'Health endpoint unavailable'
      )

    } finally {

      setIsChecking(false)

    }
  }


  // ========================================
  // Ask Operations Agent
  // ========================================

  async function handleAskOperations() {

    if (!userMessage.trim()) {
      return
    }

    setIsAsking(true)
    setAgentError('')
    setAgentResponse(null)

    try {

      const result =
        await askOperationsAgent(userMessage)

      setAgentResponse(result)

    } catch (error) {

      console.error(error)

      setAgentError(
        'Unable to communicate with the Operations Agent.'
      )

    } finally {

      setIsAsking(false)

    }
  }


  // ========================================
  // Load Inventory
  // ========================================

  async function handleInventoryStatus() {

    setIsLoadingInventory(true)
    setAgentError('')

    try {

      const result =
        await fetchInventoryStatus()

      setInventoryData(result)

    } catch (error) {

      console.error(error)

      setAgentError(
        'Unable to retrieve inventory information.'
      )

    } finally {

      setIsLoadingInventory(false)

    }
  }


  // ========================================
  // Quick question
  // ========================================

  function askLowStockQuestion() {

    setUserMessage(
      'Which materials are low in stock?'
    )

  }


  return (

    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-6 relative overflow-hidden">

      {/* Background */}

      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-indigo-500/20 rounded-full blur-[100px] animate-pulse"></div>

      <div
        className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-fuchsia-500/20 rounded-full blur-[100px] animate-pulse"
        style={{ animationDelay: '1s' }}
      ></div>


      <main className="glass-panel p-8 md:p-12 max-w-6xl w-full relative z-10">

        {/* =====================================
            HEADER
        ====================================== */}

        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8">

          <StatusBadge status={status} />

          <p className="text-sm text-slate-300">
            Node clock {systemTime}
          </p>

        </div>


        {/* =====================================
            HERO
        ====================================== */}

        <section className="text-center">

          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-tr from-indigo-500 to-fuchsia-500 mb-8 shadow-lg shadow-indigo-500/30">

            <svg
              className="w-10 h-10 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >

              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />

            </svg>

          </div>


          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-200 via-white to-fuchsia-200 mb-6">

            OMNI Intelligence

          </h1>


          <p className="text-lg md:text-xl text-slate-300 leading-relaxed max-w-2xl mx-auto mb-10">

            The Operational Multi-agent Network Intelligence platform is actively orchestrating workflows.

          </p>


          {/* Health button */}

          <button
            onClick={handleHealthCheck}
            disabled={isChecking}
            className="px-8 py-4 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl font-semibold text-white transition-all duration-300 disabled:opacity-60"
          >

            {isChecking
              ? 'Checking Health...'
              : 'Check Backend Health'}

            <span className="inline-block ml-2">
              →
            </span>

          </button>


          <p className="mt-4 text-sm text-slate-300">

            {healthMessage}

          </p>

        </section>


        {/* =====================================
            METRICS
        ====================================== */}

        <section className="mt-10">

          <MetricsGrid metrics={metrics} />

        </section>


        {/* =====================================
            OPERATIONS AGENT
        ====================================== */}

        <section className="mt-10">

          <div className="bg-white/5 border border-white/10 rounded-2xl p-6">

            <div className="flex items-center justify-between mb-5">

              <div>

                <h2 className="text-2xl font-bold text-white">

                  Operations Agent

                </h2>

                <p className="text-sm text-slate-400 mt-1">

                  Ask operational questions and let the Operations Agent route the request.

                </p>

              </div>

              <div className="px-3 py-1 rounded-full bg-green-500/20 text-green-300 text-xs font-semibold">

                ACTIVE

              </div>

            </div>


            {/* Question input */}

            <div className="flex flex-col md:flex-row gap-3">

              <input
                type="text"
                value={userMessage}
                onChange={(event) =>
                  setUserMessage(event.target.value)
                }
                onKeyDown={(event) => {

                  if (event.key === 'Enter') {
                    handleAskOperations()
                  }

                }}
                placeholder="Ask something like: Which materials are low in stock?"
                className="flex-1 px-4 py-3 rounded-xl bg-slate-900/70 border border-white/10 text-white placeholder-slate-500 outline-none focus:border-indigo-400"
              />


              <button
                onClick={handleAskOperations}
                disabled={isAsking || !userMessage.trim()}
                className="px-6 py-3 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
              >

                {isAsking
                  ? 'Processing...'
                  : 'Ask Agent'}

              </button>

            </div>


            {/* Quick question */}

            <button
              onClick={askLowStockQuestion}
              className="mt-3 text-sm text-indigo-300 hover:text-indigo-200"
            >

              Try: "Which materials are low in stock?"

            </button>


            {/* Error */}

            {agentError && (

              <div className="mt-5 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300">

                {agentError}

              </div>

            )}


            {/* Agent response */}

            {agentResponse && (

              <div className="mt-6">

                <div className="mb-4 text-sm text-slate-400">

                  Agent Response

                </div>


                <div className="bg-slate-950/60 border border-indigo-400/20 rounded-xl p-5">

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">

                    <div>

                      <p className="text-xs text-slate-500">
                        Agent
                      </p>

                      <p className="text-white font-semibold">
                        {agentResponse.agent}
                      </p>

                    </div>


                    <div>

                      <p className="text-xs text-slate-500">
                        Task
                      </p>

                      <p className="text-white font-semibold">
                        {agentResponse.task ?? 'N/A'}
                      </p>

                    </div>


                    <div>

                      <p className="text-xs text-slate-500">
                        Delegated To
                      </p>

                      <p className="text-indigo-300 font-semibold">
                        {agentResponse.delegated_to ?? 'N/A'}
                      </p>

                    </div>


                    <div>

                      <p className="text-xs text-slate-500">
                        Status
                      </p>

                      <p className="text-green-300 font-semibold">
                        {agentResponse.status}
                      </p>

                    </div>

                  </div>


                  {/* Low stock count */}

                  {agentResponse.low_stock_count !== undefined && (

                    <div className="mb-5">

                      <p className="text-sm text-slate-400">
                        Low Stock Items
                      </p>

                      <p className="text-4xl font-bold text-white">
                        {agentResponse.low_stock_count}
                      </p>

                    </div>

                  )}


                  {/* Results */}

                  {agentResponse.results?.length > 0 && (

                    <div className="space-y-3">

                      {agentResponse.results.map((item) => (

                        <div
                          key={item.material_code}
                          className="p-4 rounded-xl bg-white/5 border border-white/10"
                        >

                          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">

                            <div>

                              <p className="text-white font-semibold">
                                {item.material_name}
                              </p>

                              <p className="text-xs text-slate-500">
                                {item.material_code}
                              </p>

                            </div>


                            <div className="text-sm">

                              <span className="text-red-300 font-semibold">
                                LOW STOCK
                              </span>

                            </div>

                          </div>


                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 text-sm">

                            <div>

                              <p className="text-slate-500">
                                Current Stock
                              </p>

                              <p className="text-white font-semibold">
                                {item.current_stock} {item.unit}
                              </p>

                            </div>


                            <div>

                              <p className="text-slate-500">
                                Reorder Level
                              </p>

                              <p className="text-white font-semibold">
                                {item.reorder_level} {item.unit}
                              </p>

                            </div>


                            <div>

                              <p className="text-slate-500">
                                Shortage
                              </p>

                              <p className="text-red-300 font-semibold">
                                {item.shortage} {item.unit}
                              </p>

                            </div>


                            <div>

                              <p className="text-slate-500">
                                Recommendation
                              </p>

                              <p className="text-indigo-300 font-semibold">
                                {item.recommendation}
                              </p>

                            </div>

                          </div>

                        </div>

                      ))}

                    </div>

                  )}

                </div>

              </div>

            )}

          </div>

        </section>


        {/* =====================================
            DIRECT INVENTORY STATUS
        ====================================== */}

        <section className="mt-8">

          <div className="bg-white/5 border border-white/10 rounded-2xl p-6">

            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">

              <div>

                <h2 className="text-xl font-bold text-white">

                  Inventory Agent

                </h2>

                <p className="text-sm text-slate-400">

                  Query the inventory database directly.

                </p>

              </div>


              <button
                onClick={handleInventoryStatus}
                disabled={isLoadingInventory}
                className="px-5 py-3 rounded-xl bg-fuchsia-500 hover:bg-fuchsia-400 text-white font-semibold disabled:opacity-50"
              >

                {isLoadingInventory
                  ? 'Loading...'
                  : 'Check Inventory'}

              </button>

            </div>


            {inventoryData && (

              <div className="mt-5">

                <div className="grid grid-cols-2 gap-4 mb-5">

                  <div className="bg-slate-950/50 rounded-xl p-4">

                    <p className="text-xs text-slate-500">
                      Items Checked
                    </p>

                    <p className="text-2xl font-bold text-white">
                      {inventoryData.total_items_checked}
                    </p>

                  </div>


                  <div className="bg-slate-950/50 rounded-xl p-4">

                    <p className="text-xs text-slate-500">
                      Low Stock
                    </p>

                    <p className="text-2xl font-bold text-red-300">
                      {inventoryData.low_stock_count}
                    </p>

                  </div>

                </div>


                <div className="space-y-2">

                  {inventoryData.low_stock_items?.map(
                    (item) => (

                      <div
                        key={item.material_code}
                        className="flex justify-between items-center p-3 rounded-lg bg-red-500/5 border border-red-500/10"
                      >

                        <div>

                          <p className="text-white font-medium">
                            {item.material_name}
                          </p>

                          <p className="text-xs text-slate-500">
                            {item.material_code}
                          </p>

                        </div>


                        <p className="text-red-300 text-sm">
                          {item.shortage} {item.unit} shortage
                        </p>

                      </div>

                    )
                  )}

                </div>

              </div>

            )}

          </div>

        </section>


        {/* =====================================
            CAPABILITIES
        ====================================== */}

        <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">

          {capabilities.map((capability) => (

            <FeatureCard
              key={capability.title}
              title={capability.title}
              description={capability.description}
            />

          ))}

        </section>

      </main>

    </div>

  )

}

export default App