import { useState } from 'react'
import FeatureCard from './components/FeatureCard'
import MetricsGrid from './components/MetricsGrid'
import StatusBadge from './components/StatusBadge'
import { capabilities, metrics } from './data/omniData'
import { useSystemTime } from './hooks/useSystemTime'

const API_BASE_URL = 'http://127.0.0.1:8000'

function App() {
  const [status, setStatus] = useState('online')
  const [healthMessage, setHealthMessage] = useState('No health checks yet')
  const [isChecking, setIsChecking] = useState(false)

  const [message, setMessage] = useState('')
  const [agentResponse, setAgentResponse] = useState(null)
  const [isAsking, setIsAsking] = useState(false)
  const [error, setError] = useState('')

  const systemTime = useSystemTime()

  // ----------------------------------------
  // Backend health check
  // ----------------------------------------

  async function handleHealthCheck() {
    setIsChecking(true)

    try {
      const response = await fetch(`${API_BASE_URL}/`)

      if (!response.ok) {
        throw new Error('Backend unavailable')
      }

      const health = await response.json()

      setStatus('online')
      setHealthMessage(health?.message ?? 'System healthy')
    } catch (error) {
      console.error(error)
      setStatus('degraded')
      setHealthMessage('Health endpoint unavailable')
    } finally {
      setIsChecking(false)
    }
  }

  // ----------------------------------------
  // Ask Operations Agent
  // ----------------------------------------

  async function handleAskAgent() {
    if (!message.trim()) {
      return
    }

    setIsAsking(true)
    setError('')
    setAgentResponse(null)

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
        }),
      })

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`)
      }

      const data = await response.json()

      setAgentResponse(data)
    } catch (error) {
      console.error(error)
      setError(
        'Could not connect to the Operations Agent. Make sure the backend is running.'
      )
    } finally {
      setIsAsking(false)
    }
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

        {/* ---------------------------------------- */}
        {/* Header */}
        {/* ---------------------------------------- */}

        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8">
          <StatusBadge status={status} />

          <p className="text-sm text-slate-300">
            Node clock {systemTime}
          </p>
        </div>

        {/* ---------------------------------------- */}
        {/* Hero */}
        {/* ---------------------------------------- */}

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
            The Operational Multi-agent Network Intelligence platform is actively
            orchestrating workflows. Connect your agents to begin.
          </p>

          {/* Health Button */}

          <button
            onClick={handleHealthCheck}
            disabled={isChecking}
            className="px-8 py-4 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl font-semibold text-white transition-all duration-300 disabled:opacity-60"
          >
            {isChecking ? 'Checking Health...' : 'Check Backend Health'}

            <span className="inline-block ml-2">
              →
            </span>
          </button>

          <p className="mt-4 text-sm text-slate-300">
            {healthMessage}
          </p>

        </section>

        {/* ---------------------------------------- */}
        {/* Metrics */}
        {/* ---------------------------------------- */}

        <section className="mt-10">
          <MetricsGrid metrics={metrics} />
        </section>

        {/* ---------------------------------------- */}
        {/* Operations Agent */}
        {/* ---------------------------------------- */}

        <section className="mt-10">

          <div className="mb-5">

            <h2 className="text-2xl font-bold text-white">
              Operations Agent
            </h2>

            <p className="text-slate-400 mt-1">
              Ask the Operations Agent about inventory and operational status.
            </p>

          </div>

          {/* Input */}

          <div className="flex flex-col md:flex-row gap-3">

            <input
              type="text"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  handleAskAgent()
                }
              }}
              placeholder="Example: How much Black Cotton Fabric do we have?"
              className="flex-1 px-5 py-4 rounded-xl bg-slate-950/70 border border-white/10 text-white placeholder-slate-500 outline-none focus:border-indigo-400"
            />

            <button
              onClick={handleAskAgent}
              disabled={isAsking || !message.trim()}
              className="px-7 py-4 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAsking ? 'Asking...' : 'Ask Agent'}
            </button>

          </div>

          {/* Suggested questions */}

          <div className="flex flex-wrap gap-2 mt-4">

            {[
              'Which materials are low in stock?',
              'How much Black Cotton Fabric do we have?',
              'What is the weather today?',
            ].map((question) => (

              <button
                key={question}
                onClick={() => setMessage(question)}
                className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-slate-300 hover:bg-white/10 transition"
              >
                {question}
              </button>

            ))}

          </div>

          {/* Error */}

          {error && (
            <div className="mt-5 p-4 rounded-xl bg-red-500/10 border border-red-400/20 text-red-300">
              {error}
            </div>
          )}

          {/* ---------------------------------------- */}
          {/* Agent Response */}
          {/* ---------------------------------------- */}

          {agentResponse && (

            <div className="mt-6 p-6 rounded-2xl bg-slate-950/70 border border-white/10">

              <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-6">

                <div>
                  <p className="text-sm text-slate-500">
                    Agent
                  </p>

                  <p className="text-white font-semibold">
                    {agentResponse.agent}
                  </p>
                </div>

                <div>
                  <p className="text-sm text-slate-500">
                    Intent
                  </p>

                  <p className="text-indigo-300 font-semibold">
                    {agentResponse.intent || 'N/A'}
                  </p>
                </div>

                <div>
                  <p className="text-sm text-slate-500">
                    Delegated To
                  </p>

                  <p className="text-indigo-300 font-semibold">
                    {agentResponse.delegated_to || 'None'}
                  </p>
                </div>

                <div>
                  <p className="text-sm text-slate-500">
                    Status
                  </p>

                  <p className="text-green-400 font-semibold">
                    {agentResponse.status}
                  </p>
                </div>

              </div>

              {/* Answer */}

              {agentResponse.answer && (

                <div className="mb-6">

                  <p className="text-sm text-slate-500 mb-2">
                    Agent Answer
                  </p>

                  <p className="text-xl text-white">
                    {agentResponse.answer}
                  </p>

                </div>

              )}

              {/* Inventory result */}

              {agentResponse.result && (

                <div className="p-5 rounded-xl bg-white/5 border border-white/10">

                  <h3 className="text-lg font-semibold text-white mb-4">
                    Inventory Details
                  </h3>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

                    <div>
                      <p className="text-sm text-slate-500">
                        Material
                      </p>

                      <p className="text-white font-medium">
                        {agentResponse.result.material_name}
                      </p>
                    </div>

                    <div>
                      <p className="text-sm text-slate-500">
                        Current Stock
                      </p>

                      <p className="text-white font-medium">
                        {agentResponse.result.current_stock}{' '}
                        {agentResponse.result.unit}
                      </p>
                    </div>

                    <div>
                      <p className="text-sm text-slate-500">
                        Reorder Level
                      </p>

                      <p className="text-white font-medium">
                        {agentResponse.result.reorder_level}{' '}
                        {agentResponse.result.unit}
                      </p>
                    </div>

                    <div>
                      <p className="text-sm text-slate-500">
                        Shortage
                      </p>

                      <p className="text-red-400 font-medium">
                        {agentResponse.result.shortage}{' '}
                        {agentResponse.result.unit}
                      </p>
                    </div>

                  </div>

                  <div className="mt-4">

                    <p className="text-sm text-slate-500">
                      Recommendation
                    </p>

                    <p className="text-indigo-300 font-medium">
                      {agentResponse.result.recommendation}
                    </p>

                  </div>

                </div>

              )}

              {/* Low stock results */}

              {agentResponse.results &&
                agentResponse.results.length > 0 && (

                  <div className="space-y-3">

                    <h3 className="text-lg font-semibold text-white">
                      Low Stock Materials
                    </h3>

                    {agentResponse.results.map((item) => (

                      <div
                        key={item.material_code}
                        className="p-4 rounded-xl bg-white/5 border border-white/10"
                      >

                        <div className="flex justify-between">

                          <div>

                            <p className="text-white font-semibold">
                              {item.material_name}
                            </p>

                            <p className="text-sm text-slate-500">
                              {item.material_code}
                            </p>

                          </div>

                          <span className="text-red-400 font-semibold">
                            LOW STOCK
                          </span>

                        </div>

                        <div className="grid grid-cols-3 gap-4 mt-4 text-sm">

                          <div>
                            <p className="text-slate-500">
                              Current Stock
                            </p>

                            <p className="text-white">
                              {item.current_stock} {item.unit}
                            </p>
                          </div>

                          <div>
                            <p className="text-slate-500">
                              Reorder Level
                            </p>

                            <p className="text-white">
                              {item.reorder_level} {item.unit}
                            </p>
                          </div>

                          <div>
                            <p className="text-slate-500">
                              Shortage
                            </p>

                            <p className="text-red-400">
                              {item.shortage} {item.unit}
                            </p>
                          </div>

                        </div>

                      </div>

                    ))}

                  </div>

                )}

            </div>

          )}

        </section>

        {/* ---------------------------------------- */}
        {/* Existing capabilities */}
        {/* ---------------------------------------- */}

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