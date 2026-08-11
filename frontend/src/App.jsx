import React from 'react'

function App() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-6 relative overflow-hidden">
      
      {/* Dynamic Background Elements */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-indigo-500/20 rounded-full blur-[100px] animate-pulse"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-fuchsia-500/20 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: '1s' }}></div>

      <main className="glass-panel p-10 md:p-16 max-w-3xl w-full text-center relative z-10 transition-all duration-500 hover:shadow-indigo-500/10 hover:-translate-y-1">
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

        <button className="px-8 py-4 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl font-semibold text-white transition-all duration-300 hover:shadow-lg hover:shadow-white/10 active:scale-95 group">
          Initialize Agents
          <span className="inline-block ml-2 transition-transform duration-300 group-hover:translate-x-1">→</span>
        </button>
      </main>
    </div>
  )
}

export default App
