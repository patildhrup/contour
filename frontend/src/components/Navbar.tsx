import { ArrowUpRight } from "lucide-react";

export function Navbar() {
  return (
    <header className="nav-shell">
      <nav className="navbar wrap" aria-label="Main navigation">
        <a className="brand" href="#">
          <span className="brand-mark">c</span>contour
        </a>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
          <a href="#formats">Formats</a>
          <a href="#pricing">Pricing</a>
        </div>
        <a className="nav-start" href="#workspace">
          Get started <ArrowUpRight size={16} />
        </a>
      </nav>
    </header>
  );
}
