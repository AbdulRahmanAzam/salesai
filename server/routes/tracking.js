const express = require('express');
const router = express.Router();
const fs = require('fs');
const Session = require('../models/TrackingSession');
const { streamPipeline, writeTempJson, sseHeaders } = require('../lib/pythonRunner');

// ── POST /run — SSE stream for live tracking pipeline ──

router.post('/run', async (req, res) => {
  const { outreachQueue, icp, action, since, autoFollowUp } = req.body;
  if (!outreachQueue) {
    return res.status(400).json({ error: 'Provide outreachQueue (array)' });
  }

  sseHeaders(res);

  const tempFiles = [];
  try {
    const queuePath = writeTempJson('tracking_queue', outreachQueue);
    tempFiles.push(queuePath);

    const args = ['--queue', queuePath];
    if (action) args.push('--action', action);
    if (since) args.push('--since', since);
    if (autoFollowUp) args.push('--auto-follow-up');

    // Pass product context from ICP if available
    if (icp) {
      const icpPath = writeTempJson('tracking_icp', icp);
      tempFiles.push(icpPath);
      if (icp.product_name) args.push('--product-name', icp.product_name);
      if (icp.product_pitch) args.push('--product-pitch', icp.product_pitch);
    }

    await streamPipeline(res, 'tracking', args);
  } finally {
    tempFiles.forEach((f) => { try { fs.unlinkSync(f); } catch {} });
  }
});

router.get('/sessions', async (req, res) => {
  try {
    const sessions = await Session.find()
      .select('session_name outreach_session_id summary status created_at')
      .sort({ created_at: -1 })
      .limit(50)
      .lean();
    res.json(sessions);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/sessions/:id', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id).lean();
    if (!session) return res.status(404).json({ error: 'Session not found' });
    res.json(session);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/sessions', async (req, res) => {
  try {
    const session = new Session(req.body);
    await session.save();
    res.status(201).json(session);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.patch('/sessions/:id', async (req, res) => {
  try {
    const session = await Session.findByIdAndUpdate(
      req.params.id,
      { ...req.body, updated_at: new Date() },
      { new: true }
    );
    if (!session) return res.status(404).json({ error: 'Session not found' });
    res.json(session);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.delete('/sessions/:id', async (req, res) => {
  try {
    const session = await Session.findByIdAndDelete(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    res.json({ message: 'Session deleted' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── Entry-level operations ──

// Update an entry's status (e.g., mark as opened)
router.patch('/sessions/:id/entries/:idx', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    const idx = parseInt(req.params.idx, 10);
    if (idx < 0 || idx >= session.entries.length) return res.status(404).json({ error: 'Entry not found' });
    const entry = session.entries[idx];
    const allowed = ['status', 'opened_at', 'replied_at', 'reply_snippet', 'is_warm', 'warmth', 'last_activity_at'];
    allowed.forEach(key => {
      if (req.body[key] !== undefined) entry[key] = req.body[key];
    });
    session.updated_at = new Date();
    await session.save();
    res.json(entry);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Add a response to an entry
router.post('/sessions/:id/entries/:idx/responses', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    const idx = parseInt(req.params.idx, 10);
    if (idx < 0 || idx >= session.entries.length) return res.status(404).json({ error: 'Entry not found' });
    session.entries[idx].responses.push(req.body);
    session.entries[idx].status = 'replied';
    session.entries[idx].replied_at = req.body.received_at || new Date().toISOString();
    session.entries[idx].reply_snippet = (req.body.body || '').slice(0, 200);
    session.entries[idx].warmth = req.body.warmth || 'unknown';
    session.entries[idx].is_warm = ['warm', 'hot', 'meeting_requested'].includes(req.body.warmth);
    session.entries[idx].last_activity_at = new Date().toISOString();
    session.updated_at = new Date();
    await session.save();
    res.status(201).json(session.entries[idx]);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Add a follow-up to an entry
router.post('/sessions/:id/entries/:idx/follow-ups', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    const idx = parseInt(req.params.idx, 10);
    if (idx < 0 || idx >= session.entries.length) return res.status(404).json({ error: 'Entry not found' });
    session.entries[idx].follow_ups.push(req.body);
    session.entries[idx].follow_up_count = session.entries[idx].follow_ups.length;
    session.entries[idx].last_activity_at = new Date().toISOString();
    session.updated_at = new Date();
    await session.save();
    res.status(201).json(session.entries[idx]);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Approve / reject a follow-up within an entry
router.patch('/sessions/:id/entries/:eIdx/follow-ups/:fIdx/:action', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    const eIdx = parseInt(req.params.eIdx, 10);
    const fIdx = parseInt(req.params.fIdx, 10);
    if (eIdx < 0 || eIdx >= session.entries.length) return res.status(404).json({ error: 'Entry not found' });
    if (fIdx < 0 || fIdx >= session.entries[eIdx].follow_ups.length) return res.status(404).json({ error: 'Follow-up not found' });
    const action = req.params.action;
    if (action === 'approve') {
      session.entries[eIdx].follow_ups[fIdx].status = 'approved';
    } else if (action === 'reject') {
      session.entries[eIdx].follow_ups[fIdx].status = 'rejected';
    } else {
      return res.status(400).json({ error: 'Invalid action. Use approve or reject.' });
    }
    session.updated_at = new Date();
    await session.save();
    res.json(session.entries[eIdx].follow_ups[fIdx]);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

module.exports = router;
