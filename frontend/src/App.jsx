import { useEffect, useState } from 'react'

import InventoryPage from './components/InventoryPage'
import OperationsAgent from './components/OperationsAgent'
import DemandForecastPage from './components/DemandForecastPage'


// ============================================================
// API
// ============================================================

const API_BASE_URL = 'http://127.0.0.1:8000'


// ============================================================
// SIDEBAR
// ============================================================

function Sidebar({ activePage, setActivePage }) {

  const navigation = [
    {
      section: 'OVERVIEW',
      items: [
        {
          id: 'dashboard',
          label: 'Dashboard',
          icon: '▦',
        },
      ],
    },

    {
      section: 'AGENTS',
      items: [
        {
          id: 'operations',
          label: 'Ask Omni',
          icon: '◯',
        },
        {
          id: 'inventory',
          label: 'Fabric stock',
          icon: '◇',
        },
        {
          id: 'forecast',
          label: 'Demand forecast',
          icon: '⌁',
        },
        {
          id: 'supplier',
          label: 'Supplier intel',
          icon: '▱',
        },
        {
          id: 'production',
          label: 'Line planning',
          icon: '⚙',
        },
        {
          id: 'reports',
          label: 'Factory reports',
          icon: '▤',
        },
      ],
    },
  ]


  return (

    <aside
      className="
        w-[220px]
        h-screen
        bg-[#1a2430]
        text-white
        flex
        flex-col
        flex-shrink-0
        overflow-hidden
        shadow-[inset_-1px_0_0_rgba(255,255,255,0.08)]
      "
    >

      {/* ================================================== */}
      {/* BRAND */}
      {/* ================================================== */}

      <div
        className="
          h-[60px]
          px-5
          flex
          items-center
          gap-3
          border-b
          border-white/10
        "
      >

        <div
          className="
            w-8
            h-8
            rounded-lg
            bg-gradient-to-br from-[#d9a441] via-[#b87d39] to-[#7d5d2f]
            flex
            items-center
            justify-center
            text-sm
            font-bold
            text-[#fffaf1]
            shadow-md
          "
        >
          O
        </div>

        <span
          className="
            text-sm
            font-semibold
            tracking-wide
          "
        >
          OMNI management
        </span>

      </div>


      {/* ================================================== */}
      {/* NAVIGATION */}
      {/* ================================================== */}

      <nav className="flex-1 px-2 py-4 overflow-hidden">

        {navigation.map((group) => (

          <div
            key={group.section}
            className="mb-5"
          >

            <p
              className="
                px-2
                mb-2
                text-[10px]
                uppercase
                tracking-wider
                text-white/30
              "
            >
              {group.section}
            </p>


            {group.items.map((item) => (

              <button
                key={item.id}
                onClick={() => setActivePage(item.id)}
                className={`
                  w-full
                  flex
                  items-center
                  gap-3
                  px-3
                  py-2.5
                  mb-1
                  rounded-lg
                  text-left
                  text-sm
                  transition
                  ${
                    activePage === item.id
                      ? 'bg-[#d9a441]/15 text-[#f8f0df] border border-[#d9a441]/30'
                      : 'text-white/65 hover:bg-white/5 hover:text-white'
                  }
                `}
              >

                <span
                  className="
                    w-4
                    text-center
                    text-sm
                  "
                >
                  {item.icon}
                </span>

                <span>
                  {item.label}
                </span>

              </button>

            ))}

          </div>

        ))}

      </nav>


      {/* ================================================== */}
      {/* FOOTER */}
      {/* ================================================== */}

      <div
        className="
          px-4
          py-4
          border-t
          border-white/10
          text-xs
          text-white/60
        "
      >

        <span
          className="
            inline-block
            w-2
            h-2
            rounded-full
            bg-emerald-400
            mr-2
          "
        />

        All 6 agents synced

      </div>

    </aside>
  )
}


// ============================================================
// DASHBOARD PAGE
// ============================================================

function DashboardPage({ setActivePage }) {

  const [health, setHealth] = useState(null)

  async function checkHealth() {

    try {

      const response = await fetch(
        `${API_BASE_URL}/health`
      )

      const data = await response.json()

      setHealth(data)

    } catch {

      setHealth({
        status: 'offline',
        message: 'Backend unavailable',
      })

    }
  }


  useEffect(() => {

    checkHealth()

  }, [])


  return (

    <div className="p-8">

      {/* ================================================== */}
      {/* HEADER */}
      {/* ================================================== */}

      <div
        className="
          flex
          items-start
          justify-between
          mb-6
        "
      >

        <div>

          <div className="flex items-center gap-2 mb-3">
            <span className="inline-flex items-center gap-2 rounded-full bg-[#1f3a36] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#f3e8d3]">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
              Factory live
            </span>
          </div>

          <h1
            className="
              text-3xl
              font-semibold
              text-slate-900
              tracking-tight
            "
          >
            Garment operations overview
          </h1>

          <p
            className="
              text-sm
              text-[#86612b]
              mt-2
            "
          >
            Factory intelligence across fabric, production, and delivery · updated just now
          </p>

        </div>


        <button
          onClick={checkHealth}
          className="
            px-4
            py-2.5
            rounded-xl
            bg-white
            border
            border-slate-200
            text-sm
            text-slate-700
            shadow-sm
            hover:bg-slate-50
            transition
          "
        >
          ↻ Refresh
        </button>

      </div>

      <div className="mb-6 rounded-2xl border border-[#e7dcc7] bg-gradient-to-r from-[#1f3a36] via-[#2d4a46] to-[#2e3d4f] p-5 text-white shadow-[0_18px_40px_rgba(31,58,54,0.18)]">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-[#d7c9ae]">Production pulse</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Weekly output on target</h2>
          </div>

          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-white/10 px-3 py-2 text-right">
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#d7c9ae]">Plan vs actual</div>
              <div className="mt-1 text-lg font-semibold">98.2%</div>
            </div>
            <div className="rounded-xl bg-emerald-500/20 px-3 py-2 text-right border border-emerald-300/20">
              <div className="text-[10px] uppercase tracking-[0.2em] text-emerald-100">Efficiency</div>
              <div className="mt-1 text-lg font-semibold">+4.6%</div>
            </div>
          </div>
        </div>
      </div>


      {/* ================================================== */}
      {/* METRICS */}
      {/* ================================================== */}

      <div
        className="
          grid
          grid-cols-1
          md:grid-cols-2
          xl:grid-cols-4
          gap-4
          mb-6
        "
      >

        <MetricCard
          title="Fabric SKUs tracked"
          value="184"
          subtitle="Material master"
          accent="amber"
        />

        <MetricCard
          title="Cutting yield"
          value="96.4%"
          subtitle="Current production run"
          accent="green"
        />

        <MetricCard
          title="Open POs"
          value="27"
          subtitle="Supplier pipeline"
          accent="slate"
        />

        <MetricCard
          title="Line adherence"
          value="94.8%"
          subtitle="Production schedule"
          accent="indigo"
        />

      </div>


      {/* ================================================== */}
      {/* CHART + LINE PERFORMANCE */}
      {/* ================================================== */}

      <div className="grid grid-cols-1 xl:grid-cols-[1.7fr_1fr] gap-4 mb-4">

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-[0_10px_25px_rgba(15,23,42,0.03)]">
          <div className="flex items-center justify-between mb-5">
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Output trend</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-900">Weekly production volume</h2>
            </div>
            <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-medium text-emerald-600">+12.5%</span>
          </div>

          <div className="h-44 flex items-end gap-3 px-2 pb-2">
            {[48, 62, 58, 74, 80, 92, 88].map((value, index) => (
              <div key={index} className="flex-1 flex flex-col items-center justify-end gap-2">
                <div
                  className="w-full rounded-t-xl bg-gradient-to-t from-[#1f3a36] via-[#2d4a46] to-[#d9a441]"
                  style={{ height: `${value}%` }}
                />
                <span className="text-[10px] text-slate-400">{['M','T','W','T','F','S','S'][index]}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-[0_10px_25px_rgba(15,23,42,0.03)]">
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Production by line</p>
          <h2 className="mt-2 text-lg font-semibold text-slate-900 mb-4">Line performance</h2>

          <div className="space-y-4">
            <LinePerformance label="Line 1 - Knits" value={92} color="bg-[#1f3a36]" />
            <LinePerformance label="Line 2 - Sewing" value={86} color="bg-[#d9a441]" />
            <LinePerformance label="Line 3 - Finishing" value={78} color="bg-[#475569]" />
            <LinePerformance label="Line 4 - QC" value={96} color="bg-[#2e7d6b]" />
          </div>
        </div>

      </div>


      {/* ================================================== */}
      {/* TWO COLUMN AREA */}
      {/* ================================================== */}

      <div
        className="
          grid
          grid-cols-1
          xl:grid-cols-2
          gap-4
        "
      >

        {/* LIVE ALERT FEED */}

        <div
          className="
            bg-white
            border
            border-slate-200
            rounded-xl
            p-5
          "
        >

          <h2
            className="
              text-xs
              uppercase
              tracking-wide
              text-indigo-500
              font-medium
              mb-4
            "
          >
            Live alert feed
          </h2>


          <div className="space-y-0">

            <AlertRow
              title="Fabric stock sync complete"
              subtitle="Fabric inventory agent"
              status="Online"
              statusType="success"
            />

            <AlertRow
              title="Demand forecast recalculated"
              subtitle="Merchandising agent"
              status="Updated"
              statusType="info"
            />

            <AlertRow
              title="Supplier lead times monitored"
              subtitle="Procurement agent"
              status="Stable"
              statusType="info"
            />

            <AlertRow
              title="Line efficiency risk flagged"
              subtitle="Production planning agent"
              status="Watch"
              statusType="warning"
            />

          </div>

        </div>


        {/* AGENT HEALTH */}

        <div
          className="
            bg-white
            border
            border-slate-200
            rounded-xl
            p-5
          "
        >

          <h2
            className="
              text-xs
              uppercase
              tracking-wide
              text-indigo-500
              font-medium
              mb-4
            "
          >
            Agent health
          </h2>


          <AgentHealth
            name="Fabric inventory agent"
            status="Online"
            statusType="success"
          />

          <AgentHealth
            name="Demand forecast agent"
            status="Updated"
            statusType="info"
          />

          <AgentHealth
            name="Supplier intelligence agent"
            status="Stable"
            statusType="info"
          />

          <AgentHealth
            name="Line planning agent"
            status="Watching"
            statusType="warning"
          />

          <AgentHealth
            name="Ask Omni"
            status="Online"
            statusType="success"
          />

          <AgentHealth
            name="Factory report agent"
            status="Ready"
            statusType="info"
          />

        </div>

      </div>

      <div className="mt-4 bg-white border border-slate-200 rounded-2xl p-5 shadow-[0_10px_25px_rgba(15,23,42,0.03)]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Backlog</p>
            <h2 className="mt-2 text-lg font-semibold text-slate-900">Reorder queue</h2>
          </div>
          <button className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100">
            View all
          </button>
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-600">Material</th>
                <th className="px-4 py-3 font-medium text-slate-600">Vendor</th>
                <th className="px-4 py-3 font-medium text-slate-600">Qty</th>
                <th className="px-4 py-3 font-medium text-slate-600">ETA</th>
                <th className="px-4 py-3 font-medium text-slate-600">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              <tr>
                <td className="px-4 py-3 text-slate-800">Black Cotton Fabric</td>
                <td className="px-4 py-3 text-slate-600">Textile Hub</td>
                <td className="px-4 py-3 text-slate-800">4,000 m</td>
                <td className="px-4 py-3 text-slate-600">2 days</td>
                <td className="px-4 py-3"><span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-medium text-amber-700">In transit</span></td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-slate-800">Oxford Twill</td>
                <td className="px-4 py-3 text-slate-600">Prime Weave</td>
                <td className="px-4 py-3 text-slate-800">1,800 m</td>
                <td className="px-4 py-3 text-slate-600">5 days</td>
                <td className="px-4 py-3"><span className="rounded-full bg-sky-50 px-2 py-1 text-[10px] font-medium text-sky-700">Queued</span></td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-slate-800">Elastic Rib</td>
                <td className="px-4 py-3 text-slate-600">North Stitch</td>
                <td className="px-4 py-3 text-slate-800">900 kg</td>
                <td className="px-4 py-3 text-slate-600">1 day</td>
                <td className="px-4 py-3"><span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-medium text-emerald-700">Ready</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>


      {/* ================================================== */}
      {/* QUICK ACTIONS */}
      {/* ================================================== */}

      <div className="mt-6 flex gap-3">

        <button
          onClick={() => setActivePage('inventory')}
          className="
            px-4
            py-2
            rounded-lg
            bg-[#1f3a36]
            text-white
            text-sm
            hover:bg-[#274a44]
          "
        >
          Open Fabric Stock
        </button>

        <button
          onClick={() => setActivePage('operations')}
          className="
            px-4
            py-2
            rounded-lg
            bg-white
            border
            border-stone-200
            text-slate-700
            text-sm
            hover:bg-[#f8f3ed]
          "
        >
          Ask Omni
        </button>

      </div>


      {/* BACKEND STATUS */}

      {health && (

        <div
          className="
            mt-4
            text-xs
            text-slate-400
          "
        >
          Backend: {health.status}
        </div>

      )}

    </div>
  )
}


// ============================================================
// METRIC CARD
// ============================================================

function MetricCard({
  title,
  value,
  subtitle,
  accent = 'amber',
}) {

  const accentStyles = {
    amber: 'bg-[#fff7ea] text-[#a76913] border-[#f4d9a8]',
    green: 'bg-[#edfaf4] text-[#1d6a4a] border-[#bfe5cf]',
    slate: 'bg-[#f3f4f6] text-[#425466] border-[#dfe3ea]',
    indigo: 'bg-[#eef2ff] text-[#3f51b5] border-[#cdd7ff]',
  }

  return (

    <div
      className="
        bg-white
        border
        border-slate-200
        rounded-2xl
        p-5
        shadow-[0_10px_25px_rgba(15,23,42,0.03)]
        transition
        hover:-translate-y-0.5
        hover:shadow-[0_14px_28px_rgba(15,23,42,0.06)]
      "
    >

      <div className={`inline-flex rounded-lg border px-2 py-1 text-[10px] font-medium uppercase tracking-[0.16em] ${accentStyles[accent]}`}>
        {title}
      </div>

      <p
        className="
          text-3xl
          font-semibold
          text-slate-900
          mt-4
          tracking-tight
        "
      >
        {value}
      </p>

      <p
        className="
          text-xs
          text-slate-500
          mt-2
        "
      >
        {subtitle}
      </p>

    </div>
  )
}


// ============================================================
// ALERT ROW
// ============================================================

function AlertRow({
  title,
  subtitle,
  status,
  statusType,
}) {

  const styles = {

    success:
      'bg-emerald-50 text-emerald-600',

    warning:
      'bg-amber-50 text-amber-600',

    info:
      'bg-indigo-50 text-indigo-500',

  }

  return (

    <div
      className="
        flex
        items-center
        justify-between
        py-3
        border-t
        border-slate-100
      "
    >

      <div>

        <p className="text-sm text-slate-900">
          {title}
        </p>

        <p className="text-xs text-slate-400 mt-1">
          {subtitle}
        </p>

      </div>


      <span
        className={`
          px-3
          py-1
          rounded-full
          text-xs
          font-medium
          ${styles[statusType]}
        `}
      >
        {status}
      </span>

    </div>
  )
}


// ============================================================
// AGENT HEALTH
// ============================================================

function AgentHealth({
  name,
  status,
  statusType,
}) {

  const styles = {

    success:
      'bg-emerald-50 text-emerald-600',

    warning:
      'bg-amber-50 text-amber-600',

    info:
      'bg-indigo-50 text-indigo-500',

  }

  return (

    <div
      className="
        flex
        items-center
        justify-between
        py-3
        border-t
        border-slate-100
      "
    >

      <span
        className="
          text-sm
          text-slate-900
        "
      >
        {name}
      </span>

      <span
        className={`
          px-3
          py-1
          rounded-full
          text-xs
          font-medium
          ${styles[statusType]}
        `}
      >
        {status}
      </span>

    </div>
  )
}

function LinePerformance({ label, value, color }) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}


// ============================================================
// PLACEHOLDER PAGE
// ============================================================

function PlaceholderPage({ title }) {

  return (

    <div className="p-8">

      <h1
        className="
          text-2xl
          font-semibold
          text-slate-900
        "
      >
        {title}
      </h1>

      <p
        className="
          text-sm
          text-slate-500
          mt-2
        "
      >
        This agent is currently being developed by another team member.
      </p>


      <div
        className="
          mt-8
          bg-white
          border
          border-slate-200
          rounded-xl
          p-8
        "
      >

        <p className="text-slate-400 text-sm">
          Integration pending.
        </p>

      </div>

    </div>
  )
}


// ============================================================
// MAIN APP
// ============================================================

function App() {

  const [activePage, setActivePage] = useState(
    'dashboard'
  )

  const [chatState, setChatState] = useState({
    draft: '',
    messages: [],
    isAsking: false,
    error: '',
  })


  function renderPage() {

    switch (activePage) {

      case 'dashboard':

        return (
          <DashboardPage
            setActivePage={setActivePage}
          />
        )


      case 'inventory':

        return (
          <InventoryPage />
        )


      case 'operations':

        return (
          <OperationsAgent
            chatState={chatState}
            setChatState={setChatState}
          />
        )


      case 'forecast':

        return (
          <DemandForecastPage setActivePage={setActivePage} />
        )


      case 'supplier':

        return (
          <PlaceholderPage
            title="Supplier intelligence agent"
          />
        )


      case 'production':

        return (
          <PlaceholderPage
            title="Production scheduling agent"
          />
        )


      case 'reports':

        return (
          <PlaceholderPage
            title="Reports"
          />
        )


      default:

        return (
          <DashboardPage
            setActivePage={setActivePage}
          />
        )
    }
  }


  return (

    <div
      className="
        h-screen
        flex
        bg-[#f5f1ea]
        overflow-hidden
      "
    >

      <Sidebar
        activePage={activePage}
        setActivePage={setActivePage}
      />


      <main
        className="
          flex-1
          min-w-0
          h-screen
          overflow-y-auto
        "
      >

        {renderPage()}

      </main>

    </div>
  )
}


export default App
