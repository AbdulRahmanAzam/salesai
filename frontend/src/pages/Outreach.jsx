import { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Edit3, Eye, CheckCircle, Clock, Mail, Sparkles, Link2, Target, Search, XCircle, Check, X, CheckCircle2, Loader2, ArrowRight, Save, Plus, Wand2, User } from 'lucide-react';
import { TopBar } from '../components/layout/TopBar';
import { Card, AnimatedCard } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge, StatusBadge } from '../components/ui/Badge';
import { ScoreRing } from '../components/ui/ScoreRing';
import { ConfidenceBar } from '../components/ui/ProgressBar';
import { Modal } from '../components/ui/Modal';
import { HistoryPanel } from '../components/ui/HistoryPanel';
import { useSessions } from '../hooks/useSessions';
import { outreach as outreachApi } from '../services/api';
import { outreachDrafts as defaultDrafts, icpDefaults } from '../data/mockData';
import { runOutreachPipeline, OUTREACH_STEPS } from '../services/outreachRunner';

const statusIcon = {
  draft: Clock,
  ready: CheckCircle,
  sent: Send,
};

const draftStatusColors = {
  draft: 'bg-slate-100 text-slate-600',
  approved: 'bg-green-50 text-green-700 border-green-200',
  rejected: 'bg-red-50 text-red-600 border-red-200',
  sent: 'bg-blue-50 text-blue-700 border-blue-200',
  delivered: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  bounced: 'bg-orange-50 text-orange-600 border-orange-200',
  failed: 'bg-red-100 text-red-700 border-red-300',
};

