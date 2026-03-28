import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Target, X, Plus, Rocket, RotateCcw, Zap, ChevronDown, MessageSquare, Settings2, Sparkles, ArrowRight } from 'lucide-react';
import { TopBar } from '../components/layout/TopBar';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { HistoryPanel } from '../components/ui/HistoryPanel';
import { useSessions } from '../hooks/useSessions';
import { prospecting } from '../services/api';
import { icpDefaults, icpPresets } from '../data/mockData';

function TagInput({ label, tags, onChange, placeholder }) {
  const [input, setInput] = useState('');

  function addTag() {
    const val = input.trim();
    if (val && !tags.includes(val)) {
      onChange([...tags, val]);
    }
    setInput('');
  }

  function removeTag(tag) {
    onChange(tags.filter((t) => t !== tag));
  }

  return (
    <div>
      <label className="block text-sm font-bold text-display text-deep-blue mb-2">{label}</label>
      <div className="flex flex-wrap gap-2 p-3 neu-input min-h-[48px]">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 bg-sky-blue/20 text-deep-blue text-xs font-semibold px-2.5 py-1 rounded-lg border-2 border-deep-blue/30"
          >
            {tag}
            <button onClick={() => removeTag(tag)} className="hover:text-accent-red transition-colors cursor-pointer">
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); addTag(); }
            if (e.key === 'Backspace' && !input && tags.length) removeTag(tags[tags.length - 1]);
          }}
          placeholder={tags.length === 0 ? placeholder : ''}
          className="outline-none bg-transparent text-sm flex-1 min-w-[120px]"
        />
      </div>
    </div>
  );
}

