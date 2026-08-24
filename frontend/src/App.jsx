import { useState } from 'react'

import FeatureCard from './components/FeatureCard'
import MetricsGrid from './components/MetricsGrid'
import StatusBadge from './components/StatusBadge'
import OperationsAgent from './components/OperationsAgent'

import { capabilities, metrics } from './data/omniData'
import { useSystemTime } from './hooks/useSystemTime'


// ============================================================
// API CONFIGURATION
// ============================================================

const API_BASE_URL = 'http://127.0.0.1:8000'


// ============================================================
// APP
// ============================================================

function App() {

  const [status, setStatus] = useState('online')
  const [healthMessage, setHealthMessage] = useState(
    'No health checks yet'
  )
  const [isChecking, setIsChecking] = useState(false)

  const systemTime = useSystemTime()


  // ==========================================================
  // BACKEND HEALTH CHECK
  // ==========================================================

  async function handleHealthCheck() {

    setIsChecking(true)

    try {

      const response = await fetch(
        `${API_BASE_URL}/`
      )

      if (!response.ok) {
        throw new Error('Backend unavailable')
      }

      const health = await response.json()

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


  // ==========================================================
  // UI
  // ==========================================================

  return (

    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-6 relative overflow-hidden">


      {/* ======================================================
          BACKGROUND EFFECTS
      ====================================================== */}

      <div
        className="
          absolute
          top-[-10%]
          left-[-10%]
          w-96
          h-96
          bg-indigo-500/20
          rounded-full
          blur-[100px]
          animate-pulse
        "
      />

      <div
        className="
          absolute
          bottom-[-10%]
          right-[-10%]
          w-96
          h-96
          bg-fuchsia-500/20
          rounded-full
          blur-[100px]
          animate-pulse
        "
        style={{
          animationDelay: '1s'
        }}
      />


      {/* ======================================================
          MAIN CONTAINER
      ====================================================== */}

      <main
        className="
          glass-panel
          p-8
          md:p-12
          max-w-6xl
          w-full
          relative
          z-10
        "
      >


        {/* ====================================================
            HEADER
        ==================================================== */}

        <div
          className="
            flex
            flex-col
            gap-4
            md:flex-row
            md:items-center
            md:justify-between
            mb-8
          "
        >

          <StatusBadge status={status} />

          <p className="text-sm text-slate-300">
            Node clock {systemTime}
          </p>

        </div>


        {/* ====================================================
            HERO SECTION
        ==================================================== */}

        <section className="text-center">

          {/* OMNI ICON */}

          <div
            className="
              inline-flex
              items-center
              justify-center
              w-20
              h-20
              rounded-full
              bg-gradient-to-tr
              from-indigo-500
              to-fuchsia-500
              mb-8
              shadow-lg
              shadow-indigo-500/30
            "
          >

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


          {/* TITLE */}

          <h1
            className="
              text-5xl
              md:text-6xl
              font-extrabold
              tracking-tight
              text-transparent
              bg-clip-text
              bg-gradient-to-r
              from-indigo-200
              via-white
              to-fuchsia-200
              mb-6
            "
          >
            OMNI Intelligence
          </h1>


          {/* DESCRIPTION */}

          <p
            className="
              text-lg
              md:text-xl
              text-slate-300
              leading-relaxed
              max-w-2xl
              mx-auto
              mb-10
            "
          >
            The Operational Multi-agent Network Intelligence
            platform is actively orchestrating workflows.
            Connect your agents to begin.
          </p>


          {/* HEALTH BUTTON */}

          <button
            onClick={handleHealthCheck}
            disabled={isChecking}
            className="
              px-8
              py-4
              bg-white/10
              hover:bg-white/20
              border
              border-white/20
              rounded-xl
              font-semibold
              text-white
              transition-all
              duration-300
              disabled:opacity-60
              disabled:cursor-not-allowed
            "
          >

            {isChecking
              ? 'Checking Health...'
              : 'Check Backend Health'
            }

            <span className="inline-block ml-2">
              →
            </span>

          </button>


          {/* HEALTH MESSAGE */}

          <p className="mt-4 text-sm text-slate-300">
            {healthMessage}
          </p>

        </section>


        {/* ====================================================
            METRICS
        ==================================================== */}

        <section className="mt-10">

          <MetricsGrid metrics={metrics} />

        </section>


        {/* ====================================================
            OPERATIONS AGENT
        ==================================================== */}

        <section className="mt-10">

          <OperationsAgent />

        </section>


        {/* ====================================================
            SYSTEM CAPABILITIES
        ==================================================== */}

        <section
          className="
            mt-8
            grid
            gap-4
            sm:grid-cols-2
            lg:grid-cols-3
          "
        >

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