import { useState } from 'react'
import FeatureCard from './components/FeatureCard'
import MetricsGrid from './components/MetricsGrid'
import StatusBadge from './components/StatusBadge'
import { capabilities, metrics } from './data/omniData'
import { useSystemTime } from './hooks/useSystemTime'
import { fetchSystemHealth } from './services/systemApi'

function App() {
  const [status, setStatus] = useState('online')
  const [healthMessage, setHealthMessage] = useState('No health checks yet')
  const [isChecking, setIsChecking] = useState(false)
  const systemTime = useSystemTime()

  async function handleHealthCheck() {
    setIsChecking(true)
    try {
      const health = await fetchSystemHealth()
      setStatus('online')
      setHealthMessage(health?.message ?? 'System healthy')
    } catch {
      setStatus('degraded')
      setHealthMessage('Health endpoint unavailable')
    } finally {
      setIsChecking(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-6 relative overflow-hidden">
      
      {/* Dynamic Background Elements */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-indigo-500/20 rounded-full blur-[100px] animate-pulse"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-fuchsia-500/20 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: '1s' }}></div>

      <main className="glass-panel p-8 md:p-12 max-w-5xl w-full relative z-10 transition-all duration-500 hover:shadow-indigo-500/10 hover:-translate-y-1">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8">
          <StatusBadge status={status} />
          <p className="text-sm text-slate-300">Node clock {systemTime}</p>
        </div>

        <section className="text-center">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-tr from-indigo-500 to-fuchsia-500 mb-8 shadow-lg shadow-indigo-500/30">
          <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-200 via-white to-fuchsia-200 mb-6">
          OMNI Intelligence
        </h1>
        
        <p className="text-lg md:text-xl text-slate-300 leading-relaxed max-w-2xl mx-auto mb-10">
          The Operational Multi-agent Network Intelligence platform is actively orchestrating workflows. Connect your agents to begin.
        </p>

        <button
          onClick={handleHealthCheck}
          disabled={isChecking}
          className="px-8 py-4 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl font-semibold text-white transition-all duration-300 hover:shadow-lg hover:shadow-white/10 active:scale-95 group disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isChecking ? 'Checking Health...' : 'Check Backend Health'}
          <span className="inline-block ml-2 transition-transform duration-300 group-hover:translate-x-1">→</span>
        </button>

        <p className="mt-4 text-sm text-slate-300">{healthMessage}</p>
        </section>

        <section className="mt-10">
          <MetricsGrid metrics={metrics} />
        </section>

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
