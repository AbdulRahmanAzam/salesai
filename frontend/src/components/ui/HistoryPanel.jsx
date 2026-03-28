import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { History, Clock, Trash2, Eye, ChevronRight, Loader2, AlertCircle, X } from 'lucide-react';

function formatDate(iso) {
  if (!iso) return '--';
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
}

export function HistoryPanel({
  sessions,
  loading,
  error,
  onLoad,
  onDelete,
  onRetry,
  renderMeta,
  agentName = 'Agent',
  accentColor = 'bg-electric-blue',
}) {
  const [open, setOpen] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  async function handleDelete(e, id) {
    e.stopPropagation();
    if (!confirm('Delete this session permanently?')) return;
    setDeletingId(id);
    try {
      await onDelete(id);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold
          bg-white border-2 border-slate-200 text-slate-600 hover:border-electric-blue
          hover:text-deep-blue hover:shadow-[2px_2px_0_var(--color-electric-blue)]
          transition-all cursor-pointer"
      >
        <History className="w-4 h-4" />
        History
        {sessions.length > 0 && (
          <span className="ml-1 text-[10px] bg-electric-blue text-white px-1.5 py-0.5 rounded-full font-bold">
            {sessions.length}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/20 z-40"
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed right-0 top-0 bottom-0 w-[420px] max-w-[90vw] bg-white
                border-l-2 border-slate-200 shadow-[-4px_0_24px_rgba(0,0,0,0.1)]
                z-50 flex flex-col"
            >
              <div className="flex items-center justify-between px-5 py-4 border-b-2 border-slate-200">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-xl ${accentColor} border-2 border-border-brutal`}>
                    <History className="w-4 h-4 text-white" strokeWidth={2.5} />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-display text-deep-blue">{agentName} History</h2>
                    <p className="text-[11px] text-slate-400">{sessions.length} session{sessions.length !== 1 ? 's' : ''} saved</p>
                  </div>
                </div>
                <button
                  onClick={() => setOpen(false)}
                  className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
                {loading && (
                  <div className="flex items-center justify-center py-12 text-slate-400">
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    <span className="text-sm">Loading sessions...</span>
                  </div>
                )}

                {error && (
                  <div className="flex flex-col items-center py-8 text-center">
                    <AlertCircle className="w-8 h-8 text-accent-red mb-2" />
                    <p className="text-sm text-slate-600 font-medium mb-1">Failed to load sessions</p>
                    <p className="text-xs text-slate-400 mb-3">{error}</p>
                    {onRetry && (
                      <button
                        onClick={onRetry}
                        className="text-xs text-electric-blue font-semibold hover:underline cursor-pointer"
                      >
                        Try again
                      </button>
                    )}
                  </div>
                )}

                {!loading && !error && sessions.length === 0 && (
                  <div className="flex flex-col items-center py-12 text-center">
                    <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center mb-3">
                      <Clock className="w-6 h-6 text-slate-300" />
                    </div>
                    <p className="text-sm font-medium text-slate-500">No sessions yet</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Run the {agentName.toLowerCase()} to create your first session
                    </p>
                  </div>
                )}

                {!loading && !error && sessions.map((session) => (
                  <motion.div
                    key={session._id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="group relative p-4 rounded-xl border-2 border-slate-200 hover:border-electric-blue
                      hover:shadow-[2px_2px_0_var(--color-electric-blue)] transition-all cursor-pointer"
                    onClick={() => { onLoad(session._id); setOpen(false); }}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="text-sm font-bold text-deep-blue group-hover:text-electric-blue transition-colors pr-8 line-clamp-1">
                        {session.session_name}
                      </h3>
                      <button
                        onClick={(e) => handleDelete(e, session._id)}
                        disabled={deletingId === session._id}
                        className="absolute top-3 right-3 p-1.5 rounded-lg opacity-0 group-hover:opacity-100
                          hover:bg-red-50 text-slate-300 hover:text-accent-red transition-all cursor-pointer"
                      >
                        {deletingId === session._id
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Trash2 className="w-3.5 h-3.5" />
                        }
                      </button>
                    </div>

                    {renderMeta && (
                      <div className="mb-2">
                        {renderMeta(session)}
                      </div>
                    )}

                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-slate-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDate(session.created_at)}
                      </span>
                      <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-electric-blue transition-colors" />
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
