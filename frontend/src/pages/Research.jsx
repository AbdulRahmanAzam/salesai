import { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Building2, User, Newspaper, MessageSquare, Lightbulb, AlertTriangle, ExternalLink, Link2, Globe, CheckCircle2, Loader2, Clock, ArrowRight, Save } from 'lucide-react';
import { TopBar } from '../components/layout/TopBar';
import { Card, AnimatedCard } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { ConfidenceBar } from '../components/ui/ProgressBar';
import { ScoreRing } from '../components/ui/ScoreRing';
import { Modal } from '../components/ui/Modal';
import { HistoryPanel } from '../components/ui/HistoryPanel';
import { useSessions } from '../hooks/useSessions';
import { research as researchApi } from '../services/api';
import { researchDossiers as defaultDossiers, icpDefaults } from '../data/mockData';
import { runResearchPipeline, RESEARCH_STEPS } from '../services/researchRunner';

function DossierCard({ dossier, onClick, index }) {
  return (
    <AnimatedCard delay={index * 0.1} className="cursor-pointer" onClick={onClick}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-electric-blue to-deep-blue border-2 border-border-brutal flex items-center justify-center text-white font-bold text-display text-sm shadow-[2px_2px_0_var(--color-border-brutal)]">
            {dossier.contact_name.split(' ').map(n => n[0]).join('')}
          </div>
          <div>
            <h3 className="font-bold text-deep-blue text-display">{dossier.contact_name}</h3>
            <p className="text-xs text-slate-400">{dossier.contact_title} at {dossier.contact_company}</p>
          </div>
        </div>
        <ScoreRing score={dossier.prospect_score} size={38} strokeWidth={4} />
      </div>

      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-bold text-display text-slate-500 uppercase">Research Confidence</span>
        </div>
        <ConfidenceBar value={dossier.research_confidence} />
      </div>

      <p className="text-xs text-slate-500 line-clamp-2 mb-3">{dossier.relevance_summary}</p>

      <div className="flex flex-wrap gap-1.5">
        <Badge variant="blue">{dossier.talking_points.length} talking pts</Badge>
        <Badge variant="orange">{dossier.pain_points.length} pain pts</Badge>
        {dossier.company_profile.technologies.slice(0, 3).map(t => (
          <Badge key={t} variant="slate">{t}</Badge>
        ))}
      </div>
    </AnimatedCard>
  );
}

