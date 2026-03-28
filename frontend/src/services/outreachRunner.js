/**
 * Outreach/Personalisation pipeline runner.
 * Streams real data from the Python personalisation agent via Express SSE.
 */

import { consumeSSE } from './sseClient';

export const OUTREACH_STEPS = [
  { label: 'Loading research dossiers', icon: 'search' },
  { label: 'Writing personalised outreach', icon: 'mail' },
  { label: 'Finalising and writing output', icon: 'send' },
];

/**
 * Runs the personalisation/outreach pipeline against real LLM APIs.
 * @param {object} options
 * @param {array} options.dossiers - Research dossiers
 * @param {object} [options.icp] - ICP for product context in emails
 * @param {function} options.onStep - Called with (stepIndex, stepData) for progress
 * @param {function} options.onDraft - Called with (draft, index) as each draft is generated
 * @returns {Promise<{drafts: array, summary: object}>}
 */
export async function runOutreachPipeline({ dossiers, icp, onStep, onDraft }) {
  if (!icp || typeof icp !== 'object') {
    throw new Error('ICP is required for the personalisation pipeline');
  }

  const drafts = [];
  let summary = {};
  let pipelineError = null;

  await consumeSSE(
    '/outreach/run',
    { dossiers, icp },
    {
      onStep: (evt) => {
        onStep(evt.index, { status: evt.status, label: evt.label });
      },
      onItem: (item) => {
        drafts.push(item);
        onDraft(item, drafts.length - 1);
      },
      onDone: (data) => {
        summary = data;
      },
      onError: (err) => {
        pipelineError = err;
      },
    },
  );

  if (pipelineError) {
    throw new Error(pipelineError.message || 'Outreach pipeline error');
  }

  const avgScore = drafts.length
    ? Math.round(drafts.reduce((s, d) => s + (d.personalization_score || 0), 0) / drafts.length)
    : 0;

  return {
    drafts,
    summary: {
      total_drafts: summary.drafts ?? drafts.length,
      avg_personalization_score: summary.avg_personalization_score ?? avgScore,
      avg_prospect_score: drafts.length
        ? Math.round(drafts.reduce((s, d) => s + (d.prospect_score || 0), 0) / drafts.length)
        : 0,
      high_quality: drafts.filter((d) => (d.personalization_score || 0) >= 80).length,
      ...summary,
    },
  };
}
