import { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, Building2, Users, Mail, BarChart3,
  CheckCircle2, Loader2, Clock, ArrowRight, Copy,
  Link2, Globe, ChevronDown, ChevronUp, ExternalLink,
  XCircle, Save,
} from 'lucide-react';
import { TopBar } from '../components/layout/TopBar';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge, StatusBadge } from '../components/ui/Badge';
import { ScoreRing } from '../components/ui/ScoreRing';
import { HistoryPanel } from '../components/ui/HistoryPanel';
import { useSessions } from '../hooks/useSessions';
import { prospecting } from '../services/api';
import { runPipeline } from '../services/pipelineRunner';

const STEP_CONFIG = [
  { icon: Sparkles, label: 'Interpreting ICP', color: 'text-purple-500' },
  { icon: Building2, label: 'Discovering companies', color: 'text-electric-blue' },
  { icon: Users, label: 'Finding contacts', color: 'text-sky-blue' },
  { icon: Mail, label: 'Enriching leads', color: 'text-accent-green' },
  { icon: BarChart3, label: 'Scoring & ranking', color: 'text-accent-orange' },
];

function StepIndicator({ steps }) {
  return (
    <div className="space-y-3">
      {STEP_CONFIG.map((cfg, i) => {
        const step = steps[i];
        const Icon = cfg.icon;
        const isDone = step?.status === 'done';
        const isRunning = step?.status === 'running';
        const isPending = !step || step.status === 'pending';

        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 transition-all ${
              isDone
                ? 'bg-green-50 border-green-300'
                : isRunning
                  ? 'bg-blue-50 border-electric-blue'
                  : 'bg-slate-50 border-slate-200'
            }`}
          >
            <div className={`p-1.5 rounded-lg ${isDone ? 'bg-accent-green' : isRunning ? 'bg-electric-blue' : 'bg-slate-300'}`}>
              {isDone
                ? <CheckCircle2 className="w-4 h-4 text-white" />
                : isRunning
                  ? <Loader2 className="w-4 h-4 text-white animate-spin" />
                  : <Clock className="w-4 h-4 text-white" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-semibold ${isDone ? 'text-green-700' : isRunning ? 'text-deep-blue' : 'text-slate-400'}`}>
                {step?.label || cfg.label}
              </p>
            </div>
            {isDone && <CheckCircle2 className="w-4 h-4 text-accent-green shrink-0" />}
            {isRunning && <Loader2 className="w-4 h-4 text-electric-blue animate-spin shrink-0" />}
          </motion.div>
        );
      })}
    </div>
  );
}

function ICPCard({ icp }) {
  const [expanded, setExpanded] = useState(false);

  if (!icp) return null;

  return (
    <Card flat className="!p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-purple-500 border-2 border-border-brutal">
            <Sparkles className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-display text-deep-blue">{icp.product_name}</h3>
            <p className="text-[11px] text-slate-400">AI-interpreted Ideal Customer Profile</p>
          </div>
        </div>
        <button onClick={() => setExpanded(e => !e)} className="text-xs text-electric-blue font-semibold flex items-center gap-1 cursor-pointer hover:underline">
          {expanded ? 'Less' : 'Details'} {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      </div>

      {icp.interpretation && (
        <div className="bg-purple-50 rounded-xl px-4 py-3 border border-purple-200">
          <p className="text-xs font-bold text-purple-600 uppercase mb-1">LLM Interpretation</p>
          <p className="text-sm text-purple-800">{icp.interpretation}</p>
        </div>
      )}

      <p className="text-sm text-slate-600">{icp.product_pitch}</p>

      {expanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="grid grid-cols-2 md:grid-cols-3 gap-3 pt-2 overflow-hidden"
        >
          <TagGroup label="Industries" tags={icp.industries} />
          <TagGroup label="Persona Titles" tags={icp.persona_titles} />
          <TagGroup label="Tech Stack" tags={icp.tech_stack} />
          <TagGroup label="Keywords" tags={icp.keywords?.slice(0, 6)} />
          <TagGroup label="Locations" tags={icp.locations} />
          <TagGroup label="Employee Ranges" tags={icp.employee_ranges} />
        </motion.div>
      )}
    </Card>
  );
}

