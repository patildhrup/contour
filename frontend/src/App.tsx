import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  ArrowUpRight,
  ArrowRight,
  Upload,
  Download,
  Check,
  X,
  SlidersHorizontal,
} from "lucide-react";

import { defaults } from "./types";
import type { Result } from "./types";
import { Navbar } from "./components/Navbar";
import { FAQ } from "./components/FAQ";
import { Footer } from "./components/Footer";
import { readPalette, recolorSvg } from "./utils/palette";
import {
  buildLayers,
  mergeLayers,
  serializeLayers,
  type Layer,
} from "./utils/regions";
import { useAuth } from "./auth/AuthContext";
import { Dashboard } from "./components/Dashboard";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Login } from "./components/Login";
import { WarmHero } from "./components/WarmHero";
import { WarmFeatures } from "./components/WarmFeatures";
function getApiBase(): string {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || "")
    .trim()
    .replace(/\/+$/, "");
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    // On local environment, use same-origin proxy to local backend (port 8080)
    if (host === "localhost" || host === "127.0.0.1") {
      return "";
    }
    // When running on Vercel frontend, default to production backend if not explicitly set
    if (host.endsWith(".vercel.app") && !envUrl) {
      return "https://contour-backend.vercel.app";
    }
  }
  return envUrl;
}

const apiBase = getApiBase();

/* Lightweight History-API routing: "/" = landing, "/dashboard" = studio,
   "/login" = auth page. /dashboard is protected — guests are redirected. */
type View = "landing" | "dashboard" | "login";
const viewFromPath = (): View => {
  const path = window.location.pathname;
  if (path.startsWith("/dashboard")) return "dashboard";
  if (path.startsWith("/login")) return "login";
  return "landing";
};

