import { useEffect, useState } from "react";
import { LoaderCircle } from "lucide-react";

const STAGES = [
  { label: "READING", message: "Reading the original at native resolution…" },
  { label: "PREPROCESS", message: "Adaptive denoise, transparency, and scaling…" },
  { label: "QUANTIZING", message: "Separating meaningful color regions…" },
  { label: "TRACING", message: "Fitting smooth Bézier contours…" },
  { label: "CORNERS", message: "Preserving sharp corners and small details…" },
  { label: "ENCODING", message: "Encoding stacked SVG paths…" },
  { label: "FINALIZING", message: "Checking path quality…" },
];

export function ConversionProgress({
  busy,
  elapsed,
}: {
  busy: boolean;
  elapsed: number;
}) {
  const [stageIdx, setStageIdx] = useState(0);

  useEffect(() => {
    if (!busy) {
      setStageIdx(0);
      return;
    }
    const id = setInterval(() => {
      setStageIdx((i) => Math.min(i + 1, STAGES.length - 1));
    }, 2200);
    return () => clearInterval(id);
  }, [busy]);

  if (!busy) return null;

  const stage = STAGES[stageIdx];

  return (
    <div className="progress" role="status" aria-live="polite">
      <LoaderCircle className="spin" size={17} />
      <div className="progress-messages">
        <span>{stage.message}</span>
        <span className="progress-stage">{stage.label}</span>
      </div>
      <span>{elapsed}s</span>
    </div>
  );
}
