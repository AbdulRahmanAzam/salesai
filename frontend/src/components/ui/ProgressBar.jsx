export function ProgressBar({ value, max = 100, color = 'bg-electric-blue', className = '' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className={`w-full h-3 rounded-full border-2 border-border-brutal bg-slate-100 overflow-hidden ${className}`}>
      <div
        className={`h-full rounded-full ${color} transition-all duration-500 ease-out`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function ConfidenceBar({ value, className = '' }) {
  let color = 'bg-accent-red';
  if (value >= 0.7) color = 'bg-accent-green';
  else if (value >= 0.5) color = 'bg-accent-yellow';
  else if (value >= 0.3) color = 'bg-accent-orange';

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <ProgressBar value={value * 100} color={color} />
      <span className="text-xs font-bold text-slate-500 min-w-[3ch]">{Math.round(value * 100)}%</span>
    </div>
  );
}
