import { useState, useRef, useEffect, useMemo } from "react";
import type {
  PointerEvent as ReactPointerEvent,
  WheelEvent as ReactWheelEvent,
} from "react";
import {
  Download,
  ZoomIn,
  ZoomOut,
  Maximize,
  RotateCcw,
  SlidersHorizontal,
  ChevronRight,
  ChevronLeft,
  ArrowLeft,
  Palette,
  Layers,
  Square,
  CornerUpRight,
  Eraser,
  Undo2,
  Redo2,
  Check,
  X,
  Upload,
  LoaderCircle,
  Sparkles,
  Home,
  LogOut,
  Eye,
  FileDown,
} from "lucide-react";
import type { Settings, Result } from "../types";
import { exportPdf } from "../utils/exportPdf";
import { useAuth } from "../auth/AuthContext";

type ViewMode = "compare" | "vector" | "outlines";
type ActiveTool = null | "background" | "palette" | "regions" | "geometry" | "corners";

type DashboardProps = {
  file: File | null;
  setFile: (file: File | null) => void;
  settings: Settings;
  setSettings: (next: Settings) => void;
  result: Result | null;
  editedResult: Result | null;
  colors: string[];
  paletteMapping: Record<string, string>;
  setPaletteMapping: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  busy: boolean;
  stale: boolean;
  onConvert: () => void;
  originalUrl: string;
  vectorUrl: string;
  onBackToLanding: () => void;
};

function getApiBase(): string {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") return "";
    if (host.endsWith(".vercel.app") && !envUrl) return "https://contour-backend.vercel.app";
  }
  return envUrl;
}