function SliderField({ label, value, onChange, min = 1, max = 500, step = 1 }) {
  return (
    <div>
      <label className="block text-sm font-bold text-display text-deep-blue mb-2">
        {label}: <span className="text-electric-blue">{value}</span>
      </label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-3 bg-slate-200 rounded-full appearance-none cursor-pointer accent-electric-blue
          [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-6 [&::-webkit-slider-thumb]:h-6
          [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-electric-blue
          [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-border-brutal
          [&::-webkit-slider-thumb]:shadow-[2px_2px_0_var(--color-border-brutal)]
          [&::-webkit-slider-thumb]:cursor-pointer"
      />
      <div className="flex justify-between text-[10px] text-slate-400 mt-1">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

const nlExamples = [
  "My product is an AI invoice tool for freelance developers in the US with 1-10 employees.",
  "I have full stack development skills and want to find clients who need websites built.",
  "We sell a Kubernetes monitoring SaaS to mid-size DevOps teams in Europe.",
  "I'm a graphic designer looking for startups that need branding and logo work.",
];

export default function ICPSetup() {
  const navigate = useNavigate();
  const {
    sessions, loading: histLoading, error: histError,
    deleteSession, fetchSessions,
  } = useSessions(prospecting);

  const [mode, setMode] = useState('natural');
  const [form, setForm] = useState({ ...icpDefaults });
  const [nlPrompt, setNlPrompt] = useState('');
  const [toast, setToast] = useState(null);
  const [showPresets, setShowPresets] = useState(false);
  const [showJson, setShowJson] = useState(false);

  function update(key, val) {
    setForm((f) => ({ ...f, [key]: val }));
  }

  function loadPreset(preset) {
    setForm({ ...preset.value });
    setMode('structured');
    setShowPresets(false);
    setToast(`Loaded "${preset.label}" preset`);
    setTimeout(() => setToast(null), 2500);
  }

  function handleRunNL() {
    if (!nlPrompt.trim()) return;
    navigate('/pipeline-run', { state: { prompt: nlPrompt } });
  }

  function handleRunStructured() {
    navigate('/pipeline-run', { state: { icp: form } });
  }

  function handleReset() {
    setForm({ ...icpDefaults });
    setNlPrompt('');
  }

  function exportJson() {
    const json = JSON.stringify(form, null, 2);
    navigator.clipboard.writeText(json).then(() => {
      setToast('ICP JSON copied to clipboard!');
      setTimeout(() => setToast(null), 2500);
    });
  }

  function handleHistoryLoad(id) {
    navigate('/pipeline-run', { state: { sessionId: id } });
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <TopBar title="Ideal Customer Profile" subtitle="Tell us who you're looking for -- in plain English or structured fields" />

      <div className="p-6 max-w-4xl space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Mode Toggle */}
          <div className="flex items-center gap-2 p-1 bg-slate-100 rounded-xl border-2 border-slate-200 w-fit">
          <button
            onClick={() => setMode('natural')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all cursor-pointer ${
              mode === 'natural'
                ? 'bg-white text-deep-blue shadow-[2px_2px_0_var(--color-border-brutal)] border-2 border-border-brutal'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            Natural Language
          </button>
          <button
            onClick={() => setMode('structured')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all cursor-pointer ${
              mode === 'structured'
                ? 'bg-white text-deep-blue shadow-[2px_2px_0_var(--color-border-brutal)] border-2 border-border-brutal'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <Settings2 className="w-4 h-4" />
            Structured Fields
          </button>
          </div>

          <HistoryPanel
            sessions={sessions}
            loading={histLoading}
            error={histError}
            onLoad={handleHistoryLoad}
            onDelete={deleteSession}
            onRetry={fetchSessions}
            agentName="Prospecting Agent"
            accentColor="bg-electric-blue"
            renderMeta={(s) => (
              <div className="flex flex-wrap gap-1.5">
                {s.summary?.drafts != null && (
                  <span className="text-[10px] bg-sky-blue/10 text-deep-blue px-1.5 py-0.5 rounded">{s.summary.drafts} leads</span>
                )}
                {s.summary?.avg_score != null && (
                  <span className="text-[10px] bg-accent-green/10 text-accent-green px-1.5 py-0.5 rounded">avg {s.summary.avg_score}</span>
                )}
                {s.resolved_icp?.product_name && (
                  <span className="text-[10px] bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded truncate max-w-[200px]">{s.resolved_icp.product_name}</span>
                )}
              </div>
            )}
          />
        </div>

        <AnimatePresence mode="wait">
          {mode === 'natural' ? (
            <motion.div
              key="natural"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="space-y-5"
            >
              <Card flat className="!p-6">
                <div className="flex items-center gap-3 pb-4 border-b-2 border-slate-200 mb-5">
                  <div className="p-2.5 rounded-xl bg-purple-500 border-2 border-border-brutal">
                    <Sparkles className="w-5 h-5 text-white" strokeWidth={2.5} />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-display text-deep-blue">Describe Your Ideal Leads</h2>
                    <p className="text-xs text-slate-400">
                      Just tell us what you do. Our AI interprets your description, figures out who your ideal customers are,
                      and generates a full ICP automatically.
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  <textarea
                    value={nlPrompt}
                    onChange={(e) => setNlPrompt(e.target.value)}
                    rows={4}
                    placeholder="e.g. My product is an AI invoice tool for freelance developers in the US with 1-10 employees."
                    className="neu-input w-full resize-none text-base leading-relaxed"
                  />

                  <div>
                    <p className="text-[11px] font-bold text-slate-400 uppercase mb-2">Try an example:</p>
                    <div className="flex flex-wrap gap-2">
                      {nlExamples.map((ex) => (
                        <button
                          key={ex}
                          onClick={() => setNlPrompt(ex)}
                          className="text-[11px] text-slate-500 bg-slate-50 hover:bg-sky-blue/10 hover:text-deep-blue px-3 py-1.5 rounded-lg border border-slate-200 hover:border-electric-blue transition-all cursor-pointer"
                        >
                          {ex.length > 65 ? ex.slice(0, 65) + '...' : ex}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 space-y-2">
                    <p className="text-xs font-bold text-deep-blue text-display">How it works</p>
                    <div className="flex items-start gap-3 text-xs text-slate-500">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center font-bold text-[10px] shrink-0">1</span>
                        Your description
                      </div>
                      <ArrowRight className="w-3 h-3 mt-0.5 shrink-0 text-slate-300" />
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center font-bold text-[10px] shrink-0">2</span>
                        LLM interprets intent
                      </div>
                      <ArrowRight className="w-3 h-3 mt-0.5 shrink-0 text-slate-300" />
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center font-bold text-[10px] shrink-0">3</span>
                        Structured ICP generated
                      </div>
                      <ArrowRight className="w-3 h-3 mt-0.5 shrink-0 text-slate-300" />
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center font-bold text-[10px] shrink-0">4</span>
                        Leads discovered
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 pt-2">
                    <Button icon={Rocket} onClick={handleRunNL} disabled={!nlPrompt.trim()}>
                      Run Prospecting Agent
                    </Button>
                    <span className="text-xs text-slate-400">
                      Uses <code className="bg-slate-100 px-1 rounded font-mono text-[10px]">python run.py prospect --prompt "..."</code>
                    </span>
                  </div>
                </div>
              </Card>
            </motion.div>
          ) : (
            <motion.div
              key="structured"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="space-y-5"
            >
              {/* Presets */}
              <Card flat className="!p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-accent-yellow" />
                    <h3 className="text-sm font-bold text-display text-deep-blue">Quick Start -- Load a Preset</h3>
                  </div>
                  <button onClick={() => setShowPresets(s => !s)} className="text-xs text-electric-blue font-semibold flex items-center gap-1 cursor-pointer hover:underline">
                    {showPresets ? 'Hide' : 'Show'} presets <ChevronDown className={`w-3 h-3 transition-transform ${showPresets ? 'rotate-180' : ''}`} />
                  </button>
                </div>
                {showPresets && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {icpPresets.map((preset) => (
                      <button
                        key={preset.label}
                        onClick={() => loadPreset(preset)}
                        className="text-left p-3 rounded-xl border-2 border-slate-200 hover:border-electric-blue hover:shadow-[3px_3px_0_var(--color-electric-blue)] transition-all cursor-pointer group"
                      >
                        <p className="text-sm font-bold text-deep-blue group-hover:text-electric-blue">{preset.label}</p>
                        <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">{preset.value.product_pitch}</p>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {preset.value.persona_titles.slice(0, 3).map(t => (
                            <span key={t} className="text-[10px] bg-sky-blue/10 text-deep-blue px-1.5 py-0.5 rounded border border-sky-blue/30">{t}</span>
                          ))}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </Card>

              {/* Structured Form */}
              <Card flat className="!p-6 space-y-6">
                <div className="flex items-center gap-3 pb-4 border-b-2 border-slate-200">
                  <div className="p-2.5 rounded-xl bg-accent-yellow border-2 border-border-brutal">
                    <Target className="w-5 h-5 text-deep-blue" strokeWidth={2.5} />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-display text-deep-blue">Configure Your ICP</h2>
                    <p className="text-xs text-slate-400">
                      This generates the JSON file consumed by{' '}
                      <code className="bg-slate-100 px-1 rounded text-[11px] text-deep-blue font-mono">python run.py prospect --icp icp.json</code>
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-bold text-display text-deep-blue mb-2">Product Name</label>
                    <input
                      value={form.product_name}
                      onChange={(e) => update('product_name', e.target.value)}
                      className="neu-input w-full"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-bold text-display text-deep-blue mb-2">Product Pitch</label>
                    <textarea
                      value={form.product_pitch}
                      onChange={(e) => update('product_pitch', e.target.value)}
                      rows={3}
                      className="neu-input w-full resize-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <TagInput label="Target Industries" tags={form.industries} onChange={(v) => update('industries', v)} placeholder="e.g. SaaS, Fintech" />
                  <TagInput label="Persona Titles" tags={form.persona_titles} onChange={(v) => update('persona_titles', v)} placeholder="e.g. CTO, VP Eng" />
                  <TagInput label="Tech Stack" tags={form.tech_stack} onChange={(v) => update('tech_stack', v)} placeholder="e.g. kubernetes, aws" />
                  <TagInput label="Keywords" tags={form.keywords} onChange={(v) => update('keywords', v)} placeholder="e.g. incident response" />
                  <TagInput label="Locations" tags={form.locations} onChange={(v) => update('locations', v)} placeholder="e.g. United States" />
                  <TagInput label="Employee Ranges" tags={form.employee_ranges} onChange={(v) => update('employee_ranges', v)} placeholder='e.g. 51,200 (comma-separated min,max)' />
                  <TagInput label="Exclude Domains" tags={form.exclude_domains} onChange={(v) => update('exclude_domains', v)} placeholder="e.g. example.com" />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
                  <SliderField label="Max Companies" value={form.max_companies} onChange={(v) => update('max_companies', v)} min={5} max={500} step={5} />
                  <SliderField label="Max Contacts" value={form.max_contacts} onChange={(v) => update('max_contacts', v)} min={10} max={1000} step={10} />
                </div>

                <div className="flex items-center gap-3 pt-4 border-t-2 border-slate-200 flex-wrap">
                  <Button icon={Rocket} onClick={handleRunStructured}>Run Prospecting Agent</Button>
                  <Button variant="secondary" icon={RotateCcw} onClick={handleReset}>Reset to Defaults</Button>
                  <Button variant="ghost" size="sm" onClick={exportJson}>Copy JSON</Button>
                  <Button variant="ghost" size="sm" onClick={() => setShowJson(j => !j)}>{showJson ? 'Hide' : 'Show'} JSON Preview</Button>
                </div>

                {showJson && (
                  <pre className="text-xs bg-slate-50 border-2 border-slate-200 rounded-xl p-4 overflow-auto max-h-80 font-mono text-slate-600">
                    {JSON.stringify(form, null, 2)}
                  </pre>
                )}
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-6 right-6 neu-card-flat !p-4 bg-accent-green text-white flex items-center gap-2 z-50"
          >
            <Rocket className="w-4 h-4" />
            <span className="text-sm font-semibold">{toast}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
