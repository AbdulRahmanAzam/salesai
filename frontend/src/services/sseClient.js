/**
 * SSE client for consuming Python pipeline streams via Express.
 *
 * Uses fetch + ReadableStream to parse SSE from POST endpoints.
 * Works with the Express routes that proxy to pythonRunner.js.
 */

const API_BASE = '/api';

/**
 * Consume an SSE stream from a POST endpoint.
 *
 * @param {string} path         – API path, e.g. '/prospecting/run'
 * @param {object} body         – JSON request body
 * @param {object} callbacks
 * @param {function} callbacks.onStep    – ({ index, status, label, ...extra }) => void
 * @param {function} callbacks.onItem    – (itemData) => void
 * @param {function} callbacks.onDone    – (summaryData) => void
 * @param {function} callbacks.onError   – (errorData) => void
 * @param {AbortSignal} [signal] – optional abort signal
 * @returns {Promise<void>}
 */
export async function consumeSSE(path, body, { onStep, onItem, onDone, onError } = {}, signal) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `API error: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // keep incomplete trailing line

    let currentEvent = 'message';
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        const raw = line.slice(6);
        let data;
        try {
          data = JSON.parse(raw);
        } catch {
          // non-JSON data line — ignore
          currentEvent = 'message';
          continue;
        }
        // Dispatch outside try/catch so callback errors propagate
        switch (currentEvent) {
          case 'step':
            onStep?.(data);
            break;
          case 'item':
            onItem?.(data);
            break;
          case 'done':
            onDone?.(data);
            break;
          case 'error':
            onError?.(data);
            break;
          default:
            // summary or other events fall through to onStep
            onStep?.(data);
        }
        currentEvent = 'message'; // reset for next frame
      }
    }
  }
}
