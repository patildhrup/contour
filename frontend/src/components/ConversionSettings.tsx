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
          Color count <span>{value.colors}</span>
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
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={value.remove_background}
            onChange={(e) => update("remove_background", e.target.checked)}
          />
          Remove near-white background
        </label>
        <p className="setting-help">
          Changing a control retraces the image. Transparency is traced as a
          binary mask.
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
