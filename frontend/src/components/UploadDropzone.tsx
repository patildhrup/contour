import { useRef, useState } from "react";
import { Upload, ArrowUpRight, ArrowRight } from "lucide-react";

export function UploadDropzone({
  file,
  onFile,
  onSample,
  busy,
  maxBytes,
  maxPixels,
}: {
  maxBytes: number;
  maxPixels: number;
  file: File | null;
  onFile: (f: File) => void;
  onSample: () => void;
  busy: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  return (
    <div
      className={`dropzone ${dragging ? "dragging" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]);
      }}
    >
      <div className="upload-icon">
        <Upload size={22} />
      </div>
      <div className="drop-copy">
        <strong>{file ? file.name : "Drop your image here"}</strong>
        <span>
          {file
            ? `${(file.size / 1024).toFixed(0)} KB · Ready to trace`
            : `JPG, PNG or WebP · Up to ${(maxBytes / 1024 / 1024).toFixed(0)} MB / ${(maxPixels / 1_000_000).toFixed(1)} megapixels`}
        </span>
      </div>
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        aria-label="Choose an image"
        onChange={(e) => {
          if (e.target.files?.[0]) onFile(e.target.files[0]);
          e.target.value = "";
        }}
      />
      <button
        className="button secondary"
        onClick={() => input.current?.click()}
      >
        {file ? "Change image" : "Browse files"} <ArrowUpRight size={15} />
      </button>
      <div className="sample-line">
        Just exploring?{" "}
        <button disabled={busy} onClick={onSample}>
          Try a sample image <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
}
