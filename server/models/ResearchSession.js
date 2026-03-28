const mongoose = require('mongoose');

const researchDb = mongoose.connection.useDb('research_agent');

const dossierSchema = new mongoose.Schema({
  contact_name: String,
  contact_company: String,
  contact_title: String,
  prospect_score: Number,
  research_confidence: Number,
  company_profile: mongoose.Schema.Types.Mixed,
  person_profile: mongoose.Schema.Types.Mixed,
  talking_points: [String],
  pain_points: [String],
  relevance_summary: String,
  sources_consulted: [String],
  generated_at: String,
}, { _id: false });

const sessionSchema = new mongoose.Schema({
  session_name: { type: String, required: true },
  prospecting_session_id: String,
  dossiers: [dossierSchema],
  icp: mongoose.Schema.Types.Mixed,
  summary: {
    total_dossiers: Number,
    avg_confidence: Number,
    sources_used: [String],
  },
  status: { type: String, default: 'completed' },
  created_at: { type: Date, default: Date.now },
  updated_at: { type: Date, default: Date.now },
});

sessionSchema.pre('save', function () { this.updated_at = new Date(); });

module.exports = researchDb.model('Session', sessionSchema, 'sessions');
