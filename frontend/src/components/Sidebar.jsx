function Sidebar({ activePage, onPageChange }) {
  const menuItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: '▦',
      section: 'OVERVIEW',
    },
    {
      id: 'operations',
      label: 'Ask Omni',
      icon: '◯',
      section: 'AGENTS',
    },
    {
      id: 'inventory',
      label: 'Inventory',
      icon: '◇',
      section: 'AGENTS',
    },
    {
      id: 'forecast',
      label: 'Demand forecast',
      icon: '↗',
      section: 'AGENTS',
    },
    {
      id: 'supplier',
      label: 'Supplier intel',
      icon: '▱',
      section: 'AGENTS',
    },
    {
      id: 'production',
      label: 'Production',
      icon: '⚙',
      section: 'AGENTS',
    },
    {
      id: 'reports',
      label: 'Reports',
      icon: '▣',
      section: 'AGENTS',
    },
  ]

  return (
    <aside className="w-56 min-h-screen bg-slate-950 text-white flex flex-col border-r border-slate-800">

      {/* ================================================== */}
      {/* LOGO */}
      {/* ================================================== */}

      <div className="h-16 flex items-center px-4 border-b border-slate-800">

        <div className="w-7 h-7 rounded-md bg-indigo-500 flex items-center justify-center font-bold text-sm mr-2">
          A
        </div>

        <span className="font-semibold text-white">
          AgentOps
        </span>

      </div>


      {/* ================================================== */}
      {/* NAVIGATION */}
      {/* ================================================== */}

      <nav className="flex-1 px-2 py-6">

        {menuItems.map((item, index) => {

          const showSection =
            index === 0 ||
            item.section !== menuItems[index - 1].section

          const isActive = activePage === item.id

          return (
            <div key={item.id}>

              {showSection && (
                <p className="text-[10px] uppercase tracking-wider text-slate-500 px-2 mb-2 mt-3">
                  {item.section}
                </p>
              )}

              <button
                onClick={() => onPageChange(item.id)}
                className={`
                  w-full
                  flex
                  items-center
                  gap-3
                  px-3
                  py-2.5
                  rounded-lg
                  text-sm
                  transition
                  mb-1
                  ${
                    isActive
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-400 hover:bg-slate-900 hover:text-white'
                  }
                `}
              >

                <span className="w-5 text-center text-sm">
                  {item.icon}
                </span>

                <span>
                  {item.label}
                </span>

              </button>

            </div>
          )
        })}

      </nav>


      {/* ================================================== */}
      {/* SYSTEM STATUS */}
      {/* ================================================== */}

      <div className="border-t border-slate-800 p-4">

        <div className="flex items-center gap-2">

          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>

          <span className="text-xs text-slate-400">
            All 6 agents synced
          </span>

        </div>

      </div>

    </aside>
  )
}

export default Sidebar