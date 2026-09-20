// ============================================================
// FACTORY SCENES
// ------------------------------------------------------------
// Each page shows the isometric render for its own part of the
// garment operation. Drop the matching file into
// public/factory/ and it appears automatically; until then the
// layered gradient below stands in for it.
// ============================================================

export const SCENES = {
  overview: {
    image: '/factory/overview.png',
    aspect: '1672 / 560',
    focus: 'center top',
    tint: 'linear-gradient(160deg, #1e3a5f 0%, #1a2f4a 45%, #0f172a 100%)',
  },
  production: {
    image: '/factory/production-floor.jpg',
    aspect: '5 / 2',
    focus: 'center 30%',
    tint: 'linear-gradient(160deg, #1e40af 0%, #1e3a5f 45%, #0f172a 100%)',
  },
  fabric: {
    image: '/factory/fabric-store.jpg',
    aspect: '8 / 3',
    focus: 'center 35%',
    tint: 'linear-gradient(160deg, #334155 0%, #1e293b 45%, #0f172a 100%)',
  },
  supplier: {
    image: '/factory/supplier-yard.jpg',
    aspect: '8 / 3',
    focus: 'center 35%',
    tint: 'linear-gradient(160deg, #2f3742 0%, #232c36 45%, #0f172a 100%)',
  },
  forecast: {
    image: '/factory/planning-room.jpg',
    aspect: '8 / 3',
    focus: 'center 35%',
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