function DraftCard({ draft, index, onPreview, onApprove, onReject, onSend, sendingIdx }) {
  return (
    <AnimatedCard delay={index * 0.08} className="flex flex-col">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-electric-blue to-sky-blue border-2 border-border-brutal flex items-center justify-center text-white font-bold text-display text-xs shadow-[2px_2px_0_var(--color-border-brutal)]">
            {draft.contact_name.split(' ').map(n => n[0]).join('')}
          </div>
          <div>
            <h3 className="font-semibold text-deep-blue text-sm">{draft.contact_name}</h3>
            <p className="text-[11px] text-slate-400">{draft.contact_title} at {draft.contact_company}</p>
          </div>
        </div>
        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${draftStatusColors[draft.status] || draftStatusColors.draft}`}>
          {draft.status}
        </span>
        {draft.source === 'manual' && (
          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded border bg-sky-50 text-sky-600 border-sky-200 ml-1">
            Manual
          </span>
        )}
      </div>

      <div className="mb-3">
        <p className="text-xs font-bold text-slate-500 mb-1">Subject</p>
        <p className="text-sm text-deep-blue font-medium">{draft.subject}</p>
      </div>

      <p className="text-xs text-slate-500 line-clamp-3 mb-3 flex-1">{draft.body}</p>

      {draft.personalization_signals?.length > 0 && (
        <div className="mb-3">
          <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Signals Used</p>
          <div className="flex flex-wrap gap-1">
            {draft.personalization_signals.slice(0, 3).map((s, i) => (
              <span key={i} className="text-[10px] bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded border border-purple-200">
                {s.length > 40 ? s.slice(0, 40) + '...' : s}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-slate-200">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-accent-yellow" />
            <span className="text-[11px] font-bold text-accent-green">{draft.personalization_score}%</span>
          </div>
          <div className="flex items-center gap-1">
            <Target className="w-3 h-3 text-slate-400" />
            <span className="text-[10px] text-slate-400">Score: {draft.prospect_score}</span>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {draft.status === 'draft' && (
            <>
              <button onClick={() => onApprove(index)} className="p-1 rounded-lg bg-green-50 text-green-600 hover:bg-green-100 border border-green-200 transition-colors" title="Approve">
                <Check className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => onReject(index)} className="p-1 rounded-lg bg-red-50 text-red-500 hover:bg-red-100 border border-red-200 transition-colors" title="Reject">
                <X className="w-3.5 h-3.5" />
              </button>
            </>
          )}
          {draft.status === 'approved' && onSend && (
            <button
              onClick={() => onSend(index)}
              disabled={sendingIdx === index}
              className="px-2 py-1 rounded-lg bg-accent-green text-white hover:bg-green-600 border border-green-600 transition-colors text-[11px] font-bold flex items-center gap-1 disabled:opacity-50"
              title="Send Email"
            >
              <Send className="w-3 h-3" /> {sendingIdx === index ? 'Sending…' : 'Send'}
            </button>
          )}
          {draft.status === 'sent' && (
            <span className="text-[10px] font-bold text-accent-green flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> Sent
            </span>
          )}
          <Button variant="ghost" size="sm" icon={Eye} onClick={() => onPreview(draft, index)}>Preview</Button>
        </div>
      </div>
    </AnimatedCard>
  );
}

function MessagePreview({ draft, index, sessionId, onUpdate }) {
  if (!draft) return null;
  const [editing, setEditing] = useState(false);
  const [editSubject, setEditSubject] = useState(draft.subject);
  const [editBody, setEditBody] = useState(draft.body);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [rejectNotes, setRejectNotes] = useState('');
  const [showReject, setShowReject] = useState(false);
  const [rewriting, setRewriting] = useState(false);

  const canApprove = ['draft'].includes(draft.status);
  const canReject = ['draft', 'approved'].includes(draft.status);
  const canEdit = ['draft', 'rejected'].includes(draft.status);

  async function handleSaveEdit() {
    setSaving(true);
    try {
      if (sessionId) {
        await outreachApi.editDraft(sessionId, index, { subject: editSubject, body: editBody });
      }
      onUpdate(index, { ...draft, subject: editSubject, body: editBody, status: 'draft' });
      setEditing(false);
    } catch (e) { console.error('Edit failed:', e); }
    finally { setSaving(false); }
  }

  async function handleApprove() {
    setSaving(true);
    try {
      if (sessionId) await outreachApi.approveDraft(sessionId, index);
      onUpdate(index, { ...draft, status: 'approved', approved_at: new Date().toISOString() });
    } catch (e) { console.error('Approve failed:', e); }
    finally { setSaving(false); }
  }

  async function handleReject() {
    setSaving(true);
    try {
      if (sessionId) await outreachApi.rejectDraft(sessionId, index, rejectNotes);
      onUpdate(index, { ...draft, status: 'rejected', reviewer_notes: rejectNotes });
      setShowReject(false);
    } catch (e) { console.error('Reject failed:', e); }
    finally { setSaving(false); }
  }

  async function handleAiRewrite() {
    setRewriting(true);
    try {
      const result = await outreachApi.aiRewrite({
        subject: editSubject,
        body: editBody,
        contact_name: draft.contact_name,
        contact_company: draft.contact_company,
      });
      if (result.rewritten) setEditBody(result.rewritten);
    } catch (e) {
      console.error('AI rewrite failed:', e);
      alert(`AI rewrite failed: ${e.message}`);
    } finally { setRewriting(false); }
  }

  async function handleSend() {
    if (!sessionId) return;
    setSending(true);
    try {
      const result = await outreachApi.sendDraft(sessionId, index);
      onUpdate(index, { ...draft, status: 'sent', sent_at: new Date().toISOString(), message_id: result.messageId });
    } catch (e) { console.error('Send failed:', e); alert(`Send failed: ${e.message}`); }
    finally { setSending(false); }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-4 pb-4 border-b-2 border-slate-200">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-electric-blue to-deep-blue border-2 border-border-brutal flex items-center justify-center text-white font-bold text-display shadow-[2px_2px_0_var(--color-border-brutal)]">
          {draft.contact_name.split(' ').map(n => n[0]).join('')}
        </div>
        <div className="flex-1">
          <p className="font-bold text-deep-blue text-display">{draft.contact_name}</p>
          <p className="text-xs text-slate-400">{draft.contact_title} at {draft.contact_company}</p>
          <div className="flex items-center gap-3 mt-1">
            {draft.contact_email && (
              <p className="text-xs text-electric-blue flex items-center gap-1">
                <Mail className="w-3 h-3" /> {draft.contact_email}
              </p>
            )}
            {draft.contact_linkedin && (
              <a href={draft.contact_linkedin} target="_blank" rel="noopener noreferrer" className="text-xs text-electric-blue flex items-center gap-1 hover:underline">
                <Link2 className="w-3 h-3" /> LinkedIn
              </a>
            )}
          </div>
        </div>
        <div className="flex flex-col items-center gap-1">
          <ScoreRing score={draft.personalization_score} size={48} strokeWidth={4} />
          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${draftStatusColors[draft.status] || draftStatusColors.draft}`}>
            {draft.status}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="px-3 py-2 rounded-xl bg-slate-50 border border-slate-200">
          <p className="text-[10px] font-bold text-slate-400 uppercase">Prospect Score</p>
          <p className="text-lg font-bold text-deep-blue text-display">{draft.prospect_score}</p>
        </div>
        <div className="px-3 py-2 rounded-xl bg-slate-50 border border-slate-200">
          <p className="text-[10px] font-bold text-slate-400 uppercase">Research Confidence</p>
          <p className="text-lg font-bold text-deep-blue text-display">{Math.round(draft.research_confidence * 100)}%</p>
        </div>
      </div>

      {draft.reviewer_notes && (
        <div className="px-3 py-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 text-xs">
          <span className="font-bold">Reviewer Notes:</span> {draft.reviewer_notes}
        </div>
      )}

      <div>
        <label className="text-xs font-bold text-display text-slate-500 uppercase mb-1.5 block">Subject Line</label>
        {editing ? (
          <input
            className="neu-input w-full text-sm font-medium text-deep-blue"
            value={editSubject}
            onChange={e => setEditSubject(e.target.value)}
          />
        ) : (
          <div className="neu-input w-full text-sm font-medium text-deep-blue">{draft.subject}</div>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs font-bold text-display text-slate-500 uppercase">Message Body</label>
          {editing && (
            <button
              onClick={handleAiRewrite}
              disabled={rewriting || !editBody.trim()}
              className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-bold bg-purple-50 text-purple-600 border border-purple-200 hover:bg-purple-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {rewriting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
              {rewriting ? 'Rewriting...' : 'AI Enhance'}
            </button>
          )}
        </div>
        {editing ? (
          <textarea
            className="neu-input w-full !p-4 text-sm text-slate-700 leading-relaxed min-h-[200px] resize-y"
            value={editBody}
            onChange={e => setEditBody(e.target.value)}
          />
        ) : (
          <div className="neu-input w-full !p-4 text-sm text-slate-700 leading-relaxed whitespace-pre-line min-h-[200px]">
            {draft.body}
          </div>
        )}
      </div>

      {draft.personalization_signals?.length > 0 && (
        <div>
          <label className="text-xs font-bold text-display text-slate-500 uppercase mb-1.5 block">Personalisation Signals</label>
          <div className="space-y-1.5">
            {draft.personalization_signals.map((s, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-slate-600">
                <span className="w-5 h-5 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center text-[10px] font-bold text-purple-600 shrink-0 mt-0.5">{i + 1}</span>
                {s}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reject notes section */}
      {showReject && (
        <div className="p-3 rounded-xl bg-red-50 border-2 border-red-200 space-y-2">
          <label className="text-xs font-bold text-red-600 uppercase block">Rejection Notes (optional)</label>
          <textarea
            className="w-full rounded-lg border border-red-200 p-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-300 resize-none"
            rows={2}
            placeholder="Reason for rejection..."
            value={rejectNotes}
            onChange={e => setRejectNotes(e.target.value)}
          />
          <div className="flex gap-2">
            <Button variant="danger" size="sm" icon={XCircle} onClick={handleReject} disabled={saving}>
              Confirm Reject
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowReject(false)}>Cancel</Button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between pt-3 border-t-2 border-slate-200">
        <div className="flex items-center gap-3">
          <Sparkles className="w-4 h-4 text-accent-yellow" />
          <span className="text-sm font-bold text-slate-600">Personalisation Score</span>
          <ScoreRing score={draft.personalization_score} size={40} strokeWidth={4} />
        </div>
        <div className="flex items-center gap-2">
          {editing ? (
            <>
              <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>Cancel</Button>
              <Button size="sm" icon={CheckCircle} onClick={handleSaveEdit} disabled={saving}>
                {saving ? 'Saving…' : 'Save Changes'}
              </Button>
            </>
          ) : (
            <>
              {canEdit && (
                <Button variant="secondary" size="sm" icon={Edit3} onClick={() => { setEditSubject(draft.subject); setEditBody(draft.body); setEditing(true); }}>
                  Edit Draft
                </Button>
              )}
              {canReject && !showReject && (
                <Button variant="secondary" size="sm" icon={XCircle} onClick={() => setShowReject(true)}>
                  Reject
                </Button>
              )}
              {canApprove && (
                <Button size="sm" icon={CheckCircle} onClick={handleApprove} disabled={saving}>
                  {saving ? 'Approving…' : 'Approve'}
                </Button>
              )}
              {draft.status === 'approved' && (
                <Button size="sm" icon={Send} className="bg-accent-green border-accent-green text-white" onClick={handleSend} disabled={sending || !sessionId}>
                  {sending ? 'Sending…' : 'Send Email'}
                </Button>
              )}
              {draft.status === 'sent' && (
                <span className="text-xs font-bold text-accent-green flex items-center gap-1">
                  <CheckCircle className="w-4 h-4" /> Sent
                </span>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ManualComposeForm({ onAdd }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [company, setCompany] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [rewriting, setRewriting] = useState(false);

  function reset() {
    setEmail(''); setName(''); setCompany(''); setSubject(''); setBody('');
  }

  function handleAdd() {
    if (!email || !subject || !body) return;
    onAdd({
      _key: `manual_${Date.now()}`,
      contact_name: name || email.split('@')[0],
      contact_title: '',
      contact_company: company || '',
      contact_email: email,
      contact_linkedin: '',
      subject,
      body,
      personalization_score: 0,
      personalization_signals: [],
      prospect_score: 0,
      research_confidence: 0,
      status: 'draft',
      source: 'manual',
    });
    reset();
    setOpen(false);
  }

  async function handleAiRewrite() {
    if (!body.trim()) return;
    setRewriting(true);
    try {
      const result = await outreachApi.aiRewrite({ subject, body, contact_name: name, contact_company: company });
      if (result.rewritten) setBody(result.rewritten);
    } catch (e) {
      console.error('AI rewrite failed:', e);
      alert(`AI rewrite failed: ${e.message}`);
    } finally { setRewriting(false); }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl border-2 border-dashed border-slate-300 text-slate-500 hover:border-electric-blue hover:text-electric-blue hover:bg-blue-50/50 transition-all text-sm font-semibold"
      >
        <Plus className="w-4 h-4" /> Add Manual Recipient
      </button>
    );
  }

  return (
    <Card className="!p-5 border-electric-blue">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-electric-blue">
            <User className="w-4 h-4 text-white" />
          </div>
          <h3 className="text-sm font-bold text-display text-deep-blue">Compose Manual Email</h3>
        </div>
        <button onClick={() => { reset(); setOpen(false); }} className="text-slate-400 hover:text-slate-600">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-3">
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Email *</label>
          <input
            type="email"
            className="neu-input w-full text-sm"
            placeholder="john@company.com"
            value={email}
            onChange={e => setEmail(e.target.value)}
          />
        </div>
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Name</label>
          <input
            className="neu-input w-full text-sm"
            placeholder="John Doe"
            value={name}
            onChange={e => setName(e.target.value)}
          />
        </div>
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Company</label>
          <input
            className="neu-input w-full text-sm"
            placeholder="Acme Inc"
            value={company}
            onChange={e => setCompany(e.target.value)}
          />
        </div>
      </div>

      <div className="mb-3">
        <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Subject *</label>
        <input
          className="neu-input w-full text-sm font-medium"
          placeholder="Your email subject line..."
          value={subject}
          onChange={e => setSubject(e.target.value)}
        />
      </div>

      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <label className="text-[10px] font-bold text-slate-500 uppercase">Body *</label>
          <button
            onClick={handleAiRewrite}
            disabled={rewriting || !body.trim()}
            className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-bold bg-purple-50 text-purple-600 border border-purple-200 hover:bg-purple-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {rewriting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
            {rewriting ? 'Rewriting...' : 'AI Enhance'}
          </button>
        </div>
        <textarea
          className="neu-input w-full !p-3 text-sm text-slate-700 leading-relaxed min-h-[120px] resize-y"
          placeholder="Write your email body... then hit AI Enhance to polish it"
          value={body}
          onChange={e => setBody(e.target.value)}
        />
      </div>

      <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
        <Button variant="secondary" size="sm" onClick={() => { reset(); setOpen(false); }}>Cancel</Button>
        <Button size="sm" icon={Plus} onClick={handleAdd} disabled={!email || !subject || !body}>
          Add to Queue
        </Button>
      </div>
    </Card>
  );
}

function OutreachStepIndicator({ steps }) {
  return (
    <div className="space-y-2.5">
      {OUTREACH_STEPS.map((cfg, i) => {
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

export default function Outreach() {
  const location = useLocation();
  const navigate = useNavigate();
  const { dossiers: incomingDossiers, icp: incomingIcp } = location.state || {};
  const effectiveIcp = incomingIcp || icpDefaults;

  const [preview, setPreview] = useState(null);
  const [previewIdx, setPreviewIdx] = useState(null);
  const [draftsData, setDraftsData] = useState(incomingDossiers ? [] : defaultDrafts);
  const [activeLabel, setActiveLabel] = useState(null);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [batchThreshold, setBatchThreshold] = useState(70);
  const [batchApproving, setBatchApproving] = useState(false);
  const [sendingIdx, setSendingIdx] = useState(null);
  const [sendingAll, setSendingAll] = useState(false);
  const [phase, setPhase] = useState(incomingDossiers ? 'running' : 'idle');
  const [steps, setSteps] = useState([]);
  const [outreachSummary, setOutreachSummary] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const savedRef = useRef(false);

  const {
    sessions, loading: histLoading, error: histError,
    loadSession, saveSession, deleteSession, fetchSessions,
  } = useSessions(outreachApi);

  const handleStep = useCallback((index, data) => {
    setSteps(prev => {
      const next = [...prev];
      next[index] = data;
      return next;
    });
  }, []);

  const handleDraft = useCallback((draft) => {
    setDraftsData(prev => [...prev, draft]);
  }, []);

  useEffect(() => {
    if (!incomingDossiers || phase !== 'running') return;

    let cancelled = false;
    (async () => {
      try {
        const result = await runOutreachPipeline({
          dossiers: incomingDossiers,
          icp: effectiveIcp,
          onStep: (i, d) => { if (!cancelled) handleStep(i, d); },
          onDraft: (d) => { if (!cancelled) handleDraft(d); },
        });
        if (!cancelled) {
          setOutreachSummary(result.summary);
          setPhase('done');
        }
      } catch (err) {
        console.error('[Outreach] Pipeline error:', err);
        if (!cancelled) {
          setErrorMessage(err.message || 'Unknown error');
          setPhase('error');
        }
      }
    })();

    return () => { cancelled = true; };
  }, [incomingDossiers, phase, effectiveIcp, handleStep, handleDraft]);

  // Auto-save session when done
  useEffect(() => {
    if (phase !== 'done' || savedRef.current || !draftsData.length) return;
    savedRef.current = true;
    const name = effectiveIcp?.product_name || 'Outreach Session';

    setSaveStatus('saving');
    saveSession({
      session_name: `Outreach: ${name}`,
      drafts: draftsData,
      summary: outreachSummary,
    }).then((saved) => {
      setSaveStatus(saved ? 'saved' : 'error');
      if (saved?._id) setActiveSessionId(saved._id);
      setTimeout(() => setSaveStatus(null), 3000);
    });
  }, [phase, draftsData, outreachSummary, effectiveIcp, saveSession]);

  async function handleLoadHistory(id) {
    const session = await loadSession(id);
    if (session?.drafts) {
      setDraftsData(session.drafts);
      setActiveLabel(session.session_name);
      setActiveSessionId(id);
    }
  }

  function handleDraftUpdate(idx, updated) {
    setDraftsData(prev => {
      const next = prev.map((d, i) => i === idx ? updated : d);
      // Persist to DB if session exists
      if (activeSessionId) {
        outreachApi.updateSession(activeSessionId, { drafts: next }).catch(e =>
          console.error('Failed to sync draft update to DB:', e)
        );
      }
      return next;
    });
    if (preview && previewIdx === idx) setPreview(updated);
  }

  async function handleAddManualDraft(draft) {
    const newDrafts = [...draftsData, draft];
    setDraftsData(newDrafts);

    try {
      if (activeSessionId) {
        // Update existing session with the new drafts array
        await outreachApi.updateSession(activeSessionId, { drafts: newDrafts });
      } else {
        // No session yet — create one
        const name = effectiveIcp?.product_name || 'Outreach Session';
        const saved = await saveSession({
          session_name: `Outreach: ${name}`,
          drafts: newDrafts,
          summary: outreachSummary,
        });
        if (saved?._id) setActiveSessionId(saved._id);
      }
    } catch (e) {
      console.error('Failed to save manual draft to DB:', e);
    }
  }

  async function handleApproveDraft(idx) {
    try {
      if (activeSessionId) await outreachApi.approveDraft(activeSessionId, idx);
      handleDraftUpdate(idx, { ...draftsData[idx], status: 'approved', approved_at: new Date().toISOString() });
    } catch (e) { console.error('Approve failed:', e); }
  }

  async function handleRejectDraft(idx) {
    try {
      if (activeSessionId) await outreachApi.rejectDraft(activeSessionId, idx, '');
      handleDraftUpdate(idx, { ...draftsData[idx], status: 'rejected' });
    } catch (e) { console.error('Reject failed:', e); }
  }

  async function handleBatchApprove() {
    setBatchApproving(true);
    try {
      if (activeSessionId) {
        await outreachApi.approveBatch(activeSessionId, batchThreshold);
      }
      setDraftsData(prev => prev.map(d =>
        d.status === 'draft' && (d.personalization_score || 0) >= batchThreshold
          ? { ...d, status: 'approved', approved_at: new Date().toISOString() }
          : d
      ));
    } catch (e) { console.error('Batch approve failed:', e); }
    finally { setBatchApproving(false); }
  }

  async function handleSendDraft(idx) {
    if (!activeSessionId) return;
    setSendingIdx(idx);
    try {
      const result = await outreachApi.sendDraft(activeSessionId, idx);
      handleDraftUpdate(idx, { ...draftsData[idx], status: 'sent', sent_at: new Date().toISOString(), message_id: result.messageId });
    } catch (e) { console.error('Send failed:', e); alert(`Send failed: ${e.message}`); }
    finally { setSendingIdx(null); }
  }

  async function handleSendAllApproved() {
    if (!activeSessionId) return;
    setSendingAll(true);
    try {
      const result = await outreachApi.sendApproved(activeSessionId);
      // Update local state for all sent/failed drafts
      if (result.results) {
        setDraftsData(prev => prev.map((d, i) => {
          const r = result.results.find(r => r.idx === i);
          if (!r) return d;
          return r.success
            ? { ...d, status: 'sent', sent_at: new Date().toISOString(), message_id: r.messageId }
            : { ...d, status: 'failed', send_error: r.error };
        }));
      }
      alert(`Sent: ${result.sent}, Failed: ${result.failed}`);
    } catch (e) { console.error('Batch send failed:', e); alert(`Batch send failed: ${e.message}`); }
    finally { setSendingAll(false); }
  }

  const drafts = draftsData.filter(d => d.status === 'draft').length;
  const approved = draftsData.filter(d => d.status === 'approved').length;
  const rejected = draftsData.filter(d => d.status === 'rejected').length;
  const sent = draftsData.filter(d => ['sent', 'delivered'].includes(d.status)).length;
  const avgScore = draftsData.length > 0
    ? Math.round(draftsData.reduce((s, d) => s + (d.personalization_score || 0), 0) / draftsData.length)
    : 0;

  const isRunning = phase === 'running';

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
      <TopBar
        title={isRunning ? 'Personalisation Agent Running...' : 'Outreach Queue'}
        subtitle={
          isRunning ? `Writing personalised emails — ${draftsData.length} drafts generated`
            : activeLabel ? `Session: ${activeLabel}`
              : 'Personalised drafts from the personalisation agent'
        }
      />

      <div className="p-6 space-y-5">
        {/* Pipeline progress (shown while running) */}
        {isRunning && (
          <Card flat className="!p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-xl bg-accent-green border-2 border-border-brutal">
                <Sparkles className="w-5 h-5 text-white" strokeWidth={2.5} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-display text-deep-blue">Personalisation Agent</h3>
                <p className="text-xs text-slate-400">Extracting signals &amp; writing tailored outreach for each lead</p>
              </div>
            </div>
            <OutreachStepIndicator steps={steps} />
          </Card>
        )}

        {/* Summary cards (shown when pipeline completes) */}
        {phase === 'done' && outreachSummary && (
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Drafts', value: outreachSummary.total_drafts, color: 'text-electric-blue' },
              { label: 'Avg Personalisation', value: `${outreachSummary.avg_personalization_score}%`, color: 'text-accent-green' },
              { label: 'Avg Score', value: outreachSummary.avg_prospect_score, color: 'text-sky-blue' },
              { label: 'High Quality', value: outreachSummary.high_quality, color: 'text-purple-500' },
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

        {/* Status badges + history */}
        {draftsData.length > 0 && (
          <div className="flex items-center gap-3 flex-wrap">
            <Badge variant="slate">{drafts} Draft</Badge>
            <Badge variant="green">{approved} Approved</Badge>
            <Badge variant="red">{rejected} Rejected</Badge>
            <Badge variant="blue">{sent} Sent</Badge>
            <Badge variant="purple">Avg: {avgScore}%</Badge>
            <span className="text-xs text-slate-400 ml-auto">All messages are queued for review — never auto-sent</span>
            <div className="flex items-center gap-2">
              {saveStatus === 'saving' && (
                <span className="text-xs text-slate-400 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Saving...</span>
              )}
              {saveStatus === 'saved' && (
                <span className="text-xs text-accent-green flex items-center gap-1"><Save className="w-3 h-3" /> Saved</span>
              )}
              <HistoryPanel
                sessions={sessions}
                loading={histLoading}
                error={histError}
                onLoad={handleLoadHistory}
                onDelete={deleteSession}
                onRetry={fetchSessions}
                agentName="Outreach Agent"
                accentColor="bg-accent-green"
                renderMeta={(s) => (
                  <div className="flex flex-wrap gap-1.5">
                    {s.summary?.total_drafts && <span className="text-[10px] bg-accent-green/10 text-accent-green px-1.5 py-0.5 rounded">{s.summary.total_drafts} drafts</span>}
                    {s.summary?.avg_personalization_score && <span className="text-[10px] bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded">avg {s.summary.avg_personalization_score}%</span>}
                  </div>
                )}
              />
            </div>
          </div>
        )}

        {/* Batch approve bar */}
        {drafts > 0 && (
          <Card className="!p-3">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-xs font-bold text-slate-600 text-display uppercase">Batch Approve</span>
              <span className="text-[11px] text-slate-400">Approve all drafts with personalisation score ≥</span>
              <input
                type="number"
                min={0}
                max={100}
                value={batchThreshold}
                onChange={e => setBatchThreshold(Number(e.target.value))}
                className="w-16 text-center text-sm font-bold rounded-lg border-2 border-border-brutal px-1.5 py-1 focus:outline-none focus:ring-2 focus:ring-electric-blue"
              />
              <span className="text-[11px] text-slate-400">%</span>
              <Button size="sm" icon={CheckCircle} onClick={handleBatchApprove} disabled={batchApproving}>
                {batchApproving ? 'Approving…' : `Approve ${draftsData.filter(d => d.status === 'draft' && (d.personalization_score || 0) >= batchThreshold).length} Drafts`}
              </Button>
              {approved > 0 && activeSessionId && (
                <Button size="sm" icon={Send} onClick={handleSendAllApproved} disabled={sendingAll} className="bg-accent-green border-accent-green text-white ml-2">
                  {sendingAll ? 'Sending…' : `Send ${approved} Approved`}
                </Button>
              )}
            </div>
          </Card>
        )}

        {/* Manual compose form */}
        {(phase === 'done' || phase === 'idle') && (
          <ManualComposeForm onAdd={handleAddManualDraft} />
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {draftsData.map((d, i) => (
            <DraftCard
              key={d._key || d.id || i}
              draft={d}
              index={i}
              onPreview={(draft, idx) => { setPreviewIdx(i); setPreview(draft); }}
              onApprove={handleApproveDraft}
              onReject={handleRejectDraft}
              onSend={activeSessionId ? handleSendDraft : null}
              sendingIdx={sendingIdx}
            />
          ))}
        </div>

        {/* Empty state while running with no drafts yet */}
        {isRunning && draftsData.length === 0 && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center space-y-2">
              <Loader2 className="w-8 h-8 animate-spin text-accent-green mx-auto" />
              <p className="text-sm text-slate-500">Writing personalised outreach emails...</p>
            </div>
          </div>
        )}

        {/* Continue to Tracking */}
        {(phase === 'done' || (phase === 'idle' && draftsData.length > 0)) && draftsData.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 pt-2"
          >
            <Button icon={ArrowRight} onClick={() => navigate('/tracking')}>
              Continue to Tracking
            </Button>
            <Button variant="secondary" onClick={() => navigate('/icp')}>
              New Search
            </Button>
          </motion.div>
        )}

        {phase === 'error' && (
          <Card flat className="!p-6 text-center">
            <p className="text-accent-red font-bold">Personalisation pipeline failed. Please try again.</p>
            {errorMessage && <p className="text-xs text-slate-400 mt-1">{errorMessage}</p>}
            <Button variant="secondary" onClick={() => navigate('/research')} className="mt-3">Back to Research</Button>
          </Card>
        )}
      </div>

      <Modal
        isOpen={!!preview}
        onClose={() => { setPreview(null); setPreviewIdx(null); }}
        title={preview ? `Outreach: ${preview.contact_name}` : ''}
        wide
      >
        <MessagePreview
          draft={preview}
          index={previewIdx}
          sessionId={activeSessionId}
          onUpdate={handleDraftUpdate}
        />
      </Modal>
    </motion.div>
  );
}
