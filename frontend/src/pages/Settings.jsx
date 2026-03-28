// eslint-disable-next-line no-unused-vars
import { motion } from 'framer-motion';
import { Key, Shield, Database, Terminal } from 'lucide-react';
import { TopBar } from '../components/layout/TopBar';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { prospects, researchDossiers, outreachDrafts, companies } from '../data/mockData';

const prospectingKeys = [
  { name: 'DigitalOcean AI (LLM)', key: 'PROSPECTING_LLM_API_KEY', required: true, desc: 'ICP interpretation + relevance scoring (openai-gpt-oss-120b)' },
  { name: 'Serper.dev', key: 'SERPER_API_KEY', required: false, desc: 'Google Search API — 2,500 free searches/month, no credit card. Best company & LinkedIn discovery.' },
  { name: 'Apollo.io', key: 'APOLLO_API_KEY', required: false, desc: 'Company and contact search (best source)' },
  { name: 'Hunter.io', key: 'HUNTER_API_KEY', required: false, desc: 'Email discovery + verification' },
  { name: 'Google CSE', key: 'GOOGLE_CSE_API_KEY', required: false, desc: 'Company discovery + LinkedIn lookup' },
  { name: 'OpenCorporates', key: 'OPENCORPORATES_API_TOKEN', required: false, desc: 'Company registry data' },
  { name: 'GitHub', key: 'GITHUB_TOKEN', required: false, desc: 'Org search, avoids rate limits' },
  { name: 'Product Hunt', key: 'PRODUCTHUNT_TOKEN', required: false, desc: 'Startup discovery' },
];

const researchKeys = [
  { name: 'OpenAI', key: 'OPENAI_API_KEY', required: true, desc: 'LLM synthesis (gpt-4o-mini)' },
  { name: 'Google CSE', key: 'GOOGLE_CSE_API_KEY', required: false, desc: 'Custom search engine' },
  { name: 'Google CSE CX', key: 'GOOGLE_CSE_CX', required: false, desc: 'Search engine ID' },
  { name: 'BuiltWith', key: 'BUILTWITH_API_KEY', required: false, desc: 'Tech stack detection (free tier works)' },
];

const personalisationKeys = [
  { name: 'DigitalOcean AI', key: 'PERSONALISATION_LLM_API_KEY', required: true, desc: 'OpenAI-compatible LLM endpoint (DigitalOcean)' },
  { name: 'Base URL', key: 'PERSONALISATION_LLM_BASE_URL', required: false, desc: 'Default: https://inference.do-ai.run/v1' },
  { name: 'Model', key: 'PERSONALISATION_LLM_MODEL', required: false, desc: 'Default: openai-gpt-oss-120b' },
];

function KeyRow({ api }) {
  return (
    <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-slate-50 border border-slate-200">
      <div>
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold text-deep-blue">{api.name}</p>
          {api.required && <span className="text-[10px] font-bold text-accent-red uppercase">Required</span>}
        </div>
        <p className="text-[11px] text-slate-400">{api.desc}</p>
      </div>
      <code className="text-[11px] text-slate-500 font-mono bg-white px-2 py-1 rounded border border-slate-200">{api.key}</code>
    </div>
  );
}

