const express = require('express');
const router = express.Router();
const fs = require('fs');
const Session = require('../models/ResearchSession');
const { streamPipeline, writeTempJson, sseHeaders } = require('../lib/pythonRunner');

// ── POST /run — SSE stream for live research pipeline ──

router.post('/run', async (req, res) => {
  const { prospectQueue, icp, maxResearch, minScore } = req.body;
  if (!prospectQueue || !icp) {
    return res.status(400).json({ error: 'Provide prospectQueue (array) and icp (object)' });
  }

  sseHeaders(res);

  const tempFiles = [];
  try {
    const queuePath = writeTempJson('queue', prospectQueue);
    const icpPath = writeTempJson('icp', icp);
    tempFiles.push(queuePath, icpPath);

    const args = ['--queue', queuePath, '--icp', icpPath];
    if (maxResearch) args.push('--max-research', String(maxResearch));
    if (minScore != null) args.push('--min-score', String(minScore));

    await streamPipeline(res, 'research', args);
  } finally {
    tempFiles.forEach((f) => { try { fs.unlinkSync(f); } catch {} });
  }
});

router.get('/sessions', async (req, res) => {
  try {
    const sessions = await Session.find()
      .select('session_name prospecting_session_id summary status created_at')
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
