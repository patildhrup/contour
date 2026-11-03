/** Edit only the tracer's path fills, leaving path geometry and stacking intact. */
export function readPalette(svg: string): string[] {
  if (!svg) return [];
  const doc = new DOMParser().parseFromString(svg, "image/svg+xml");
  return [
    ...new Set(
      Array.from(doc.querySelectorAll("path[fill]"))
        .map((path) => path.getAttribute("fill")!.toLowerCase())
        .filter((fill) => /^#[0-9a-f]{6}$/.test(fill)),
    ),
  ];
}

export function recolorSvg(
  svg: string,
  mapping: Record<string, string>,
): string {
  if (!Object.keys(mapping).length) return svg;
  const doc = new DOMParser().parseFromString(svg, "image/svg+xml");
  for (const path of doc.querySelectorAll("path[fill]")) {
    const original = path.getAttribute("fill")!.toLowerCase();
    const replacement = mapping[original];
    if (replacement && /^#[0-9a-f]{6}$/i.test(replacement)) {
      path.setAttribute("fill", replacement);
      // Seam strokes share the fill colour, so recolour them together.
      if ((path.getAttribute("stroke") || "").toLowerCase() === original)
        path.setAttribute("stroke", replacement);
    }
  }
  return new XMLSerializer().serializeToString(doc.documentElement);
}
