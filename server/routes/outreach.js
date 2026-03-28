const express = require('express');
const router = express.Router();
const fs = require('fs');
const nodemailer = require('nodemailer');
const Session = require('../models/OutreachSession');
const { streamPipeline, writeTempJson, sseHeaders } = require('../lib/pythonRunner');

// ── Nodemailer transporter (lazy init) ──
let _transporter = null;
function getTransporter() {
  if (!_transporter) {
    _transporter = nodemailer.createTransport({
      host: process.env.OUTREACH_SMTP_HOST || 'smtp.gmail.com',
      port: parseInt(process.env.OUTREACH_SMTP_PORT || '587', 10),
      secure: false,
      auth: {
        user: process.env.OUTREACH_SMTP_USERNAME,
        pass: process.env.OUTREACH_SMTP_PASSWORD,
      },
    });
  }
  return _transporter;
}

// ── POST /run — SSE stream for live personalisation pipeline ──

router.post('/run', async (req, res) => {
  const { dossiers, icp, maxDrafts, minConfidence } = req.body;
  console.log(`[outreach/run] dossiers: ${Array.isArray(dossiers) ? dossiers.length : typeof dossiers}, icp: ${icp ? Object.keys(icp).join(',') : 'null'}`);
  if (!dossiers || !icp) {
    console.error('[outreach/run] Missing dossiers or icp');
    return res.status(400).json({ error: 'Provide dossiers (array) and icp (object)' });
  }

  sseHeaders(res);

  const tempFiles = [];
  try {
    const dossiersPath = writeTempJson('dossiers', dossiers);
    const icpPath = writeTempJson('icp', icp);
    tempFiles.push(dossiersPath, icpPath);

    const args = ['--dossiers', dossiersPath, '--icp', icpPath];
    if (maxDrafts) args.push('--max-drafts', String(maxDrafts));
    if (minConfidence != null) args.push('--min-confidence', String(minConfidence));

    await streamPipeline(res, 'personalise', args);
    console.log('[outreach/run] Pipeline stream completed');
  } catch (err) {
    console.error('[outreach/run] Pipeline error:', err.message);
  } finally {
    tempFiles.forEach((f) => { try { fs.unlinkSync(f); } catch {} });
  }
});

