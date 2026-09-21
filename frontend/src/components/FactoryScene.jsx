// ============================================================
// FACTORY SCENES
// ------------------------------------------------------------
// Each page shows the isometric render for its own part of the
// garment operation. The files live in src/assets and are
// imported so the bundler hashes them and a missing one breaks
// the build instead of the page.
// ============================================================

import overviewScene from '../assets/overview.png'
import productionScene from '../assets/line.png'
import fabricScene from '../assets/fabric.png'
import supplierScene from '../assets/supplier.png'
import forecastScene from '../assets/demand.png'

export const SCENES = {
  overview: {
    image: overviewScene,
    aspect: '1672 / 560',
    focus: 'center 21%',
    tint: 'linear-gradient(160deg, #1e3a5f 0%, #1a2f4a 45%, #0f172a 100%)',
  },
  production: {
    image: productionScene,
    aspect: '1382 / 532',
    focus: 'center 50%',
    tint: 'linear-gradient(160deg, #1e40af 0%, #1e3a5f 45%, #0f172a 100%)',
  },
  fabric: {
    image: fabricScene,
    aspect: '1672 / 570',
    focus: 'center 50%',
    tint: 'linear-gradient(160deg, #334155 0%, #1e293b 45%, #0f172a 100%)',
  },
  supplier: {
    image: supplierScene,
    aspect: '1672 / 570',
    focus: 'center 50%',
    tint: 'linear-gradient(160deg, #2f3742 0%, #232c36 45%, #0f172a 100%)',
  },
  forecast: {
    image: forecastScene,
    aspect: '1342 / 516',
    focus: 'center 50%',
    tint: 'linear-gradient(160deg, #1d4ed8 0%, #243b53 45%, #0f172a 100%)',
  },
}

function sceneBackground(scene) {
  const config = SCENES[scene] || SCENES.overview

  return {
    backgroundImage: `url('${config.image}'), ${config.tint}`,
    backgroundSize: 'cover, cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat, no-repeat',
  }
}


// ============================================================
// PAGE BACKDROP — full-bleed scene behind an entire page
// ============================================================