function DossierDetail({ dossier }) {
  if (!dossier) return null;
  const { company_profile: cp, person_profile: pp } = dossier;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 pb-4 border-b-2 border-slate-200">
        <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-electric-blue to-deep-blue border-2 border-border-brutal flex items-center justify-center text-white font-bold text-display text-lg shadow-[3px_3px_0_var(--color-border-brutal)]">
          {dossier.contact_name.split(' ').map(n => n[0]).join('')}
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-xl font-bold text-display text-deep-blue">{dossier.contact_name}</h2>
          <p className="text-sm text-slate-500">{dossier.contact_title} at {dossier.contact_company}</p>
          <div className="flex items-center gap-3 mt-1">
            {dossier.contact_linkedin && (
              <a href={dossier.contact_linkedin} target="_blank" rel="noopener noreferrer" className="text-electric-blue hover:underline text-xs font-semibold">LinkedIn</a>
            )}
            {dossier.contact_email && (
              <span className="text-xs text-slate-400">{dossier.contact_email}</span>
            )}
          </div>
        </div>
        <ScoreRing score={dossier.prospect_score} size={56} strokeWidth={5} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="neu-card-flat p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-electric-blue" />
            <h3 className="text-sm font-bold text-display text-deep-blue">Company Profile</h3>
          </div>
          <div className="space-y-2 text-sm">
            {cp.description && <p className="text-slate-600">{cp.description}</p>}
            {!cp.description && <p className="text-slate-400 italic">No description available</p>}
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
              {cp.industry && <p><span className="font-semibold text-slate-500">Industry:</span> {cp.industry}</p>}
              {cp.employee_count && <p><span className="font-semibold text-slate-500">Size:</span> {cp.employee_count}</p>}
              {cp.headquarters && <p><span className="font-semibold text-slate-500">HQ:</span> {cp.headquarters}</p>}
              {cp.founded_year && <p><span className="font-semibold text-slate-500">Founded:</span> {cp.founded_year}</p>}
              {cp.funding_stage && <p><span className="font-semibold text-slate-500">Stage:</span> {cp.funding_stage}</p>}
              {cp.total_funding && <p><span className="font-semibold text-slate-500">Funding:</span> {cp.total_funding}</p>}
            </div>
            {Object.keys(cp.key_metrics || {}).length > 0 && (
              <div className="flex flex-wrap gap-2 pt-1">
                {Object.entries(cp.key_metrics).map(([k, v]) => (
                  <span key={k} className="text-[11px] bg-sky-blue/10 text-deep-blue px-2 py-0.5 rounded-md border border-sky-blue/30 font-mono">
                    {k.replace(/_/g, ' ')}: {v}
                  </span>
                ))}
              </div>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {cp.technologies.slice(0, 8).map(t => (
                <span key={t} className="text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md border border-slate-200">{t}</span>
              ))}
            </div>
            {cp.competitors?.length > 0 && (
              <p className="text-xs"><span className="font-semibold text-slate-500">Competitors:</span> {cp.competitors.join(', ')}</p>
            )}
            {cp.social_profiles && Object.keys(cp.social_profiles).length > 0 && (
              <div className="flex items-center gap-3 pt-2">
                {Object.entries(cp.social_profiles).map(([platform, url]) => (
                  <a key={platform} href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-deep-blue font-medium capitalize">
                    <Link2 className="w-3.5 h-3.5" /> {platform}
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="neu-card-flat p-4 space-y-3">
          <div className="flex items-center gap-2">
            <User className="w-4 h-4 text-electric-blue" />
            <h3 className="text-sm font-bold text-display text-deep-blue">Person Profile</h3>
          </div>
          <div className="space-y-2 text-sm">
            {pp.bio && <p className="text-slate-600">{pp.bio}</p>}
            {!pp.bio && <p className="text-slate-400 italic">No bio available</p>}
            {pp.skills?.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {pp.skills.map(s => <span key={s} className="text-[11px] bg-electric-blue/10 text-electric-blue px-2 py-0.5 rounded-md border border-electric-blue/20">{s}</span>)}
              </div>
            )}
            {pp.career_history?.length > 0 && (
              <div className="space-y-1">
                <span className="text-xs font-semibold text-slate-500">Career:</span>
                {pp.career_history.map((c, i) => (
                  <p key={i} className="text-xs text-slate-600">{c.title} at {c.company}{c.start_date ? ` (${c.start_date}–${c.end_date || 'present'})` : ''}</p>
                ))}
              </div>
            )}
            {pp.education?.length > 0 && (
              <div className="space-y-1">
                <span className="text-xs font-semibold text-slate-500">Education:</span>
                {pp.education.map((e, i) => (
                  <p key={i} className="text-xs text-slate-600">{e.degree || 'Degree'}{e.field_of_study ? ` in ${e.field_of_study}` : ''} — {e.institution}</p>
                ))}
              </div>
            )}
            {pp.mutual_interests?.length > 0 && (
              <div>
                <span className="font-semibold text-slate-500">Shared Interests: </span>
                {pp.mutual_interests.join(', ')}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="neu-card-flat p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-accent-yellow" />
          <h3 className="text-sm font-bold text-display text-deep-blue">Talking Points</h3>
        </div>
        <ul className="space-y-2">
          {dossier.talking_points.map((tp, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
              <span className="w-5 h-5 rounded-lg bg-accent-yellow/20 border border-yellow-400 flex items-center justify-center text-[10px] font-bold text-yellow-700 shrink-0 mt-0.5">{i + 1}</span>
              {tp}
            </li>
          ))}
        </ul>
      </div>

      <div className="neu-card-flat p-4 space-y-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-accent-orange" />
          <h3 className="text-sm font-bold text-display text-deep-blue">Pain Points</h3>
        </div>
        <ul className="space-y-2">
          {dossier.pain_points.map((pp, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
              <span className="w-2 h-2 rounded-full bg-accent-orange mt-1.5 shrink-0" />
              {pp}
            </li>
          ))}
        </ul>
      </div>

      {pp.recent_activity?.length > 0 && (
        <div className="neu-card-flat p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-sky-blue" />
            <h3 className="text-sm font-bold text-display text-deep-blue">Recent Activity</h3>
          </div>
          <div className="space-y-2.5 max-h-64 overflow-y-auto scrollbar-thin">
            {pp.recent_activity.map((a, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <span className="text-[10px] font-mono bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded border border-slate-200 shrink-0 mt-0.5">
                  {a.activity_type}
                </span>
                <div className="min-w-0">
                  <p className="text-slate-600 truncate">{a.title}</p>
                  <p className="text-[11px] text-slate-400">{a.date}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {cp.recent_news?.length > 0 && (
        <div className="neu-card-flat p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-electric-blue" />
            <h3 className="text-sm font-bold text-display text-deep-blue">Company News</h3>
          </div>
          <div className="space-y-2">
            {cp.recent_news.map((n, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <Globe className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-slate-600">{n.title}</p>
                  <p className="text-[11px] text-slate-400">{n.source} &middot; {n.published_date}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold text-display text-slate-500 uppercase">Research Confidence</span>
          <span className="text-sm font-bold text-deep-blue">{Math.round(dossier.research_confidence * 100)}%</span>
        </div>
        <ConfidenceBar value={dossier.research_confidence} />
      </div>
    </div>
  );
}

function ResearchStepIndicator({ steps }) {
  return (
    <div className="space-y-2.5">
      {RESEARCH_STEPS.map((cfg, i) => {
        const step = steps[i];
        const isDone = step?.status === 'done';
        const isRunning = step?.status === 'running';

        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`flex items-center gap-3 px-4 py-2.5 rounded-xl border-2 transition-all ${
              isDone ? 'bg-green-50 border-green-300'
                : isRunning ? 'bg-blue-50 border-electric-blue'
                  : 'bg-slate-50 border-slate-200'
            }`}
          >
            <div className={`p-1.5 rounded-lg ${isDone ? 'bg-accent-green' : isRunning ? 'bg-electric-blue' : 'bg-slate-300'}`}>
              {isDone ? <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                : isRunning ? <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
                  : <Clock className="w-3.5 h-3.5 text-white" />}
            </div>
            <p className={`text-sm font-semibold flex-1 ${isDone ? 'text-green-700' : isRunning ? 'text-deep-blue' : 'text-slate-400'}`}>
              {step?.label || cfg.label}
            </p>
            {isDone && <CheckCircle2 className="w-3.5 h-3.5 text-accent-green shrink-0" />}
            {isRunning && <Loader2 className="w-3.5 h-3.5 text-electric-blue animate-spin shrink-0" />}
          </motion.div>
        );
      })}
    </div>
  );
}

export default function Research() {
  const location = useLocation();
  const navigate = useNavigate();
  const { leads: incomingLeads, icp: incomingIcp } = location.state || {};

  const [selected, setSelected] = useState(null);
  const [dossiers, setDossiers] = useState(incomingLeads ? [] : defaultDossiers);
  const [activeLabel, setActiveLabel] = useState(null);
  const [phase, setPhase] = useState(incomingLeads ? 'running' : 'idle');
  const [steps, setSteps] = useState([]);
  const [researchSummary, setResearchSummary] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);
  const savedRef = useRef(false);
  const [icpData, setIcpData] = useState(incomingIcp || null);

  const {
    sessions, loading: histLoading, error: histError,
    loadSession, saveSession, deleteSession, fetchSessions,
  } = useSessions(researchApi);

  const handleStep = useCallback((index, data) => {
    setSteps(prev => {
      const next = [...prev];
      next[index] = data;
      return next;
    });
  }, []);

  const handleDossier = useCallback((dossier) => {
    setDossiers(prev => [...prev, dossier]);
  }, []);

  useEffect(() => {
    if (!incomingLeads || phase !== 'running') return;

    let cancelled = false;
    (async () => {
      try {
        const result = await runResearchPipeline({
          leads: incomingLeads,
          icp: incomingIcp,
          onStep: (i, d) => { if (!cancelled) handleStep(i, d); },
          onDossier: (d) => { if (!cancelled) handleDossier(d); },
        });
        if (!cancelled) {
          setResearchSummary(result.summary);
          setPhase('done');
        }
      } catch (err) {
        if (!cancelled) setPhase('error');
      }
    })();

    return () => { cancelled = true; };
  }, [incomingLeads, phase, handleStep, handleDossier]);

  // Auto-save session when done
  useEffect(() => {
    if (phase !== 'done' || savedRef.current || !dossiers.length) return;
    savedRef.current = true;
    const name = icpData?.product_name || 'Research Session';

    setSaveStatus('saving');
    saveSession({
      session_name: `Research: ${name}`,
      dossiers,
      icp: icpData,
      summary: researchSummary,
    }).then((saved) => {
      setSaveStatus(saved ? 'saved' : 'error');
      setTimeout(() => setSaveStatus(null), 3000);
    });
  }, [phase, dossiers, researchSummary, saveSession]);

  async function handleLoadHistory(id) {
    const session = await loadSession(id);
    if (session?.dossiers) {
      setDossiers(session.dossiers);
      if (session.icp) setIcpData(session.icp);
      setActiveLabel(session.session_name);
      setPhase('idle');
      setSteps([]);
    }
  }

  const isRunning = phase === 'running';
  const isDone = phase === 'done' || (phase === 'idle' && dossiers.length > 0);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
      <TopBar
        title={isRunning ? 'Research Agent Running...' : 'Research Dossiers'}
        subtitle={
          isRunning ? `Researching ${incomingLeads?.length || 0} leads — ${dossiers.length} dossiers generated`
            : activeLabel ? `Session: ${activeLabel}`
              : `${dossiers.length} dossiers available`
        }
      />

      <div className="p-6 space-y-4">
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
            agentName="Research Agent"
            accentColor="bg-sky-blue"
            renderMeta={(s) => (
              <div className="flex flex-wrap gap-1.5">
                {s.summary?.total_dossiers && <span className="text-[10px] bg-sky-blue/10 text-deep-blue px-1.5 py-0.5 rounded">{s.summary.total_dossiers} dossiers</span>}
                {s.summary?.avg_confidence && <span className="text-[10px] bg-accent-green/10 text-accent-green px-1.5 py-0.5 rounded">{Math.round(s.summary.avg_confidence * 100)}% conf</span>}
              </div>
            )}
          />
        </div>

        {/* Pipeline progress (shown while running) */}
        {isRunning && (
          <Card flat className="!p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-xl bg-sky-blue border-2 border-border-brutal">
                <Search className="w-5 h-5 text-white" strokeWidth={2.5} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-display text-deep-blue">Research Agent</h3>
                <p className="text-xs text-slate-400">Researching company profiles, person backgrounds, news &amp; talking points</p>
              </div>
            </div>
            <ResearchStepIndicator steps={steps} />
          </Card>
        )}

        {/* Summary cards (shown when done with pipeline) */}
        {phase === 'done' && researchSummary && (
          <div className="grid grid-cols-5 gap-3">
            {[
              { label: 'Dossiers', value: researchSummary.total_dossiers, color: 'text-electric-blue' },
              { label: 'Avg Confidence', value: `${Math.round(researchSummary.avg_confidence * 100)}%`, color: 'text-accent-green' },
              { label: 'Avg Score', value: researchSummary.avg_score, color: 'text-sky-blue' },
              { label: 'Talking Pts', value: researchSummary.total_talking_points, color: 'text-accent-yellow' },
              { label: 'Pain Pts', value: researchSummary.total_pain_points, color: 'text-accent-orange' },
            ].map((c, i) => (
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
        )}

        {/* Dossier grid */}
        {dossiers.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {dossiers.map((d, i) => (
              <DossierCard key={d._key || i} dossier={d} index={i} onClick={() => setSelected(d)} />
            ))}
          </div>
        )}

        {/* Empty state while running with no dossiers yet */}
        {isRunning && dossiers.length === 0 && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center space-y-2">
              <Loader2 className="w-8 h-8 animate-spin text-electric-blue mx-auto" />
              <p className="text-sm text-slate-500">Generating research dossiers...</p>
            </div>
          </div>
        )}

        {/* Continue to Outreach button */}
        {isDone && dossiers.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 pt-2"
          >
            <Button icon={ArrowRight} onClick={() => navigate('/outreach', { state: { dossiers, icp: icpData || icpDefaults } })}>
              Continue to Outreach Agent
            </Button>
            <Button variant="secondary" onClick={() => navigate('/icp')}>
              New Search
            </Button>
            <span className="text-xs text-slate-400 ml-2">
              Personalisation agent will tailor outreach to each lead's context
            </span>
          </motion.div>
        )}

        {phase === 'error' && (
          <Card flat className="!p-6 text-center">
            <p className="text-accent-red font-bold">Research pipeline failed. Please try again.</p>
            <Button variant="secondary" onClick={() => navigate('/icp')} className="mt-3">Back to ICP Setup</Button>
          </Card>
        )}
      </div>

      <Modal
        isOpen={!!selected}
        onClose={() => setSelected(null)}
        title={selected ? `Research: ${selected.contact_name}` : ''}
        wide
      >
        <DossierDetail dossier={selected} />
      </Modal>
    </motion.div>
  );
}