router.get('/sessions', async (req, res) => {
  try {
    const sessions = await Session.find()
      .select('session_name prospecting_session_id research_session_id summary status created_at')
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

// ── Draft approval / rejection ──

router.patch('/sessions/:id/drafts/:idx/approve', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    const idx = parseInt(req.params.idx, 10);
    if (idx < 0 || idx >= session.drafts.length) return res.status(404).json({ error: 'Draft not found' });
    session.drafts[idx].status = 'approved';
    session.drafts[idx].approved_at = new Date().toISOString();
    session.drafts[idx].reviewer_notes = req.body.notes || '';
    session.updated_at = new Date();
    await session.save();
    res.json(session.drafts[idx]);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.patch('/sessions/:id/drafts/:idx/reject', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    const idx = parseInt(req.params.idx, 10);
    if (idx < 0 || idx >= session.drafts.length) return res.status(404).json({ error: 'Draft not found' });
    session.drafts[idx].status = 'rejected';
    session.drafts[idx].reviewer_notes = req.body.notes || '';
    session.updated_at = new Date();
    await session.save();
    res.json(session.drafts[idx]);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.patch('/sessions/:id/drafts/:idx/edit', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    const idx = parseInt(req.params.idx, 10);
    if (idx < 0 || idx >= session.drafts.length) return res.status(404).json({ error: 'Draft not found' });
    if (req.body.subject) session.drafts[idx].subject = req.body.subject;
    if (req.body.body) session.drafts[idx].body = req.body.body;
    session.drafts[idx].status = 'draft';
    session.updated_at = new Date();
    await session.save();
    res.json(session.drafts[idx]);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Batch approve all drafts above a threshold
router.post('/sessions/:id/approve-batch', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    const threshold = parseFloat(req.body.threshold || 50);
    let count = 0;
    const now = new Date().toISOString();
    session.drafts.forEach(d => {
      if (d.status === 'draft' && d.personalization_score >= threshold && d.contact_email) {
        d.status = 'approved';
        d.approved_at = now;
        count++;
      }
    });
    session.updated_at = new Date();
    await session.save();
    res.json({ approved: count, threshold });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Mark drafts as sent (used after Python agent sends via SMTP)
router.post('/sessions/:id/mark-sent', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    const { results } = req.body; // [{ idx, message_id, sent_at, error? }]
    if (!Array.isArray(results)) return res.status(400).json({ error: 'results array required' });
    let sent = 0, failed = 0;
    results.forEach(r => {
      const idx = r.idx;
      if (idx >= 0 && idx < session.drafts.length) {
        if (r.error) {
          session.drafts[idx].status = 'failed';
          session.drafts[idx].send_error = r.error;
          failed++;
        } else {
          session.drafts[idx].status = 'sent';
          session.drafts[idx].sent_at = r.sent_at || new Date().toISOString();
          session.drafts[idx].message_id = r.message_id || '';
          sent++;
        }
      }
    });
    session.updated_at = new Date();
    await session.save();
    res.json({ sent, failed });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// ── Send a single draft via Nodemailer ──
router.post('/sessions/:id/drafts/:idx/send', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    const idx = parseInt(req.params.idx, 10);
    if (idx < 0 || idx >= session.drafts.length) return res.status(404).json({ error: 'Draft not found' });

    const draft = session.drafts[idx];
    if (!draft.contact_email) return res.status(400).json({ error: 'Draft has no contact email' });
    if (draft.status === 'sent') return res.status(400).json({ error: 'Draft already sent' });

    const transporter = getTransporter();
    const senderEmail = process.env.OUTREACH_SENDER_EMAIL || process.env.OUTREACH_SMTP_USERNAME;
    const senderName = process.env.OUTREACH_SENDER_NAME || 'Sales Intelligence';

    const info = await transporter.sendMail({
      from: `"${senderName}" <${senderEmail}>`,
      to: draft.contact_email,
      subject: draft.subject,
      text: draft.body,
      html: draft.body.replace(/\n/g, '<br>'),
    });

    session.drafts[idx].status = 'sent';
    session.drafts[idx].sent_at = new Date().toISOString();
    session.drafts[idx].message_id = info.messageId || '';
    session.updated_at = new Date();
    await session.save();

    res.json({ success: true, messageId: info.messageId, draft: session.drafts[idx] });
  } catch (err) {
    res.status(500).json({ error: `Send failed: ${err.message}` });
  }
});

// ── Send all approved drafts ──
router.post('/sessions/:id/send-approved', async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });

    const transporter = getTransporter();
    const senderEmail = process.env.OUTREACH_SENDER_EMAIL || process.env.OUTREACH_SMTP_USERNAME;
    const senderName = process.env.OUTREACH_SENDER_NAME || 'Sales Intelligence';
    const delay = parseInt(process.env.OUTREACH_SEND_DELAY || '2', 10) * 1000;

    const results = [];
    for (let i = 0; i < session.drafts.length; i++) {
      const draft = session.drafts[i];
      if (draft.status !== 'approved' || !draft.contact_email) continue;

      try {
        const info = await transporter.sendMail({
          from: `"${senderName}" <${senderEmail}>`,
          to: draft.contact_email,
          subject: draft.subject,
          text: draft.body,
          html: draft.body.replace(/\n/g, '<br>'),
        });
        session.drafts[i].status = 'sent';
        session.drafts[i].sent_at = new Date().toISOString();
        session.drafts[i].message_id = info.messageId || '';
        results.push({ idx: i, success: true, messageId: info.messageId });
      } catch (sendErr) {
        session.drafts[i].status = 'failed';
        session.drafts[i].send_error = sendErr.message;
        results.push({ idx: i, success: false, error: sendErr.message });
      }

      // Rate limit between sends
      if (delay > 0 && i < session.drafts.length - 1) {
        await new Promise(r => setTimeout(r, delay));
      }
    }

    session.updated_at = new Date();
    await session.save();

    const sent = results.filter(r => r.success).length;
    const failed = results.filter(r => !r.success).length;
    res.json({ sent, failed, results });
  } catch (err) {
    res.status(500).json({ error: `Batch send failed: ${err.message}` });
  }
});

// ── AI Rewrite — polish email body via LLM ──
router.post('/ai-rewrite', async (req, res) => {
  try {
    const { subject, body, contact_name, contact_company } = req.body;
    if (!body) return res.status(400).json({ error: 'Provide a body to rewrite' });

    const apiKey = process.env.PERSONALISATION_LLM_API_KEY;
    const baseUrl = process.env.PERSONALISATION_LLM_BASE_URL || 'https://inference.do-ai.run/v1';
    const model = process.env.PERSONALISATION_LLM_MODEL || 'openai-gpt-oss-120b';

    if (!apiKey) return res.status(500).json({ error: 'LLM API key not configured' });

    const systemPrompt = `You are an expert cold-email copywriter. Rewrite the given email to be more compelling, concise and professional while keeping the core message. Use a confident but friendly tone. Add a hook in the opening line. Keep it under 200 words. Output ONLY the rewritten email body — no subject line, no greeting prefix like "Hi [Name]" unless already present, no explanations.`;

    const userPrompt = [
      subject ? `Subject: ${subject}` : '',
      contact_name ? `Recipient: ${contact_name}${contact_company ? ` at ${contact_company}` : ''}` : '',
      '',
      'Original email:',
      body,
    ].filter(Boolean).join('\n');

    const llmRes = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
        temperature: 0.7,
        max_tokens: 800,
      }),
    });

    if (!llmRes.ok) {
      const errText = await llmRes.text();
      console.error('[ai-rewrite] LLM error:', llmRes.status, errText);
      return res.status(502).json({ error: 'LLM request failed' });
    }

    const llmData = await llmRes.json();
    const rewritten = llmData.choices?.[0]?.message?.content?.trim();
    if (!rewritten) return res.status(502).json({ error: 'LLM returned empty response' });

    res.json({ rewritten });
  } catch (err) {
    console.error('[ai-rewrite] Error:', err.message);
    res.status(500).json({ error: `AI rewrite failed: ${err.message}` });
  }
});

// ── Test email endpoint ──
router.post('/test-email', async (req, res) => {
  try {
    const { to } = req.body;
    if (!to) return res.status(400).json({ error: 'Provide "to" email address' });

    const transporter = getTransporter();
    const senderEmail = process.env.OUTREACH_SENDER_EMAIL || process.env.OUTREACH_SMTP_USERNAME;
    const senderName = process.env.OUTREACH_SENDER_NAME || 'Sales Intelligence';

    const info = await transporter.sendMail({
      from: `"${senderName}" <${senderEmail}>`,
      to,
      subject: 'Test Email - Sales Intelligence Agent',
      text: 'This is a test email from the Sales Intelligence Agent outreach system. If you received this, email sending is configured correctly!',
      html: '<h2>Test Email</h2><p>This is a test email from the <strong>Sales Intelligence Agent</strong> outreach system.</p><p>If you received this, email sending is configured correctly!</p>',
    });

    res.json({ success: true, messageId: info.messageId });
  } catch (err) {
    res.status(500).json({ error: `Test email failed: ${err.message}` });
  }
});

module.exports = router;
