import { SlidersHorizontal, RotateCcw } from "lucide-react";
import { defaults } from "../types";
import type { Settings } from "../types";

export function ConversionSettings({
  value,
  setValue,
  busy,
}: {
  value: Settings;
  setValue: (s: Settings) => void;
  busy: boolean;
}) {
  const update = <K extends keyof Settings>(key: K, val: Settings[K]) =>
    setValue({ ...value, [key]: val });
  return (
    <aside className="settings">
      <div className="settings-title">
        <SlidersHorizontal size={16} />
        <h3>Trace settings</h3>
      </div>
      <fieldset disabled={busy}>
        <legend className="sr-only">Vector tracing and mask settings</legend>
        <div className="curve-presets segmented" aria-label="Curve finish presets">
          <button type="button"
            aria-pressed={value.smoothing === 2 && value.corner === 0 && value.simplify === 2 && value.detail === 2}
            onClick={() => setValue({ ...value, smoothing: 2, corner: 0, simplify: 2, detail: 2 })}>
            Clean curves
          </button>
          <button type="button"
            aria-pressed={value.smoothing === 1 && value.corner === 2 && value.simplify === 0 && value.detail === 3}
            onClick={() => setValue({ ...value, smoothing: 1, corner: 2, simplify: 0, detail: 3 })}>
            Fine detail
          </button>
        </div>
        <p className="setting-help">Clean curves softens contour noise. Fine detail keeps small features and more corners.</p>
        <h4 className="settings-section">01 / Color &amp; curves</h4>
        <label className="setting-label" htmlFor="mode">
          Color mode
        </label>
        <select
          id="mode"
          value={value.mode}
          onChange={(e) => update("mode", e.target.value as Settings["mode"])}
        >
          <option value="color">Full color</option>
          <option value="monochrome">Black & white</option>
        </select>
        <label className="setting-label" htmlFor="colors">
          Palette limit <span>{value.colors}</span>
        </label>
        <input
          id="colors"
          type="range"
          min="2"
          max="64"
          value={value.colors}
          disabled={value.mode === "monochrome"}
          onChange={(e) => update("colors", +e.target.value)}
        />
        <label className="setting-label" htmlFor="color_precision">
          Color precision <span>{value.color_precision}</span>
        </label>
        <input
          id="color_precision"
          type="range"
          min="4"
          max="8"
          value={value.color_precision}
          disabled={value.mode === "monochrome"}
          onChange={(e) => update("color_precision", +e.target.value)}
        />
        <label className="setting-label" htmlFor="detail">
          Detail level
        </label>
        <select
          id="detail"
          value={value.detail}
          onChange={(e) => update("detail", +e.target.value)}
        >
          <option value="1">Low · simpler paths</option>
          <option value="2">Balanced</option>
          <option value="3">High · finer details</option>
        </select>
        <label className="setting-label" htmlFor="smoothing">
          Curve smoothing
        </label>
        <select
          id="smoothing"
          value={value.smoothing}
          onChange={(e) => update("smoothing", +e.target.value)}
        >
          <option value="0">Angular · polygons</option>
          <option value="1">Smooth Bézier</option>
          <option value="2">Extra smooth</option>
        </select>
        <label className="setting-label" htmlFor="corner">
          Corner precision
        </label>
        <select
          id="corner"
          value={value.corner}
          onChange={(e) => update("corner", +e.target.value)}
        >
          <option value="0">Soft · keep curves round</option>
          <option value="1">Balanced</option>
          <option value="2">Sharp geometric corners</option>
        </select>
        <label className="setting-label" htmlFor="speckle">
          Noise reduction <span>{value.speckle} px</span>
        </label>
        <input
          id="speckle"
          type="range"
          min="0"
          max="64"
          value={value.speckle}
          onChange={(e) => update("speckle", +e.target.value)}
        />
        <label className="setting-label" htmlFor="simplify">
          Path simplification
        </label>
        <select
          id="simplify"
          value={value.simplify}
          onChange={(e) => update("simplify", +e.target.value)}
        >
          <option value="0">Minimal · keep contours</option>
          <option value="1">Balanced</option>
          <option value="2">Aggressive</option>
        </select>
        <h4 className="settings-section">02 / Background &amp; mask</h4>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={value.remove_background}
            onChange={(e) => update("remove_background", e.target.checked)}
          />
          Remove near-white background
        </label>
        <label className="setting-label" htmlFor="background_tolerance">
          White tolerance <span>{value.background_tolerance}</span>
        </label>
        <input
          id="background_tolerance"
          type="range"
          min="0"
          max="120"
          value={value.background_tolerance}
          disabled={!value.remove_background}
          onChange={(e) => update("background_tolerance", +e.target.value)}
        />
        <p className="setting-help mask-help">
          Higher tolerance removes darker near-white pixels, including white
          details inside the artwork.
        </p>
        <label className="setting-label" htmlFor="alpha_threshold">
          Opacity cutoff{" "}
          <span>{Math.round((value.alpha_threshold / 255) * 100)}%</span>
        </label>
        <input
          id="alpha_threshold"
          type="range"
          min="1"
          max="254"
          value={value.alpha_threshold}
          onChange={(e) => update("alpha_threshold", +e.target.value)}
        />
        <label className="setting-label" htmlFor="mask_expand">
          Mask expansion{" "}
          <span>
            {value.mask_expand > 0 ? "+" : ""}
            {value.mask_expand} px
          </span>
        </label>
        <input
          id="mask_expand"
          type="range"
          min="-5"
          max="5"
          value={value.mask_expand}
          onChange={(e) => update("mask_expand", +e.target.value)}
        />
        <p className="setting-help">
          Positive expansion fills mask edges; negative values trim them. After
          your first conversion, changes retrace automatically.
        </p>
      </fieldset>
      <button
        className="text-button"
        disabled={busy}
        onClick={() => setValue(defaults)}
      >
        <RotateCcw size={13} /> Restore defaults
      </button>
    </aside>
  );
}
