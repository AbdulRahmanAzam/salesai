import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Filter, ChevronDown, ChevronUp, ExternalLink, CheckCircle, XCircle, ArrowRight, Link2, Mail, Globe } from 'lucide-react';
import { TopBar } from '../components/layout/TopBar';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge, Badge } from '../components/ui/Badge';
import { ScoreRing } from '../components/ui/ScoreRing';
import { Table, Thead, Th, Td, Tr } from '../components/ui/Table';
import { HistoryPanel } from '../components/ui/HistoryPanel';
import { useSessions } from '../hooks/useSessions';
import { prospecting } from '../services/api';
import { prospects as initialProspects } from '../data/mockData';

export default function Prospects() {
  const {
    sessions, loading: histLoading, error: histError,
    loadSession, deleteSession, fetchSessions,
  } = useSessions(prospecting);

  const [data, setData] = useState(initialProspects);
  const [activeLabel, setActiveLabel] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [sortBy, setSortBy] = useState('score');
  const [sortDir, setSortDir] = useState('desc');
  const [showFilters, setShowFilters] = useState(false);

  async function handleLoadHistory(id) {
    const session = await loadSession(id);
    if (session?.leads) {
      setData(session.leads);
      setActiveLabel(session.session_name);
    }
  }

  const sources = useMemo(() => [...new Set(data.map(p => p.contact.source))], [data]);

  const filtered = useMemo(() => {
    let list = [...data];
    if (statusFilter !== 'all') list = list.filter(p => p.status === statusFilter);
    if (sourceFilter !== 'all') list = list.filter(p => p.contact.source === sourceFilter);
    list.sort((a, b) => {
      let va, vb;
      if (sortBy === 'score') { va = a.score; vb = b.score; }
      else if (sortBy === 'name') { va = a.contact.full_name; vb = b.contact.full_name; }
      else if (sortBy === 'company') { va = a.contact.company_name; vb = b.contact.company_name; }
      else { va = a.score; vb = b.score; }
      if (typeof va === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
      return sortDir === 'asc' ? va - vb : vb - va;
    });
    return list;
  }, [data, statusFilter, sourceFilter, sortBy, sortDir]);

  function toggleSort(col) {
    if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortBy(col); setSortDir('desc'); }
  }

  function pKey(p) {
    return p.contact.full_name + '|' + p.contact.company_name;
  }

  function updateStatus(prospect, status) {
    setData(d => d.map(p => pKey(p) === pKey(prospect) ? { ...p, status } : p));
  }

  const SortIcon = ({ col }) => {
    if (sortBy !== col) return null;
    return sortDir === 'asc' ? <ChevronUp className="w-3 h-3 inline ml-0.5" /> : <ChevronDown className="w-3 h-3 inline ml-0.5" />;
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
      <TopBar title="Prospect Queue" subtitle={activeLabel ? `Session: ${activeLabel}` : `${filtered.length} prospects found`} />

      <div className="p-6 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="secondary" size="sm" icon={Filter} onClick={() => setShowFilters(f => !f)}>
              Filters
            </Button>
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
                </div>
              )}
            />
            {statusFilter !== 'all' && (
              <Badge variant="blue">{statusFilter} <button onClick={() => setStatusFilter('all')} className="ml-1 cursor-pointer"><XCircle className="w-3 h-3" /></button></Badge>
            )}
            {sourceFilter !== 'all' && (
              <Badge variant="blue">{sourceFilter} <button onClick={() => setSourceFilter('all')} className="ml-1 cursor-pointer"><XCircle className="w-3 h-3" /></button></Badge>
            )}
          </div>
          <p className="text-xs text-slate-400">
            {data.filter(p => p.status === 'approved').length} approved, {data.filter(p => p.status === 'review_required').length} pending review
          </p>
        </div>

        <AnimatePresence>
          {showFilters && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
              <Card flat className="!p-4 flex flex-wrap gap-4">
                <div>
                  <label className="text-xs font-bold text-display text-slate-500 uppercase mb-1 block">Status</label>
                  <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="neu-input text-sm py-2">
                    <option value="all">All Statuses</option>
                    <option value="review_required">Review Required</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold text-display text-slate-500 uppercase mb-1 block">Source</label>
                  <select value={sourceFilter} onChange={e => setSourceFilter(e.target.value)} className="neu-input text-sm py-2">
                    <option value="all">All Sources</option>
                    {sources.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        <Card flat className="!p-0 overflow-hidden">
          <Table>
            <Thead>
              <Th className="cursor-pointer select-none" onClick={() => toggleSort('score')}>Score <SortIcon col="score" /></Th>
              <Th className="cursor-pointer select-none" onClick={() => toggleSort('name')}>Name <SortIcon col="name" /></Th>
              <Th className="hidden md:table-cell cursor-pointer select-none" onClick={() => toggleSort('company')}>Company <SortIcon col="company" /></Th>
              <Th className="hidden sm:table-cell">Source</Th>
              <Th>Status</Th>
              <Th>Actions</Th>
            </Thead>
            <tbody>
              {filtered.map((p) => {
                const k = pKey(p);
                return (
                  <ProspectRow
                    key={k}
                    prospect={p}
                    expanded={expanded === k}
                    onToggle={() => setExpanded(expanded === k ? null : k)}
                    onApprove={() => updateStatus(p, 'approved')}
                    onReject={() => updateStatus(p, 'rejected')}
                  />
                );
              })}
            </tbody>
          </Table>
        </Card>
      </div>
    </motion.div>
  );
}

