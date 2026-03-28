import { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
// eslint-disable-next-line no-unused-vars
import { motion } from 'framer-motion';
import { Send, Eye, MessageSquare, Flame, Clock, CheckCircle, XCircle, ChevronDown, ChevronUp, ArrowRightCircle, MailPlus, Loader2 } from 'lucide-react';
import { TopBar } from '../components/layout/TopBar';
import { Card, AnimatedCard, MetricCard } from '../components/ui/Card';
import { Badge, StatusBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { HistoryPanel } from '../components/ui/HistoryPanel';
import { useSessions } from '../hooks/useSessions';
import { tracking as trackingApi } from '../services/api';
import { runTrackingPipeline } from '../services/trackingRunner';
import { trackingData as defaultTrackingData, prospects, researchDossiers, outreachDrafts } from '../data/mockData';

const statusIcons = {
  sent: Send,
  opened: Eye,
  replied: MessageSquare,
  warm_lead: Flame,
  no_response: Clock,
};

const statusColors = {
  sent: 'border-l-electric-blue',
  opened: 'border-l-accent-orange',
  replied: 'border-l-accent-green',
  warm_lead: 'border-l-purple-500',
  no_response: 'border-l-slate-400',
};

const warmthConfig = {
  cold: { color: 'bg-slate-100 text-slate-600 border-slate-200', label: 'Cold' },
  neutral: { color: 'bg-blue-50 text-blue-600 border-blue-200', label: 'Neutral' },
  warm: { color: 'bg-orange-50 text-orange-600 border-orange-200', label: 'Warm' },
  hot: { color: 'bg-red-50 text-red-600 border-red-200', label: 'Hot' },
  meeting_requested: { color: 'bg-purple-50 text-purple-700 border-purple-200', label: 'Meeting Requested' },
};

const followUpStatusColors = {
  draft: 'bg-slate-100 text-slate-600',
  approved: 'bg-green-50 text-green-700 border-green-200',
  sent: 'bg-blue-50 text-blue-700 border-blue-200',
  failed: 'bg-red-50 text-red-600 border-red-200',
  rejected: 'bg-red-50 text-red-500 border-red-200',
};

function formatDate(iso) {
  if (!iso) return '--';
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

function WarmthBadge({ warmth }) {
  const cfg = warmthConfig[warmth] || warmthConfig.neutral;
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function ResponseDetail({ response }) {
  return (
    <div className="mt-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg space-y-1.5">
      <div className="flex items-center gap-2 flex-wrap">
        <WarmthBadge warmth={response.warmth} />
        {response.sentiment && (
          <span className="text-[10px] text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
            {response.sentiment}
          </span>
        )}
        <span className="text-[10px] text-slate-400 ml-auto">{formatDate(response.received_at)}</span>
      </div>
      {response.snippet && (
        <p className="text-xs text-green-800 italic">"{response.snippet}"</p>
      )}
      {response.key_points?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {response.key_points.map((kp, i) => (
            <span key={i} className="text-[10px] bg-white text-green-700 px-1.5 py-0.5 rounded border border-green-200">{kp}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function FollowUpCard({ followUp, entryIdx, followUpIdx, sessionId, onUpdate }) {
  const [approving, setApproving] = useState(false);

  async function handleAction(action) {
    setApproving(true);
    try {
      if (sessionId) {
        if (action === 'approve') await trackingApi.approveFollowUp(sessionId, entryIdx, followUpIdx);
        else await trackingApi.rejectFollowUp(sessionId, entryIdx, followUpIdx);
      }
      onUpdate(entryIdx, followUpIdx, action === 'approve' ? 'approved' : 'rejected');
    } catch (e) { console.error(`Follow-up ${action} failed:`, e); }
    finally { setApproving(false); }
  }

  return (
    <div className="mt-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <MailPlus className="w-3.5 h-3.5 text-blue-500" />
        <span className="text-[10px] font-bold text-blue-700 uppercase">Follow-up #{followUp.follow_up_number || 1}</span>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${followUpStatusColors[followUp.status] || followUpStatusColors.draft}`}>
          {followUp.status}
        </span>
        {followUp.sent_at && <span className="text-[10px] text-slate-400 ml-auto">Sent: {formatDate(followUp.sent_at)}</span>}
      </div>
      {followUp.subject && (
        <p className="text-xs font-medium text-blue-800">Subject: {followUp.subject}</p>
      )}
      {followUp.body && (
        <p className="text-xs text-blue-700 whitespace-pre-line line-clamp-4">{followUp.body}</p>
      )}
      {followUp.status === 'draft' && (
        <div className="flex items-center gap-2 pt-1">
          <button
            onClick={() => handleAction('approve')}
            disabled={approving}
            className="flex items-center gap-1 text-[10px] font-bold text-green-600 bg-green-50 hover:bg-green-100 px-2 py-1 rounded border border-green-200 transition-colors"
          >
            <CheckCircle className="w-3 h-3" /> Approve
          </button>
          <button
            onClick={() => handleAction('reject')}
            disabled={approving}
            className="flex items-center gap-1 text-[10px] font-bold text-red-500 bg-red-50 hover:bg-red-100 px-2 py-1 rounded border border-red-200 transition-colors"
          >
            <XCircle className="w-3 h-3" /> Reject
          </button>
        </div>
      )}
    </div>
  );
}

export default function Tracking() {
  const location = useLocation();
  const incomingDrafts = location.state?.drafts;
  const incomingIcp = location.state?.icp;

  const [data, setData] = useState(() => incomingDrafts ? [] : defaultTrackingData);
  const [activeLabel, setActiveLabel] = useState(null);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [expanded, setExpanded] = useState(new Set());

  // Pipeline streaming state
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineSteps, setPipelineSteps] = useState([]);
  const [pipelineSummary, setPipelineSummary] = useState(null);
  const [pipelineError, setPipelineError] = useState(null);
  const cancelRef = useRef(null);

  const {
    sessions, loading: histLoading, error: histError,
    loadSession, deleteSession, fetchSessions,
  } = useSessions(trackingApi);

  // Auto-run tracking pipeline when incoming drafts arrive from Outreach
  useEffect(() => {
    if (!incomingDrafts || !Array.isArray(incomingDrafts) || incomingDrafts.length === 0) return;

    setPipelineRunning(true);
    setPipelineError(null);
    setPipelineSummary(null);
    setData([]);

    const { cancel } = runTrackingPipeline({
      outreachQueue: incomingDrafts,
      icp: incomingIcp,
      action: 'check',
      onStep: (idx, status, label, extra) => {
        setPipelineSteps(prev => {
          const next = [...prev];
          next[idx] = { status, label, ...(extra?.count != null ? { count: extra.count } : {}) };
          return next;
        });
      },
      onEntry: (entry) => {
        setData(prev => [...prev, entry]);
      },
      onDone: (summary) => {
        setPipelineSummary(summary);
        setPipelineRunning(false);
      },
      onError: (msg) => {
        setPipelineError(msg);
        setPipelineRunning(false);
      },
    });

    cancelRef.current = cancel;
    return () => cancel();
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  async function handleLoadHistory(id) {
    const session = await loadSession(id);
    if (session?.entries) {
      setData(session.entries);
      setActiveLabel(session.session_name);
      setActiveSessionId(id);
    }
  }

  function toggleExpand(key) {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  function handleFollowUpUpdate(entryIdx, followUpIdx, newStatus) {
    setData(prev => prev.map((entry, eI) => {
      if (eI !== entryIdx || !entry.follow_ups) return entry;
      const updatedFollowUps = entry.follow_ups.map((fu, fI) =>
        fI === followUpIdx ? { ...fu, status: newStatus } : fu
      );
      return { ...entry, follow_ups: updatedFollowUps };
    }));
  }

  const replied = data.filter(t => t.status === 'replied').length;
  const opened = data.filter(t => t.status === 'opened').length;
  const warm = data.filter(t => {
    const warmth = t.warmth || t.responses?.[0]?.warmth;
    return warmth && ['warm', 'hot', 'meeting_requested'].includes(warmth);
  }).length;
  const total = data.length;

  const funnelData = useMemo(() => [
    { name: 'Prospects', value: prospects.length, fill: '#3b82f6' },
    { name: 'Researched', value: researchDossiers.length, fill: '#60a5fa' },
    { name: 'Outreach Drafts', value: outreachDrafts.length, fill: '#22c55e' },
    { name: 'Sent / Tracked', value: data.length, fill: '#f97316' },
    { name: 'Replied', value: data.filter(t => t.status === 'replied').length, fill: '#a855f7' },
  ], [data]);

  const openPct = total ? Math.round((opened / total) * 100) : 0;
  const replyPct = total ? Math.round((replied / total) * 100) : 0;
  const followUpsDraft = data.reduce((sum, t) => sum + (t.follow_ups?.filter(f => f.status === 'draft').length || 0), 0);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
      <TopBar title="Response Tracking" subtitle={activeLabel ? `Session: ${activeLabel}` : 'Monitor outreach performance & manage follow-ups'} />

      <div className="p-6 space-y-6">
        <div className="flex items-center justify-end">
          <HistoryPanel
            sessions={sessions}
            loading={histLoading}
            error={histError}
            onLoad={handleLoadHistory}
            onDelete={deleteSession}
            onRetry={fetchSessions}
            agentName="Tracking Agent"
            accentColor="bg-accent-orange"
            renderMeta={(s) => (
              <div className="flex flex-wrap gap-1.5">
                {s.summary?.total_tracked && <span className="text-[10px] bg-accent-orange/10 text-accent-orange px-1.5 py-0.5 rounded">{s.summary.total_tracked} tracked</span>}
                {s.summary?.replied > 0 && <span className="text-[10px] bg-green-50 text-green-600 px-1.5 py-0.5 rounded">{s.summary.replied} replied</span>}
                {s.summary?.follow_ups_generated > 0 && <span className="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">{s.summary.follow_ups_generated} follow-ups</span>}
              </div>
            )}
          />
        </div>

        {/* Pipeline progress banner */}
        {(pipelineRunning || pipelineSummary || pipelineError) && (
          <Card flat className="!p-4">
            <div className="flex items-center gap-3 mb-3">
              {pipelineRunning && <Loader2 className="w-4 h-4 text-electric-blue animate-spin" />}
              <h4 className="text-sm font-bold text-deep-blue">
                {pipelineRunning ? 'Tracking Pipeline Running...' : pipelineError ? 'Pipeline Error' : 'Pipeline Complete'}
              </h4>
            </div>
            {pipelineError && (
              <p className="text-xs text-red-500 bg-red-50 px-3 py-2 rounded border border-red-200">{pipelineError}</p>
            )}
            <div className="flex flex-wrap gap-2">
              {pipelineSteps.map((step, i) => (
                <span key={i} className={`text-[10px] font-bold px-2 py-1 rounded border ${
                  step.status === 'done' ? 'bg-green-50 text-green-700 border-green-200' :
                  step.status === 'running' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                  'bg-slate-50 text-slate-500 border-slate-200'
                }`}>
                  {step.label} {step.count != null && `(${step.count})`}
                </span>
              ))}
            </div>
          </Card>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <MetricCard icon={Send} label="Total Sent" value={total} color="bg-electric-blue" delay={0} />
          <MetricCard icon={Eye} label="Opened" value={opened} sub={`${openPct}% open rate`} color="bg-accent-orange" delay={0.08} />
          <MetricCard icon={MessageSquare} label="Replied" value={replied} sub={`${replyPct}% reply rate`} color="bg-accent-green" delay={0.16} />
          <MetricCard icon={Flame} label="Warm+ Leads" value={warm} sub="warm / hot / meeting" color="bg-purple-500" delay={0.24} />
          <MetricCard icon={MailPlus} label="Pending Follow-ups" value={followUpsDraft} sub="drafts awaiting review" color="bg-sky-500" delay={0.32} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Card flat className="!p-5">
            <h3 className="text-sm font-bold text-display text-deep-blue uppercase tracking-wide mb-4">Conversion Funnel</h3>
            <div className="space-y-3">
              {funnelData.map((item, i) => {
                const width = Math.max(20, (item.value / funnelData[0].value) * 100);
                return (
                  <motion.div
                    key={item.name}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="flex items-center gap-3"
                  >
                    <span className="text-xs font-medium text-slate-500 w-24 text-right shrink-0">{item.name}</span>
                    <div className="flex-1 h-8 bg-slate-100 rounded-lg border-2 border-border-brutal overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${width}%` }}
                        transition={{ duration: 0.8, delay: i * 0.1, ease: 'easeOut' }}
                        className="h-full rounded-lg flex items-center justify-end pr-2"
                        style={{ background: item.fill }}
                      >
                        <span className="text-xs font-bold text-white">{item.value}</span>
                      </motion.div>
                    </div>
                    {i < funnelData.length - 1 && (
                      <span className="text-[10px] font-bold text-slate-400 w-10 text-center">
                        {Math.round((funnelData[i + 1].value / item.value) * 100)}%
                      </span>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </Card>

          <Card flat className="!p-5">
            <h3 className="text-sm font-bold text-display text-deep-blue uppercase tracking-wide mb-4">Agent Status</h3>
            <div className="space-y-4">
              {[
                { name: 'Prospecting Agent', info: `Completed \u00B7 ${prospects.length} prospects scored` },
                { name: 'Research Agent', info: `Completed \u00B7 ${researchDossiers.length} dossiers built` },
                { name: 'Personalisation Agent', info: `Completed \u00B7 ${outreachDrafts.length} drafts generated (DigitalOcean GPT-oss-120b)` },
                { name: 'Outreach Agent', info: `Completed \u00B7 ${outreachDrafts.length} messages queued` },
                { name: 'Tracking Agent', info: `Completed \u00B7 ${total} entries tracked, ${replied} replies, ${warm} warm leads` },
              ].map((agent) => (
                <div key={agent.name} className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border-2 border-slate-200">
                  <div className="w-3 h-3 rounded-full bg-accent-green animate-pulse" />
                  <div>
                    <p className="text-sm font-bold text-deep-blue">{agent.name}</p>
                    <p className="text-xs text-slate-400">{agent.info}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <Card flat className="!p-5">
          <h3 className="text-sm font-bold text-display text-deep-blue uppercase tracking-wide mb-4">Response Timeline</h3>
          <div className="space-y-3">
            {data.map((t, i) => {
              const Icon = statusIcons[t.status] || Clock;
              const entryWarmth = t.warmth || t.responses?.[0]?.warmth;
              const isWarm = entryWarmth && ['warm', 'hot', 'meeting_requested'].includes(entryWarmth);
              const hasDetails = (t.responses?.length > 0) || (t.follow_ups?.length > 0);
              const isExpanded = expanded.has(t._key || i);

              return (
                <motion.div
                  key={t._key || i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.08 }}
                  className={`neu-card-flat !p-4 border-l-4 ${statusColors[t.status]}`}
                >
                  <div
                    className={`flex items-start gap-4 ${hasDetails ? 'cursor-pointer' : ''}`}
                    onClick={() => hasDetails && toggleExpand(t._key || i)}
                  >
                    <div className={`p-2 rounded-xl ${isWarm ? 'bg-purple-100' : 'bg-slate-100'} shrink-0`}>
                      <Icon className={`w-5 h-5 ${isWarm ? 'text-purple-600' : 'text-slate-500'}`} strokeWidth={2} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-semibold text-deep-blue text-sm">{t.contact_name}</span>
                        <span className="text-xs text-slate-400">at {t.contact_company}</span>
                        <StatusBadge status={t.status} />
                        {entryWarmth && <WarmthBadge warmth={entryWarmth} />}
                        {t.follow_up_count > 0 && (
                          <span className="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded border border-blue-200">
                            {t.follow_up_count} follow-up{t.follow_up_count > 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-[11px] text-slate-400">
                        {t.sent_at && <span>Sent: {formatDate(t.sent_at)}</span>}
                        {t.opened_at && <span>Opened: {formatDate(t.opened_at)}</span>}
                        {t.replied_at && <span className="text-accent-green font-semibold">Replied: {formatDate(t.replied_at)}</span>}
                        {t.last_activity_at && <span>Last Activity: {formatDate(t.last_activity_at)}</span>}
                      </div>
                      {/* Inline snippet when collapsed */}
                      {!isExpanded && t.reply_snippet && (
                        <div className="mt-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg">
                          <p className="text-xs text-green-800 italic">"{t.reply_snippet}"</p>
                        </div>
                      )}
                    </div>
                    {hasDetails && (
                      <div className="shrink-0 p-1 rounded-lg hover:bg-slate-100 transition-colors">
                        {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                      </div>
                    )}
                  </div>

                  {/* Expanded details */}
                  {isExpanded && hasDetails && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      transition={{ duration: 0.2 }}
                      className="mt-3 ml-14 space-y-2"
                    >
                      {t.responses?.length > 0 && (
                        <div>
                          <p className="text-[10px] font-bold text-slate-400 uppercase mb-1.5">
                            Responses ({t.responses.length})
                          </p>
                          {t.responses.map((r, ri) => (
                            <ResponseDetail key={r.id || ri} response={r} />
                          ))}
                        </div>
                      )}
                      {t.follow_ups?.length > 0 && (
                        <div>
                          <p className="text-[10px] font-bold text-slate-400 uppercase mb-1.5 mt-3">
                            Follow-ups ({t.follow_ups.length})
                          </p>
                          {t.follow_ups.map((fu, fi) => (
                            <FollowUpCard
                              key={fu.id || fi}
                              followUp={fu}
                              entryIdx={i}
                              followUpIdx={fi}
                              sessionId={activeSessionId}
                              onUpdate={handleFollowUpUpdate}
                            />
                          ))}
                        </div>
                      )}
                    </motion.div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </Card>
      </div>
    </motion.div>
  );
}
