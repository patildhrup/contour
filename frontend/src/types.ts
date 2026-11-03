export type Settings = {
  mode: "color" | "monochrome";
  colors: number;
  color_precision: number;
  smoothing: number;
  detail: number;
  speckle: number;
  corner: number;
  simplify: number;
  remove_background: boolean;
  background_tolerance: number;
  alpha_threshold: number;
  mask_expand: number;
};
export type Result = {
  id: string;
  svg: string;
  width: number;
  height: number;
  paths: number;
  filename: string;
  warnings: string[];
  elapsed_ms: number;
};
export const defaults: Settings = {
  mode: "color",
  colors: 16,
  color_precision: 6,
  smoothing: 1,
  detail: 2,
  speckle: 4,
  corner: 1,
  simplify: 1,
  remove_background: false,
  background_tolerance: 10,
  alpha_threshold: 128,
  mask_expand: 0,
};