function TagGroup({ label, tags }) {
  if (!tags?.length) return null;
  return (
    <div>
      <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">{label}</p>
      <div className="flex flex-wrap gap-1">
        {tags.map(t => (
          <span key={t} className="text-[10px] bg-sky-blue/10 text-deep-blue px-1.5 py-0.5 rounded border border-sky-blue/30">{t}</span>
        ))}
      </div>
    </div>
  );
}

function SummaryCards({ summary }) {
  if (!summary) return null;
  const cards = [
    { label: 'Companies', value: summary.companies, color: 'text-electric-blue' },
    { label: 'Contacts', value: summary.contacts, color: 'text-sky-blue' },
    { label: 'With Email', value: summary.contacts_with_email, color: 'text-accent-green' },
    { label: 'With LinkedIn', value: summary.contacts_with_linkedin, color: 'text-purple-500' },
    { label: 'Avg Score', value: summary.avg_score, color: 'text-accent-orange' },
  ];
  return (
    <div className="grid grid-cols-5 gap-3">
      {cards.map((c, i) => (
        <motion.div
          key={c.label}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.08 }}
          className="text-center p-3 rounded-xl bg-white border-2 border-slate-200 shadow-[2px_2px_0_var(--color-border-brutal)]"
        >
          <p className={`text-2xl font-bold text-display ${c.color}`}>{c.value}</p>
          <p className="text-[10px] text-slate-400 font-semibold uppercase">{c.label}</p>
        </motion.div>
      ))}
    </div>
  );
}

