/**
 * Spawns a Python pipeline as a child process, parses JSON-line events
 * from stderr and streams them as SSE to the Express response.
 *
 * Protocol:
 *   stderr → one JSON object per line  (progress events)
 *   stdout → single JSON blob at exit  (final summary)
 */

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const os = require("os");

const ROOT = path.resolve(__dirname, "..", "..");
const PYTHON = process.env.PYTHON_PATH || "python";
const RUN_PY = path.join(ROOT, "run.py");
const TIMEOUT_MS = parseInt(process.env.PIPELINE_TIMEOUT_MS, 10) || 5 * 60 * 1000;

/**
 * Write a temporary JSON file and return its path.
 * Caller must clean up after use.
 */
function writeTempJson(prefix, data) {
  const tmpDir = os.tmpdir();
  const filePath = path.join(tmpDir, `${prefix}_${Date.now()}.json`);
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf-8");
  return filePath;
}

/**
 * Stream a Python pipeline run as SSE.
 *
 * @param {import('express').Response} res  – Express response (headers set by caller)
 * @param {string} command                  – run.py subcommand: "prospect" | "research" | "personalise"
 * @param {string[]} extraArgs              – additional CLI args (e.g. ["--icp", "/tmp/icp.json"])
 * @param {object} [env]                    – extra env vars to merge
 * @returns {Promise<void>}
 */
function streamPipeline(res, command, extraArgs = [], env = {}) {
  return new Promise((resolve, reject) => {
    const args = [RUN_PY, command, "--json-events", ...extraArgs];
    console.log(`[pythonRunner] Spawning: ${PYTHON} ${args.join(" ")}`);

    const child = spawn(PYTHON, args, {
      cwd: ROOT,
      env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONUNBUFFERED: "1", ...env },
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let killed = false;

    // Timeout guard
    const timer = setTimeout(() => {
      killed = true;
      child.kill("SIGTERM");
      sendSSE(res, "error", { message: "Pipeline timed out" });
      res.end();
    }, TIMEOUT_MS);

    // --- stderr: JSON-line events → SSE ---
    let stderrBuf = "";
    child.stderr.on("data", (chunk) => {
      stderrBuf += chunk.toString();
      const lines = stderrBuf.split("\n");
      stderrBuf = lines.pop(); // keep incomplete trailing line
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const evt = JSON.parse(trimmed);
          sendSSE(res, evt.event || "message", evt);
        } catch {
          // non-JSON stderr line – log for debugging
          console.log(`[python stderr] ${trimmed}`);
        }
      }
    });

    // --- stdout: final result ---
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });

    child.on("close", (code) => {
      clearTimeout(timer);
      if (killed) return;

      console.log(`[pythonRunner] Process exited with code ${code}`);

      if (code !== 0) {
        console.error(`[pythonRunner] stdout: ${stdout.slice(-500)}`);
        sendSSE(res, "error", { message: `Process exited with code ${code}` });
        res.end();
        return resolve();
      }

      // Try to parse final summary from stdout
      try {
        const summary = JSON.parse(stdout.trim());
        sendSSE(res, "done", summary);
      } catch {
        sendSSE(res, "done", { raw: stdout.trim() });
      }
      res.end();
      resolve();
    });

    child.on("error", (err) => {
      clearTimeout(timer);
      sendSSE(res, "error", { message: err.message });
      res.end();
      resolve();
    });
  });
}

/** Send one SSE frame */
function sendSSE(res, event, data) {
  console.log(`[SSE] event=${event} keys=${Object.keys(data).join(',')}`);
  res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

/** Set standard SSE headers on a response */
function sseHeaders(res) {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");
  res.flushHeaders();
}

module.exports = {
  streamPipeline,
  writeTempJson,
  sendSSE,
  sseHeaders,
  ROOT,
};