function ProspectRow({ prospect: p, expanded, onToggle, onApprove, onReject }) {
  return (
    <>
      <Tr onClick={onToggle}>
        <Td><ScoreRing score={p.score} size={42} strokeWidth={4} /></Td>
        <Td>
          <p className="font-semibold text-deep-blue">{p.contact.full_name}</p>
          <p className="text-xs text-slate-400">{p.contact.title}</p>
        </Td>
        <Td className="hidden md:table-cell">
          <p className="text-slate-600">{p.contact.company_name}</p>
          <p className="text-[11px] text-slate-400">{p.contact.company_domain}</p>
        </Td>
        <Td className="hidden sm:table-cell">
          <span className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">{p.contact.source}</span>
        </Td>
        <Td><StatusBadge status={p.status} /></Td>
        <Td>
          <div className="flex items-center gap-1.5" onClick={e => e.stopPropagation()}>
            {p.status === 'review_required' && (
              <>
                <button onClick={onApprove} className="p-1.5 rounded-lg hover:bg-green-50 text-accent-green transition-colors cursor-pointer" title="Approve">
                  <CheckCircle className="w-4 h-4" />
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
        </Td>
      </Tr>
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
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <h4 className="text-xs font-bold text-display text-slate-500 uppercase mb-2">Signals</h4>
                      <ul className="space-y-1">
                        {p.contact.signals.map((s, i) => (
                          <li key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-electric-blue mt-1.5 shrink-0" />
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-display text-slate-500 uppercase mb-2">Reasons</h4>
                      <ul className="space-y-1">
                        {p.reasons.map((r, i) => (
                          <li key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-accent-yellow mt-1.5 shrink-0" />
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-display text-slate-500 uppercase mb-2">Links & Notes</h4>
                      <div className="space-y-2">
                        {p.contact.linkedin_url && (
                          <a href={p.contact.linkedin_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-xs text-electric-blue font-semibold hover:underline">
                            <Link2 className="w-3.5 h-3.5" /> LinkedIn Profile
                          </a>
                        )}
                        {p.contact.email && (
                          <p className="flex items-center gap-1.5 text-xs text-slate-600">
                            <Mail className="w-3.5 h-3.5 text-slate-400" /> {p.contact.email}
                          </p>
                        )}
                        {p.contact.company_domain && (
                          <a href={`https://${p.contact.company_domain}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-xs text-electric-blue font-semibold hover:underline">
                            <Globe className="w-3.5 h-3.5" /> {p.contact.company_domain}
                          </a>
                        )}
                        {p.contact.research_notes.map((n, i) => (
                          <p key={i} className="text-xs text-slate-500 italic">{n}</p>
                        ))}
                      </div>
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
