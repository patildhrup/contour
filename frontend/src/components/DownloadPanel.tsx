import { useState } from "react";
import { Check, Download, ShieldCheck, LoaderCircle } from "lucide-react";
import type { Result } from "../types";
import { exportPdf } from "../utils/exportPdf";

export function DownloadPanel({
  result,
  url,
  disabled = false,
}: {
  result: Result | null;
  url: string;
  disabled?: boolean;
}) {
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState<"png" | "pdf" | "eps" | null>(null);

  const exportPng = () => {
    if (!result || !url || exporting || disabled) return;
    setError("");
    setExporting("png");
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = result.width;
        canvas.height = result.height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          setError("PNG export failed. Please download the SVG instead.");
          setExporting(null);
          return;
        }
        ctx.drawImage(img, 0, 0);
        canvas.toBlob((blob) => {
          setExporting(null);
          if (!blob) {
            setError("PNG export failed. Please download the SVG instead.");
            return;
          }
          const link = document.createElement("a");
          link.href = URL.createObjectURL(blob);
          link.download = result.filename.replace(/\.svg$/i, ".png");
          link.click();
          setTimeout(() => URL.revokeObjectURL(link.href), 1000);
        });
      } catch {
        setError("PNG export failed. Please download the SVG instead.");
        setExporting(null);
      }
    };
    img.onerror = () => {
      setError("PNG export failed. Please download the SVG instead.");
      setExporting(null);
    };
    img.src = url;
  };

  const handleExportPdf = async () => {
    if (!result || !url || exporting || disabled) return;
    setError("");
    setExporting("pdf");
    try {
      await exportPdf(result, url);
    } catch {
      setError("PDF export failed. Please download the SVG instead.");
    } finally {
      setExporting(null);
    }
  };

  const exportEps = async () => {
    if (!result || exporting || disabled) return;
    setError("");
    setExporting("eps");
    try {
      const apiBase = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");
      const res = await fetch(`${apiBase}/api/export/eps`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ svg: result.svg, filename: result.filename }),
      });
      if (!res.ok) throw new Error("EPS export failed");
      const blob = await res.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = result.filename.replace(/\.svg$/i, ".eps");
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    } catch {
      setError("EPS export failed. Please download the SVG instead.");
    } finally {
      setExporting(null);
    }
  };

  if (!result)
    return (
      <div className="download-empty">
        <ShieldCheck size={15} /> No account. No permanent uploads. Just your
        vector.
      </div>
    );

  return (
    <div className={`download-panel ${disabled ? "download-pending" : ""}`}>
      <div>
        <strong>
          <Check size={16} />{" "}
          {disabled
            ? "Downloads paused while settings update."
            : "Your vector is ready."}
        </strong>
        <p>
          {result.paths.toLocaleString()} paths · {result.width} ×{" "}
          {result.height} · {(result.elapsed_ms / 1000).toFixed(1)}s
        </p>
      </div>
      <div className="download-actions">
        <button
          type="button"
          className="button secondary"
          onClick={handleExportPdf}
          disabled={!!exporting || disabled}
          title="Download vector as PDF document"
        >
          {exporting === "pdf" ? (
            <LoaderCircle size={15} className="spin" />
          ) : (
            <Download size={15} />
          )}
          PDF <span>(vector)</span>
        </button>
        <button
          type="button"
          className="button secondary"
          onClick={exportEps}
          disabled={!!exporting || disabled}
          title="Download vector as EPS (PostScript)"
        >
          {exporting === "eps" ? (
            <LoaderCircle size={15} className="spin" />
          ) : (
            <Download size={15} />
          )}
          EPS <span>(vector)</span>
        </button>
        <button
          type="button"
          className="button secondary"
          onClick={exportPng}
          disabled={!!exporting || disabled}
          title="Download vector rasterized as PNG"
        >
          {exporting === "png" ? (
            <LoaderCircle size={15} className="spin" />
          ) : (
            <Download size={15} />
          )}
          PNG <span>(raster)</span>
        </button>
        <a
          className="button primary"
          href={disabled ? undefined : url}
          aria-disabled={disabled}
          tabIndex={disabled ? -1 : 0}
          onClick={(event) => {
            if (disabled) event.preventDefault();
          }}
          download={result.filename}
          title="Download genuine SVG vector file"
        >
          <Download size={15} /> SVG
        </a>
      </div>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
