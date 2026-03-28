const mongoose = require('mongoose');

const outreachDb = mongoose.connection.useDb('outreach_agent');

const draftSchema = new mongoose.Schema({
  id: String,
  contact_name: String,
  contact_company: String,
  contact_title: String,
  contact_email: String,
  contact_linkedin: String,
  subject: String,
  body: String,
  personalization_score: Number,
  personalization_signals: [String],
  prospect_score: Number,
  research_confidence: Number,
  status: { type: String, default: 'draft' },
  reviewer_notes: { type: String, default: '' },
  approved_at: String,
  scheduled_at: String,
  sent_at: String,
  delivered_at: String,
  message_id: String,
  send_error: String,
  created_at: String,
}, { _id: false });

const sessionSchema = new mongoose.Schema({
  session_name: { type: String, required: true },
  prospecting_session_id: String,
  research_session_id: String,
  drafts: [draftSchema],
  summary: {
    total_drafts: Number,
    approved: Number,
    sent: Number,
    failed: Number,
    rejected: Number,
    skipped_no_email: Number,
    avg_personalization_score: Number,
    statuses: mongoose.Schema.Types.Mixed,
  },
  status: { type: String, default: 'completed' },
  created_at: { type: Date, default: Date.now },
  updated_at: { type: Date, default: Date.now },
});

sessionSchema.pre('save', function () { this.updated_at = new Date(); });

module.exports = outreachDb.model('Session', sessionSchema, 'sessions');
