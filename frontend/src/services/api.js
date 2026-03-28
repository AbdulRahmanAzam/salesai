const API_BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `API error: ${res.status}`);
  }
  return res.json();
}

// ─── Prospecting Agent ───

export const prospecting = {
  getSessions: () => request('/prospecting/sessions'),
  getSession: (id) => request(`/prospecting/sessions/${id}`),
  saveSession: (data) => request('/prospecting/sessions', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateSession: (id, data) => request(`/prospecting/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  deleteSession: (id) => request(`/prospecting/sessions/${id}`, {
    method: 'DELETE',
  }),
};

// ─── Research Agent ───

export const research = {
  getSessions: () => request('/research/sessions'),
  getSession: (id) => request(`/research/sessions/${id}`),
  saveSession: (data) => request('/research/sessions', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateSession: (id, data) => request(`/research/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  deleteSession: (id) => request(`/research/sessions/${id}`, {
    method: 'DELETE',
  }),
};

// ─── Outreach Agent (Personalisation) ───

export const outreach = {
  getSessions: () => request('/outreach/sessions'),
  getSession: (id) => request(`/outreach/sessions/${id}`),
  saveSession: (data) => request('/outreach/sessions', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateSession: (id, data) => request(`/outreach/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  deleteSession: (id) => request(`/outreach/sessions/${id}`, {
    method: 'DELETE',
  }),
  approveDraft: (sessionId, idx, notes = '') => request(`/outreach/sessions/${sessionId}/drafts/${idx}/approve`, {
    method: 'PATCH',
    body: JSON.stringify({ notes }),
  }),
  rejectDraft: (sessionId, idx, notes = '') => request(`/outreach/sessions/${sessionId}/drafts/${idx}/reject`, {
    method: 'PATCH',
    body: JSON.stringify({ notes }),
  }),
  editDraft: (sessionId, idx, data) => request(`/outreach/sessions/${sessionId}/drafts/${idx}/edit`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  approveBatch: (sessionId, threshold = 50) => request(`/outreach/sessions/${sessionId}/approve-batch`, {
    method: 'POST',
    body: JSON.stringify({ threshold }),
  }),
  markSent: (sessionId, results) => request(`/outreach/sessions/${sessionId}/mark-sent`, {
    method: 'POST',
    body: JSON.stringify({ results }),
  }),
  sendDraft: (sessionId, idx) => request(`/outreach/sessions/${sessionId}/drafts/${idx}/send`, {
    method: 'POST',
  }),
  sendApproved: (sessionId) => request(`/outreach/sessions/${sessionId}/send-approved`, {
    method: 'POST',
  }),
  testEmail: (to) => request('/outreach/test-email', {
    method: 'POST',
    body: JSON.stringify({ to }),
  }),
  aiRewrite: (data) => request('/outreach/ai-rewrite', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
};

// ─── Tracking Agent ───

export const tracking = {
  getSessions: () => request('/tracking/sessions'),
  getSession: (id) => request(`/tracking/sessions/${id}`),
  saveSession: (data) => request('/tracking/sessions', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateSession: (id, data) => request(`/tracking/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  deleteSession: (id) => request(`/tracking/sessions/${id}`, {
    method: 'DELETE',
  }),
  updateEntry: (sessionId, idx, data) => request(`/tracking/sessions/${sessionId}/entries/${idx}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  addResponse: (sessionId, entryIdx, data) => request(`/tracking/sessions/${sessionId}/entries/${entryIdx}/responses`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  addFollowUp: (sessionId, entryIdx, data) => request(`/tracking/sessions/${sessionId}/entries/${entryIdx}/follow-ups`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  approveFollowUp: (sessionId, entryIdx, followUpIdx) => request(`/tracking/sessions/${sessionId}/entries/${entryIdx}/follow-ups/${followUpIdx}/approve`, {
    method: 'PATCH',
  }),
  rejectFollowUp: (sessionId, entryIdx, followUpIdx) => request(`/tracking/sessions/${sessionId}/entries/${entryIdx}/follow-ups/${followUpIdx}/reject`, {
    method: 'PATCH',
  }),
};

// ─── Dashboard ───

export const dashboard = {
  getSummary: () => request('/dashboard/summary'),
};
