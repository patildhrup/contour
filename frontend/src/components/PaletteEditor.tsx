import { useState } from "react";
import { Palette, RotateCcw } from "lucide-react";

export function PaletteEditor({
  colors,
  mapping,
  onChange,
  disabled,
}: {
  colors: string[];
  mapping: Record<string, string>;
  onChange: (mapping: Record<string, string>) => void;
  disabled: boolean;
}) {
  const [selected, setSelected] = useState(0);
  if (!colors.length) return null;
  const color = colors[Math.min(selected, colors.length - 1)];
  const current = mapping[color] || color;
  const used = [...new Set(colors.map((c) => mapping[c] || c))];
  return (
    <section className="palette-editor" aria-labelledby="palette-title">
      <div className="palette-heading">
        <div>
          <h3 id="palette-title">
            <Palette size={16} /> Recolor &amp; merge{" "}
            <span>{used.length} colors</span>
          </h3>
          <p>
            Select a swatch to recolor. Match another color to share its fill;
            paths stay editable.
          </p>
        </div>
        <button
          className="text-button"
          disabled={disabled || !Object.keys(mapping).length}
          onClick={() => onChange({})}
        >
          <RotateCcw size={13} /> Reset palette
        </button>
      </div>
      <fieldset disabled={disabled}>
        <legend className="sr-only">Vector color palette</legend>
        <div className="palette-swatches">
          {colors.map((c, index) => (
            <button
              key={c}
              className="palette-swatch"
              style={{ backgroundColor: mapping[c] || c }}
              aria-label={`Select color ${index + 1}: ${mapping[c] || c}`}
              title={`Color ${index + 1}: ${mapping[c] || c}`}
              aria-pressed={c === color}
              onClick={() => setSelected(index)}
            />
          ))}
        </div>
        <div className="palette-controls">
          <label className="palette-color-label">
            Color {colors.indexOf(color) + 1}
            <input
              type="color"
              aria-label={`Recolor color ${colors.indexOf(color) + 1}`}
              value={current}
              onChange={(event) =>
                onChange({ ...mapping, [color]: event.target.value })
              }
            />
            <output>{current.toUpperCase()}</output>
          </label>
          <label className="palette-merge-label">
            Match a palette color
            <select
              aria-label="Merge selected color into"
              value=""
              onChange={(event) => {
                if (event.target.value)
                  onChange({ ...mapping, [color]: event.target.value });
              }}
            >
              <option value="">Choose a color…</option>
              {used
                .filter((c) => c !== current)
                .map((c) => (
                  <option key={c} value={c}>
                    {c.toUpperCase()}
                  </option>
                ))}
            </select>
          </label>
        </div>
      </fieldset>
      {disabled && (
        <p className="palette-pending">
          Retrace with your current settings to edit this palette.
        </p>
      )}
    </section>
  );
}
