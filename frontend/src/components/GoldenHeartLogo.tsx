export function GoldenHeartLogo({ size = 32 }: { size?: number }) {
  const heartScale = size / 32;
  const radius = Math.round(size * 0.22);

  return (
    <div
      className="golden-squircle-logo"
      style={{
        width: size,
        height: size,
        background: "linear-gradient(145deg, #FFC933 0%, #FFB800 55%, #F59E0B 100%)",
        borderRadius: `${radius}px`,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "0 4px 14px rgba(255, 184, 0, 0.42), inset 0 1px 2px rgba(255, 255, 255, 0.6)",
        flexShrink: 0,
        position: "relative",
      }}
    >
      <svg
        width={18 * heartScale}
        height={18 * heartScale}
        viewBox="0 0 24 24"
        fill="none"
        stroke="#ffffff"
        strokeWidth="2.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{
          filter: "drop-shadow(0 1px 2px rgba(0, 0, 0, 0.15))",
        }}
      >
        <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
      </svg>
    </div>
  );
}

