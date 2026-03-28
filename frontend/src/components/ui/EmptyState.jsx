import { Inbox } from 'lucide-react';
import { Button } from './Button';

export function EmptyState({
  icon: Icon = Inbox,
  title = 'Nothing here yet',
  description = 'Data will appear once the pipeline runs.',
  action,
  actionLabel,
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-sky-blue/20 border-2 border-border-brutal flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-electric-blue" strokeWidth={2} />
      </div>
      <h3 className="text-lg font-bold text-display text-deep-blue mb-1">{title}</h3>
      <p className="text-sm text-slate-500 max-w-sm">{description}</p>
      {action && (
        <Button className="mt-4" onClick={action}>{actionLabel}</Button>
      )}
    </div>
  );
}
