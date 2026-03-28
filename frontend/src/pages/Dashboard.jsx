import { useState, useEffect } from 'react';
// eslint-disable-next-line no-unused-vars
import { motion } from 'framer-motion';
import { Users, Search, Send, TrendingUp, ArrowRight, Clock, ExternalLink, Sparkles, History, Database } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { TopBar } from '../components/layout/TopBar';
import { MetricCard, Card } from '../components/ui/Card';
import { PipelineVisual } from '../components/pipeline/PipelineVisual';
import { ScoreRing } from '../components/ui/ScoreRing';
import { StatusBadge, Badge } from '../components/ui/Badge';
import { Table, Thead, Th, Td, Tr } from '../components/ui/Table';
import { prospects, pipelineStages, activityLog, researchDossiers, outreachDrafts, trackingData } from '../data/mockData';
import { dashboard } from '../services/api';
import { Link, useNavigate } from 'react-router-dom';

function computeSourceData(data) {
  const map = {};
  data.forEach((p) => {
    const parts = (p.contact.source || 'unknown').split('+');
    parts.forEach((s) => {
      const name = s.trim() || 'unknown';
      map[name] = (map[name] || 0) + 1;
    });
  });
  const colors = { apollo: '#3b82f6', hackernews: '#facc15', hunter: '#22c55e', github: '#a855f7', producthunt: '#f97316', unknown: '#94a3b8' };
  return Object.entries(map).map(([name, value]) => ({ name, value, color: colors[name] || '#94a3b8' }));
}

function computeScoreDistribution(data) {
  const buckets = [
    { range: '0-30', count: 0 },
    { range: '31-50', count: 0 },
    { range: '51-70', count: 0 },
    { range: '71-85', count: 0 },
    { range: '86-100', count: 0 },
  ];
  data.forEach((p) => {
    if (p.score <= 30) buckets[0].count++;
    else if (p.score <= 50) buckets[1].count++;
    else if (p.score <= 70) buckets[2].count++;
    else if (p.score <= 85) buckets[3].count++;
    else buckets[4].count++;
  });
  return buckets;
}

const activityIcons = {
  prospect: Users,
  research: Search,
  personalisation: Sparkles,
  outreach: Send,
  tracking: TrendingUp,
};

const activityColors = {
  prospect: 'bg-electric-blue',
  research: 'bg-sky-blue',
  personalisation: 'bg-purple-500',
  outreach: 'bg-accent-green',
  tracking: 'bg-accent-orange',
};

