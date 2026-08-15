function FeatureCard({ title, description }) {
  return (
    <article className="glass-panel p-5 h-full transition-transform duration-300 hover:-translate-y-1">
      <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-300">{description}</p>
    </article>
  )
}

export default FeatureCard
