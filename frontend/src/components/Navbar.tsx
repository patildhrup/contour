import { useState } from "react";
import { User as UserIcon, LogOut, Sparkles } from "lucide-react";
import { Login } from "./Login";
import { useAuth } from "../auth/AuthContext";

type NavbarProps = {
  onOpenDashboard?: () => void;
  onGoToLogin?: () => void;
};

export function Navbar({ onOpenDashboard, onGoToLogin }: NavbarProps) {
  const { user, signOut, loading } = useAuth();
  const [loginOpen, setLoginOpen] = useState(false);

  const handleSignOut = async () => {
    try {
      await signOut();
      // Logging out always lands on the protected login page
      if (onGoToLogin) onGoToLogin();
    } catch {
      // handled in context
    }
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
        </nav>
      </header>
      {loginOpen && <Login onClose={() => setLoginOpen(false)} />}
    </>
  );
}
