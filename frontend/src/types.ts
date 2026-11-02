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
  color_precision: 8,
  smoothing: 1,
  detail: 2,
  speckle: 4,
  corner: 1,
  simplify: 0,
  remove_background: false,
};
