import { useEffect, useRef, useState } from "react";

import {
  ArrowUpRight,
  ArrowRight,
  Upload,
  Download,
  Check,
  X,
  SlidersHorizontal,
  Layers,
  LoaderCircle,
} from "lucide-react";

import { defaults } from "./types";
import type { Result } from "./types";
import { Navbar } from "./components/Navbar";
import { UploadDropzone } from "./components/UploadDropzone";
import { ConversionSettings } from "./components/ConversionSettings";
import { BeforeAfterViewer } from "./components/BeforeAfterViewer";
import { ConversionProgress } from "./components/ConversionProgress";
import { DownloadPanel } from "./components/DownloadPanel";
import { FAQ } from "./components/FAQ";
import { Footer } from "./components/Footer";
function getApiBase(): string {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");
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

function makeSample(): Promise<File> {
  const canvas = document.createElement("canvas");
  canvas.width = 720;
  canvas.height = 720;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#efe9dc";
  ctx.fillRect(0, 0, 720, 720);
  ctx.translate(360, 360);
  for (let i = 0; i < 8; i++) {
    ctx.save();
    ctx.rotate((i * Math.PI) / 4);
    ctx.fillStyle = i % 2 ? "#f0502b" : "#232c29";
    ctx.beginPath();
    ctx.ellipse(0, -135, 67, 143, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
  ctx.fillStyle = "#efe9dc";
  ctx.beginPath();
  ctx.arc(0, 0, 61, 0, Math.PI * 2);
  ctx.fill();
  return new Promise((resolve) =>
    canvas.toBlob(
      (blob) =>
        resolve(new File([blob!], "contour-flower.png", { type: "image/png" })),
      "image/png",
    ),
  );
}
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
  const [file, setFile] = useState<File | null>(null);
  const [sample, setSample] = useState<File | null>(null);
  const [settings, setSettings] = useState(defaults);
  const [result, setResult] = useState<Result | null>(null);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [modal, setModal] = useState("");
  const request = useRef<AbortController | null>(null);
  const convertedOnce = useRef(false);
  const selection = useRef(0);
  const modalRef = useRef<HTMLDialogElement>(null);
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
  const sampleUrl = useObjectUrl(sample);
  const vectorUrl = useObjectUrl(blob);
  useEffect(() => {
    let alive = true;
    makeSample().then((f) => {
      if (alive) setSample(f);
    });
    return () => {
      alive = false;
      request.current?.abort();
    };
  }, []);
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
    if (!["image/jpeg", "image/png", "image/webp"].includes(f.type)) {
      setError("Please choose a JPG, PNG or WebP image.");
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
    setBlob(null);
  };
  const convert = async () => {
    if (!file) return;
    const controller = new AbortController();
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
      if (controller.signal.aborted) return;
      convertedOnce.current = true;
      setResult(json);
      setBlob(new Blob([json.svg], { type: "image/svg+xml" }));
    } catch (e) {
      if (!controller.signal.aborted)
        setError(
          e instanceof TypeError
            ? "The conversion server is unavailable. Start the backend and try again."
            : e instanceof Error
              ? e.message
              : "Something went wrong. Please try again.",
        );
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };
  const convertRef = useRef(convert);
  convertRef.current = convert;
  useEffect(() => {
    if (!file || !convertedOnce.current) return;
    const timer = window.setTimeout(() => {
      void convertRef.current();
    }, 650);
    return () => window.clearTimeout(timer);
  }, [file, settings]);
  return (
    <>
      <Navbar />
      <main>
        <section className="hero wrap">
          <div className="hero-copy">
            <span className="eyebrow">
              <span className="live-dot" /> LESS PIXEL. MORE POSSIBILITY.
            </span>
            <h1>
              Turn Any Image
              <br />
              Into a{" "}
              <em>
                Scalable
                <br />
                Vector
              </em>
              <span className="period">.</span>
            </h1>
            <p>
              Transform pixel-based images into clean, editable SVG graphics in
              seconds.
            </p>
            <div className="hero-meta">
              <span>
                <Check size={14} /> Editable paths
              </span>
              <span>
                <Check size={14} /> Infinitely scalable
              </span>
              <span>
                <Check size={14} /> Yours to keep
              </span>
            </div>
          </div>
          <div className="hero-art">
            <div className="art-top">
              <span>THE BIG PICTURE, REFINED.</span>
              <ArrowUpRight size={18} />
            </div>
            <div className="art-canvas">
              <img
                className="demo-original"
                src="/demo/flower.png"
                alt="Raster half of sample geometric flower"
              />
              <div className="demo-vector">
                <img
                  src="/demo/flower.svg"
                  alt="Genuine traced SVG half of sample geometric flower"
                />
              </div>
              <div className="demo-seam">
                <span>↔</span>
              </div>
              <div className="demo-labels">
                <span>RASTER</span>
                <span>TRACED SVG</span>
              </div>
              <span className="art-cross tl">+</span>
              <span className="art-cross br">+</span>
              <div className="art-caption">
                <span>01 / REAL TRACING SAMPLE</span>
                <span>180 × 180 → SVG</span>
              </div>
            </div>
            <div className="art-bottom">
              <span>Built for your next big idea.</span>
              <span className="mini-pill">
                PNG <ArrowRight size={12} /> SVG
              </span>
            </div>
          </div>
        </section>
        <section className="workspace wrap" id="workspace">
          <div className="section-top">
            <div>
              <span className="eyebrow">YOUR VECTOR STARTS HERE</span>
              <h2>Small pixels. Big potential.</h2>
            </div>
            <span className="workspace-number">01 — CONVERSION STUDIO</span>
          </div>
          <UploadDropzone
            maxBytes={limits.max_upload_bytes}
            maxPixels={limits.max_pixels}
            file={file}
            onFile={choose}
            onSample={() => {
              if (sample) void choose(sample);
            }}
            busy={busy}
          />
          <div className="workbench">
            <BeforeAfterViewer
              original={originalUrl}
              vector={vectorUrl}
              sample={sampleUrl}
              svg={result?.svg || ""}
              width={result?.width}
              height={result?.height}
            />
            <ConversionSettings
              value={settings}
              setValue={setSettings}
              busy={busy}
            />
          </div>
          <div className="conversion-row">
            <p>
              <span className="live-dot" />
              {busy
                ? "Tracing paths. This uses your current settings."
                : result
                  ? "Conversion complete. Changing a setting retraces automatically."
                  : file
                    ? "Image loaded. Make it resolution independent."
                    : "Choose an image to unlock its next dimension."}
            </p>
            <button
              className="button primary convert"
              disabled={!file || busy}
              onClick={convert}
            >
              {busy ? (
                <LoaderCircle size={17} className="spin" />
              ) : (
                <Layers size={17} />
              )}{" "}
              {busy ? "Converting…" : "Convert to Vector"}
              {!busy && <ArrowRight size={17} />}
            </button>
          </div>
          <ConversionProgress busy={busy} elapsed={elapsed} />
          {busy && (
            <button
              className="cancel"
              onClick={() => {
                request.current?.abort();
                setBusy(false);
              }}
            >
              Cancel conversion
            </button>
          )}
          {error && (
            <div className="error" role="alert">
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {result?.warnings?.map((w) => (
            <p className="warning" key={w}>
              {w}
            </p>
          ))}
          <DownloadPanel result={result} url={vectorUrl} />
        </section>
        <section className="benefits" id="features">
          <div className="wrap benefits-inner">
            <div>
              <span className="eyebrow">NO PIXELS. NO LIMITS.</span>
              <h2>
                Made to go
                <br />
                <em>beyond the original.</em>
              </h2>
            </div>
            <div className="benefit-list">
              {[
                [
                  "01",
                  "Crisp at every scale",
                  "From a business card to a billboard. Keep edges clean at any size.",
                ],
                [
                  "02",
                  "Every path is yours",
                  "Real editable SVG paths. Take your work into your favorite design tool.",
                ],
                [
                  "03",
                  "A more flexible finish",
                  "Tune the palette, smooth your curves, and make space for what matters.",
                ],
              ].map(([n, title, description]) => (
                <article key={n}>
                  <span>{n}</span>
                  <div>
                    <h3>{title}</h3>
                    <p>{description}</p>
                  </div>
                  <ArrowUpRight size={20} />
                </article>
              ))}
            </div>
          </div>
        </section>
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
            SVG and PDF are scalable vector exports. PNG export provides a raster
            image. Photographs and complex textures may lose detail or produce
            large files.
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
          <a className="button secondary" href="#workspace">
            Make your first vector <ArrowUpRight size={16} />
          </a>
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