export function Dashboard({
  file,
  setFile,
  settings,
  setSettings,
  result,
  editedResult,
  colors,
  paletteMapping,
  setPaletteMapping,
  busy,
  stale,
  onConvert,
  originalUrl,
  vectorUrl,
  onBackToLanding,
}: DashboardProps) {
  const { user, signOut } = useAuth();
  const [viewMode, setViewMode] = useState<ViewMode>("compare");
  const [activeTool, setActiveTool] = useState<ActiveTool>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [splitPos, setSplitPos] = useState(50);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [downloadModalOpen, setDownloadModalOpen] = useState(false);
  const [exporting, setExporting] = useState<"png" | "pdf" | "eps" | null>(null);
  const [exportError, setExportError] = useState("");

  // Inspector cursor circle
  const [cursorPos, setCursorPos] = useState<{ x: number; y: number } | null>(null);

  // Corner tool specific state (matching Screenshot 2)
  const [cornerPreset, setCornerPreset] = useState<"auto" | "sharp" | "round">("auto");
  const [sharpThreshold, setSharpThreshold] = useState(settings.corner === 0 ? 105 : settings.corner === 1 ? 70 : 45);
  const [roundRadiusMode, setRoundRadiusMode] = useState<"default" | "relative">("default");
  const [roundRadius, setRoundRadius] = useState(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const dragStartRef = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const isDraggingSplitRef = useRef(false);

  // Reset zoom/pan when file changes
  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, [file]);

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSplitPos(50);
  };

  const handleZoom = (delta: number) => {
    setZoom((z) => Math.min(16, Math.max(0.2, +(z + delta).toFixed(2))));
  };

  // Pointer panning & inspection ring
  const handlePointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    // Never capture pan on interactive targets — pointer capture would
    // swallow their click (e.g. the "Browse files" label opening the picker)
    if (
      (e.target as HTMLElement).closest(
        ".split-handle, button, input, label, a, select, .studio-upload-box",
      )
    )
      return;
    dragStartRef.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    // Inspection circle position inside viewport
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setCursorPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    }

    if (isDraggingSplitRef.current && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const pct = Math.max(5, Math.min(95, ((e.clientX - rect.left) / rect.width) * 100));
      setSplitPos(pct);
      return;
    }

    if (dragStartRef.current) {
      const dx = e.clientX - dragStartRef.current.x;
      const dy = e.clientY - dragStartRef.current.y;
      setPan({ x: dragStartRef.current.px + dx, y: dragStartRef.current.py + dy });
    }
  };

  const handlePointerUp = () => {
    dragStartRef.current = null;
    isDraggingSplitRef.current = false;
  };

  const handleWheel = (e: ReactWheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom((z) => Math.min(16, Math.max(0.2, +(z * factor).toFixed(3))));
  };

  // Quick settings updater
  const updateSetting = <K extends keyof Settings>(key: K, val: Settings[K]) => {
    setSettings({ ...settings, [key]: val });
  };

  // Corner setting presets
  const applyCornerPreset = (preset: "auto" | "sharp" | "round") => {
    setCornerPreset(preset);
    if (preset === "sharp") {
      updateSetting("corner", 0);
      setSharpThreshold(105);
    } else if (preset === "round") {
      updateSetting("corner", 2);
      setSharpThreshold(45);
    } else {
      updateSetting("corner", 1);
      setSharpThreshold(70);
    }
  };

  // Exports
  const handleExportPng = () => {
    if (!editedResult || !vectorUrl) return;
    setExporting("png");
    setExportError("");
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = editedResult.width;
      canvas.height = editedResult.height;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        setExportError("PNG export failed.");
        setExporting(null);
        return;
      }
      ctx.drawImage(img, 0, 0);
      canvas.toBlob((blob) => {
        setExporting(null);
        if (!blob) {
          setExportError("PNG export failed.");
          return;
        }
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = editedResult.filename.replace(/\.svg$/i, ".png");
        link.click();
        setTimeout(() => URL.revokeObjectURL(link.href), 1000);
      });
    };
    img.onerror = () => {
      setExportError("PNG export failed.");
      setExporting(null);
    };
    img.src = vectorUrl;
  };

  const handleExportPdf = async () => {
    if (!editedResult || !vectorUrl) return;
    setExporting("pdf");
    setExportError("");
    try {
      await exportPdf(editedResult, vectorUrl);
    } catch {
      setExportError("PDF export failed.");
    } finally {
      setExporting(null);
    }
  };

  const handleExportEps = async () => {
    if (!editedResult) return;
    setExporting("eps");
    setExportError("");
    try {
      const res = await fetch(`${getApiBase()}/api/export/eps`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ svg: editedResult.svg, filename: editedResult.filename }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as { detail?: string }).detail || "EPS export failed.");
      }
      const blob = await res.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = editedResult.filename.replace(/\.svg$/i, ".eps");
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "EPS export failed.");
    } finally {
      setExporting(null);
    }
  };

  // Color change in palette
  const handleColorChange = (origHex: string, newHex: string) => {
    setPaletteMapping((prev) => ({ ...prev, [origHex.toLowerCase()]: newHex.toLowerCase() }));
  };

  // Compute wireframe outline SVG for "Outlines" mode (matches Screenshot 2)
  const outlineSvg = useMemo(() => {
    if (!editedResult?.svg) return "";
    // Replace fill colors with none, and add distinct colored strokes
    return editedResult.svg
      .replace(/fill="[^"]*"/g, 'fill="none"')
      .replace(/stroke="[^"]*"/g, 'stroke="#22c55e"') // bright green for sharp lines
      .replace(/stroke-width="[^"]*"/g, 'stroke-width="1.2"')
      .replace(/<svg /, '<svg class="outline-svg-rendered" ');
  }, [editedResult?.svg]);

  const totalCornersEstimate = useMemo(() => {
    if (!result?.paths) return 1200;
    return Math.max(120, result.paths * 28);
  }, [result?.paths]);

  const sharpCornersEstimate = useMemo(() => {
    return Math.round(totalCornersEstimate * (settings.corner === 0 ? 0.85 : settings.corner === 1 ? 0.65 : 0.25));
  }, [totalCornersEstimate, settings.corner]);

  const roundCornersEstimate = totalCornersEstimate - sharpCornersEstimate;

  const currentDisplayUrl = originalUrl;

  return (
    <div className="studio-root">
      {/* ── TOP HEADER TOOLBAR (Matching Screenshot 1 & 2) ────────────────── */}
      <header className="studio-topbar">
        <div className="studio-topbar-left">
          <div className="studio-brand" onClick={onBackToLanding} title="Back to Homepage">
            <span className="studio-brand-mark">c</span>
            <span className="studio-brand-name">contour</span>
            <span className="studio-brand-badge">STUDIO</span>
          </div>

          <div className="studio-divider" />

          {/* View mode switcher */}
          <div className="studio-segmented" role="tablist">
            <button
              className={`studio-tab ${viewMode === "compare" ? "active" : ""}`}
              onClick={() => setViewMode("compare")}
              role="tab"
              aria-selected={viewMode === "compare"}
            >
              Compare
            </button>
            <button
              className={`studio-tab ${viewMode === "vector" ? "active" : ""}`}
              onClick={() => setViewMode("vector")}
              role="tab"
              aria-selected={viewMode === "vector"}
            >
              Vector
            </button>
            <button
              className={`studio-tab ${viewMode === "outlines" ? "active" : ""}`}
              onClick={() => setViewMode("outlines")}
              role="tab"
              aria-selected={viewMode === "outlines"}
            >
              Outlines
            </button>
          </div>

          <div className="studio-divider" />

          {/* Zoom & Canvas controls */}
          <div className="studio-canvas-actions">
            <button
              className="studio-icon-btn"
              onClick={() => handleZoom(0.25)}
              title="Zoom in (+)"
            >
              <ZoomIn size={16} />
            </button>
            <button
              className="studio-icon-btn"
              onClick={() => handleZoom(-0.25)}
              title="Zoom out (-)"
            >
              <ZoomOut size={16} />
            </button>
            <button
              className="studio-icon-btn"
              onClick={resetView}
              title="Fit to view ([ ])"
            >
              <Maximize size={15} />
            </button>
            <button
              className="studio-icon-btn studio-zoom-reset"
              onClick={() => setZoom(1)}
              title="Actual size 1:1"
            >
              1:1
            </button>
            <div className="studio-zoom-level">{Math.round(zoom * 100)}%</div>
          </div>
        </div>

        <div className="studio-topbar-right">
          {busy && (
            <div className="studio-status-chip busy">
              <LoaderCircle size={14} className="spin" />
              <span>Tracing…</span>
            </div>
          )}

          {stale && !busy && (
            <button className="studio-retrace-chip" onClick={onConvert}>
              <Sparkles size={13} />
              <span>Update vector</span>
            </button>
          )}

          <label
            className="studio-upload-btn"
            title="Upload a new image"
          >
            <Upload size={15} />
            <span>Upload</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,image/bmp,image/gif"
              style={{ display: "none" }}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) setFile(f);
                e.target.value = "";
              }}
            />
          </label>

          <button
            className="studio-home-btn"
            onClick={onBackToLanding}
            title="Return to website home"
          >
            <Home size={15} />
            <span>Home</span>
          </button>

          {user && (
            <div className="studio-user-chip" title={user.email || ""}>
              <span className="studio-user-initial">
                {(user.displayName?.[0] || user.email?.[0] || "U").toUpperCase()}
              </span>
              <button
                className="studio-signout-btn"
                onClick={() => signOut()}
                title="Sign out"
              >
                <LogOut size={13} />
              </button>
            </div>
          )}

          <button
            className="studio-download-btn"
            onClick={() => setDownloadModalOpen(true)}
            disabled={!editedResult || busy}
          >
            <Download size={15} />
            <span>Download</span>
          </button>
        </div>
      </header>

      {/* ── MAIN STUDIO WORKSPACE ────────────────────────────────────────── */}
      <div className="studio-body">
        {/* ── LEFT SIDEBAR ("Refine result") ────────────────────────────── */}
        <aside className={`studio-sidebar ${sidebarCollapsed ? "collapsed" : ""}`}>
          {!activeTool ? (
            /* Main Tools Menu (Matching Screenshot 1) */
            <div className="studio-sidebar-content">
              <div className="studio-sidebar-header">
                <h2>Refine result</h2>
                <button
                  className="studio-collapse-btn"
                  onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                  title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                >
                  <ChevronLeft size={16} />
                </button>
              </div>

              <nav className="studio-tool-list" aria-label="Vector refinement tools">
                {/* 1. Background */}
                <button
                  className="studio-tool-card"
                  onClick={() => setActiveTool("background")}
                >
                  <div className="studio-tool-icon">
                    <Eraser size={18} />
                  </div>
                  <div className="studio-tool-info">
                    <div className="studio-tool-title">
                      <span>Background</span>
                      {settings.remove_background && (
                        <span className="studio-badge-subtle">ON</span>
                      )}
                    </div>
                    <p className="studio-tool-desc">
                      Remove the background and correct what to keep.
                    </p>
                  </div>
                  <ChevronRight size={16} className="studio-tool-chevron" />
                </button>

                {/* 2. Palette */}
                <button
                  className="studio-tool-card"
                  onClick={() => setActiveTool("palette")}
                >
                  <div className="studio-tool-icon palette-icon">
                    <Palette size={18} />
                  </div>
                  <div className="studio-tool-info">
                    <div className="studio-tool-title">
                      <span>Palette</span>
                      <span className="studio-badge">{colors.length || settings.colors}</span>
                    </div>
                    <p className="studio-tool-desc">
                      Choose and edit the colors used throughout your image.
                    </p>
                  </div>
                  <ChevronRight size={16} className="studio-tool-chevron" />
                </button>

                {/* 3. Regions */}
                <button
                  className="studio-tool-card"
                  onClick={() => setActiveTool("regions")}
                >
                  <div className="studio-tool-icon">
                    <Square size={18} />
                  </div>
                  <div className="studio-tool-info">
                    <div className="studio-tool-title">
                      <span>Regions</span>
                    </div>
                    <p className="studio-tool-desc">
                      Recolor, merge, or remove individual regions.
                    </p>
                  </div>
                  <ChevronRight size={16} className="studio-tool-chevron" />
                </button>

                {/* 4. Geometry */}
                <button
                  className="studio-tool-card"
                  onClick={() => setActiveTool("geometry")}
                >
                  <div className="studio-tool-icon">
                    <Layers size={18} />
                  </div>
                  <div className="studio-tool-info">
                    <div className="studio-tool-title">
                      <span>Geometry</span>
                    </div>
                    <p className="studio-tool-desc">
                      Symmetries, repeating shapes, and simplified shapes.
                    </p>
                  </div>
                  <ChevronRight size={16} className="studio-tool-chevron" />
                </button>

                {/* 5. Corners (Matching Screenshot 1 & 2) */}
                <button
                  className="studio-tool-card active-pulse"
                  onClick={() => setActiveTool("corners")}
                >
                  <div className="studio-tool-icon">
                    <CornerUpRight size={18} />
                  </div>
                  <div className="studio-tool-info">
                    <div className="studio-tool-title">
                      <span>Corners</span>
                      <span className="studio-badge">{totalCornersEstimate.toLocaleString()}</span>
                    </div>
                    <p className="studio-tool-desc">
                      Sharpen or round corners individually or throughout the image
                    </p>
                  </div>
                  <ChevronRight size={16} className="studio-tool-chevron" />
                </button>
              </nav>

              {/* Bottom Actions */}
              <div className="studio-sidebar-footer">
                <div className="studio-history-actions">
                  <button className="studio-history-btn" title="Undo change" disabled>
                    <Undo2 size={15} />
                    <span>Undo</span>
                  </button>
                  <button className="studio-history-btn" title="Redo change" disabled>
                    <Redo2 size={15} />
                    <span>Redo</span>
                  </button>
                </div>
                <button
                  className="studio-sidebar-download-btn"
                  onClick={() => setDownloadModalOpen(true)}
                  disabled={!editedResult || busy}
                >
                  <Download size={16} />
                  <span>Download</span>
                </button>
              </div>
            </div>
          ) : (
            /* Sub-Tool Panels (e.g. Corners in Screenshot 2) */
            <div className="studio-sidebar-content subpanel">
              <div className="studio-subpanel-header">
                <button
                  className="studio-back-link"
                  onClick={() => setActiveTool(null)}
                >
                  <ArrowLeft size={15} />
                  <span>All tools</span>
                </button>
              </div>

              {/* ── CORNERS SUBPANEL (Exact Match to Screenshot 2) ── */}
              {activeTool === "corners" && (
                <div className="studio-tool-detail">
                  <h2 className="studio-detail-title">Corners</h2>
                  <div className="studio-stats-row">
                    <span className="stat-total">{totalCornersEstimate} total</span>
                    <span className="stat-sharp">◆ {sharpCornersEstimate} sharp</span>
                    <span className="stat-round">● {roundCornersEstimate} rounded</span>
                  </div>

                  <div className="studio-radio-group">
                    <label className="studio-radio-label">
                      <input
                        type="radio"
                        name="cornerPreset"
                        checked={cornerPreset === "auto"}
                        onChange={() => applyCornerPreset("auto")}
                      />
                      <span>Automatic</span>
                    </label>
                    <label className="studio-radio-label">
                      <input
                        type="radio"
                        name="cornerPreset"
                        checked={cornerPreset === "sharp"}
                        onChange={() => applyCornerPreset("sharp")}
                      />
                      <span>Make all corners sharp</span>
                    </label>
                    <label className="studio-radio-label">
                      <input
                        type="radio"
                        name="cornerPreset"
                        checked={cornerPreset === "round"}
                        onChange={() => applyCornerPreset("round")}
                      />
                      <span>Make all corners round</span>
                    </label>
                  </div>

                  <div className="studio-control-block">
                    <div className="studio-control-header">
                      <label>Sharp corners</label>
                      <div className="studio-value-box">
                        <input
                          type="number"
                          value={sharpThreshold}
                          onChange={(e) => {
                            const val = +e.target.value;
                            setSharpThreshold(val);
                            updateSetting("corner", val > 80 ? 0 : val > 55 ? 1 : 2);
                          }}
                        />
                        <button
                          className="studio-reset-btn"
                          onClick={() => {
                            setSharpThreshold(70);
                            updateSetting("corner", 1);
                          }}
                          title="Reset"
                        >
                          <RotateCcw size={12} />
                        </button>
                      </div>
                    </div>
                    <input
                      type="range"
                      min="30"
                      max="120"
                      value={sharpThreshold}
                      onChange={(e) => {
                        const val = +e.target.value;
                        setSharpThreshold(val);
                        updateSetting("corner", val > 80 ? 0 : val > 55 ? 1 : 2);
                      }}
                      className="studio-range"
                    />
                    <div className="studio-range-labels">
                      <span>Fewer sharp</span>
                      <span>More sharp</span>
                    </div>
                  </div>

                  <div className="studio-control-block">
                    <label className="studio-section-label">Round corner radius</label>
                    <div className="studio-radio-group">
                      <label className="studio-radio-label">
                        <input
                          type="radio"
                          name="roundRadiusMode"
                          checked={roundRadiusMode === "default"}
                          onChange={() => {
                            setRoundRadiusMode("default");
                            setRoundRadius(0);
                            updateSetting("smoothing", 1);
                          }}
                        />
                        <span>Default</span>
                      </label>
                      <div className="studio-radio-with-box">
                        <label className="studio-radio-label">
                          <input
                            type="radio"
                            name="roundRadiusMode"
                            checked={roundRadiusMode === "relative"}
                            onChange={() => setRoundRadiusMode("relative")}
                          />
                          <span>Relative</span>
                        </label>
                        <div className="studio-value-box">
                          <input
                            type="number"
                            value={roundRadius}
                            onChange={(e) => {
                              const val = +e.target.value;
                              setRoundRadius(val);
                              updateSetting("smoothing", val > 0 ? 2 : val < 0 ? 0 : 1);
                            }}
                          />
                          <button
                            className="studio-reset-btn"
                            onClick={() => {
                              setRoundRadius(0);
                              updateSetting("smoothing", 1);
                            }}
                            title="Reset"
                          >
                            <RotateCcw size={12} />
                          </button>
                        </div>
                      </div>
                    </div>
                    <input
                      type="range"
                      min="-2"
                      max="2"
                      value={roundRadius}
                      onChange={(e) => {
                        const val = +e.target.value;
                        setRoundRadius(val);
                        setRoundRadiusMode("relative");
                        updateSetting("smoothing", val > 0 ? 2 : val < 0 ? 0 : 1);
                      }}
                      className="studio-range"
                    />
                    <div className="studio-range-labels">
                      <span>Sharper</span>
                      <span>Rounder</span>
                    </div>
                  </div>

                  <button
                    className="studio-btn-reset-all"
                    onClick={() => {
                      applyCornerPreset("auto");
                      setRoundRadiusMode("default");
                      setRoundRadius(0);
                    }}
                  >
                    <RotateCcw size={13} />
                    <span>Reset all</span>
                  </button>
                </div>
              )}

              {/* ── PALETTE SUBPANEL ── */}
              {activeTool === "palette" && (
                <div className="studio-tool-detail">
                  <h2 className="studio-detail-title">Palette</h2>
                  <p className="studio-tool-hint">
                    Click any swatch below to remap its color, or adjust palette size.
                  </p>

                  <div className="studio-swatches-grid">
                    {colors.map((color) => {
                      const lower = color.toLowerCase();
                      const current = paletteMapping[lower] || lower;
                      return (
                        <div key={color} className="studio-swatch-item">
                          <input
                            type="color"
                            value={current}
                            onChange={(e) => handleColorChange(lower, e.target.value)}
                            className="studio-color-picker"
                            title={`Remap ${color}`}
                          />
                          <span className="studio-swatch-hex">{current.toUpperCase()}</span>
                        </div>
                      );
                    })}
                  </div>

                  {Object.keys(paletteMapping).length > 0 && (
                    <button
                      className="studio-text-link"
                      onClick={() => setPaletteMapping({})}
                    >
                      Reset all color edits
                    </button>
                  )}

                  <div className="studio-control-block" style={{ marginTop: 20 }}>
                    <div className="studio-control-header">
                      <label>Color limit</label>
                      <span className="studio-value-pill">{settings.colors} colors</span>
                    </div>
                    <input
                      type="range"
                      min="2"
                      max="64"
                      value={settings.colors}
                      onChange={(e) => updateSetting("colors", +e.target.value)}
                      className="studio-range"
                    />
                  </div>

                  <div className="studio-control-block">
                    <div className="studio-control-header">
                      <label>Color precision</label>
                      <span className="studio-value-pill">{settings.color_precision}</span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="8"
                      value={settings.color_precision}
                      onChange={(e) => updateSetting("color_precision", +e.target.value)}
                      className="studio-range"
                    />
                  </div>
                </div>
              )}

              {/* ── BACKGROUND SUBPANEL ── */}
              {activeTool === "background" && (
                <div className="studio-tool-detail">
                  <h2 className="studio-detail-title">Background</h2>
                  <div className="studio-toggle-row">
                    <span>Remove white/light background</span>
                    <input
                      type="checkbox"
                      checked={settings.remove_background}
                      onChange={(e) => updateSetting("remove_background", e.target.checked)}
                      className="studio-checkbox"
                    />
                  </div>

                  {settings.remove_background && (
                    <div className="studio-control-block">
                      <div className="studio-control-header">
                        <label>Tolerance</label>
                        <span className="studio-value-pill">{settings.background_tolerance}</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="120"
                        value={settings.background_tolerance}
                        onChange={(e) => updateSetting("background_tolerance", +e.target.value)}
                        className="studio-range"
                      />
                    </div>
                  )}

                  <div className="studio-control-block">
                    <div className="studio-control-header">
                      <label>Opacity cutoff</label>
                      <span className="studio-value-pill">{Math.round((settings.alpha_threshold / 255) * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="254"
                      value={settings.alpha_threshold}
                      onChange={(e) => updateSetting("alpha_threshold", +e.target.value)}
                      className="studio-range"
                    />
                  </div>

                  <div className="studio-control-block">
                    <div className="studio-control-header">
                      <label>Mask expansion</label>
                      <span className="studio-value-pill">
                        {settings.mask_expand > 0 ? "+" : ""}{settings.mask_expand} px
                      </span>
                    </div>
                    <input
                      type="range"
                      min="-5"
                      max="5"
                      value={settings.mask_expand}
                      onChange={(e) => updateSetting("mask_expand", +e.target.value)}
                      className="studio-range"
                    />
                  </div>
                </div>
              )}

              {/* ── REGIONS SUBPANEL ── */}
              {activeTool === "regions" && (
                <div className="studio-tool-detail">
                  <h2 className="studio-detail-title">Regions</h2>
                  <div className="studio-control-block">
                    <div className="studio-control-header">
                      <label>Noise filter (speckle)</label>
                      <span className="studio-value-pill">{settings.speckle} px²</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="64"
                      value={settings.speckle}
                      onChange={(e) => updateSetting("speckle", +e.target.value)}
                      className="studio-range"
                    />
                    <div className="studio-range-labels">
                      <span>Keep fine detail</span>
                      <span>Remove dust/artifacts</span>
                    </div>
                  </div>

                  <div className="studio-control-block">
                    <div className="studio-control-header">
                      <label>Detail level</label>
                      <span className="studio-value-pill">
                        {settings.detail === 1 ? "Low" : settings.detail === 2 ? "Balanced" : "High"}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="3"
                      value={settings.detail}
                      onChange={(e) => updateSetting("detail", +e.target.value)}
                      className="studio-range"
                    />
                  </div>

                  <div className="studio-control-block">
                    <div className="studio-control-header">
                      <label>Path simplification</label>
                      <span className="studio-value-pill">
                        {settings.simplify === 0 ? "Exact" : settings.simplify === 1 ? "Balanced" : "High"}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      value={settings.simplify}
                      onChange={(e) => updateSetting("simplify", +e.target.value)}
                      className="studio-range"
                    />
                  </div>
                </div>
              )}

              {/* ── GEOMETRY SUBPANEL ── */}
              {activeTool === "geometry" && (
                <div className="studio-tool-detail">
                  <h2 className="studio-detail-title">Geometry</h2>
                  <div className="studio-control-block">
                    <label className="studio-section-label">Color mode</label>
                    <div className="studio-segmented" style={{ width: "100%", marginTop: 8 }}>
                      <button
                        className={`studio-tab ${settings.mode === "color" ? "active" : ""}`}
                        onClick={() => updateSetting("mode", "color")}
                        style={{ flex: 1 }}
                      >
                        Full Color
                      </button>
                      <button
                        className={`studio-tab ${settings.mode === "monochrome" ? "active" : ""}`}
                        onClick={() => updateSetting("mode", "monochrome")}
                        style={{ flex: 1 }}
                      >
                        Monochrome
                      </button>
                    </div>
                  </div>

                  <div className="studio-control-block">
                    <div className="studio-control-header">
                      <label>Curve smoothing</label>
                      <span className="studio-value-pill">
                        {settings.smoothing === 0 ? "Sharp/Exact" : settings.smoothing === 1 ? "Smooth" : "Artistic"}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      value={settings.smoothing}
                      onChange={(e) => updateSetting("smoothing", +e.target.value)}
                      className="studio-range"
                    />
                  </div>
                </div>
              )}

              {/* Retrace button in subpanel */}
              <button
                className="studio-sidebar-download-btn"
                style={{ marginTop: "auto" }}
                onClick={onConvert}
                disabled={busy}
              >
                {busy ? <LoaderCircle size={15} className="spin" /> : <Sparkles size={15} />}
                <span>{busy ? "Tracing…" : "Apply & Retrace"}</span>
              </button>
            </div>
          )}
        </aside>

        {/* Floating re-expand handle — the sidebar's own toggle hides with it */}
        {sidebarCollapsed && (
          <button
            className="studio-expand-btn"
            onClick={() => setSidebarCollapsed(false)}
            title="Expand sidebar"
            aria-label="Expand sidebar"
          >
            <ChevronRight size={16} />
          </button>
        )}

        {/* ── MAIN CANVAS AREA (Matching Screenshot 1 & 2) ────────────────── */}
        <main
          className="studio-canvas"
          ref={containerRef}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onWheel={handleWheel}
        >
          {!file ? (
            /* Upload Dropzone inside Studio — real drag & drop target */
            <div
              className="studio-empty-state"
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                const f = e.dataTransfer.files?.[0];
                if (f) setFile(f);
              }}
            >
              <div
                className={`studio-upload-box ${isDragging ? "dragging" : ""}`}
              >
                <Upload size={38} className="studio-upload-icon" />
                <h3>Drop an image here to vectorize</h3>
                <p>Supports PNG, JPG, WebP, BMP, GIF up to 20MB</p>
                <div className="studio-upload-actions">
                  <label className="studio-primary-btn">
                    Browse files
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/bmp,image/gif"
                      style={{ display: "none" }}
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) setFile(f);
                        e.target.value = "";
                      }}
                    />
                  </label>
                </div>
              </div>
            </div>
          ) : (
            /* Active Image / Vector Viewer */
            <div className="studio-viewport">
              {/* Inspection Magnifier Circle (Matches Screenshots!) */}
              {cursorPos && (
                <div
                  className="studio-lens-circle"
                  style={{
                    left: `${cursorPos.x}px`,
                    top: `${cursorPos.y}px`,
                  }}
                />
              )}

              {/* Mode 1: COMPARE — Original & Contour on separate planes */}
              {viewMode === "compare" && (
                <div
                  className="studio-dual-container"
                  style={{
                    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                  }}
                >
                  <div className="studio-plane">
                    <div className="studio-plane-card">
                      <img
                        src={currentDisplayUrl}
                        alt="Original raster"
                        draggable={false}
                      />
                    </div>
                    <div className="studio-plane-label">Original</div>
                  </div>

                  <div className="studio-plane">
                    <div className="studio-plane-card">
                      {editedResult?.svg ? (
                        <div
                          className="studio-svg-render"
                          dangerouslySetInnerHTML={{ __html: editedResult.svg }}
                        />
                      ) : (
                        <div className="studio-loading-placeholder">
                          {busy ? "Tracing contours…" : "Awaiting trace…"}
                        </div>
                      )}
                    </div>
                    <div className="studio-plane-label">Contour</div>
                  </div>
                </div>
              )}

              {/* Mode 2: VECTOR (Pure Vector View) */}
              {viewMode === "vector" && (
                <div
                  className="studio-single-container"
                  style={{
                    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                  }}
                >
                  {editedResult?.svg ? (
                    <div
                      className="studio-svg-render"
                      dangerouslySetInnerHTML={{ __html: editedResult.svg }}
                    />
                  ) : (
                    <div className="studio-loading-placeholder">Processing vector…</div>
                  )}
                  <div className="studio-badge-overlay right">Contour Result</div>
                </div>
              )}

              {/* Mode 3: OUTLINES (Wireframe Mode - Matching Screenshot 2!) */}
              {viewMode === "outlines" && (
                <div
                  className="studio-outlines-container"
                  style={{
                    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                  }}
                >
                  {/* Faded original underneath */}
                  <img
                    src={currentDisplayUrl}
                    alt="Original reference"
                    className="outlines-background-img"
                    draggable={false}
                  />
                  {/* Vector contours rendered as colored wireframes */}
                  <div
                    className="studio-outlines-render"
                    dangerouslySetInnerHTML={{ __html: outlineSvg }}
                  />
                  <div className="studio-badge-overlay left">Outlines & Corners Mode</div>
                </div>
              )}

              {/* Bottom Resolution Badge (e.g. 563 x 557 px from Screenshot 1) */}
              {editedResult && (
                <div className="studio-resolution-pill">
                  {editedResult.width} × {editedResult.height} px · {editedResult.paths} paths
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* ── DOWNLOAD MODAL / DRAWER ───────────────────────────────────────── */}
      {downloadModalOpen && editedResult && (
        <div className="studio-modal-overlay" onClick={() => setDownloadModalOpen(false)}>
          <div className="studio-download-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <FileDown size={18} />
                <h3>Export Vector Graphics</h3>
              </div>
              <button
                className="modal-close-btn"
                onClick={() => setDownloadModalOpen(false)}
              >
                <X size={16} />
              </button>
            </div>

            <p className="modal-subtitle">
              Choose your target format. All vector exports maintain infinite scalability and clean Bézier curves.
            </p>

            <div className="export-grid">
              {/* SVG */}
              <a
                className="export-card primary"
                href={vectorUrl}
                download={editedResult.filename}
                onClick={() => setDownloadModalOpen(false)}
              >
                <div className="export-badge">RECOMMENDED</div>
                <div className="export-format">SVG</div>
                <div className="export-desc">Standard Scalable Vector Graphics for web, design, and apps.</div>
                <div className="export-action">
                  <Download size={14} /> Download SVG
                </div>
              </a>

              {/* PDF */}
              <button
                className="export-card"
                onClick={handleExportPdf}
                disabled={!!exporting}
              >
                <div className="export-format">PDF</div>
                <div className="export-desc">Native vector PDF document with exact curves for print & publishing.</div>
                <div className="export-action">
                  {exporting === "pdf" ? <LoaderCircle size={14} className="spin" /> : <Download size={14} />}
                  <span>{exporting === "pdf" ? "Exporting…" : "Download PDF"}</span>
                </div>
              </button>

              {/* EPS */}
              <button
                className="export-card"
                onClick={handleExportEps}
                disabled={!!exporting}
              >
                <div className="export-format">EPS</div>
                <div className="export-desc">PostScript format for Adobe Illustrator, CorelDRAW, CNC & Plotters.</div>
                <div className="export-action">
                  {exporting === "eps" ? <LoaderCircle size={14} className="spin" /> : <Download size={14} />}
                  <span>{exporting === "eps" ? "Exporting…" : "Download EPS"}</span>
                </div>
              </button>

              {/* PNG */}
              <button
                className="export-card"
                onClick={handleExportPng}
                disabled={!!exporting}
              >
                <div className="export-format">PNG</div>
                <div className="export-desc">Clean raster export rendered at original resolution with transparency.</div>
                <div className="export-action">
                  {exporting === "png" ? <LoaderCircle size={14} className="spin" /> : <Download size={14} />}
                  <span>{exporting === "png" ? "Exporting…" : "Download PNG"}</span>
                </div>
              </button>
            </div>

            {exportError && (
              <div className="modal-error" role="alert">
                {exportError}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

