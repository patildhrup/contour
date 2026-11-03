export function WarmFeatures() {
  const cards = [
    {
      id: "tracing",
      title: "Sub-Pixel Tracing",
      desc: "Tease out boundaries with subpixel accuracy according to anti-aliased pixel values instead of snapping.",
      badge: "ENGINE",
      illustration: (
        <svg viewBox="0 0 120 100" className="chunky-illustration">
          <defs>
            <linearGradient id="gold-grad-1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FFE169" />
              <stop offset="50%" stopColor="#FFB800" />
              <stop offset="100%" stopColor="#E69500" />
            </linearGradient>
            <filter id="chunky-shadow-1">
              <feDropShadow dx="0" dy="6" stdDeviation="4" floodColor="#1A1200" floodOpacity="0.18" />
            </filter>
          </defs>
          {/* Black shadow background shape */}
          <rect x="24" y="24" width="72" height="52" rx="18" fill="#1A1200" />
          {/* Chunky gold offset block */}
          <rect
            x="20"
            y="18"
            width="72"
            height="52"
            rx="18"
            fill="url(#gold-grad-1)"
            stroke="#1A1200"
            strokeWidth="3.5"
            filter="url(#chunky-shadow-1)"
          />
          {/* 3D Magnifying glass with heart */}
          <circle cx="56" cy="40" r="16" fill="#FFFBF1" stroke="#1A1200" strokeWidth="3.5" />
          <path d="M68 52 L82 66" stroke="#1A1200" strokeWidth="6" strokeLinecap="round" />
          <path d="M68 52 L82 66" stroke="#FFB800" strokeWidth="2.5" strokeLinecap="round" />
          {/* Smooth sub-pixel wave inside lens */}
          <path d="M46 42 Q 56 30, 66 42" fill="none" stroke="#FFB800" strokeWidth="3.5" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      id: "bezier",
      title: "Infinite Scaling",
      desc: "Continuous cubic Béziers and clean corner detection that scale cleanly from mobile icons to billboards.",
      badge: "VECTOR",
      illustration: (
        <svg viewBox="0 0 120 100" className="chunky-illustration">
          <defs>
            <linearGradient id="gold-grad-2" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FFE169" />
              <stop offset="50%" stopColor="#FFB800" />
              <stop offset="100%" stopColor="#D97706" />
            </linearGradient>
          </defs>
          {/* Black base shape */}
          <path
            d="M30 65 Q 60 15, 90 65 Z"
            fill="#1A1200"
            transform="translate(4, 5)"
          />
          {/* Chunky 3D vector pen / star */}
          <path
            d="M30 65 Q 60 15, 90 65 Z"
            fill="url(#gold-grad-2)"
            stroke="#1A1200"
            strokeWidth="3.5"
          />
          {/* Bezier control points */}
          <circle cx="30" cy="65" r="5" fill="#1A1200" />
          <circle cx="90" cy="65" r="5" fill="#1A1200" />
          <circle cx="60" cy="15" r="6" fill="#FFFBF1" stroke="#1A1200" strokeWidth="3" />
          {/* Star sparkle */}
          <path
            d="M86 20 L89 26 L96 28 L90 33 L92 40 L86 36 L80 40 L82 33 L76 28 L83 26 Z"
            fill="#FFB800"
            stroke="#1A1200"
            strokeWidth="2"
          />
        </svg>
      ),
    },
    {
      id: "export",
      title: "Multi-Format Export",
      desc: "Instant export to genuine SVG, native cubic PDF, PostScript EPS for laser & CNC, and clean raster PNG.",
      badge: "OUTPUT",
      illustration: (
        <svg viewBox="0 0 120 100" className="chunky-illustration">
          <defs>
            <linearGradient id="gold-grad-3" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FFE066" />
              <stop offset="50%" stopColor="#FFB800" />
              <stop offset="100%" stopColor="#E69500" />
            </linearGradient>
          </defs>
          {/* Back document (Black) */}
          <rect x="42" y="16" width="48" height="60" rx="10" fill="#1A1200" />
          {/* Front document (Gold) */}
          <rect
            x="30"
            y="24"
            width="48"
            height="60"
            rx="10"
            fill="url(#gold-grad-3)"
            stroke="#1A1200"
            strokeWidth="3.5"
          />
          {/* File folded corner */}
          <path d="M64 24 L78 38 L64 38 Z" fill="#1A1200" />
          {/* Text lines */}
          <rect x="38" y="44" width="22" height="4" rx="2" fill="#1A1200" />
          <rect x="38" y="52" width="32" height="4" rx="2" fill="#1A1200" />
          <rect x="38" y="60" width="16" height="4" rx="2" fill="#1A1200" />
          {/* Floating badge */}
          <rect x="66" y="62" width="30" height="18" rx="6" fill="#1A1200" />
          <text x="81" y="75" fill="#FFB800" fontSize="9" fontWeight="800" textAnchor="middle" fontFamily="sans-serif">
            SVG
          </text>
        </svg>
      ),
    },
    {
      id: "studio",
      title: "Precision Studio",
      desc: "Remap colors, merge layers, remove backgrounds, and adjust corner radiuses in the interactive Studio.",
      badge: "STUDIO",
      illustration: (
        <svg viewBox="0 0 120 100" className="chunky-illustration">
          <defs>
            <linearGradient id="gold-grad-4" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FFE680" />
              <stop offset="50%" stopColor="#FFB800" />
              <stop offset="100%" stopColor="#F59E0B" />
            </linearGradient>
          </defs>
          {/* Black shadow palette */}
          <path
            d="M60 20 C36 20, 20 34, 20 54 C20 70, 32 80, 48 80 C54 80, 58 76, 58 70 C58 66, 62 62, 68 62 C80 62, 100 56, 100 44 C100 30, 84 20, 60 20 Z"
            fill="#1A1200"
            transform="translate(4, 5)"
          />
          {/* Chunky gold palette */}
          <path
            d="M60 20 C36 20, 20 34, 20 54 C20 70, 32 80, 48 80 C54 80, 58 76, 58 70 C58 66, 62 62, 68 62 C80 62, 100 56, 100 44 C100 30, 84 20, 60 20 Z"
            fill="url(#gold-grad-4)"
            stroke="#1A1200"
            strokeWidth="3.5"
          />
          {/* Color paint wells */}
          <circle cx="40" cy="38" r="6" fill="#1A1200" />
          <circle cx="58" cy="34" r="6" fill="#FFFBF1" stroke="#1A1200" strokeWidth="2" />
          <circle cx="76" cy="40" r="6" fill="#1A1200" />
          {/* Thumb hole */}
          <ellipse cx="44" cy="62" rx="7" ry="9" fill="#FFFBF1" stroke="#1A1200" strokeWidth="3" />
        </svg>
      ),
    },
  ];

  return (
    <section className="warm-features-section" id="features">
      <div className="warm-features-container">
        <div className="warm-features-header">
          <span className="warm-eyebrow">✦ Featured on Contour</span>
          <h2 className="warm-section-title">Everything built for pure precision</h2>
          <p className="warm-section-subtitle">
            From raster noise to crystal-clear Bézier outlines in milliseconds.
          </p>
        </div>

        {/* ── ROW OF 4 EQUAL CARDS (40px radius, 32px padding, warm tint, soft shadow) ── */}
        <div className="warm-cards-row">
          {cards.map((c) => (
            <div key={c.id} className="warm-link-card">
              <div className="card-top-icon">
                <div className="chunky-illustration-wrapper">{c.illustration}</div>
              </div>
              <div className="card-content">
                <span className="card-badge">{c.badge}</span>
                <h3 className="card-title">{c.title}</h3>
                <p className="card-description">{c.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