function LeadRow({ lead, index, expanded, onToggle, onApprove, onReject }) {
  const c = lead.contact;
  return (
    <>
      <motion.tr
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.04 }}
        onClick={onToggle}
        className="border-b border-slate-100 hover:bg-sky-blue/5 cursor-pointer transition-colors"
      >
        <td className="px-4 py-3"><ScoreRing score={lead.score} size={38} strokeWidth={3.5} /></td>
        <td className="px-4 py-3">
          <p className="font-semibold text-deep-blue text-sm">{c.full_name}</p>
          <p className="text-[11px] text-slate-400">{c.title}</p>
        </td>
        <td className="px-4 py-3 hidden md:table-cell">
          <p className="text-slate-600 text-sm">{c.company_name}</p>
          <p className="text-[10px] text-slate-400">{c.company_domain}</p>
        </td>
        <td className="px-4 py-3 hidden sm:table-cell">
          <div className="flex items-center gap-2">
            {c.email && <Mail className="w-3.5 h-3.5 text-accent-green" title={c.email} />}
            {c.linkedin_url && <Link2 className="w-3.5 h-3.5 text-electric-blue" title="LinkedIn" />}
            {!c.email && !c.linkedin_url && <span className="text-[10px] text-slate-300">--</span>}
          </div>
        </td>
        <td className="px-4 py-3">
          <StatusBadge status={lead.status} />
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-1.5" onClick={e => e.stopPropagation()}>
            {lead.status === 'review_required' && (
              <>
                <button onClick={onApprove} className="p-1.5 rounded-lg hover:bg-green-50 text-accent-green transition-colors cursor-pointer" title="Approve">
                  <CheckCircle2 className="w-4 h-4" />
                </button>
                <button onClick={onReject} className="p-1.5 rounded-lg hover:bg-red-50 text-accent-red transition-colors cursor-pointer" title="Reject">
                  <XCircle className="w-4 h-4" />
                </button>
              </>
            )}
            <button onClick={onToggle} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 transition-colors cursor-pointer">
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
        </td>
      </motion.tr>
      <AnimatePresence>
        {expanded && (
          <tr>
            <td colSpan={6}>
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="px-5 py-4 bg-sky-blue/5 border-t border-b border-sky-blue/20">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <h4 className="text-xs font-bold text-display text-slate-500 uppercase mb-2">Contact Details</h4>
                      <div className="space-y-1.5">
                        {c.email && (
                          <p className="text-xs text-slate-600 flex items-center gap-1.5">
                            <Mail className="w-3 h-3 text-accent-green" /> {c.email}
                          </p>
                        )}
                        {c.linkedin_url && (
                          <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-xs text-electric-blue flex items-center gap-1.5 hover:underline">
                            <Link2 className="w-3 h-3" /> LinkedIn Profile
                          </a>
                        )}
                        {c.company_domain && (
                          <a href={`https://${c.company_domain}`} target="_blank" rel="noopener noreferrer" className="text-xs text-electric-blue flex items-center gap-1.5 hover:underline">
                            <Globe className="w-3 h-3" /> {c.company_domain}
                          </a>
                        )}
                        {c.location && <p className="text-xs text-slate-500">{c.location}</p>}
                      </div>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-display text-slate-500 uppercase mb-2">Signals</h4>
                      <ul className="space-y-1">
                        {c.signals.map((s, i) => (
                          <li key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-electric-blue mt-1.5 shrink-0" />
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-display text-slate-500 uppercase mb-2">Score Reasons</h4>
                      <ul className="space-y-1">
                        {lead.reasons.map((r, i) => (
                          <li key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-accent-yellow mt-1.5 shrink-0" />
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-display text-slate-500 uppercase mb-2">Notes</h4>
                      {lead.relevance_explanation && (
                        <p className="text-xs text-purple-600 bg-purple-50 rounded-lg px-2 py-1 mb-2">{lead.relevance_explanation}</p>
                      )}
                      {c.research_notes.map((n, i) => (
                        <p key={i} className="text-xs text-slate-500 italic">{n}</p>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            </td>
          </tr>
        )}
      </AnimatePresence>
    </>
  );
}

export default function PipelineRun() {
  const location = useLocation();
  const navigate = useNavigate();
  const { prompt, icp: inputIcp, sessionId } = location.state || {};
  const savedRef = useRef(false);

  const {
    sessions, loading: histLoading, error: histError,
    loadSession, saveSession, deleteSession, fetchSessions,
  } = useSessions(prospecting);

  const [phase, setPhase] = useState(sessionId ? 'loading' : 'running');
  const [steps, setSteps] = useState([]);
  const [resolvedIcp, setResolvedIcp] = useState(null);
  const [leads, setLeads] = useState([]);
  const [summary, setSummary] = useState(null);
  const [expandedLead, setExpandedLead] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);

  const handleStep = useCallback((index, data) => {
    setSteps(prev => {
      const next = [...prev];
      next[index] = data;
      return next;
    });
    if (data.data && index === 0 && data.status === 'done') {
      setResolvedIcp(data.data);
    }
  }, []);

  useEffect(() => {
    if (sessionId) {
      (async () => {
        const session = await loadSession(sessionId);
        if (session) {
          setResolvedIcp(session.resolved_icp);
          setLeads(session.leads || []);
          setSummary(session.summary);
          setSteps(STEP_CONFIG.map((_, i) => ({ status: 'done', label: 'Loaded from history' })));
          setPhase('done');
          savedRef.current = true;
        } else {
          navigate('/icp');
        }
      })();
      return;
    }

    if (!prompt && !inputIcp) {
      navigate('/icp');
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const result = await runPipeline({
          prompt,
          icp: inputIcp,
          onStep: (i, d) => { if (!cancelled) handleStep(i, d); },
        });
        if (!cancelled) {
          setLeads(result.leads);
          setSummary(result.summary);
          setResolvedIcp(result.icp);
          setPhase('done');
        }
      } catch (err) {
        if (!cancelled) setPhase('error');
      }
    })();

    return () => { cancelled = true; };
  }, [prompt, inputIcp, sessionId, navigate, handleStep, loadSession]);

  useEffect(() => {
    if (phase !== 'done' || savedRef.current || !resolvedIcp || !leads.length) return;
    savedRef.current = true;
    const name = resolvedIcp.product_name
      || (prompt ? prompt.slice(0, 60) : 'Prospecting Session');

    setSaveStatus('saving');
    saveSession({
      session_name: name,
      prompt: prompt || null,
      icp: inputIcp || null,
      resolved_icp: resolvedIcp,
      leads,
      summary,
    }).then((saved) => {
      setSaveStatus(saved ? 'saved' : 'error');
      setTimeout(() => setSaveStatus(null), 3000);
    });
  }, [phase, resolvedIcp, leads, summary, prompt, inputIcp, saveSession]);

  function updateLeadStatus(index, status) {
    setLeads(prev => prev.map((l, i) => i === index ? { ...l, status } : l));
  }

  function leadKey(l) {
    return l.contact.full_name + '|' + l.contact.company_name;
  }

  function handleLoadHistory(id) {
    navigate('/pipeline-run', { state: { sessionId: id } });
    window.location.reload();
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
      <TopBar
        title={phase === 'done' ? 'Pipeline Complete' : phase === 'loading' ? 'Loading Session...' : 'Running Prospecting Agent...'}
        subtitle={prompt ? `"${prompt.slice(0, 80)}${prompt.length > 80 ? '...' : ''}"` : resolvedIcp?.product_name || 'Processing...'}
      />

      <div className="p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {saveStatus === 'saving' && (
              <span className="text-xs text-slate-400 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Saving...</span>
            )}
            {saveStatus === 'saved' && (
              <span className="text-xs text-accent-green flex items-center gap-1"><Save className="w-3 h-3" /> Saved to history</span>
            )}
          </div>
          <HistoryPanel
            sessions={sessions}
            loading={histLoading}
            error={histError}
            onLoad={handleLoadHistory}
            onDelete={deleteSession}
            onRetry={fetchSessions}
            agentName="Prospecting Agent"
            accentColor="bg-electric-blue"
            renderMeta={(s) => (
              <div className="flex flex-wrap gap-1.5">
                {s.summary?.drafts && <span className="text-[10px] bg-sky-blue/10 text-deep-blue px-1.5 py-0.5 rounded">{s.summary.drafts} leads</span>}
                {s.summary?.avg_score && <span className="text-[10px] bg-accent-green/10 text-accent-green px-1.5 py-0.5 rounded">avg {s.summary.avg_score}</span>}
                {s.resolved_icp?.product_name && <span className="text-[10px] bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded">{s.resolved_icp.product_name}</span>}
              </div>
            )}
          />
        </div>

        {phase === 'loading' && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-electric-blue" />
          </div>
        )}

        {phase !== 'loading' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <StepIndicator steps={steps} />
            {resolvedIcp && <ICPCard icp={resolvedIcp} />}
          </div>
        )}

        <AnimatePresence>
          {phase === 'done' && summary && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-5"
            >
              <SummaryCards summary={summary} />

              <Card flat className="!p-0 overflow-hidden">
                <div className="px-5 py-3 border-b-2 border-slate-200 flex items-center justify-between">
                  <h3 className="text-sm font-bold text-display text-deep-blue">
                    Discovered Leads ({leads.length})
                  </h3>
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <span>{leads.filter(l => l.status === 'approved').length} approved</span>
                    <span>{leads.filter(l => l.status === 'review_required').length} pending</span>
                  </div>
                </div>
                <table className="w-full text-left">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase">Score</th>
                      <th className="px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase">Name</th>
                      <th className="px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase hidden md:table-cell">Company</th>
                      <th className="px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase hidden sm:table-cell">Reach</th>
                      <th className="px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase">Status</th>
                      <th className="px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map((lead, i) => {
                      const k = leadKey(lead);
                      return (
                        <LeadRow
                          key={k}
                          lead={lead}
                          index={i}
                          expanded={expandedLead === k}
                          onToggle={() => setExpandedLead(expandedLead === k ? null : k)}
                          onApprove={() => updateLeadStatus(i, 'approved')}
                          onReject={() => updateLeadStatus(i, 'rejected')}
                        />
                      );
                    })}
                  </tbody>
                </table>
              </Card>

              <div className="flex items-center gap-3">
                <Button icon={ArrowRight} onClick={() => navigate('/research', { state: { leads, icp: resolvedIcp } })}>
                  Continue to Research Agent
                </Button>
                <Button variant="secondary" onClick={() => navigate('/icp')}>
                  New Search
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {phase === 'error' && (
          <Card flat className="!p-6 text-center">
            <p className="text-accent-red font-bold">Pipeline execution failed. Please try again.</p>
            <Button variant="secondary" onClick={() => navigate('/icp')} className="mt-3">Back to ICP Setup</Button>
          </Card>
        )}
      </div>
    </motion.div>
  );
}
