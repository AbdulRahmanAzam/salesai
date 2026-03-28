import { Search, Bell, Sparkles } from 'lucide-react';

export function TopBar({ title, subtitle }) {
  return (
    <header className="sticky top-0 z-30 bg-surface/80 backdrop-blur-md border-b-2 border-border-brutal px-6 py-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-display text-deep-blue">{title}</h1>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>

        <div className="flex items-center gap-3">
          <div className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search prospects, companies..."
              className="neu-input pl-9 pr-4 py-2 w-64 text-sm"
            />
          </div>

          <button className="relative p-2.5 rounded-xl border-2 border-border-brutal bg-white hover:bg-slate-50 transition-colors cursor-pointer shadow-[2px_2px_0_var(--color-border-brutal)]">
            <Bell className="w-4 h-4 text-slate-500" />
            <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-accent-red rounded-full border-2 border-white" />
          </button>

          <div className="flex items-center gap-2 pl-3 border-l-2 border-slate-200">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-electric-blue to-deep-blue border-2 border-border-brutal flex items-center justify-center shadow-[2px_2px_0_var(--color-border-brutal)]">
              <Sparkles className="w-4 h-4 text-accent-yellow" />
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-bold text-deep-blue text-display leading-tight">Founder</p>
              <p className="text-[10px] text-slate-400">Pro Plan</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
