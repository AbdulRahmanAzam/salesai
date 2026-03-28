/**
 * Prospecting pipeline runner.
 * Streams real data from the Python prospecting agent via Express SSE.
 */

import { consumeSSE } from './sseClient';

/**
 * Runs the prospecting pipeline against real APIs.
 * @param {object} options
 * @param {string} [options.prompt] - Natural language input
 * @param {object} [options.icp] - Structured ICP object
 * @param {function} options.onStep - Called with (stepIndex, stepData) as each phase progresses
 * @returns {Promise<{icp: object, leads: array, summary: object}>}
 */
export async function runPipeline({ prompt, icp, onStep }) {
  const leads = [];
  let resolvedIcp = icp || null;
  let summary = {};
  let pipelineError = null;

  await consumeSSE(
    '/prospecting/run',
    { icp, prompt },
    {
      onStep: (evt) => {
        onStep(evt.index, { status: evt.status, label: evt.label, data: evt });
        // If the step event carries ICP data (from interpret phase), capture it
        if (evt.icp) resolvedIcp = evt.icp;
      },
      onItem: (item) => {
        leads.push(item);
      },
      onDone: (data) => {
        summary = data;
        // Extract ICP from summary if available
        if (data.icp) resolvedIcp = data.icp;
      },
      onError: (err) => {
        pipelineError = err;
      },
    },
  );

  if (pipelineError) {
    throw new Error(pipelineError.message || 'Pipeline error');
  }

  // Build a summary compatible with what PipelineRun.jsx expects
  const withEmail = leads.filter((l) => l.contact?.email).length;
  const withLinkedin = leads.filter((l) => l.contact?.linkedin_url).length;
  const avgScore = leads.length
    ? Math.round(leads.reduce((s, l) => s + (l.score || 0), 0) / leads.length)
    : 0;

  return {
    icp: resolvedIcp || {},
    leads,
    summary: {
      companies: summary.companies_found ?? leads.length,
      contacts: summary.contacts_found ?? leads.length,
      contacts_with_email: summary.contacts_with_email ?? withEmail,
      contacts_with_linkedin: summary.contacts_with_linkedin ?? withLinkedin,
      drafts: leads.length,
      llm_scoring: summary.llm_scoring ?? true,
      avg_score: summary.avg_score ?? avgScore,
      ...summary,
    },
  };
}
