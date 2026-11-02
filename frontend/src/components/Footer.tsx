export function Footer({ open }: { open: (s: string) => void }) {
  return (
    <footer className="wrap">
      <a className="brand" href="#">
        <span className="brand-mark">c</span>contour
      </a>
      <p>A sharper way forward.</p>
      <div>
        {["Privacy", "Terms", "Contact"].map((s) => (
          <button key={s} onClick={() => open(s)}>
            {s}
          </button>
        ))}
      </div>
      <span>© {new Date().getFullYear()} Contour</span>
    </footer>
  );
}
