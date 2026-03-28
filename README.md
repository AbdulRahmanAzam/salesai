## SalesFlow AI

**Team:** Azama

**Theme & Challenge:** Theme 3 — Multi-Agent Orchestration for Sales Intelligence

**Track:** Hard

### Demo

[[Link to demo video]](https://youtu.be/_XkuIMCGghE)

### Problem statement

B2B sales teams waste hours manually prospecting, researching leads, writing personalised outreach, and tracking responses across disconnected tools. SalesFlow AI automates the entire sales intelligence pipeline end-to-end — from lead discovery to follow-up — using cooperating AI agents that work on free/freemium APIs, making it accessible to startups with near-zero budget.

### Why multi-agent?

Each stage of the sales pipeline requires fundamentally different skills and data sources. A single monolithic agent cannot effectively handle ICP interpretation, multi-source lead discovery, deep research synthesis, personalised copywriting, email delivery, and response classification. By decomposing the workflow into five specialised agents, each can operate with its own tools, prompts, and logic — and run in parallel where possible. The agents form a sequential pipeline where each agent's output feeds the next, but they can also be invoked independently, enabling flexible orchestration and human-in-the-loop review between stages.

### Agent architecture

| Agent | Role |
|-------|------|
| **Prospecting Agent** | Interprets the Ideal Customer Profile (ICP) via LLM, discovers companies from Hacker News Algolia and Apollo, enriches contacts through Hunter.io domain search, deduplicates with fuzzy matching, and scores/prioritises leads based on tech overlap, recency, and multi-source verification. |
| **Research Agent** | Takes the prospect queue and builds rich dossiers per lead by pulling data from Google News RSS, Hacker News, GitHub API, DEV.to, Medium RSS, BuiltWith, and Google Custom Search — then synthesises everything via LLM into talking points, pain points, and relevance summaries. |
| **Personalisation Agent** | Consumes research dossiers and generates tailored outreach drafts per lead using LLM, referencing real data points from the dossier to craft genuine, non-generic messaging with confidence scoring. |
| **Outreach Agent** | Manages the email delivery pipeline — queues reviewed drafts, supports auto-approve thresholds, sends via SMTP (Nodemailer), and logs delivery status. Operates in queue/approve/send/status modes. |
| **Tracking Agent** | Monitors IMAP inbox for responses, classifies reply sentiment and intent via LLM (interested, objection, out-of-office, etc.), generates follow-up drafts for leads that need them, and sends approved follow-ups. |

### How to run

**Prerequisites:** Python 3.11+, Node.js 18+

#### 1. Clone and install Python dependencies

```bash
git clone <repo-url> && cd sales
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

#### 2. Configure environment

Copy `.env.example` to `.env` and set your API keys:

```
OPENAI_API_KEY=...          # Required — LLM for ICP interpretation, research synthesis, drafting
HUNTER_API_KEY=...          # Optional — contact enrichment via Hunter.io
APOLLO_API_KEY=...          # Optional — company enrichment via Apollo
GITHUB_TOKEN=...            # Optional — GitHub research source
GOOGLE_CSE_API_KEY=...      # Optional — Google Custom Search
GOOGLE_CSE_CX=...           # Optional — Google CSE engine ID
SMTP_HOST=...               # Required for outreach sending
SMTP_USER=...
SMTP_PASS=...
IMAP_HOST=...               # Required for tracking
IMAP_USER=...
IMAP_PASS=...
```

#### 3. Run the agents (CLI)

```bash
# Prospecting — discover and score leads
python run.py prospect --icp templates/icp.sample.json --out output --max-leads 50

# Research — build dossiers on prospects
python run.py research --queue output/prospect_queue.json --icp templates/icp.sample.json --out output/research --max-research 20

# Personalisation — generate outreach drafts
python run.py personalise --dossiers output/research/research_dossiers.json --icp templates/icp.sample.json --out output/personalisation

# Outreach — queue and send emails
python run.py outreach --drafts output/personalisation/outreach_drafts.json --out output/outreach --action queue

# Tracking — check for responses and generate follow-ups
python run.py tracking --queue output/outreach/outreach_queue.json --out output/tracking --action check
```

#### 4. Run the dashboard (optional)

```bash
# Start the API server
cd server && npm install && npm run dev

# In another terminal, start the frontend
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173` to view the pipeline dashboard.



### Tech stack

| Category | Technologies |
|----------|-------------|
| **Backend agents** | Python 3.11, OpenAI SDK, Requests, BeautifulSoup, lxml |
| **LLM** | DigitalOcean AI Inference (`openai-gpt-oss-120b`) via OpenAI-compatible API |
| **API server** | Node.js, Express 5, Mongoose, Nodemailer |
| **Frontend** | React 19, Vite 8, Tailwind CSS 4, Recharts, Framer Motion, React Router 7 |
| **Data sources** | Hacker News Algolia, Apollo, Hunter.io, GitHub API, Google News RSS, DEV.to, Medium RSS, BuiltWith, Google Custom Search, DuckDuckGo Search |
| **Database** | MongoDB (via Mongoose) |
