import { useEffect, useState } from "react";
import { Mail, Lock, X } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

type LoginMode = "signin" | "signup";

function GoogleIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
      />
    </svg>
  );
}

export function Login({ onClose }: { onClose: () => void }) {
  const {
    signInWithGoogle,
    signInWithEmail,
    signUpWithEmail,
    loading,
    error,
    clearError,
    isConfigured,
  } = useAuth();
  const [mode, setMode] = useState<LoginMode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    try {
      if (mode === "signin") {
        await signInWithEmail(email, password);
      } else {
        await signUpWithEmail(email, password);
      }
      onClose();
    } catch {
      // error is captured in context
    }
  };

  const handleGoogle = async () => {
    try {
      await signInWithGoogle();
      onClose();
    } catch {
      // error is captured in context
    }
  };

  const switchMode = (newMode: LoginMode) => {
    clearError();
    setMode(newMode);
  };

  return (
    <div
      className="login-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="login-title"
    >
      <div className="login-card" onClick={(e) => e.stopPropagation()}>
        <button
          className="login-close"
          type="button"
          aria-label="Close"
          onClick={onClose}
        >
          <X size={18} />
        </button>

        <div className="login-header">
          <span className="login-eyebrow">CONTOUR / AUTH</span>
          <h2 id="login-title">
            {mode === "signin" ? "Sign in to Contour" : "Create an account"}
          </h2>
          <p className="login-subtitle">
            {mode === "signin"
              ? "Access your vector preferences and export settings."
              : "Sign up to save vector presets and customization options."}
          </p>
        </div>

        {!isConfigured && (
          <div className="login-warning" role="alert">
            Firebase is not configured. Add your <code>VITE_FIREBASE_*</code> keys to <code>.env</code>.
          </div>
        )}

        <button
          className="login-google-button"
          type="button"
          disabled={loading || !isConfigured}
          onClick={handleGoogle}
        >
          <GoogleIcon size={18} />
          <span>{loading ? "Connecting…" : "Continue with Google"}</span>
        </button>

        <div className="login-divider">
          <span>or continue with email</span>
        </div>

        <form onSubmit={handleEmailAuth} className="login-form">
          <div className="login-field">
            <label className="login-label" htmlFor="login-email">
              <Mail size={14} /> Email address
            </label>
            <input
              id="login-email"
              className="login-input"
              type="email"
              autoComplete="email"
              placeholder="you@domain.com"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading || !isConfigured}
            />
          </div>

          <div className="login-field">
            <label className="login-label" htmlFor="login-password">
              <Lock size={14} /> Password
            </label>
            <input
              id="login-password"
              className="login-input"
              type="password"
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
              placeholder="••••••••"
              minLength={6}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading || !isConfigured}
            />
          </div>

          {error && (
            <div className="login-error" role="alert">
              {error}
            </div>
          )}

          <button
            className="login-submit-button"
            type="submit"
            disabled={loading || !isConfigured}
          >
            {loading
              ? "Please wait…"
              : mode === "signin"
                ? "Sign in"
                : "Create account"}
          </button>

          <p className="login-toggle">
            {mode === "signin"
              ? "Don't have an account? "
              : "Already have an account? "}
            <button
              type="button"
              className="login-toggle-link"
              onClick={() => switchMode(mode === "signin" ? "signup" : "signin")}
            >
              {mode === "signin" ? "Create one" : "Sign in"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
