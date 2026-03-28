/**
 * Tracking pipeline SSE runner.
 *
 * Streams tracking results from the Python tracking agent via SSE.
 * Follows the same pattern as researchRunner.js and outreachRunner.js.
 */

import { consumeSSE } from './sseClient';

const TRACKING_STEPS = [
  'Loading sent messages',
  'Checking for responses',
  'Building tracking summary',
];

/**
 * Run the tracking pipeline via SSE.
 *
 * @param {Object}   opts
 * @param {Array}    opts.outreachQueue  - Array of sent outreach messages
 * @param {Object}   [opts.icp]         - ICP object for product context
 * @param {string}   [opts.action]      - Tracking action: check, analyze, follow-up, send, status
 * @param {Function} opts.onStep        - (stepIndex, status, label, extra) => void
 * @param {Function} opts.onEntry       - (entryData) => void — called per tracking entry
 * @param {Function} [opts.onDone]      - (summary) => void
 * @param {Function} [opts.onError]     - (message) => void
 * @returns {{ cancel: () => void }}
 */
export function runTrackingPipeline({
  outreachQueue,
  icp,
  action = 'check',
  onStep,
  onEntry,
  onDone,
  onError,
}) {
  // Initialise steps
  TRACKING_STEPS.forEach((label, i) => {
    onStep(i, 'pending', label);
  });

  const controller = new AbortController();

  consumeSSE(
    '/tracking/run',
    { outreachQueue, icp, action },
    {
      onStep: (data) => {
        const idx = data.index ?? 0;
        const status = data.status || 'running';
        const label = data.label || TRACKING_STEPS[idx] || `Step ${idx}`;
        onStep(idx, status, label, data);
      },
      onItem: (data) => {
        onEntry(data);
      },
      onDone: (data) => {
        onDone?.(data);
      },
      onError: (data) => {
        const msg = data?.message || 'Tracking pipeline failed';
        onError?.(msg);
      },
    },
    controller.signal,
  );

  return { cancel: () => controller.abort() };
}
