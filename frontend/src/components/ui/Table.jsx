export function Table({ children, className = '' }) {
  return (
    <div className={`overflow-x-auto scrollbar-thin ${className}`}>
      <table className="w-full text-sm">
        {children}
      </table>
    </div>
  );
}

export function Thead({ children }) {
  return (
    <thead>
      <tr className="border-b-2 border-border-brutal bg-slate-50/70 text-left">
        {children}
      </tr>
    </thead>
  );
}

export function Th({ children, className = '' }) {
  return (
    <th className={`px-4 py-3 font-bold text-display text-xs uppercase tracking-wider text-slate-500 ${className}`}>
      {children}
    </th>
  );
}

export function Td({ children, className = '' }) {
  return (
    <td className={`px-4 py-3.5 ${className}`}>
      {children}
    </td>
  );
}

export function Tr({ children, className = '', onClick }) {
  return (
    <tr
      className={`border-b border-slate-200 last:border-b-0 hover:bg-sky-blue/5 transition-colors ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </tr>
  );
}