export function FactoryBackdrop({ scene, children }) {
  const config = SCENES[scene] || SCENES.overview

  return (
    <div className="relative min-h-full">

      {/* Scene image, with a scrim over the top third so the
          page heading stays legible whatever the render shows. */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-[700px]"
        style={{
          backgroundImage:
            'linear-gradient(to bottom, rgba(14,26,32,0.78) 0%, rgba(14,26,32,0.45) 22%, rgba(14,26,32,0.12) 40%, rgba(14,26,32,0) 55%), ' +
            `url('${config.image}'), ${config.tint}`,
          backgroundSize: 'cover, cover, cover',
          backgroundPosition: 'center top, center 38%, center top',
          backgroundRepeat: 'no-repeat',
        }}
      />

      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-[700px]"
        style={{
          backgroundImage:
            'linear-gradient(to bottom, rgba(241,245,249,0) 0%, rgba(241,245,249,0.18) 42%, rgba(241,245,249,0.62) 64%, rgba(241,245,249,0.93) 82%, #f1f5f9 92%, #f1f5f9 100%)',
        }}
      />

      <div className="relative">
        {children}
      </div>

    </div>
  )
}


// ============================================================
// SCENE HERO — a contained scene panel inside a page
// ============================================================

export function SceneHero({ scene, className = '', children }) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl border border-slate-200 shadow-[0_18px_40px_rgba(15,23,42,0.12)] ${className}`}
      style={sceneBackground(scene)}
    >
      {children}
    </div>
  )
}


// ============================================================
// GLASS PANELS
// ============================================================

// Light glass — for cards sitting on the page surface.
export function GlassCard({ className = '', children }) {
  return (
    <div
      className={`rounded-2xl border border-white/60 bg-white/70 backdrop-blur-xl shadow-[0_10px_30px_rgba(15,23,42,0.07)] ${className}`}
    >
      {children}
    </div>
  )
}

// Dark glass — for cards floating directly on a scene image.
export function SceneCard({ className = '', children }) {
  return (
    <div
      className={`rounded-xl border border-white/15 bg-slate-900/55 text-white backdrop-blur-md ${className}`}
    >
      {children}
    </div>
  )
}


// ============================================================
// SCENE STAGE — the render fills the whole page and the cards
// float on top of it, warehouse-console style.
// ============================================================

export function SceneStage({ scene = 'overview', children }) {
  const config = SCENES[scene] || SCENES.overview

  return (
    <div className="relative min-h-full bg-[#eef2f7]">

      {/* The render sits in a band across the top of the page, sized
          by its own aspect, so long pages scroll off it onto the
          page surface rather than tiling or stretching it. */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0"
        style={{
          aspectRatio: config.aspect,
          backgroundImage: `url('${config.image}')`,
          backgroundSize: 'cover',
          backgroundPosition: config.focus || 'center top',
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* Wash — settles the corners where the floating cards sit and
          fades the foot of the render into the page surface. */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0"
        style={{
          aspectRatio: config.aspect,
          backgroundImage:
            'radial-gradient(125% 96% at 50% 42%, rgba(238,242,247,0) 58%, rgba(238,242,247,0.22) 84%, rgba(238,242,247,0.55) 99%), ' +
            'linear-gradient(to bottom, rgba(238,242,247,0) 74%, rgba(238,242,247,0.55) 90%, #eef2f7 100%)',
        }}
      />

      <div className="relative">
        {children}
      </div>

    </div>
  )
}


// ============================================================
// SCENE BANNER — contained hero band for the content pages
// ------------------------------------------------------------
// The dashboard can afford a full-bleed stage because its cards
// hug the left and right edges and leave the middle of the render
// open. A page built around a table cannot: its cards run the full
// width, so they cover the scene instead of framing it.
//
// Here the render is an in-flow band that the content sits BELOW,
// with only the page heading floating on it.
// ============================================================

export function SceneBanner({ scene = 'overview', maxHeight = '24rem', children }) {
  const config = SCENES[scene] || SCENES.overview

  return (
    <div
      className="relative w-full overflow-hidden"
      style={{
        aspectRatio: config.aspect,
        maxHeight,
        backgroundImage: `url('${config.image}')`,
        backgroundSize: 'cover',
        backgroundPosition: config.focus || 'center top',
        backgroundRepeat: 'no-repeat',
      }}
    >

      {/* Foot of the render dissolves into the page surface so the
          content below starts on clean ground. */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            'linear-gradient(to bottom, rgba(238,242,247,0) 58%, rgba(238,242,247,0.45) 84%, #eef2f7 100%)',
        }}
      />

      <div className="relative flex h-full items-end">
        {children}
      </div>

    </div>
  )
}


// ============================================================
// SCENE PAGE — banner on top, page content underneath
// ============================================================

export function ScenePage({ scene, banner, bannerMaxHeight, contentPull = '-mt-6', children }) {
  return (
    <div className="min-h-full bg-[#eef2f7]">

      <SceneBanner scene={scene} maxHeight={bannerMaxHeight}>
        {banner}
      </SceneBanner>

      {/* Tucked slightly under the fade so the first row of cards
          overlaps the render the way the dashboard's cards do. */}
      <div className={`relative pt-1 ${contentPull}`}>
        {children}
      </div>

    </div>
  )
}


// ============================================================
// FLOAT CARD — bright panel that sits on the stage
// ============================================================

export function FloatCard({ className = '', children }) {
  return (
    <div
      className={`rounded-2xl border border-white/80 bg-white/[0.96] backdrop-blur-2xl shadow-[0_18px_44px_rgba(15,23,42,0.18)] ${className}`}
    >
      {children}
    </div>
  )
}


// ============================================================
// SKELETONS
// ------------------------------------------------------------
// The page reserves the shape of its cards while the agents are
// still answering, so the layout does not jump when data lands.
// ============================================================

export function Shimmer({ className = '' }) {
  return (
    <div className={`animate-pulse rounded bg-slate-200/70 ${className}`} />
  )
}


// A card-shaped placeholder matching the content pages' card style.
export function SkeletonCard({ className = '', lines = 2 }) {
  return (
    <div
      className={`rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)] ${className}`}
    >
      <Shimmer className="h-2 w-20" />
      <Shimmer className="mt-2.5 h-5 w-16" />
      {Array.from({ length: Math.max(0, lines - 1) }).map((_, index) => (
        <Shimmer key={index} className="mt-2 h-2 w-28" />
      ))}
    </div>
  )
}


// A row of stat cards — the usual first thing a content page shows.
export function SkeletonStatRow({ count = 4 }) {
  return (
    <div className="grid grid-cols-2 gap-2.5 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <SkeletonCard key={index} lines={1} />
      ))}
    </div>
  )
}


// A table-shaped placeholder: header strip plus evenly spaced rows.
const CELL_WIDTHS = ['w-16', 'w-24', 'w-12', 'w-20', 'w-14']


export function SkeletonTable({ rows = 6, columns = 5, title = true }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

      {title && (
        <div className="px-4 pb-2 pt-3">
          <Shimmer className="h-3 w-32" />
        </div>
      )}

      <div className="border-y border-slate-200/70 bg-slate-50/70 px-4 py-2">
        <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
          {Array.from({ length: columns }).map((_, index) => (
            <Shimmer key={index} className="h-2 w-14" />
          ))}
        </div>
      </div>

      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="border-b border-slate-100 px-4 py-2.5 last:border-b-0">
          <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
            {Array.from({ length: columns }).map((_, cellIndex) => (
              // widths vary so a row reads as text rather than a bar chart
              <Shimmer
                key={cellIndex}
                className={`h-2.5 ${CELL_WIDTHS[(rowIndex + cellIndex) % CELL_WIDTHS.length]}`}
              />
            ))}
          </div>
        </div>
      ))}

    </div>
  )
}