export default function Settings() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
      <TopBar title="Settings" subtitle="Pipeline configuration and environment" />

      <div className="p-6 max-w-4xl space-y-5">
        <Card flat className="!p-5 space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b-2 border-slate-200">
            <div className="p-2 rounded-xl bg-electric-blue border-2 border-border-brutal">
              <Key className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-display text-deep-blue">Prospecting Agent Keys</h3>
              <p className="text-[11px] text-slate-400">Set these in <code className="bg-white px-1 rounded font-mono">.env</code> at the project root</p>
            </div>
          </div>
          <div className="space-y-2.5">
            {prospectingKeys.map((api) => <KeyRow key={api.key} api={api} />)}
          </div>
        </Card>

        <Card flat className="!p-5 space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b-2 border-slate-200">
            <div className="p-2 rounded-xl bg-sky-blue border-2 border-border-brutal">
              <Key className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-display text-deep-blue">Research Agent Keys</h3>
              <p className="text-[11px] text-slate-400">OpenAI is required for LLM synthesis; others are optional boosters</p>
            </div>
          </div>
          <div className="space-y-2.5">
            {researchKeys.map((api) => <KeyRow key={api.key} api={api} />)}
          </div>
        </Card>

        <Card flat className="!p-5 space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b-2 border-slate-200">
            <div className="p-2 rounded-xl bg-purple-500 border-2 border-border-brutal">
              <Key className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-display text-deep-blue">Personalisation Agent Keys</h3>
              <p className="text-[11px] text-slate-400">DigitalOcean AI inference for outreach draft generation</p>
            </div>
          </div>
          <div className="space-y-2.5">
            {personalisationKeys.map((api) => <KeyRow key={api.key} api={api} />)}
          </div>
        </Card>

        <Card flat className="!p-5 space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b-2 border-slate-200">
            <div className="p-2 rounded-xl bg-accent-yellow border-2 border-border-brutal">
              <Shield className="w-4 h-4 text-deep-blue" strokeWidth={2.5} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-display text-deep-blue">Outreach Safety</h3>
              <p className="text-[11px] text-slate-400">All messages are queued for human review -- never auto-sent</p>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-slate-50 border border-slate-200">
              <div>
                <p className="text-sm font-semibold text-deep-blue">Manual review required</p>
                <p className="text-[11px] text-slate-400">Backend enforces status=review_required on every prospect</p>
              </div>
              <div className="w-11 h-6 bg-accent-green rounded-full border-2 border-border-brutal relative">
                <div className="absolute right-0.5 top-0.5 w-4 h-4 bg-white rounded-full border border-border-brutal shadow" />
              </div>
            </div>

            <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-slate-50 border border-slate-200">
              <div>
                <p className="text-sm font-semibold text-deep-blue">Minimum prospect score</p>
                <p className="text-[11px] text-slate-400">Research agent default: --min-score 30</p>
              </div>
              <span className="text-sm font-bold text-electric-blue text-display">30</span>
            </div>

            <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-amber-50 border border-amber-200">
              <div>
                <p className="text-sm font-semibold text-deep-blue">Mock Data Fallback</p>
                <p className="text-[11px] text-slate-400">When API credits are exhausted, pipeline returns ICP-matched demo leads (labelled <code className="bg-white px-1 rounded font-mono">mock_fallback</code>)</p>
              </div>
              <code className="text-[11px] text-slate-500 font-mono bg-white px-2 py-1 rounded border border-slate-200">ENABLE_MOCK_FALLBACK=true</code>
            </div>
          </div>
        </Card>

        <Card flat className="!p-5 space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b-2 border-slate-200">
            <div className="p-2 rounded-xl bg-deep-blue border-2 border-border-brutal">
              <Database className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-display text-deep-blue">Current Data</h3>
              <p className="text-[11px] text-slate-400">From output/ directory</p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Companies', value: companies.length },
              { label: 'Prospects', value: prospects.length },
              { label: 'Dossiers', value: researchDossiers.length },
              { label: 'Outreach Drafts', value: outreachDrafts.length },
            ].map((s) => (
              <div key={s.label} className="px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-center">
                <p className="text-xl font-bold text-deep-blue text-display">{s.value}</p>
                <p className="text-[11px] text-slate-400">{s.label}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card flat className="!p-5 space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b-2 border-slate-200">
            <div className="p-2 rounded-xl bg-slate-600 border-2 border-border-brutal">
              <Terminal className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-display text-deep-blue">CLI Reference</h3>
              <p className="text-[11px] text-slate-400">Run these from the project root</p>
            </div>
          </div>

          <div className="space-y-3 text-sm">
            <div className="bg-slate-900 text-slate-100 rounded-xl p-4 font-mono text-xs leading-relaxed space-y-1">
              <p className="text-slate-500"># 1a. Prospect (natural language -- LLM interprets your intent)</p>
              <p>python run.py prospect --prompt "AI invoice tool for freelancers" --out output</p>
              <p className="text-slate-500 mt-3"># 1b. Prospect (structured JSON ICP)</p>
              <p>python run.py prospect --icp templates/icp.sample.json --out output</p>
              <p className="text-slate-500 mt-3"># 2. Research</p>
              <p>python run.py research --queue output/prospect_queue.json \</p>
              <p className="pl-6">--icp output/icp_resolved.json --out output/research</p>
              <p className="text-slate-500 mt-3"># 3. Personalise</p>
              <p>python run.py personalise --dossiers output/research/research_dossiers.json \</p>
              <p className="pl-6">--icp output/icp_resolved.json --out output/personalisation</p>
            </div>
          </div>
        </Card>
      </div>
    </motion.div>
  );
}
