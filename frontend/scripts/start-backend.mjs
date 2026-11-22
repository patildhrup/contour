// Starts the Contour API for local development, unless it is already running.
// Keeps `npm run dev:all` usable when a backend is already up on the same port.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptsDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptsDir, "..", "..");
const port = Number(process.env.BACKEND_PORT || 8000);
const healthUrl = `http://127.0.0.1:${port}/api/health`;

async function backendIsHealthy() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 1500);
  try {
    const response = await fetch(healthUrl, { signal: controller.signal });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

if (await backendIsHealthy()) {
  console.log(`[backend] Already healthy on port ${port}; skipping startup.`);
  process.exit(0);
}

const python = process.platform === "win32"
  ? path.join(root, "backend", ".venv", "Scripts", "python.exe")
  : path.join(root, "backend", ".venv", "bin", "python");

if (!existsSync(python)) {
  console.error(
    `[backend] Missing ${python}. Create the venv first: python -m venv backend/.venv`,
  );
  process.exit(1);
}

console.log(`[backend] Starting uvicorn on http://127.0.0.1:${port}`);
const child = spawn(
  python,
  [
    "-m", "uvicorn", "backend.main:app",
    "--host", "127.0.0.1",
    "--port", String(port),
    "--reload",
    "--reload-dir", "backend",
  ],
  { cwd: root, stdio: "inherit", env: process.env },
);

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}
child.on("error", (error) => {
  console.error(`[backend] Failed to start: ${error.message}`);
  process.exit(1);
});
child.on("exit", (code, signal) => {
  process.exit(code ?? (signal ? 1 : 0));
});
