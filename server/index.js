const path = require('path');
// Load root .env first (has all API keys), then server/.env (has MongoDB + PORT)
require('dotenv').config({ path: path.resolve(__dirname, '..', '.env') });
require('dotenv').config(); // server/.env — won't overwrite already-set vars
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 4000;

app.use(cors());
app.use(express.json({ limit: '10mb' }));

const prospectingRoutes = require('./routes/prospecting');
const researchRoutes = require('./routes/research');
const outreachRoutes = require('./routes/outreach');
const trackingRoutes = require('./routes/tracking');
const dashboardRoutes = require('./routes/dashboard');

app.use('/api/prospecting', prospectingRoutes);
app.use('/api/research', researchRoutes);
app.use('/api/outreach', outreachRoutes);
app.use('/api/tracking', trackingRoutes);
app.use('/api/dashboard', dashboardRoutes);

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', mongo: mongoose.connection.readyState === 1 ? 'connected' : 'disconnected' });
});

// ── Config status: which API keys are present? ──
app.get('/api/config/status', (req, res) => {
  const check = (key) => !!process.env[key];
  res.json({
    apollo: check('APOLLO_API_KEY'),
    hunter: check('HUNTER_API_KEY'),
    google_cse: check('GOOGLE_CSE_API_KEY') && check('GOOGLE_CSE_CX'),
    github: check('GITHUB_TOKEN'),
    prospecting_llm: check('PROSPECTING_LLM_API_KEY'),
    research_llm: check('RESEARCH_LLM_API_KEY'),
    personalisation_llm: check('PERSONALISATION_LLM_API_KEY'),
    tracking_llm: check('TRACKING_LLM_API_KEY'),
    producthunt: check('PRODUCTHUNT_TOKEN'),
  });
});

mongoose.connect(process.env.MONGODB_URI, {
  dbName: 'sales_agent',
})
  .then(() => {
    console.log('MongoDB connected');
    app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
  })
  .catch((err) => {
    console.error('MongoDB connection error:', err.message);
    process.exit(1);
  });
