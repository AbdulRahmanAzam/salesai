const express = require('express');
const router = express.Router();
const fs = require('fs');
const Session = require('../models/ProspectingSession');
const { streamPipeline, writeTempJson, sseHeaders } = require('../lib/pythonRunner');

// ── POST /run — SSE stream for live prospecting pipeline ──

router.post('/run', async (req, res) => {
  const { icp, prompt, maxLeads } = req.body;
  if (!icp && !prompt) {
    return res.status(400).json({ error: 'Provide either icp (object) or prompt (string)' });
  }

  sseHeaders(res);

  const tempFiles = [];
  try {
    const args = [];

    if (icp) {
      const icpPath = writeTempJson('icp', icp);
      tempFiles.push(icpPath);
      args.push('--icp', icpPath);
    } else {
      args.push('--prompt', prompt);
    }

    if (maxLeads) args.push('--max-leads', String(maxLeads));

    await streamPipeline(res, 'prospect', args);
  } finally {
    tempFiles.forEach((f) => { try { fs.unlinkSync(f); } catch {} });
  }
});

router.get('/sessions', async (req, res) => {
  try {
    const sessions = await Session.find()
      .select('session_name prompt resolved_icp.product_name summary status created_at')
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

module.exports = router;
