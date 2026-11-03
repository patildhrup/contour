import { useEffect, useRef, useState } from "react";
import type {
  PointerEvent as ReactPointerEvent,
  WheelEvent as ReactWheelEvent,
} from "react";
import { Layers, Move, Minus, Plus, Maximize, RotateCcw } from "lucide-react";
import { ImagePreview } from "./ImagePreview";

export function BeforeAfterViewer({
  original,
  vector,
  sample,
  svg,
  width,
  height,
}: {
  original: string;
  vector: string;
  sample: string;
  svg: string;
  width?: number;
  height?: number;
}) {
  const [mode, setMode] = useState<"side" | "slider">("side");
  const [bg, setBg] = useState("check");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [split, setSplit] = useState(50);
  const start = useRef<{ x: number; y: number; px: number; py: number } | null>(
    null,
  );
  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, [original]);
  const reset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };
  const transform = {
    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
  };
  const pointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("input,button")) return;
    start.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onWheel = (e: ReactWheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom((z) => Math.min(16, Math.max(0.25, +(z * factor).toFixed(3))));
  };
  const source = original || sample;
  return (
    <section className="viewer" aria-label="Image comparison">
      <div className="viewer-top">
        <div className="segmented">
          <button
            aria-pressed={mode === "side"}
            onClick={() => setMode("side")}
          >
            Side by side
          </button>
          <button
            aria-pressed={mode === "slider"}
            onClick={() => setMode("slider")}
          >
            Compare
          </button>
        </div>
        <div className="backgrounds" aria-label="Preview background">
          {["check", "light", "dark"].map((b) => (
            <button
              key={b}
              className={`swatch ${b}`}
              aria-label={`${b === "check" ? "Transparent checkerboard" : b} background`}
              aria-pressed={bg === b}
              onClick={() => setBg(b)}
            />
          ))}
        </div>
      </div>
      <div
        className={`preview-area ${bg} ${mode}`}
        tabIndex={0}
        role="group"
        aria-label="Image preview. Use arrow keys to pan, plus and minus to zoom, and zero to reset."
        onKeyDown={(e) => {
          if (e.target !== e.currentTarget) return;
          const directions: Record<string, [number, number]> = {
            ArrowLeft: [-20, 0],
            ArrowRight: [20, 0],
            ArrowUp: [0, -20],
            ArrowDown: [0, 20],
          };
          if (directions[e.key]) {
            e.preventDefault();
            const [x, y] = directions[e.key];
            setPan((p) => ({ x: p.x + x, y: p.y + y }));
          } else if (e.key === "+" || e.key === "=") {
            e.preventDefault();
            setZoom((z) => Math.min(16, z + 0.25));
          } else if (e.key === "-") {
            e.preventDefault();
            setZoom((z) => Math.max(0.25, z - 0.25));
          } else if (e.key === "0") reset();
        }}
        onWheel={onWheel}
        onPointerDown={pointerDown}
        onPointerMove={(e) => {
          if (start.current)
            setPan({
              x: start.current.px + e.clientX - start.current.x,
              y: start.current.py + e.clientY - start.current.y,
            });
        }}
        onPointerUp={() => {
          start.current = null;
        }}
        onPointerCancel={() => {
          start.current = null;
        }}
      >
        {mode === "side" ? (
          <>
            <div className="preview-half">
              <span className="preview-tag">
                {original ? "ORIGINAL" : "SAMPLE / RASTER"}
              </span>
              {source && (
                <ImagePreview
                  url={source}
                  label="Original raster image"
                  transform={transform}
                  raster
                />
              )}
            </div>
            <div className="preview-half">
              <span className="preview-tag">
                {vector ? "VECTOR / SVG" : "VECTOR PREVIEW"}
              </span>
              {vector ? (
                <ImagePreview
                  url={vector}
                  label="Converted vector image"
                  transform={transform}
                  markup={svg}
                />
              ) : (
                <div className="awaiting">
                  <Layers size={27} />
                  <strong>Your next dimension.</strong>
                  <span>
                    {original
                      ? "Convert your image to see the result here."
                      : "Upload an image or try the sample to begin."}
                  </span>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="slider-stage">
            {source && (
              <ImagePreview
                url={source}
                label="Original raster image"
                transform={transform}
                raster
              />
            )}
            {vector ? (
              <div
                className={`slider-overlay ${bg}`}
                style={{ clipPath: `inset(0 0 0 ${split}%)` }}
              >
                <ImagePreview
                  url={vector}
                  label="Converted vector image"
                  transform={transform}
                  markup={svg}
                />
              </div>
            ) : (
              <span className="slider-empty">
                Convert an image to compare the result
              </span>
            )}
            <div className="divider" style={{ left: `${split}%` }}>
              <span>↔</span>
            </div>
            <input
              className="compare-range"
              aria-label="Before and after comparison position"
              type="range"
              min="0"
              max="100"
              value={split}
              onChange={(e) => setSplit(+e.target.value)}
            />
            <span className="preview-tag">ORIGINAL</span>
            <span className="preview-tag right-tag">VECTOR</span>
          </div>
        )}
      </div>
      <div className="viewer-bottom">
        <span>
          <Move size={13} /> Drag to pan
          {width && height ? (
            <em className="output-size">
              {width} × {height} px
            </em>
          ) : null}
        </span>
        <div className="zoom-controls">
          <button
            aria-label="Zoom out"
            onClick={() =>
              setZoom((z) => Math.max(0.25, +(z / 1.25).toFixed(3)))
            }
          >
            <Minus size={15} />
          </button>
          <output aria-label="Zoom level">{Math.round(zoom * 100)}%</output>
          <button
            aria-label="Zoom in"
            onClick={() => setZoom((z) => Math.min(16, +(z * 1.25).toFixed(3)))}
          >
            <Plus size={15} />
          </button>
          <i />
          <button
            aria-label="Fit to screen"
            title="Fit to screen"
            onClick={reset}
          >
            <Maximize size={15} />
          </button>
          <button aria-label="Reset view" title="Reset view" onClick={reset}>
            <RotateCcw size={15} />
          </button>
        </div>
      </div>
    </section>
  );
}
