import { motion } from 'framer-motion';

export function Card({ children, className = '', hover = true, flat = false, ...props }) {
  const base = flat ? 'neu-card-flat' : hover ? 'neu-card' : 'neu-card-flat';
  return (
    <div className={`${base} p-5 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function AnimatedCard({ children, className = '', delay = 0, ...props }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: 'easeOut' }}
      className={`neu-card p-5 ${className}`}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export function MetricCard({ icon: Icon, label, value, sub, color = 'bg-electric-blue', delay = 0 }) {
  return (
    <AnimatedCard delay={delay} className="flex items-start gap-4">
      <div className={`${color} p-3 rounded-xl border-2 border-border-brutal`}>
        <Icon className="w-6 h-6 text-white" strokeWidth={2.5} />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-500 uppercase tracking-wide">{label}</p>
        <p className="text-3xl font-bold text-display text-deep-blue mt-0.5">{value}</p>
        {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
      </div>
    </AnimatedCard>
  );
}
