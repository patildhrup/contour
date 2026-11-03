import type { Result } from "../types";

function buildPdfDocument(
  objects: { id: number; dict: string; stream: Uint8Array | null }[],
): Blob {
  const encoder = new TextEncoder();
  const chunks: Uint8Array[] = [];
  let currentByteLength = 0;

  function appendText(str: string) {
    const bytes = encoder.encode(str);
    chunks.push(bytes);
    currentByteLength += bytes.length;
  }

  function appendBytes(bytes: Uint8Array) {
    chunks.push(bytes);
    currentByteLength += bytes.length;
  }

  appendText("%PDF-1.4\n");
  const offsets: number[] = [];

  for (let i = 0; i < objects.length; i++) {
    offsets.push(currentByteLength);
    const obj = objects[i];
    appendText(
      `${obj.id} 0 obj\n${obj.dict}\n` + (obj.stream ? "stream\n" : ""),
    );
    if (obj.stream) {
      appendBytes(obj.stream);
      appendText("\nendstream\n");
    }
    appendText("endobj\n");
  }

  const xrefOffset = currentByteLength;
  let xref = `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const off of offsets) {
    xref += off.toString().padStart(10, "0") + " 00000 n \n";
  }
  xref += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  appendText(xref);

  return new Blob(chunks, { type: "application/pdf" });
}

function parseSvgColor(col: string): string | null {
  if (!col || col === "none" || col === "transparent") return null;
  col = col.trim().toLowerCase();
  const NAMED: Record<string, string> = {
    black: "0 0 0",
    white: "1 1 1",
    red: "1 0 0",
    green: "0 0.502 0",
    blue: "0 0 1",
    yellow: "1 1 0",
    gray: "0.502 0.502 0.502",
    grey: "0.502 0.502 0.502",
  };
  if (NAMED[col]) return `${NAMED[col]} rg`;
  if (col.startsWith("#")) {
    let hex = col.slice(1);
    if (hex.length === 3 || hex.length === 4) {
      hex = hex
        .split("")
        .slice(0, 3)
        .map((c) => c + c)
        .join("");
    }
    const r = (parseInt(hex.slice(0, 2), 16) / 255).toFixed(4);
    const g = (parseInt(hex.slice(2, 4), 16) / 255).toFixed(4);
    const b = (parseInt(hex.slice(4, 6), 16) / 255).toFixed(4);
    return `${r} ${g} ${b} rg`;
  }
  const rgb = col.match(/rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
  if (rgb) {
    const r = (parseInt(rgb[1], 10) / 255).toFixed(4);
    const g = (parseInt(rgb[2], 10) / 255).toFixed(4);
    const b = (parseInt(rgb[3], 10) / 255).toFixed(4);
    return `${r} ${g} ${b} rg`;
  }
  return "0 0 0 rg";
}

function parsePathDataToPdf(d: string): string {
  const tokens =
    d.match(/[a-df-z]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?/gi) || [];
  let i = 0;
  let cmd = "";
  let curX = 0,
    curY = 0;
  let startX = 0,
    startY = 0;
  let prevCtrlX = 0,
    prevCtrlY = 0;
  let out = "";

  while (i < tokens.length) {
    if (/^[a-df-z]$/i.test(tokens[i])) {
      cmd = tokens[i++];
    }
    if (cmd === "M" || cmd === "m") {
      let x = parseFloat(tokens[i++]);
      let y = parseFloat(tokens[i++]);
      if (cmd === "m") {
        x += curX;
        y += curY;
      }
      curX = x;
      curY = y;
      startX = x;
      startY = y;
      prevCtrlX = x;
      prevCtrlY = y;
      out += `${x.toFixed(3)} ${y.toFixed(3)} m `;
      cmd = cmd === "m" ? "l" : "L";
    } else if (cmd === "L" || cmd === "l") {
      let x = parseFloat(tokens[i++]);
      let y = parseFloat(tokens[i++]);
      if (cmd === "l") {
        x += curX;
        y += curY;
      }
      curX = x;
      curY = y;
      prevCtrlX = x;
      prevCtrlY = y;
      out += `${x.toFixed(3)} ${y.toFixed(3)} l `;
    } else if (cmd === "H" || cmd === "h") {
      let x = parseFloat(tokens[i++]);
      if (cmd === "h") x += curX;
      curX = x;
      prevCtrlX = x;
      prevCtrlY = curY;
      out += `${x.toFixed(3)} ${curY.toFixed(3)} l `;
    } else if (cmd === "V" || cmd === "v") {
      let y = parseFloat(tokens[i++]);
      if (cmd === "v") y += curY;
      curY = y;
      prevCtrlX = curX;
      prevCtrlY = y;
      out += `${curX.toFixed(3)} ${y.toFixed(3)} l `;
    } else if (cmd === "C" || cmd === "c") {
      let x1 = parseFloat(tokens[i++]);
      let y1 = parseFloat(tokens[i++]);
      let x2 = parseFloat(tokens[i++]);
      let y2 = parseFloat(tokens[i++]);
      let x = parseFloat(tokens[i++]);
      let y = parseFloat(tokens[i++]);
      if (cmd === "c") {
        x1 += curX;
        y1 += curY;
        x2 += curX;
        y2 += curY;
        x += curX;
        y += curY;
      }
      curX = x;
      curY = y;
      prevCtrlX = x2;
      prevCtrlY = y2;
      out += `${x1.toFixed(3)} ${y1.toFixed(3)} ${x2.toFixed(3)} ${y2.toFixed(3)} ${x.toFixed(3)} ${y.toFixed(3)} c `;
    } else if (cmd === "S" || cmd === "s") {
      let x2 = parseFloat(tokens[i++]);
      let y2 = parseFloat(tokens[i++]);
      let x = parseFloat(tokens[i++]);
      let y = parseFloat(tokens[i++]);
      if (cmd === "s") {
        x2 += curX;
        y2 += curY;
        x += curX;
        y += curY;
      }
      const x1 = 2 * curX - prevCtrlX;
      const y1 = 2 * curY - prevCtrlY;
      curX = x;
      curY = y;
      prevCtrlX = x2;
      prevCtrlY = y2;
      out += `${x1.toFixed(3)} ${y1.toFixed(3)} ${x2.toFixed(3)} ${y2.toFixed(3)} ${x.toFixed(3)} ${y.toFixed(3)} c `;
    } else if (cmd === "Q" || cmd === "q") {
      let qx1 = parseFloat(tokens[i++]);
      let qy1 = parseFloat(tokens[i++]);
      let x = parseFloat(tokens[i++]);
      let y = parseFloat(tokens[i++]);
      if (cmd === "q") {
        qx1 += curX;
        qy1 += curY;
        x += curX;
        y += curY;
      }
      const cx1 = curX + (2 / 3) * (qx1 - curX);
      const cy1 = curY + (2 / 3) * (qy1 - curY);
      const cx2 = x + (2 / 3) * (qx1 - x);
      const cy2 = y + (2 / 3) * (qy1 - y);
      curX = x;
      curY = y;
      prevCtrlX = qx1;
      prevCtrlY = qy1;
      out += `${cx1.toFixed(3)} ${cy1.toFixed(3)} ${cx2.toFixed(3)} ${cy2.toFixed(3)} ${x.toFixed(3)} ${y.toFixed(3)} c `;
    } else if (cmd === "Z" || cmd === "z") {
      out += "h ";
      curX = startX;
      curY = startY;
      prevCtrlX = curX;
      prevCtrlY = curY;
      cmd = "";
    } else {
      throw new Error(`Unsupported SVG path command: ${cmd}`);
    }
  }
  return out;
}

export function svgToVectorPdfBlob(
  svgString: string,
  width: number,
  height: number,
): Blob | null {
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(svgString, "image/svg+xml");
    if (doc.querySelector("parsererror")) return null;
    const pathElements = doc.querySelectorAll("path");

    let pdfStream = `q\n1 0 0 -1 0 ${height} cm\n`;
    let count = 0;

    for (const el of Array.from(pathElements)) {
      const d = el.getAttribute("d");
      if (!d) continue;

      const fill = el.getAttribute("fill") || "#000000";
      const colorCmd = parseSvgColor(fill);
      if (!colorCmd) continue;

      pdfStream += "q\n";
      // Apply group transforms before each path's local transform, preserving
      // the original coordinate system in genuinely vector PDF output.
      const ancestors: Element[] = [];
      for (let node: Element | null = el; node; node = node.parentElement) {
        ancestors.unshift(node);
      }
      for (const node of ancestors) {
        const transform = (node as SVGGraphicsElement).transform?.baseVal;
        if (node.hasAttribute("transform") && !transform) return null;
        if (transform?.numberOfItems) {
          const matrix = transform.consolidate()?.matrix;
          if (!matrix) return null;
          pdfStream += `${[matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f].join(" ")} cm\n`;
        }
      }
      pdfStream += colorCmd + "\n";
      // Seam strokes painted with the fill colour become fill+stroke (B/B*).
      const strokeColor = el.getAttribute("stroke") || "";
      const strokeCmd = strokeColor ? parseSvgColor(strokeColor)?.replace(/rg$/, "RG") : null;
      const strokeWidth = parseFloat(el.getAttribute("stroke-width") || "");
      const hasStroke = Boolean(strokeCmd) && isFinite(strokeWidth) && strokeWidth > 0;
      if (hasStroke) {
        pdfStream += `${strokeCmd}\n${strokeWidth.toFixed(3)} w\n`;
        if ((el.getAttribute("stroke-linejoin") || "").toLowerCase() === "round") {
          pdfStream += "1 j\n";
        }
      }
      pdfStream += parsePathDataToPdf(d);

      const fillRule =
        el.getAttribute("fill-rule")?.toLowerCase() === "evenodd" ? "f*" : "f";
      const paintOp = hasStroke ? fillRule === "f*" ? "B*" : "B" : fillRule;
      pdfStream += `${paintOp}\nQ\n`;
      count++;
    }

    pdfStream += "Q\n";
    if (pathElements.length && count === 0) return null;

    const streamBytes = new TextEncoder().encode(pdfStream);
    const objects = [
      { id: 1, dict: "<< /Type /Catalog /Pages 2 0 R >>", stream: null },
      {
        id: 2,
        dict: "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        stream: null,
      },
      {
        id: 3,
        dict: `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${width} ${height}] /Contents 4 0 R >>`,
        stream: null,
      },
      {
        id: 4,
        dict: `<< /Length ${streamBytes.length} >>`,
        stream: streamBytes,
      },
    ];

    return buildPdfDocument(objects);
  } catch {
    return null;
  }
}

export async function svgToCanvasPdfBlob(
  url: string,
  width: number,
  height: number,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Canvas context is unavailable"));
          return;
        }
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, width, height);
        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob(
          async (blob) => {
            if (!blob) {
              reject(new Error("Canvas blob conversion failed"));
              return;
            }
            try {
              const buffer = await blob.arrayBuffer();
              const jpegBytes = new Uint8Array(buffer);
              const content = `q\n${width} 0 0 ${height} 0 0 cm\n/Im1 Do\nQ\n`;
              const contentBytes = new TextEncoder().encode(content);
              const objects = [
                {
                  id: 1,
                  dict: "<< /Type /Catalog /Pages 2 0 R >>",
                  stream: null,
                },
                {
                  id: 2,
                  dict: "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                  stream: null,
                },
                {
                  id: 3,
                  dict: `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${width} ${height}] /Resources << /XObject << /Im1 4 0 R >> >> /Contents 5 0 R >>`,
                  stream: null,
                },
                {
                  id: 4,
                  dict: `<< /Type /XObject /Subtype /Image /Width ${width} /Height ${height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpegBytes.length} >>`,
                  stream: jpegBytes,
                },
                {
                  id: 5,
                  dict: `<< /Length ${contentBytes.length} >>`,
                  stream: contentBytes,
                },
              ];
              resolve(buildPdfDocument(objects));
            } catch (err) {
              reject(err);
            }
          },
          "image/jpeg",
          0.95,
        );
      } catch (err) {
        reject(err);
      }
    };
    img.onerror = () => reject(new Error("Failed to load SVG for PDF export"));
    img.src = url;
  });
}

export async function exportPdf(result: Result, _url: string): Promise<void> {
  let pdfBlob: Blob | null = null;
  try {
    pdfBlob = svgToVectorPdfBlob(result.svg, result.width, result.height);
  } catch {
    pdfBlob = null;
  }
  if (!pdfBlob) {
    throw new Error("The result could not be exported as a vector PDF.");
  }
  const link = document.createElement("a");
  const pdfUrl = URL.createObjectURL(pdfBlob);
  link.href = pdfUrl;
  link.download = result.filename.replace(/\.svg$/i, ".pdf");
  link.click();
  setTimeout(() => URL.revokeObjectURL(pdfUrl), 1000);
}

