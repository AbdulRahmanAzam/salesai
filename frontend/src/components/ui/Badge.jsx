const variants = {
  blue: 'bg-sky-blue/20 text-deep-blue border-deep-blue',
  green: 'bg-green-100 text-green-800 border-green-700',
  red: 'bg-red-100 text-red-700 border-red-600',
  yellow: 'bg-yellow-100 text-yellow-800 border-yellow-600',
  orange: 'bg-orange-100 text-orange-700 border-orange-600',
  slate: 'bg-slate-100 text-slate-600 border-slate-500',
  purple: 'bg-purple-100 text-purple-700 border-purple-600',
};

const statusMap = {
  review_required: { variant: 'yellow', label: 'Review Required' },
  approved: { variant: 'green', label: 'Approved' },
  rejected: { variant: 'red', label: 'Rejected' },
  researched: { variant: 'blue', label: 'Researched' },
  draft: { variant: 'slate', label: 'Draft' },
  ready: { variant: 'green', label: 'Ready' },
  sent: { variant: 'blue', label: 'Sent' },
  opened: { variant: 'orange', label: 'Opened' },
  replied: { variant: 'green', label: 'Replied' },
  warm_lead: { variant: 'purple', label: 'Warm Lead' },
  no_response: { variant: 'slate', label: 'No Response' },
};

export function Badge({ children, variant = 'blue', className = '' }) {
  return (
    <span className={`neu-badge ${variants[variant] || variants.blue} ${className}`}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }) {
  const config = statusMap[status] || { variant: 'slate', label: status };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

export function ScoreBadge({ score }) {
  let variant = 'red';
  if (score >= 70) variant = 'green';
  else if (score >= 50) variant = 'yellow';
  else if (score >= 30) variant = 'orange';
  return <Badge variant={variant}>{score}</Badge>;
}
