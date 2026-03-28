const mongoose = require('mongoose');

const trackingDb = mongoose.connection.useDb('tracking_agent');

const responseSchema = new mongoose.Schema({
  id: String,
  outreach_message_id: String,
  contact_name: String,
  contact_company: String,
  contact_email: String,
  subject: String,
  body: String,
  received_at: String,
  warmth: { type: String, default: 'unknown' },
  sentiment: { type: String, default: 'unknown' },
  key_points: [String],
  needs_follow_up: { type: Boolean, default: false },
  auto_classified: { type: Boolean, default: false },
}, { _id: false });

const followUpSchema = new mongoose.Schema({
  id: String,
  response_id: String,
  outreach_message_id: String,
  contact_name: String,
  contact_company: String,
  contact_email: String,
  subject: String,
  body: String,
  follow_up_number: { type: Number, default: 1 },
  status: { type: String, default: 'draft' },
  sent_at: String,
  message_id: String,
  created_at: String,
}, { _id: false });

const trackingEntrySchema = new mongoose.Schema({
  outreach_message_id: String,
  contact_name: String,
  contact_company: String,
  contact_email: String,
  original_subject: String,
  status: { type: String, default: 'sent' },
  sent_at: String,
  opened_at: String,
  replied_at: String,
  reply_snippet: String,
  is_warm: { type: Boolean, default: false },
  warmth: { type: String, default: 'unknown' },
  follow_up_count: { type: Number, default: 0 },
  responses: [responseSchema],
  follow_ups: [followUpSchema],
  last_activity_at: String,
}, { _id: false });

const sessionSchema = new mongoose.Schema({
  session_name: { type: String, required: true },
  outreach_session_id: String,
  entries: [trackingEntrySchema],
  funnel: {
    prospects: Number,
    researched: Number,
    drafted: Number,
    sent: Number,
    opened: Number,
    replied: Number,
  },
  summary: {
    total_tracked: Number,
    sent: Number,
    opened: Number,
    replied: Number,
    warm_leads: Number,
    no_response: Number,
    follow_ups_generated: Number,
    follow_ups_sent: Number,
    open_rate: Number,
    reply_rate: Number,
  },
  status: { type: String, default: 'completed' },
  created_at: { type: Date, default: Date.now },
  updated_at: { type: Date, default: Date.now },
});

sessionSchema.pre('save', function () { this.updated_at = new Date(); });

module.exports = trackingDb.model('Session', sessionSchema, 'sessions');
