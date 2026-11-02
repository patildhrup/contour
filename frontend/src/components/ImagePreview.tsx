import type { CSSProperties } from "react";

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
  return (
    <div className="image-stage">
      {markup ? (
        <div
          className="svg-frame"
          style={transform}
          role="img"
          aria-label={label}
          dangerouslySetInnerHTML={{ __html: markup }}
        />
      ) : (
        <img
          src={url}
          alt={label}
          draggable={false}
          style={{ ...transform, imageRendering: raster ? "pixelated" : "auto" }}
        />
      )}
    </div>
  );
}
