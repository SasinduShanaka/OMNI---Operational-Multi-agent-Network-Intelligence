// ============================================================
// OMNI MARK
// ------------------------------------------------------------
// The assistant's face. One drawing, used at every size: the nav
// pill, the floating launcher, and the chat bubbles — so the
// agent is recognisable wherever it appears.
// ============================================================

export default function OmniMark({ size = 24, className = '' }) {

  const id = `omni-${size}`

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#1e3a8a" />
          <stop offset="60%" stopColor="#1b3270" />
          <stop offset="100%" stopColor="#111f4d" />
        </linearGradient>
      </defs>

      {/* head — deep navy so the orange accents carry the eye */}
      <rect x="4" y="7" width="24" height="20" rx="7" fill={`url(#${id})`} />

      {/* antenna — reads as "listening" rather than a plain icon */}
      <path d="M16 7V3.5" stroke="#f97316" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="16" cy="2.6" r="1.9" fill="#f97316" />

      {/* eyes */}
      <circle cx="12" cy="15.5" r="2.05" fill="#ffffff" />
      <circle cx="20" cy="15.5" r="2.05" fill="#ffffff" />

      {/* mouth */}
      <path
        d="M12.4 21.2c1.1 1.05 2.3 1.55 3.6 1.55s2.5-.5 3.6-1.55"
        stroke="#fb923c"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}


// The mark on its own tile — used where the agent needs presence
// rather than just an icon.
export function OmniAvatar({ size = 34, className = '' }) {
  return (
    <span
      className={`inline-flex flex-shrink-0 items-center justify-center rounded-xl bg-[#eff6ff] ring-1 ring-inset ring-[#bfdbfe] shadow-[0_6px_16px_-8px_rgba(30,58,138,0.55)] ${className}`}
      style={{ width: size, height: size }}
    >
      <OmniMark size={Math.round(size * 0.68)} />
    </span>
  )
}
