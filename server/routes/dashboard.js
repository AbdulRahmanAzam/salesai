const express = require('express');
const router = express.Router();
const ProspectingSession = require('../models/ProspectingSession');
const ResearchSession = require('../models/ResearchSession');
const OutreachSession = require('../models/OutreachSession');
const TrackingSession = require('../models/TrackingSession');

router.get('/summary', async (req, res) => {
  try {
    const [prospecting, research, outreach, tracking] = await Promise.all([
      ProspectingSession.find()
        .select('session_name summary.drafts summary.avg_score status created_at')
        .sort({ created_at: -1 }).limit(10).lean(),
      ResearchSession.find()
        .select('session_name summary.total_dossiers status created_at')
        .sort({ created_at: -1 }).limit(10).lean(),
      OutreachSession.find()
        .select('session_name summary.total_drafts summary.avg_personalization_score status created_at')
        .sort({ created_at: -1 }).limit(10).lean(),
      TrackingSession.find()
        .select('session_name summary.total_tracked summary.warm_leads status created_at')
        .sort({ created_at: -1 }).limit(10).lean(),
    ]);

    const totalLeads = prospecting.reduce((s, p) => s + (p.summary?.drafts || 0), 0);
    const totalDossiers = research.reduce((s, r) => s + (r.summary?.total_dossiers || 0), 0);
    const totalDrafts = outreach.reduce((s, o) => s + (o.summary?.total_drafts || 0), 0);
    const totalTracked = tracking.reduce((s, t) => s + (t.summary?.total_tracked || 0), 0);

    res.json({
      counts: {
        prospecting_sessions: prospecting.length,
        research_sessions: research.length,
        outreach_sessions: outreach.length,
        tracking_sessions: tracking.length,
        total_leads: totalLeads,
        total_dossiers: totalDossiers,
        total_drafts: totalDrafts,
        total_tracked: totalTracked,
      },
      recent: {
        prospecting: prospecting.slice(0, 5),
        research: research.slice(0, 5),
        outreach: outreach.slice(0, 5),
        tracking: tracking.slice(0, 5),
      },
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
