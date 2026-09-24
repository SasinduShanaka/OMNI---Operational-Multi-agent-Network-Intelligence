import { useEffect, useState } from 'react'

import InventoryPage from './components/InventoryPage'
import OperationsAgent from './components/OperationsAgent'
import SupplyChainPanel from './components/SupplyChainPanel'
import DemandForecastPage from './components/DemandForecastPage'
import ProductionPage from './components/ProductionPage'
import ReportsPage from './components/ReportsPage'
import AuthPage from './components/AuthPage'
import { FloatCard, SceneStage } from './components/FactoryScene'
import OmniMark from './components/OmniMark'
import { authApi } from './api/authApi'
import { apiFetch, API_BASE_URL } from './api/http'


// ============================================================
// API
// ============================================================



// ============================================================
// TOP NAVIGATION
// ============================================================

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: '▦' },
  { id: 'inventory', label: 'Fabric stock', icon: '◇' },
  { id: 'forecast', label: 'Demand forecast', icon: '⌁' },
  { id: 'supplier', label: 'Supplier intel', icon: '▱' },
  { id: 'production', label: 'Line planning', icon: '⚙' },
  { id: 'reports', label: 'Factory reports', icon: '▤' },
]


function TopNav({ activePage, setActivePage, user, onLogout }) {

  return (

    <header
      className="
        sticky
        top-0
        z-30
        flex-shrink-0
        border-b
        border-slate-200
        bg-white/85
        backdrop-blur-xl
      "
    >

      <div className="flex h-16 items-center gap-6 px-6">

        {/* ============================================== */}
        {/* BRAND */}
        {/* ============================================== */}

        <div className="flex items-center gap-3 flex-shrink-0">

          <div
            className="
              flex
              h-9
              w-9
              items-center
              justify-center
              rounded-xl
              bg-gradient-to-br from-[#3b82f6] via-[#2563eb] to-[#1e40af]
              text-sm
              font-bold
              text-white
              shadow-[0_6px_16px_rgba(37,99,235,0.35)]
            "
          >
            O
          </div>

          <span className="text-sm font-semibold tracking-tight text-slate-900">
            OMNI management
          </span>

        </div>


        {/* ============================================== */}
        {/* NAVIGATION PILLS */}
        {/* ============================================== */}

        {/* ============================================== */}
        {/* ASK OMNI — the way into every agent, so it is    */}
        {/* not one pill among seven                         */}
        {/* ============================================== */}

        <button
          onClick={() => setActivePage('operations')}
          aria-current={activePage === 'operations' ? 'page' : undefined}
          className={`
            group
            flex
            flex-shrink-0
            items-center
            gap-2
            rounded-xl
            py-1.5
            pl-1.5
            pr-3.5
            text-sm
            font-medium
            transition
            ${
              activePage === 'operations'
                ? 'bg-gradient-to-r from-[#2563eb] to-[#1e40af] text-white shadow-[0_8px_20px_-6px_rgba(29,78,216,0.85)]'
                : 'bg-[#eff6ff] text-[#1d4ed8] ring-1 ring-inset ring-[#bfdbfe] hover:bg-[#dbeafe]'
            }
          `}
        >

          <span className="relative flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-white shadow-[0_2px_6px_-2px_rgba(15,23,42,0.35)]">
            <OmniMark size={20} />
            <span className="absolute -right-0.5 -top-0.5 flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-70" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-white" />
            </span>
          </span>

          <span className="whitespace-nowrap">Ask Omni</span>

        </button>

        <span className="h-6 w-px flex-shrink-0 bg-slate-200" />


        <nav className="flex flex-1 items-center gap-1 overflow-x-auto">

          {NAV_ITEMS.map((item) => {

            const isActive = activePage === item.id

            return (
              <button
                key={item.id}
                onClick={() => setActivePage(item.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`
                  flex
                  flex-shrink-0
                  items-center
                  gap-2
                  rounded-xl
                  px-3.5
                  py-2
                  text-sm
                  transition
                  ${
                    isActive
                      ? 'bg-slate-900 text-white shadow-[0_6px_16px_rgba(15,23,42,0.25)]'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }
                `}
              >
                <span className="text-xs">{item.icon}</span>
                <span className="whitespace-nowrap">{item.label}</span>
              </button>
            )
          })}

        </nav>


        {/* ============================================== */}
        {/* STATUS */}
        {/* ============================================== */}

        <div className="flex flex-shrink-0 items-center gap-2 border-l border-slate-200 pl-3">
          <div className="hidden min-w-0 text-right xl:block">
            <p className="max-w-36 truncate text-xs font-semibold text-slate-800">{user.name}</p>
            <p className="max-w-36 truncate text-[10px] text-slate-500">{user.email}</p>
          </div>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-xs font-bold uppercase text-blue-800" title={`${user.name} (${user.email})`}>
            {user.name?.charAt(0) || 'U'}
          </div>
          <button type="button" onClick={onLogout} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900">
            Sign out
          </button>
        </div>

      </div>

    </header>
  )
}


// ============================================================
// DASHBOARD PAGE
// ------------------------------------------------------------
// The factory render is the page. Every card floats on top of
// it: a tall stack on the left, the output panels on the right,
// the queue and floor map along the bottom.
// ============================================================

const ALERTS = [
  { title: 'Fabric stock sync complete', subtitle: 'Fabric inventory agent', status: 'Online', statusType: 'success' },
  { title: 'Demand forecast recalculated', subtitle: 'Merchandising agent', status: 'Updated', statusType: 'info' },
  { title: 'Supplier lead times monitored', subtitle: 'Procurement agent', status: 'Stable', statusType: 'info' },
  { title: 'Line efficiency risk flagged', subtitle: 'Production planning agent', status: 'Watch', statusType: 'warning' },
]

const AGENTS = [
  { title: 'Fabric inventory agent', subtitle: 'Bin + roll level sync', status: 'Online', statusType: 'success' },
  { title: 'Demand forecast agent', subtitle: 'Season SS26 model', status: 'Updated', statusType: 'info' },
  { title: 'Supplier intelligence agent', subtitle: 'Lead time watch', status: 'Stable', statusType: 'info' },
  { title: 'Line planning agent', subtitle: 'Line 3 finishing risk', status: 'Watching', statusType: 'warning' },
  { title: 'Ask Omni', subtitle: 'Operations copilot', status: 'Online', statusType: 'success' },
  { title: 'Factory report agent', subtitle: 'Nightly pack', status: 'Ready', statusType: 'info' },
]

const REORDERS = [
  { material: 'Black Cotton Fabric', vendor: 'Textile Hub', qty: '4,000 m', eta: '2 days', status: 'In transit', tone: 'amber' },
  { material: 'Oxford Twill', vendor: 'Prime Weave', qty: '1,800 m', eta: '5 days', status: 'Queued', tone: 'sky' },
  { material: 'Elastic Rib', vendor: 'North Stitch', qty: '900 kg', eta: '1 day', status: 'Ready', tone: 'emerald' },
]

const OUTPUT_TREND = [48, 62, 58, 74, 80, 92, 88]


function DashboardPage({ setActivePage }) {

  const [health, setHealth] = useState(null)

  const [feedTab, setFeedTab] = useState('all')

  async function checkHealth() {

    try {

      const response = await apiFetch(
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


  const feedRows =
    feedTab === 'alerts' ? ALERTS : feedTab === 'agents' ? AGENTS : [...ALERTS, ...AGENTS]


  return (

    <SceneStage scene="overview">

      <div
        className="
          grid
          min-h-[calc(100vh-4rem)]
          grid-cols-1
          gap-4
          p-4
          pt-8
          xl:h-[calc(100vh-4rem)]
          xl:grid-cols-[20rem_minmax(0,1fr)_20rem]
          xl:grid-rows-[auto_minmax(0,1fr)_auto]
          xl:gap-5
          xl:px-5
          xl:pb-5
          xl:pt-[7.5rem]
        "
      >

        {/* ============================================== */}
        {/* CENTRE — heading sits straight above the queue */}
        {/* ============================================== */}

        <div className="flex flex-col justify-end gap-4 xl:col-start-2 xl:row-span-3 xl:row-start-1 xl:gap-5">

          <div className="flex flex-wrap items-end justify-between gap-3">

            <div className="rounded-2xl border border-white/60 bg-white/70 px-4 py-3 backdrop-blur-xl">

              <span className="inline-flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
                Factory live
              </span>

              <h1 className="mt-1.5 text-xl font-semibold tracking-tight text-slate-900">
                Garment operations overview
              </h1>

              <p className="mt-1 text-[11px] text-slate-500">
                Fabric, production and delivery · updated just now
                {health && <span className="ml-2 text-slate-400">Backend: {health.status}</span>}
              </p>

            </div>


            <div className="flex items-center gap-2">

              <button
                onClick={() => setActivePage('inventory')}
                className="rounded-xl bg-[#1d4ed8] px-3.5 py-2 text-xs font-medium text-white shadow-[0_8px_20px_rgba(29,78,216,0.32)] transition hover:bg-[#1e40af]"
              >
                Fabric stock
              </button>

              <button
                onClick={() => setActivePage('operations')}
                className="rounded-xl border border-white/70 bg-white/80 px-3.5 py-2 text-xs font-medium text-slate-700 backdrop-blur-md transition hover:bg-white"
              >
                Ask Omni
              </button>

              <button
                onClick={checkHealth}
                className="rounded-xl border border-white/70 bg-white/80 px-3 py-2 text-xs text-slate-600 backdrop-blur-md transition hover:bg-white"
                title="Refresh"
              >
                ↻
              </button>

            </div>

          </div>


          <ReorderQueueCard setActivePage={setActivePage} />

        </div>


        {/* ============================================== */}
        {/* LEFT STACK — pulse + live feed */}
        {/* ============================================== */}

        <div className="flex min-h-0 flex-col gap-4 xl:col-start-1 xl:row-span-3 xl:row-start-1 xl:gap-5">

          <ProductionPulseCard />

          <ActivityFeedCard
            tab={feedTab}
            setTab={setFeedTab}
            rows={feedRows}
          />

        </div>


        {/* ============================================== */}
        {/* RIGHT STACK — output trend + line split */}
        {/* ============================================== */}

        <div className="flex flex-col justify-end gap-4 xl:col-start-3 xl:row-span-3 xl:row-start-1 xl:gap-5">

          <OutputTrendCard />

          <LineSplitCard />

        </div>

      </div>

    </SceneStage>
  )
}


// ============================================================
// PRODUCTION PULSE — headline output for the shift
// ============================================================

function ProductionPulseCard() {

  return (

    <FloatCard className="p-4">

      <CardHeader title="Production pulse" />

      <p className="mt-3 text-[11px] text-slate-500">Units completed today</p>

      <div className="mt-1 flex items-end gap-2">

        <span className="text-[26px] font-semibold leading-none tracking-tight text-[#1d4ed8]">
          8,412
        </span>

        <span className="pb-0.5 text-[11px] text-slate-400">/ day</span>

        <span className="ml-auto pb-0.5 text-[11px] font-medium text-emerald-600">▲ 12.5%</span>

      </div>


      <div className="mt-3">

        <div className="flex items-center justify-between text-[10px] text-slate-500">
          <span>Daily target 9,800</span>
          <span className="font-medium text-slate-700">86%</span>
        </div>

        <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-gradient-to-r from-[#3b82f6] to-[#1d4ed8]" style={{ width: '86%' }} />
        </div>

      </div>


      <div className="mt-4 grid grid-cols-2 gap-x-3 gap-y-3 border-t border-slate-100 pt-3">

        <PulseStat value="184" label="Fabric SKUs" bars={[40, 70, 55, 85, 60]} tone="bg-[#1d4ed8]" />

        <PulseStat value="96.4%" label="Cutting yield" bars={[60, 80, 72, 90, 96]} tone="bg-emerald-500" />

        <PulseStat value="27" label="Open POs" bars={[30, 55, 45, 65, 50]} tone="bg-slate-400" />

        <PulseStat value="94.8%" label="Line adherence" bars={[70, 62, 88, 80, 94]} tone="bg-[#3b82f6]" />

      </div>

    </FloatCard>
  )
}


function PulseStat({ value, label, bars, tone }) {

  return (

    <div className="flex items-end justify-between gap-2">

      <div>

        <p className="text-base font-semibold leading-none tracking-tight text-slate-900">
          {value}
        </p>

        <p className="mt-1 text-[10px] text-slate-400">{label}</p>

      </div>

      <div className="flex h-6 items-end gap-[3px]">

        {bars.map((bar, index) => (
          <span
            key={index}
            className={`w-[3px] rounded-full ${tone} opacity-80`}
            style={{ height: `${bar}%` }}
          />
        ))}

      </div>

    </div>
  )
}


// ============================================================
// ACTIVITY FEED — alerts and agent health behind tabs
// ============================================================

function ActivityFeedCard({ tab, setTab, rows }) {

  const tabs = [
    { id: 'all', label: 'All' },
    { id: 'alerts', label: 'Alerts' },
    { id: 'agents', label: 'Agents' },
  ]

  return (

    <FloatCard className="flex min-h-0 flex-1 flex-col p-4">

      <CardHeader title="Live activity" />

      <div className="mt-3 flex items-center gap-1.5">

        {tabs.map((item) => (
          <button
            key={item.id}
            onClick={() => setTab(item.id)}
            className={`rounded-lg px-2.5 py-1 text-[11px] transition ${
              tab === item.id
                ? 'bg-[#1d4ed8] text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {item.label}
          </button>
        ))}

      </div>


      <div className="mt-2 min-h-0 flex-1 overflow-y-auto pr-1">

        {rows.map((row) => (
          <FeedRow key={`${row.title}-${row.status}`} {...row} />
        ))}

      </div>

    </FloatCard>
  )
}


function FeedRow({ title, subtitle, status, statusType }) {

  const styles = {
    success: 'bg-emerald-50 text-emerald-600',
    warning: 'bg-amber-50 text-amber-600',
    info: 'bg-indigo-50 text-indigo-500',
  }

  return (

    <div className="flex items-center justify-between gap-3 border-b border-slate-100 py-2.5 last:border-b-0">

      <div className="min-w-0">

        <p className="truncate text-[12px] text-slate-900">{title}</p>

        <p className="mt-0.5 truncate text-[10px] text-slate-400">{subtitle}</p>

      </div>

      <span className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${styles[statusType]}`}>
        {status}
      </span>

    </div>
  )
}


// ============================================================
// REORDER QUEUE
// ============================================================

function ReorderQueueCard({ setActivePage }) {

  const tones = {
    amber: 'bg-amber-50 text-amber-700',
    sky: 'bg-sky-50 text-sky-700',
    emerald: 'bg-emerald-50 text-emerald-700',
  }

  return (

    <FloatCard className="p-4">

      <CardHeader title="Reorder queue" />

      <div className="mt-2 grid grid-cols-1 gap-x-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">

        <div>

        {REORDERS.map((row) => (

          <div key={row.material} className="flex items-center justify-between gap-3 border-b border-slate-100 py-2.5">

            <div className="min-w-0">

              <p className="truncate text-[12px] text-slate-900">{row.material}</p>

              <p className="mt-0.5 text-[10px] text-slate-400">{row.vendor} · ETA {row.eta}</p>

            </div>

            <div className="flex flex-shrink-0 items-center gap-2">

              <span className="text-[11px] text-slate-700">{row.qty}</span>

              <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${tones[row.tone]}`}>
                {row.status}
              </span>

            </div>

          </div>
        ))}

        </div>


        {/* Summary column — sits beside the queue on wide screens */}

        <div className="mt-3 flex flex-col border-t border-slate-100 pt-3 lg:mt-0 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-1">

          <div className="space-y-2 text-[11px]">

            <div className="flex items-center justify-between">
              <span className="text-slate-500">Open purchase orders</span>
              <span className="font-medium text-slate-900">27</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-500">Plan vs actual</span>
              <span className="font-medium text-slate-900">98.2%</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-500">Efficiency</span>
              <span className="font-medium text-emerald-600">+4.6%</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-500">Fabric SKUs tracked</span>
              <span className="font-medium text-slate-900">184</span>
            </div>

          </div>


          <button
            onClick={() => setActivePage('supplier')}
            className="mt-auto w-full rounded-lg border border-slate-200 bg-slate-50 py-1.5 text-[11px] font-medium text-slate-600 transition hover:bg-slate-100"
          >
            View all
          </button>

        </div>

      </div>

    </FloatCard>
  )
}


// ============================================================
// OUTPUT TREND
// ============================================================

function OutputTrendCard() {

  const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

  return (

    <FloatCard className="p-4">

      <CardHeader title="Weekly output" />

      <div className="mt-2 flex items-end justify-between">

        <div>

          <p className="text-[22px] font-semibold leading-none tracking-tight text-slate-900">
            46.2k
          </p>

          <p className="mt-1 text-[10px] text-slate-400">Units this week</p>

        </div>

        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-600">
          ▲ 12.5%
        </span>

      </div>


      <div className="mt-4 flex h-28 items-end gap-2">

        {OUTPUT_TREND.map((value, index) => (

          <div key={index} className="flex h-full flex-1 flex-col items-center justify-end gap-1.5">

            <div
              className="w-full rounded-t-md bg-gradient-to-t from-[#1d4ed8] via-[#2563eb] to-[#60a5fa]"
              style={{ height: `${value}%` }}
            />

            <span className="text-[9px] text-slate-400">{days[index]}</span>

          </div>
        ))}

      </div>

    </FloatCard>
  )
}


// ============================================================
// LINE SPLIT — how the shift hours were spent
// ============================================================

function LineSplitCard() {

  const split = [
    { label: 'Running', value: '84%', tone: 'text-[#1d4ed8]' },
    { label: 'Changeover', value: '9%', tone: 'text-[#3b82f6]' },
    { label: 'Idle', value: '7%', tone: 'text-slate-400' },
  ]

  const hourly = [42, 58, 66, 74, 61, 80, 88, 70, 64, 52, 76, 84]

  return (

    <FloatCard className="p-4">

      <CardHeader title="Shift statistics" />

      <div className="mt-3 grid grid-cols-3 gap-2">

        {split.map((item) => (

          <div key={item.label}>

            <p className={`text-lg font-semibold leading-none tracking-tight ${item.tone}`}>
              {item.value}
            </p>

            <p className="mt-1 text-[10px] text-slate-400">{item.label}</p>

          </div>
        ))}

      </div>


      <div className="mt-4 flex h-16 items-end gap-[5px]">

        {hourly.map((value, index) => (
          <span
            key={index}
            className="flex-1 rounded-t-[3px] bg-[#1d4ed8]"
            style={{ height: `${value}%`, opacity: 0.35 + (value / 100) * 0.6 }}
          />
        ))}

      </div>


      <div className="mt-1.5 flex justify-between text-[9px] text-slate-400">
        <span>06:00</span>
        <span>12:00</span>
        <span>18:00</span>
      </div>

    </FloatCard>
  )
}


// ============================================================
// CARD HEADER — title plus the small panel controls
// ============================================================

function CardHeader({ title }) {

  return (

    <div className="flex items-center justify-between">

      <h2 className="text-[13px] font-semibold text-slate-900">{title}</h2>

      <div className="flex items-center gap-1.5 text-[11px] text-slate-300">
        <span>▤</span>
        <span>⤢</span>
      </div>

    </div>
  )
}


// ============================================================
// MAIN APP
// ============================================================

function App() {

  const [user, setUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)

  const [activePage, setActivePage] = useState(
    'dashboard'
  )

  const [scQuery, setScQuery] = useState(null)

  const [chatState, setChatState] = useState({
    draft: '',
    messages: [],
    isAsking: false,
    error: '',
  })

  useEffect(() => {
    let active = true
    async function restoreSession() {
      try {
        const currentUser = await authApi.currentUser()
        if (active) setUser(currentUser)
      } catch {
        if (active) setUser(null)
      } finally {
        if (active) setAuthLoading(false)
      }
    }
    restoreSession()
    return () => { active = false }
  }, [])

  useEffect(() => {
    function expireSession() {
      setUser(null)
      setChatState({ draft: '', messages: [], isAsking: false, error: '' })
    }
    window.addEventListener('omni:session-expired', expireSession)
    return () => window.removeEventListener('omni:session-expired', expireSession)
  }, [])

  async function handleLogout() {
    try {
      await authApi.logout()
    } finally {
      setUser(null)
      setActivePage('dashboard')
      setChatState({ draft: '', messages: [], isAsking: false, error: '' })
    }
  }


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
            setActivePage={setActivePage}
            setScQuery={setScQuery}
          />
        )


      case 'forecast':

        return (
          <DemandForecastPage setActivePage={setActivePage} />
        )


      case 'supplier':

        return (
          <SupplyChainPanel initialQuery={scQuery} clearQuery={() => setScQuery(null)} setActivePage={setActivePage} />
        )


      case 'production':

        return (
          <ProductionPage />
        )


      case 'reports':

        return (
          <ReportsPage />
        )


      default:

        return (
          <DashboardPage
            setActivePage={setActivePage}
          />
        )
    }
  }


  if (authLoading) {
    return <div className="flex h-[100dvh] items-center justify-center bg-slate-950 text-white"><div className="flex items-center gap-3"><span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-600 border-t-blue-400" /><span className="text-sm font-medium">Restoring your session...</span></div></div>
  }

  if (!user) {
    return <AuthPage onAuthenticated={setUser} />
  }

  return (

    <div
      className="
        h-screen
        flex
        flex-col
        bg-[#f1f5f9]
        overflow-hidden
      "
    >

      <TopNav
        activePage={activePage}
        setActivePage={setActivePage}
        user={user}
        onLogout={handleLogout}
      />


      <main
        className="
          flex-1
          min-w-0
          overflow-y-auto
        "
      >

        {renderPage()}

      </main>


      {/* ================================================== */}
      {/* ASK OMNI LAUNCHER — reachable from every page.      */}
      {/* Hidden on Ask Omni itself, and on Supplier intel    */}
      {/* where the procurement copilot already owns this     */}
      {/* corner.                                             */}
      {/* ================================================== */}

      {activePage !== 'operations' && activePage !== 'supplier' && (
        <OmniLauncher onClick={() => setActivePage('operations')} />
      )}

    </div>
  )
}


// ============================================================
// OMNI LAUNCHER
// ============================================================

function OmniLauncher({ onClick }) {

  return (
    <button
      onClick={onClick}
      aria-label="Ask Omni"
      className="
        group
        fixed
        bottom-6
        right-6
        z-40
        flex
        items-center
        gap-2.5
        rounded-full
        bg-gradient-to-br from-[#1e3a8a] to-[#111f4d]
        py-2
        pl-2
        pr-3
        text-white
        shadow-[0_18px_36px_-12px_rgba(29,78,216,0.85)]
        transition
        hover:pr-4
        hover:shadow-[0_22px_44px_-12px_rgba(29,78,216,0.95)]
      "
    >

      <span className="relative flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-white shadow-[0_2px_8px_-2px_rgba(15,23,42,0.4)]">
        <OmniMark size={26} />
        <span className="absolute -right-0.5 -top-0.5 flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-70" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-[#1e40af]" />
        </span>
      </span>

      <span className="max-w-0 overflow-hidden whitespace-nowrap text-[13px] font-medium opacity-0 transition-all duration-300 group-hover:max-w-[120px] group-hover:opacity-100">
        Ask Omni
      </span>

    </button>
  )
}


export default App
