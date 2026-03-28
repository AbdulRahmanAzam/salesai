/**
 * Research pipeline runner.
 * Streams real data from the Python research agent via Express SSE.
 */

import { consumeSSE } from './sseClient';

export const RESEARCH_STEPS = [
  { label: 'Loading and filtering prospect queue', icon: 'filter' },
  { label: 'Researching prospects across news, GitHub, HN', icon: 'search' },
  { label: 'Writing dossiers and summary', icon: 'file' },
];

/**
 * Runs the research pipeline against real APIs.
 * @param {object} options
 * @param {array} options.leads - Leads from prospecting pipeline (prospect queue records)
 * @param {function} options.onStep - Called with (stepIndex, stepData) for overall progress
 * @param {function} options.onDossier - Called with (dossier, index) as each lead is researched
 * @returns {Promise<{dossiers: array, summary: object}>}
 */
export async function runResearchPipeline({ leads, icp, onStep, onDossier }) {
  const dossiers = [];
  let summary = {};

  // Build the prospect queue in the format the Python agent expects
  const prospectQueue = leads.map((l) => ({
    contact: l.contact,
    company: l.company,
    score: l.score,
    reasons: l.reasons,
    relevance_explanation: l.relevance_explanation,
    status: l.status,
  }));

  if (!icp || !icp.product_name) {
    throw new Error('ICP with product_name is required for research pipeline');
  }

  let pipelineError = null;

  await consumeSSE(
    '/research/run',
    { prospectQueue, icp },
    {
      onStep: (evt) => {
        onStep(evt.index, { status: evt.status, label: evt.label });
      },
      onItem: (item) => {
        dossiers.push(item);
        onDossier(item, dossiers.length - 1);
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
    throw new Error(pipelineError.message || 'Research pipeline error');
  }

  const avgConfidence = dossiers.length
    ? Math.round(
        (dossiers.reduce((s, d) => s + (d.research_confidence || 0), 0) / dossiers.length) * 100,
      )
    : 0;

  return {
    dossiers,
    summary: {
      total_dossiers: summary.researched ?? dossiers.length,
      avg_confidence: avgConfidence / 100,
      avg_score: dossiers.length
        ? Math.round(dossiers.reduce((s, d) => s + (d.prospect_score || 0), 0) / dossiers.length)
        : 0,
      total_talking_points: dossiers.reduce((s, d) => s + (d.talking_points?.length || 0), 0),
      total_pain_points: dossiers.reduce((s, d) => s + (d.pain_points?.length || 0), 0),
      ...summary,
    },
  };
}
