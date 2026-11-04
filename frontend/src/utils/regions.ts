import type { Result, Region } from "../types";

/** One editable vector layer: a traced region, possibly merged with others. */
export type Layer = {
  id: number;
  fill: string;
  d: string;
  hidden: boolean;
  /** Region ids folded into this layer (length > 1 after a merge). */
  members: number[];
};

const SEAM_STROKE = 0.3;

export function buildLayers(regions: Region[] | undefined): Layer[] {
  if (!regions) return [];
  return regions.map((region, index) => ({
    id: index,
    fill: region.fill,
    d: region.d,
    hidden: false,
    members: [index],
  }));
}

/** Rebuild the same wrapper the backend emits, honouring hide/recolor/merge. */
export function serializeLayers(
  layers: Layer[],
  result: Result,
  mapping: Record<string, string>,
): string {
  const { width, height, scale } = result;
  const sx = scale?.[0] ?? 1;
  const sy = scale?.[1] ?? 1;
  const grouped = sx !== 1 || sy !== 1;
  const strokeWidth = (SEAM_STROKE / Math.min(sx, sy)).toFixed(4);
  const body = layers
    .filter((layer) => !layer.hidden && layer.d)
    .map((layer) => {
      const lower = layer.fill.toLowerCase();
      const fill = (mapping[lower] || layer.fill).trim();
      return `<path fill="${fill}" fill-rule="evenodd" stroke="${fill}" ` +
        `stroke-width="${strokeWidth}" stroke-linejoin="round" d="${layer.d}"/>`;
    })
    .join("");
  const inner = grouped
    ? `<g transform="scale(${sx.toFixed(8)} ${sy.toFixed(8)})">${body}</g>`
    : body;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" ` +
    `viewBox="0 0 ${width} ${height}">${inner}</svg>`;
}

/** Fold every selected layer into the first one, keeping its colour. */
export function mergeLayers(layers: Layer[], ids: number[]): Layer[] {
  const chosen = layers.filter((layer) => ids.includes(layer.id));
  if (chosen.length < 2) return layers;
  const head = chosen[0];
  const merged: Layer = {
    ...head,
    d: chosen.map((layer) => layer.d).join(" "),
    members: chosen.flatMap((layer) => layer.members),
  };
  return layers
    .filter((layer) => !ids.includes(layer.id))
    .concat([merged])
    .sort((a, b) => a.id - b.id);
}
