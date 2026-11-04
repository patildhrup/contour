import { useEffect, useState } from "react";
import {
  User as UserIcon,
  LogOut,
  Sparkles,
  Menu,
  X,
} from "lucide-react";
import { Login } from "./Login";
import { useAuth } from "../auth/AuthContext";

type NavbarProps = {
  onOpenDashboard?: () => void;
  onGoToLogin?: () => void;
};

// Mirrors the nav breakpoint in styles.css (max-width: 900px).
const MENU_QUERY = "(max-width: 900px)";

export function Navbar({ onOpenDashboard, onGoToLogin }: NavbarProps) {
  const { user, signOut, loading } = useAuth();
  const [loginOpen, setLoginOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  // The hamburger only exists on narrow viewports; drop the open panel when
  // the layout returns to desktop so it can't linger empty after a resize.
  useEffect(() => {
    const wide = window.matchMedia(`not all and ${MENU_QUERY}`);
    const close = () => setMenuOpen(false);
    wide.addEventListener("change", close);
    return () => wide.removeEventListener("change", close);
  }, []);

  useEffect(() => {
    if (!menuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Element | null;
      if (!target?.closest(".warm-nav-shell")) setMenuOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [menuOpen]);

  const closeMenu = () => setMenuOpen(false);

  const handleSignOut = async () => {
    try {
      await signOut();
      // Logging out always lands on the protected login page
      if (onGoToLogin) onGoToLogin();
    } catch {
      // handled in context
    }
  };

  const openDashboard = () => {
    closeMenu();
    onOpenDashboard?.();
  };

  const openLogin = () => {
    closeMenu();
    if (onGoToLogin) onGoToLogin();
    else setLoginOpen(true);
  };

  const displayName =
    user?.displayName ||
    (user?.email ? user.email.split("@")[0] : null) ||
    "Account";

  const initial = (
    user?.displayName?.[0] ||
    user?.email?.[0] ||
    "U"
  ).toUpperCase();

  return (
    <>
      <header className="warm-nav-shell">
        <nav className="warm-navbar wrap" aria-label="Main navigation">
          {/* Left: footer-style "c" brand mark + app name */}
          <a className="warm-brand" href="#">
            <span className="warm-brand-mark">c</span>
            <span className="warm-brand-text">contour</span>
          </a>

          {/* Centre: Nav links (14px, 55% ink) */}
          <div className="warm-nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
            <button
              type="button"
              onClick={() => onOpenDashboard?.()}
              title="Open the Vector Studio Dashboard"
            >
              Vectorize
            </button>
            <a href="#pricing">Pricing</a>
          </div>

          {/* Right: Soft pill Download / Sign in buttons (38px tall, rgba(26,18,0,.1)) */}
          {user ? (
            <div className="warm-nav-user">
              {onOpenDashboard && (
                <button
                  className="warm-nav-pill-studio"
                  type="button"
                  onClick={onOpenDashboard}
                  title="Open full Vector Studio Dashboard"
                >
                  <Sparkles size={14} />
                  <span>Open Studio</span>
                </button>
              )}
              <div className="warm-user-badge">
                {user.photoURL ? (
                  <img
                    src={user.photoURL}
                    alt={displayName}
                    className="warm-user-avatar"
                  />
                ) : (
                  <span className="warm-user-initial">{initial}</span>
                )}
                <span className="warm-user-label" title={user.email ?? ""}>
                  {displayName}
                </span>
              </div>
              <button
                className="warm-signout-btn"
                type="button"
                onClick={handleSignOut}
                disabled={loading}
                title="Sign out of your account"
              >
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <div className="warm-nav-actions">
              <button
                className="warm-nav-pill-signin"
                type="button"
                onClick={() =>
                  onGoToLogin ? onGoToLogin() : setLoginOpen(true)
                }
              >
                <UserIcon size={14} />
                <span>Sign in</span>
              </button>
              <button
                className="warm-nav-pill-download"
                type="button"
                onClick={() => onOpenDashboard?.()}
                title="Open the Vector Studio Dashboard"
              >
                <span>Get started</span>
              </button>
            </div>
          )}

          {/* Mobile: collapses links + account actions into a dropdown panel */}
          <button
            className="warm-nav-toggle"
            type="button"
            aria-expanded={menuOpen}
            aria-controls="warm-nav-menu"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </nav>

        {menuOpen && (
          <div className="warm-nav-menu" id="warm-nav-menu">
            <div className="warm-nav-menu-links">
              <a href="#features" onClick={closeMenu}>
                Features
              </a>
              <a href="#how-it-works" onClick={closeMenu}>
                How it works
              </a>
              <button type="button" onClick={openDashboard}>
                Vectorize
              </button>
              <a href="#pricing" onClick={closeMenu}>
                Pricing
              </a>
            </div>

            <div className="warm-nav-menu-actions">
              {user ? (
                <>
                  <div className="warm-nav-menu-account">
                    {user.photoURL ? (
                      <img
                        src={user.photoURL}
                        alt={displayName}
                        className="warm-user-avatar"
                      />
                    ) : (
                      <span className="warm-user-initial">{initial}</span>
                    )}
                    <span className="warm-user-label" title={user.email ?? ""}>
                      {displayName}
                    </span>
                  </div>
                  <button
                    className="warm-nav-menu-primary"
                    type="button"
                    onClick={openDashboard}
                  >
                    <Sparkles size={15} />
                    <span>Open Studio</span>
                  </button>
                  <button
                    className="warm-nav-menu-secondary"
                    type="button"
                    onClick={() => {
                      closeMenu();
                      handleSignOut();
                    }}
                    disabled={loading}
                  >
                    <LogOut size={15} />
                    <span>Sign out</span>
                  </button>
                </>
              ) : (
                <>
                  <button
                    className="warm-nav-menu-primary"
                    type="button"
                    onClick={openDashboard}
                  >
                    <span>Get started</span>
                  </button>
                  <button
                    className="warm-nav-menu-secondary"
                    type="button"
                    onClick={openLogin}
                  >
                    <UserIcon size={15} />
                    <span>Sign in</span>
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </header>
      {loginOpen && <Login onClose={() => setLoginOpen(false)} />}
    </>
  );
}
