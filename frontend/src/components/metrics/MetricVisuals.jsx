// ============================================================
// METRIC VISUALS
// ------------------------------------------------------------
// Shared chart primitives. The three-hue categorical set below
// was validated against the light surface (lightness band,
// chroma floor, CVD separation, contrast). Amber/emerald sit in
// the CVD floor band, which is why every segment here is
// direct-labelled rather than relying on colour alone.
// ============================================================

export const SERIES = {
  blue:    '#2563eb',
  amber:   '#d97706',
  emerald: '#059669',
}

// Neutral track behind a meter — a surface, never a series.
const TRACK = '#e2e8f0'


// ------------------------------------------------------------
// METER — one proportion against its track, with an optional
// target tick. For "x of y", utilisation, fill rate.
// ------------------------------------------------------------

export function Meter({ label, value, max = 100, display, caption, color = SERIES.blue, target }) {

  const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0

  return (
    <div>

      <div className="flex items-baseline justify-between gap-3">
        <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">{label}</p>
        <p className="text-[13px] font-semibold tabular-nums text-slate-900">{display ?? `${Math.round(pct)}%`}</p>
      </div>

      <div className="relative mt-2 h-2 w-full overflow-hidden rounded-full" style={{ background: TRACK }}>
        <div
          className="h-full rounded-full transition-[width] duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
        {target != null && (
          <div
            className="absolute top-[-2px] h-[calc(100%+4px)] w-[2px] rounded-full bg-slate-900/70"
            style={{ left: `calc(${Math.min(100, Math.max(0, target))}% - 1px)` }}
            title={`Target ${target}%`}
          />
        )}
      </div>

      {caption && <p className="mt-1.5 text-[11px] text-slate-400">{caption}</p>}

    </div>
  )
}


// ------------------------------------------------------------
// SEGMENTED BAR — parts of a whole, each part direct-labelled,
// with 2px of surface between fills.
// ------------------------------------------------------------

export function SegmentedBar({ segments, caption }) {

  const present = segments.filter((item) => item.value > 0)

  return (
    <div>

      <div className="flex h-2.5 w-full gap-[2px] overflow-hidden rounded-full" style={{ background: TRACK }}>
        {present.map((item) => (
          <div
            key={item.label}
            className="h-full transition-[flex-grow] duration-500 first:rounded-l-full last:rounded-r-full"
            style={{ flexGrow: item.value, background: item.color }}
            title={`${item.label}: ${item.value}`}
          />
        ))}
      </div>

      <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1.5">
        {segments.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <span className="h-2 w-2 flex-shrink-0 rounded-[3px]" style={{ background: item.color }} />
            <span className="text-[11px] text-slate-500">{item.label}</span>
            <span className="text-[11px] font-semibold tabular-nums text-slate-900">{item.value}</span>
          </div>
        ))}
      </div>

      {caption && <p className="mt-2 text-[11px] text-slate-400">{caption}</p>}

    </div>
  )
}


// ------------------------------------------------------------
// DONUT — one share against its maximum, value in the middle.
// Parts of a whole belong in SegmentedBar, not stacked here.
// ------------------------------------------------------------

export function Donut({ value, max = 100, label, caption, color = SERIES.blue, size = 84 }) {

  const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0
  const stroke = 9
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius

  return (
    <div className="flex items-center gap-3">

      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90 flex-shrink-0">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={TRACK} strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * circumference} ${circumference}`}
          className="transition-[stroke-dasharray] duration-700"
        />
      </svg>

      <div className="min-w-0">
        <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">{label}</p>
        <p className="mt-1 text-[20px] font-semibold leading-none tabular-nums text-slate-900">
          {Math.round(pct)}<span className="text-[13px] text-slate-400">%</span>
        </p>
        {caption && <p className="mt-1 text-[11px] text-slate-400">{caption}</p>}
      </div>

    </div>
  )
}


// ------------------------------------------------------------
// MINI BARS — a short series. The peak keeps full weight so the
// eye lands on it without a label on every bar.
// ------------------------------------------------------------

export function MiniBars({ data, color = SERIES.blue, height = 56, valueFormat = (value) => value }) {

  const peak = Math.max(1, ...data.map((item) => item.value))

  return (
    <div>
      <div className="flex items-end gap-1.5" style={{ height }}>
        {data.map((item) => (
          <div
            key={item.label}
            className="flex h-full flex-1 flex-col justify-end"
            title={`${item.label}: ${valueFormat(item.value)}`}
          >
            <div
              className="w-full rounded-t-[4px] transition-[height] duration-500"
              style={{
                height: `${(item.value / peak) * 100}%`,
                background: color,
                opacity: item.value === peak ? 1 : 0.55,
              }}
            />
          </div>
        ))}
      </div>

      <div className="mt-1.5 flex gap-1.5">
        {data.map((item) => (
          <span key={item.label} className="flex-1 truncate text-center text-[9px] text-slate-400">
            {item.label}
          </span>
        ))}
      </div>
    </div>
  )
}
