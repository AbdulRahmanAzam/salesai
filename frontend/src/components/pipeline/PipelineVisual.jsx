import { motion } from 'framer-motion';
import { Search, Users, Sparkles, Send, BarChart3, CheckCircle2, Loader2, Clock } from 'lucide-react';

const stageConfig = {
  prospecting: { icon: Users, color: 'bg-electric-blue' },
  research: { icon: Search, color: 'bg-sky-blue' },
  personalisation: { icon: Sparkles, color: 'bg-purple-500' },
  outreach: { icon: Send, color: 'bg-accent-green' },
  tracking: { icon: BarChart3, color: 'bg-accent-orange' },
};

const statusConfig = {
  completed: { icon: CheckCircle2, color: 'text-accent-green', bg: 'bg-green-50', border: 'border-green-500' },
  active: { icon: Loader2, color: 'text-electric-blue', bg: 'bg-blue-50', border: 'border-electric-blue', animate: true },
  pending: { icon: Clock, color: 'text-slate-400', bg: 'bg-slate-50', border: 'border-slate-300' },
};

export function PipelineVisual({ stages }) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto scrollbar-thin py-2">
      {stages.map((stage, i) => {
        const cfg = stageConfig[stage.id] || { icon: Clock, color: 'bg-slate-400' };
        const sts = statusConfig[stage.status] || statusConfig.pending;
        const Icon = cfg.icon;
        const StatusIcon = sts.icon;

        return (
          <div key={stage.id} className="flex items-center gap-2">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.1 }}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 ${sts.border} ${sts.bg} min-w-[150px]`}
            >
              <div className={`${cfg.color} p-2 rounded-lg border-2 border-border-brutal`}>
                <Icon className="w-4 h-4 text-white" strokeWidth={2.5} />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-display text-slate-700 truncate">{stage.name}</p>
                <div className="flex items-center gap-1 mt-0.5">
                  <StatusIcon
                    className={`w-3 h-3 ${sts.color} ${sts.animate ? 'animate-spin' : ''}`}
                    strokeWidth={2.5}
                  />
                  <span className="text-[10px] font-semibold text-slate-500">{stage.count} items</span>
                </div>
              </div>
            </motion.div>
            {i < stages.length - 1 && (
              <div className={`w-6 h-0.5 ${stage.status === 'completed' ? 'bg-accent-green' : 'bg-slate-300'} shrink-0 rounded-full`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
