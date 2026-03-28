const sizeMap = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-5 py-2.5 text-sm',
  lg: 'px-6 py-3 text-base',
};

const variantMap = {
  primary: 'bg-electric-blue text-white hover:bg-blue-600',
  secondary: 'bg-white text-deep-blue hover:bg-slate-50',
  accent: 'bg-accent-yellow text-deep-blue hover:bg-yellow-400',
  danger: 'bg-accent-red text-white hover:bg-red-600',
  ghost: 'bg-transparent text-slate-600 hover:bg-slate-100 border-transparent shadow-none hover:border-border-brutal hover:shadow-[3px_3px_0_var(--color-border-brutal)]',
};

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconRight: IconRight,
  className = '',
  ...props
}) {
  const isGhost = variant === 'ghost';
  return (
    <button
      className={`
        ${isGhost ? '' : 'neu-btn'} 
        ${variantMap[variant]} 
        ${sizeMap[size]} 
        inline-flex items-center gap-2 
        ${isGhost ? 'rounded-xl font-semibold text-display cursor-pointer transition-all duration-150' : ''}
        disabled:opacity-50 disabled:cursor-not-allowed
        ${className}
      `}
      {...props}
    >
      {Icon && <Icon className="w-4 h-4" strokeWidth={2.5} />}
      {children}
      {IconRight && <IconRight className="w-4 h-4" strokeWidth={2.5} />}
    </button>
  );
}
