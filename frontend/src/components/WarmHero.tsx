import { useState, useEffect, useRef } from "react";
import { Camera, ChevronDown } from "lucide-react";
import { GoldenHeartLogo } from "./GoldenHeartLogo";

export function WarmHero({ onExplore }: { onExplore: () => void }) {
  const [mouseOffset, setMouseOffset] = useState({ x: 0, y: 0 });
  const heroRef = useRef<HTMLDivElement>(null);

  // Parallax reaction to cursor
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!heroRef.current) return;
    const rect = heroRef.current.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = (e.clientX - cx) / (rect.width / 2);
    const dy = (e.clientY - cy) / (rect.height / 2);
    setMouseOffset({ x: dx * 14, y: dy * 14 });
  };

  const resetMouse = () => setMouseOffset({ x: 0, y: 0 });

  return (
    <section
      className="warm-hero-section"
      ref={heroRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={resetMouse}
    >
      <div className="warm-hero-stage">
        {/* ── FLOATING STICKERS & POLAROIDS AROUND THE PHONE ───────────── */}
        <div
          className="sticker-layer"
          style={{
            transform: `translate3d(${mouseOffset.x * 0.8}px, ${mouseOffset.y * 0.8}px, 0)`,
          }}
        >
          {/* 1. Pair of yellow 3D hearts */}
          <div className="floating-item sticker-pair-hearts" style={{ top: "10%", left: "16%" }}>
            <span className="emoji-3d">💛</span>
            <span className="emoji-3d sub">💛</span>
          </div>

          {/* 2. Rounded photo of friends taking selfie (24px radius, white border, soft shadow) */}
          <div className="floating-item photo-bubble photo-friends" style={{ top: "18%", left: "4%" }}>
            <img
              src="https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=260&q=80"
              alt="Friends photo"
            />
          </div>

          {/* 3. Gold "BEST FRIENDS FIRST" / "VECTORS FIRST" wavy sticker badge */}
          <div className="floating-item badge-wavy-gold" style={{ top: "44%", left: "8%" }}>
            <svg viewBox="0 0 140 140" className="wavy-svg">
              <path
                d="M70 0 C78 12 90 8 100 18 C110 28 106 40 118 48 C130 56 128 70 134 82 C140 94 130 106 130 118 C120 126 110 134 96 136 C82 138 72 130 60 136 C48 142 36 134 26 126 C16 118 20 104 14 92 C8 80 0 70 4 58 C8 46 20 40 24 28 C28 16 40 14 52 8 Z"
                fill="#FFB800"
                stroke="#1A1200"
                strokeWidth="4"
              />
            </svg>
            <div className="wavy-badge-text">
              <span>VECTORS</span>
              <span>FIRST!</span>
            </div>
          </div>

          {/* 4. Glossy Gold 3D Heart */}
          <div className="floating-item sticker-gold-heart-3d" style={{ top: "68%", left: "14%" }}>
            <svg width="64" height="64" viewBox="0 0 100 100">
              <defs>
                <linearGradient id="gold3d" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#FFE066" />
                  <stop offset="50%" stopColor="#FFB800" />
                  <stop offset="100%" stopColor="#D97706" />
                </linearGradient>
                <filter id="shadow3d">
                  <feDropShadow dx="0" dy="6" stdDeviation="6" floodColor="#B45309" floodOpacity="0.4" />
                </filter>
              </defs>
              <path
                d="M50 88 C20 65 5 45 5 28 C5 12 18 2 32 2 C41 2 48 8 50 14 C52 8 59 2 68 2 C82 2 95 12 95 28 C95 45 80 65 50 88 Z"
                fill="url(#gold3d)"
                filter="url(#shadow3d)"
              />
              {/* Gloss highlight */}
              <ellipse cx="32" cy="18" rx="10" ry="5" fill="#ffffff" opacity="0.65" transform="rotate(-30 32 18)" />
            </svg>
          </div>

          {/* 5. "I ♥ CONTOUR" oval sticker */}
          <div className="floating-item sticker-oval-love" style={{ top: "6%", right: "20%" }}>
            <span>I ♥ CONTOUR</span>
          </div>

          {/* 6. Black "GOLD" pill sticker */}
          <div className="floating-item sticker-pill-gold" style={{ top: "18%", right: "9%" }}>
            <span>✦ GOLD</span>
          </div>

          {/* 7. Rotated gold stamp with repeating text */}
          <div className="floating-item stamp-rotated-gold" style={{ top: "34%", right: "6%" }}>
            <div className="stamp-inner">
              <span>★ CONTOUR ★ CONTOUR ★ CONTOUR</span>
            </div>
          </div>

          {/* 8. Small landscape photo polaroid */}
          <div className="floating-item photo-bubble photo-landscape" style={{ top: "54%", right: "12%" }}>
            <img
              src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=260&q=80"
              alt="Landscape"
            />
          </div>

          {/* 9. Pink-and-white text sticker */}
          <div className="floating-item sticker-pink-white" style={{ top: "74%", right: "22%" }}>
            <span>SUPER SHARP ✨</span>
          </div>

          {/* 10. Megaphone emoji sticker */}
          <div className="floating-item sticker-megaphone" style={{ top: "28%", left: "26%" }}>
            <span>📣</span>
          </div>

          {/* 11. Close-up photo with a heart pin */}
          <div className="floating-item photo-bubble photo-smile" style={{ top: "72%", left: "28%" }}>
            <img
              src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=240&q=80"
              alt="Creative smile"
            />
            <span className="photo-pin-heart">💛</span>
          </div>
        </div>

        {/* ── THE FROSTED TILTED IPHONE ──────────────────────────────── */}
        <div
          className="warm-phone-wrapper"
          style={{
            transform: `rotate(-8deg) translate3d(${mouseOffset.x * -0.4}px, ${mouseOffset.y * -0.4}px, 0)`,
          }}
        >
          <div className="warm-phone-frame">
            {/* Dynamic Island / Notch */}
            <div className="phone-island" />

            {/* Time & Battery */}
            <div className="phone-status-bar">
              <span className="phone-time">9:41</span>
              <div className="phone-indicators">
                <span className="bar-signal">●●●●</span>
                <span className="bar-battery" />
              </div>
            </div>

            {/* Home Screen App Grid */}
            <div className="phone-app-grid">
              {/* Row 1 */}
              <div className="phone-app-icon app-music">🎵</div>
              <div className="phone-app-icon app-camera">📷</div>
              <div className="phone-app-icon app-photos">🌸</div>
              {/* Gold Heart Contour Icon */}
              <div className="phone-app-icon app-contour-gold">
                <GoldenHeartLogo size={42} />
              </div>

              {/* Row 2 */}
              <div className="phone-app-icon app-notes">📝</div>
              <div className="phone-app-icon app-map">🗺️</div>
              <div className="phone-app-icon app-weather">☀️</div>
              <div className="phone-app-icon app-messages">💬</div>

              {/* Row 3 */}
              <div className="phone-app-icon app-vector-draw">🎨</div>
              <div className="phone-app-icon app-star">⭐</div>
              <div className="phone-app-icon app-compass">🧭</div>
              <div className="phone-app-icon app-safari">🧭</div>
            </div>

            {/* Widget Area */}
            <div className="phone-widget-card">
              <div className="widget-header">
                <GoldenHeartLogo size={20} />
                <span>Contour Studio</span>
              </div>
              <p>Ready to trace in vector 4K</p>
              <div className="widget-progress-bar">
                <div className="widget-progress-fill" />
              </div>
            </div>

            {/* Fade out toward the bottom */}
            <div className="phone-fade-overlay" />
          </div>

          {/* ── QR CODE CARD (Overlapping lower right of phone) ───────── */}
          <div className="qr-code-card" title="Scan with your phone to use Contour">
            <div className="qr-code-box">
              {/* Authentic QR pattern illustration with camera icon */}
              <svg viewBox="0 0 100 100" className="qr-svg">
                {/* 3 Corner Targets */}
                <rect x="6" y="6" width="26" height="26" rx="4" fill="#1A1200" />
                <rect x="11" y="11" width="16" height="16" rx="2" fill="#ffffff" />
                <rect x="15" y="15" width="8" height="8" rx="1" fill="#1A1200" />

                <rect x="68" y="6" width="26" height="26" rx="4" fill="#1A1200" />
                <rect x="73" y="11" width="16" height="16" rx="2" fill="#ffffff" />
                <rect x="77" y="15" width="8" height="8" rx="1" fill="#1A1200" />

                <rect x="6" y="68" width="26" height="26" rx="4" fill="#1A1200" />
                <rect x="11" y="73" width="16" height="16" rx="2" fill="#ffffff" />
                <rect x="15" y="77" width="8" height="8" rx="1" fill="#1A1200" />

                {/* QR Data Grid Matrix */}
                <rect x="38" y="8" width="6" height="6" fill="#1A1200" />
                <rect x="48" y="14" width="6" height="6" fill="#1A1200" />
                <rect x="56" y="8" width="6" height="6" fill="#1A1200" />
                <rect x="38" y="22" width="6" height="6" fill="#1A1200" />
                <rect x="50" y="24" width="6" height="6" fill="#1A1200" />

                <rect x="8" y="38" width="6" height="6" fill="#1A1200" />
                <rect x="18" y="44" width="6" height="6" fill="#1A1200" />
                <rect x="24" y="36" width="6" height="6" fill="#1A1200" />
                <rect x="14" y="52" width="6" height="6" fill="#1A1200" />

                <rect x="68" y="40" width="6" height="6" fill="#1A1200" />
                <rect x="78" y="46" width="6" height="6" fill="#1A1200" />
                <rect x="86" y="38" width="6" height="6" fill="#1A1200" />

                <rect x="38" y="68" width="6" height="6" fill="#1A1200" />
                <rect x="46" y="76" width="6" height="6" fill="#1A1200" />
                <rect x="54" y="84" width="6" height="6" fill="#1A1200" />
                <rect x="68" y="70" width="6" height="6" fill="#1A1200" />
                <rect x="82" y="82" width="6" height="6" fill="#1A1200" />
              </svg>

              {/* Camera icon in the center */}
              <div className="qr-camera-center">
                <Camera size={14} color="#1A1200" />
              </div>
            </div>
            <div className="qr-hover-tooltip">
              <span>Scan with your phone to use Contour</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── BELOW THE PHONE: LARGE LOGO LOCKUP & TAGLINE ─────────────── */}
      <div className="warm-hero-lockup">
        <div className="hero-logo-row">
          <GoldenHeartLogo size={56} />
          <h1 className="hero-logo-text">Contour</h1>
        </div>

        <p className="hero-tagline">
          Turn any image into a scalable vector... right on your screen.
        </p>

        {/* Small bouncing chevron */}
        <button
          className="hero-bouncing-chevron"
          onClick={onExplore}
          aria-label="Scroll to features"
        >
          <ChevronDown size={28} />
        </button>
      </div>
    </section>
  );
}