function formatTime(iso) {
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function formatDateShort(iso) {
  if (!iso) return '--';
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [dbSummary, setDbSummary] = useState(null);

  useEffect(() => {
    dashboard.getSummary().then(setDbSummary).catch(() => {});
  }, []);

  const topProspects = [...prospects].sort((a, b) => b.score - a.score).slice(0, 5);
  const sourceData = computeSourceData(prospects);
  const scoreDistribution = computeScoreDistribution(prospects);
  const avgConfidence = researchDossiers.length > 0
    ? Math.round((researchDossiers.reduce((s, d) => s + d.research_confidence, 0) / researchDossiers.length) * 100)
    : 0;
  const avgPersonalisation = outreachDrafts.length > 0
    ? Math.round(outreachDrafts.reduce((s, d) => s + d.personalization_score, 0) / outreachDrafts.length)
    : 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <TopBar title="Dashboard" subtitle="Sales Intelligence Pipeline Overview" />

      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard icon={Users} label="Total Prospects" value={prospects.length} sub={`All ${prospects.length} pending review`} color="bg-electric-blue" delay={0} />
          <MetricCard icon={Search} label="Researched" value={researchDossiers.length} sub={`Avg confidence ${avgConfidence}%`} color="bg-sky-blue" delay={0.08} />
          <MetricCard icon={Sparkles} label="Personalised" value={outreachDrafts.length} sub={`Avg score ${avgPersonalisation}%`} color="bg-purple-500" delay={0.16} />
          <MetricCard icon={TrendingUp} label="Tracking" value={trackingData.length} sub="Agent not yet active" color="bg-accent-orange" delay={0.24} />
        </div>

        <Card flat className="!p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-display text-deep-blue uppercase tracking-wide">Pipeline Status</h3>
            <Link to="/prospects" className="text-xs text-electric-blue font-semibold hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <PipelineVisual stages={pipelineStages} />
        </Card>

        {dbSummary && (
          <Card flat className="!p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-electric-blue" />
                <h3 className="text-sm font-bold text-display text-deep-blue uppercase tracking-wide">Saved Sessions</h3>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-400">
                <span>{dbSummary.counts.total_leads} total leads</span>
                <span>{dbSummary.counts.total_dossiers} dossiers</span>
                <span>{dbSummary.counts.total_drafts} drafts</span>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                { label: 'Prospecting', count: dbSummary.counts.prospecting_sessions, sessions: dbSummary.recent.prospecting, color: 'border-l-electric-blue', link: '/prospects' },
                { label: 'Research', count: dbSummary.counts.research_sessions, sessions: dbSummary.recent.research, color: 'border-l-sky-blue', link: '/research' },
                { label: 'Outreach', count: dbSummary.counts.outreach_sessions, sessions: dbSummary.recent.outreach, color: 'border-l-accent-green', link: '/outreach' },
                { label: 'Tracking', count: dbSummary.counts.tracking_sessions, sessions: dbSummary.recent.tracking, color: 'border-l-accent-orange', link: '/tracking' },
              ].map(agent => (
                <div key={agent.label} className={`p-3 rounded-xl border-2 border-slate-200 border-l-4 ${agent.color}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-deep-blue">{agent.label}</span>
                    <Badge variant="slate">{agent.count}</Badge>
                  </div>
                  {agent.sessions.length > 0 ? (
                    <div className="space-y-1.5">
                      {agent.sessions.slice(0, 3).map(s => (
                        <button
                          key={s._id}
                          onClick={() => navigate(agent.link)}
                          className="w-full text-left text-[11px] text-slate-500 hover:text-electric-blue truncate cursor-pointer flex items-center gap-1 transition-colors"
                        >
                          <History className="w-3 h-3 shrink-0" />
                          <span className="truncate">{s.session_name}</span>
                          <span className="text-[9px] text-slate-400 ml-auto shrink-0">{formatDateShort(s.created_at)}</span>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[10px] text-slate-400">No sessions yet</p>
                  )}
                </div>
              ))}
            </div>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <Card flat className="lg:col-span-2 !p-0">
            <div className="flex items-center justify-between px-5 pt-5 pb-3">
              <h3 className="text-sm font-bold text-display text-deep-blue uppercase tracking-wide">Top Prospects</h3>
              <Link to="/prospects" className="text-xs text-electric-blue font-semibold hover:underline flex items-center gap-1">
                View all <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            <Table>
              <Thead>
                <Th>Score</Th>
                <Th>Name</Th>
                <Th className="hidden md:table-cell">Company</Th>
                <Th className="hidden sm:table-cell">Source</Th>
                <Th>Status</Th>
              </Thead>
              <tbody>
                {topProspects.map((p, idx) => (
                  <Tr key={p.contact.full_name + idx}>
                    <Td><ScoreRing score={p.score} size={40} strokeWidth={4} /></Td>
                    <Td>
                      <div>
                        <p className="font-semibold text-deep-blue">{p.contact.full_name}</p>
                        <p className="text-xs text-slate-400">{p.contact.title}</p>
                      </div>
                    </Td>
                    <Td className="hidden md:table-cell">
                      <span className="text-slate-600">{p.contact.company_name}</span>
                    </Td>
                    <Td className="hidden sm:table-cell">
                      <span className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">{p.contact.source}</span>
                    </Td>
                    <Td><StatusBadge status={p.status} /></Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </Card>

          <Card flat className="!p-4 space-y-4">
            <h3 className="text-sm font-bold text-display text-deep-blue uppercase tracking-wide">Recent Activity</h3>
            <div className="space-y-3">
              {activityLog.slice(0, 5).map((a) => {
                const Icon = activityIcons[a.type] || Clock;
                return (
                  <div key={a.id} className="flex items-start gap-3">
                    <div className={`${activityColors[a.type]} p-1.5 rounded-lg shrink-0`}>
                      <Icon className="w-3.5 h-3.5 text-white" strokeWidth={2.5} />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-slate-700">{a.action}</p>
                      <p className="text-[11px] text-slate-400 truncate">{a.detail}</p>
                    </div>
                    <span className="text-[10px] text-slate-400 shrink-0 ml-auto">{formatTime(a.timestamp)}</span>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Card flat className="!p-5">
            <h3 className="text-sm font-bold text-display text-deep-blue uppercase tracking-wide mb-4">Score Distribution</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={scoreDistribution}>
                <XAxis dataKey="range" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    background: '#fff',
                    border: '2px solid #1e293b',
                    borderRadius: '12px',
                    boxShadow: '3px 3px 0 #1e293b',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card flat className="!p-5">
            <h3 className="text-sm font-bold text-display text-deep-blue uppercase tracking-wide mb-4">Lead Sources</h3>
            <div className="flex items-center justify-center gap-8">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie
                    data={sourceData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="#1e293b"
                    strokeWidth={2}
                  >
                    {sourceData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {sourceData.map((s) => (
                  <div key={s.name} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-sm border border-border-brutal" style={{ background: s.color }} />
                    <span className="text-xs font-medium text-slate-600">{s.name}</span>
                    <span className="text-xs font-bold text-deep-blue ml-auto">{s.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </motion.div>
  );
}