function useObjectUrl(blob: Blob | null) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    if (!blob) {
      setUrl("");
      return;
    }
    const next = URL.createObjectURL(blob);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [blob]);
  return url;
}
export default function App() {
  const { user, loading } = useAuth();
  const [currentView, setCurrentView] = useState<View>(viewFromPath);
  const [file, setFile] = useState<File | null>(null);
  const [settings, setSettings] = useState(defaults);
  const [result, setResult] = useState<Result | null>(null);
  const [paletteMapping, setPaletteMapping] = useState<Record<string, string>>(
    {},
  );
  const [layers, setLayers] = useState<Layer[]>([]);
  const [crop, setCrop] = useState("");

  const navigate = useCallback((view: View, replace = false) => {
    setCurrentView(view);
    const path =
      view === "dashboard"
        ? "/dashboard"
        : view === "login"
          ? "/login"
          : "/";
    if (window.location.pathname !== path) {
      if (replace) window.history.replaceState({}, "", path);
      else window.history.pushState({}, "", path);
    }
  }, []);

  // Keep the view in sync with browser back / forward
  useEffect(() => {
    const onPopState = () => setCurrentView(viewFromPath());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  // Automatically open the /dashboard route upon successful login
  useEffect(() => {
    if (user) {
      navigate("dashboard");
    }
  }, [user, navigate]);

  // Route guard: /dashboard requires an account — guests go to /login
  useEffect(() => {
    if (!loading && !user && currentView === "dashboard") {
      navigate("login", true);
    }
  }, [loading, user, currentView, navigate]);
  const [convertedSettings, setConvertedSettings] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [modal, setModal] = useState("");
  const request = useRef<AbortController | null>(null);
  const convertedOnce = useRef(false);
  const retraceTimer = useRef<number | undefined>(undefined);
  const selection = useRef(0);
  const modalRef = useRef<HTMLDialogElement>(null);
  const settingsKey = JSON.stringify({ ...settings, crop });
  const latestSettingsKey = useRef(settingsKey);
  latestSettingsKey.current = settingsKey;
  const stale = !!result && convertedSettings !== settingsKey;
  const colors = useMemo(() => readPalette(result?.svg || ""), [result?.svg]);
  const editedResult = useMemo(
    () =>
      result
        ? {
            ...result,
            svg: layers.length
              ? serializeLayers(layers, result, paletteMapping)
              : recolorSvg(result.svg, paletteMapping),
          }
        : null,
    [result, layers, paletteMapping],
  );
  const blob = useMemo(
    () =>
      editedResult
        ? new Blob([editedResult.svg], { type: "image/svg+xml" })
        : null,
    [editedResult],
  );
  const [limits, setLimits] = useState({
    max_upload_bytes: 10 * 1024 * 1024,
    max_pixels: 4_000_000,
    max_dimension: 8192,
  });
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/api/health`, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (
          data &&
          [data.max_upload_bytes, data.max_pixels, data.max_dimension].every(
            (n) => Number.isSafeInteger(n) && n > 0,
          )
        )
          setLimits(data);
      })
      .catch(() => {});
    return () => controller.abort();
  }, []);
  const originalUrl = useObjectUrl(file);
  const vectorUrl = useObjectUrl(blob);
  useEffect(() => {
    if (!busy) return;
    const timer = window.setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(timer);
  }, [busy]);
  useEffect(() => {
    if (modal) modalRef.current?.showModal();
    else modalRef.current?.close();
  }, [modal]);
  const choose = async (f: File) => {
    const token = ++selection.current;
    request.current?.abort();
    setBusy(false);
    setError("");
    const validTypes = [
      "image/jpeg",
      "image/png",
      "image/webp",
      "image/bmp",
      "image/gif",
      "image/tiff",
    ];
    if (f.type && !validTypes.includes(f.type)) {
      setError("Please choose a PNG, JPEG, WebP, BMP, GIF or TIFF image.");
      return;
    }
    if (f.size > limits.max_upload_bytes) {
      setError(
        `This image is too large. Please choose a file under ${(limits.max_upload_bytes / 1024 / 1024).toFixed(1)} MB.`,
      );
      return;
    }
    try {
      const image = await createImageBitmap(f);
      const pixels = image.width * image.height;
      const dimension = Math.max(image.width, image.height);
      image.close();
      if (token !== selection.current) return;
      if (pixels > limits.max_pixels || dimension > limits.max_dimension) {
        setError(
          `Please resize this image to ${(limits.max_pixels / 1_000_000).toFixed(1)} megapixels and ${limits.max_dimension} pixels per side or less.`,
        );
        return;
      }
    } catch {
      if (token === selection.current)
        setError(
          "This file could not be read as an image. Please choose another file.",
        );
      return;
    }
    convertedOnce.current = false;
    setFile(f);
    setResult(null);
    setLayers([]);
    setPaletteMapping({});
    setConvertedSettings("");
  };
  const convert = async () => {
    if (!file) return;
    window.clearTimeout(retraceTimer.current);
    const controller = new AbortController();
    const tracingSettingsKey = settingsKey;
    request.current?.abort();
    request.current = controller;
    setBusy(true);
    setElapsed(0);
    setError("");
    const data = new FormData();
    data.append("file", file);
    Object.entries(settings).forEach(([key, value]) =>
      data.append(key, String(value)),
    );
    if (crop) data.append("crop", crop);
    try {
      const response = await fetch(`${apiBase}/api/convert`, {
        method: "POST",
        body: data,
        signal: controller.signal,
      });
      const json = await response.json().catch(() => null);
      if (!response.ok)
        throw new Error(
          typeof json?.detail === "string"
            ? json.detail
            : "Conversion failed. Please try another image or simpler settings.",
        );
      if (!json?.svg || !json.svg.includes("<svg"))
        throw new Error(
          "The server returned an invalid vector result. Please try again.",
        );
      if (
        controller.signal.aborted ||
        tracingSettingsKey !== latestSettingsKey.current
      )
        return;
      convertedOnce.current = true;
      setResult(json);
      setLayers(buildLayers(json.regions));
      setPaletteMapping({});
      setConvertedSettings(tracingSettingsKey);
    } catch (e) {
      if (
        !controller.signal.aborted &&
        tracingSettingsKey === latestSettingsKey.current
      )
        setError(
          e instanceof TypeError
            ? "The conversion server is unavailable. Start the backend and try again."
            : e instanceof Error
              ? e.message
              : "Something went wrong. Please try again.",
        );
    } finally {
      if (request.current === controller) setBusy(false);
    }
  };
  const convertRef = useRef(convert);
  convertRef.current = convert;
  useEffect(() => {
    if (!file) return;
    // Already traced with these exact settings — nothing to do
    if (convertedOnce.current && convertedSettings === settingsKey) return;
    // First upload traces immediately; later setting tweaks debounce
    retraceTimer.current = window.setTimeout(
      () => {
        void convertRef.current();
      },
      convertedOnce.current ? 650 : 60,
    );
    return () => window.clearTimeout(retraceTimer.current);
  }, [file, settingsKey, convertedSettings]);
  if (currentView === "login") {
    return (
      <>
        <Navbar
          onOpenDashboard={() => navigate("dashboard")}
          onGoToLogin={() => navigate("login")}
        />
        <Login onClose={() => navigate("landing")} />
      </>
    );
  }

  if (currentView === "dashboard") {
    return (
      <ProtectedRoute fallback={null}>
        <Dashboard
        file={file}
        setFile={(f) => {
          if (f) void choose(f);
          else {
            request.current?.abort();
            setBusy(false);
            setFile(null);
            setResult(null);
            setLayers([]);
            setPaletteMapping({});
            setConvertedSettings("");
          }
        }}
        settings={settings}
        setSettings={(next) => {
          request.current?.abort();
          setBusy(false);
          setSettings(next);
        }}
        result={result}
        editedResult={editedResult}
        colors={colors}
        paletteMapping={paletteMapping}
        setPaletteMapping={setPaletteMapping}
        layers={layers}
        onToggleLayer={(id) =>
          setLayers((prev) =>
            prev.map((l) => (l.id === id ? { ...l, hidden: !l.hidden } : l)),
          )
        }
        onRecolorLayer={(id, fill) =>
          setLayers((prev) =>
            prev.map((l) => (l.id === id ? { ...l, fill } : l)),
          )
        }
        onMergeLayers={(ids) => setLayers((prev) => mergeLayers(prev, ids))}
        onRemoveLayer={(id) =>
          setLayers((prev) => prev.filter((l) => l.id !== id))
        }
        onResetLayers={() => setLayers(buildLayers(result?.regions))}
        crop={crop}
        setCrop={setCrop}
        busy={busy}
        stale={stale}
        onConvert={() => void convert()}
        originalUrl={originalUrl}
        vectorUrl={vectorUrl}
        onBackToLanding={() => navigate("landing")}
        />
      </ProtectedRoute>
    );
  }

  return (
    <>
      <Navbar
        onOpenDashboard={() => navigate("dashboard")}
        onGoToLogin={() => navigate("login")}
      />
      <main>
        {/* Section 1: Warm Hero with Tilted Frosted Phone, Stickers, QR card, Golden Heart Logo */}
        <WarmHero
          onExplore={() =>
            document.getElementById("features")?.scrollIntoView({ behavior: "smooth" })
          }
        />

        {/* Section 2: Four Link Cards (Features) with chunky 3D gold-and-black illustrations */}
        <WarmFeatures />

        {/* Conversion workspace lives in the Dashboard (Open Studio) */}
        <section className="how wrap" id="how-it-works">
          <div className="section-top">
            <div>
              <span className="eyebrow">FROM HERE TO ANYWHERE</span>
              <h2>Three steps. A sharper result.</h2>
            </div>
            <p>No steep learning curve required.</p>
          </div>
          <div className="steps">
            {[
              [
                "01",
                "Bring your pixels.",
                "Drop in a JPG, PNG or WebP. Logos, icons and flat illustrations are a great place to start.",
                Upload,
              ],
              [
                "02",
                "Find your finish.",
                "Choose your colors and detail level. Our tracing engine turns pixels into editable paths.",
                SlidersHorizontal,
              ],
              [
                "03",
                "Take it everywhere.",
                "Inspect the result, download your SVG, and keep creating at any scale.",
                Download,
              ],
            ].map(([n, title, description, Icon]) => {
              const StepIcon = Icon as typeof Upload;
              return (
                <article key={n as string}>
                  <div>
                    <span>{n as string}</span>
                    <StepIcon size={23} />
                  </div>
                  <h3>{title as string}</h3>
                  <p>{description as string}</p>
                </article>
              );
            })}
          </div>
        </section>
        <section className="formats wrap" id="formats">
          <div>
            <span className="eyebrow">
              FAMILIAR INPUTS. FRESH POSSIBILITIES.
            </span>
            <h2>A new life for your graphics.</h2>
            <p>
              Built for logos · Icons · Illustrations · Line art · Simple
              graphics
            </p>
          </div>
          <div className="format-flow">
            <span>JPG</span>
            <span>PNG</span>
            <span>WebP</span>
            <ArrowRight size={24} />
            <strong>
              SVG <ArrowUpRight size={18} />
            </strong>
          </div>
          <p className="format-note">
            SVG and PDF are scalable vector exports. PNG export provides a
            raster image. Photographs and complex textures may lose detail or
            produce large files.
          </p>
        </section>
        <section className="pricing wrap" id="pricing">
          <div>
            <span className="eyebrow">START WITHOUT A SUBSCRIPTION</span>
            <h2>Your ideas don't need a paywall.</h2>
            <p>
              This self-hosted edition is free to use. No accounts or paid plans
              are currently offered; hosting costs depend on your deployment.
            </p>
          </div>
          <button
            className="button secondary"
            onClick={() => navigate("dashboard")}
          >
            Make your first vector <ArrowUpRight size={16} />
          </button>
        </section>
        <FAQ />
      </main>
      <Footer open={setModal} />
      <dialog
        ref={modalRef}
        onCancel={() => setModal("")}
        onClick={(e) => {
          if (e.target === e.currentTarget) setModal("");
        }}
      >
        <button
          className="dialog-close"
          aria-label="Close dialog"
          onClick={() => setModal("")}
        >
          <X size={20} />
        </button>
        <span className="eyebrow">CONTOUR / INFORMATION</span>
        <h2>{modal}</h2>
        <p>
          {modal === "Privacy"
            ? "Images are processed by the configured conversion server and removed from temporary storage after processing. Results are held in this browser session. This app has no analytics or account system. Your deployment operator controls server access and any infrastructure logs."
            : modal === "Terms"
              ? "This self-hosted tool is provided as-is. Only upload images you have permission to process. Tracing can simplify or alter artwork; review the output before production use. There are no paid subscriptions or guaranteed conversion results."
              : "This is a self-hosted installation of Contour. For support, contact the person or team managing this deployment. No external support service or email address has been configured."}
        </p>
        <button className="button primary" onClick={() => setModal("")}>
          Got it <Check size={15} />
        </button>
      </dialog>
    </>
  );
}
