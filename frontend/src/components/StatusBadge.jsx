function StatusBadge({ status = 'online' }) {
  const isOnline = status.toLowerCase() === 'online'

  return (
    <span
      className={[
        'inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium uppercase tracking-wide',
        isOnline
          ? 'bg-emerald-400/15 text-emerald-200 ring-1 ring-emerald-300/30'
          : 'bg-amber-400/15 text-amber-100 ring-1 ring-amber-300/30',
      ].join(' ')}
    >
      <span
        className={[
          'h-2 w-2 rounded-full',
          isOnline ? 'bg-emerald-300 animate-pulse' : 'bg-amber-200',
        ].join(' ')}
      />
      {status}
    </span>
  )
}

export default StatusBadge
