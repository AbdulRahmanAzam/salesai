const mongoose = require('mongoose');

const prospectingDb = mongoose.connection.useDb('prospecting_agent');

const leadSchema = new mongoose.Schema({
  contact: {
    full_name: String,
    title: String,
    company_name: String,
    company_domain: String,
    email: String,
    linkedin_url: String,
    phone: String,
    location: String,
    source: String,
    source_url: String,
    confidence: Number,
    signals: [String],
    research_notes: [String],
  },
  company: {
    name: String,
    domain: String,
    description: String,
    industry: String,
  },
  score: Number,
  reasons: [String],
  relevance_explanation: String,
  status: { type: String, default: 'review_required' },
  generated_at: String,
}, { _id: false });

const sessionSchema = new mongoose.Schema({
  session_name: { type: String, required: true },
  prompt: String,
  icp: mongoose.Schema.Types.Mixed,
  resolved_icp: mongoose.Schema.Types.Mixed,
  leads: [leadSchema],
  summary: {
    companies: Number,
    contacts: Number,
    contacts_with_email: Number,
    contacts_with_linkedin: Number,
    drafts: Number,
    llm_scoring: Boolean,
    avg_score: Number,
  },
  status: { type: String, default: 'completed' },
  created_at: { type: Date, default: Date.now },
  updated_at: { type: Date, default: Date.now },
});

sessionSchema.pre('save', function () { this.updated_at = new Date(); });

module.exports = prospectingDb.model('Session', sessionSchema, 'sessions');
