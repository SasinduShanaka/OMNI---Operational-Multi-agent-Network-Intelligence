function MetricsGrid({ metrics }) {
  return (
    <section className="grid gap-4 sm:grid-cols-3">
      {metrics.map((metric) => (
        <article key={metric.label} className="glass-panel p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{metric.label}</p>
          <p className="mt-2 text-2xl font-bold text-white">{metric.value}</p>
          <p className="mt-1 text-xs text-emerald-200">{metric.trend}</p>
        </article>
      ))}
    </section>
  )
}

export default MetricsGrid
