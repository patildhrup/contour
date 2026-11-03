import { createElement, useMemo } from "react";
import type { CSSProperties, ReactNode } from "react";

function vectorMarkup(markup: string): ReactNode {
  const doc = new DOMParser().parseFromString(markup, "image/svg+xml");
  if (doc.querySelector("parsererror") || doc.documentElement.localName !== "svg") return null;
  // Reconstruct only the tracing engine's geometry. Do not inject server markup
  // or copy scripts, event handlers, foreign content or external references.
  const geometry = (element: Element, key: number): ReactNode => {
    const tag = element.localName;
    if (!["svg", "g", "path"].includes(tag)) return null;
    const props: Record<string, string | number> = { key };
    const camel = { "fill-rule": "fillRule", "stroke-width": "strokeWidth", "stroke-linejoin": "strokeLinejoin" };
    for (const attr of ["d", "viewBox", "width", "height", "transform", "fill", "fill-rule",
      "stroke", "stroke-width", "stroke-linejoin"]) {
      const value = element.getAttribute(attr);
      if (!value || /url\s*\(/i.test(value)) continue;
      props[camel[attr as keyof typeof camel] ?? attr] = value;
    }
    return createElement(tag, props, ...Array.from(element.children).map(geometry));
  };
  return geometry(doc.documentElement, 0);
}

export function ImagePreview({
  url,
  label,
  transform,
  raster = false,
  markup,
}: {
  url: string;
  label: string;
  transform?: CSSProperties;
  raster?: boolean;
  markup?: string;
}) {
  const vector = useMemo(() => markup ? vectorMarkup(markup) : null, [markup]);
  return (
    <div className="image-stage">
      {vector ? (
        <div className="svg-frame" style={transform} role="img" aria-label={label}>
          {vector}
        </div>
      ) : <img
        src={url}
        alt={label}
        draggable={false}
        style={{ ...transform, imageRendering: raster ? "pixelated" : "auto" }}
      />}
    </div>
  );
}
