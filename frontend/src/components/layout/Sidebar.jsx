import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Target,
  Users,
  Search,
  Send,
  BarChart3,
  Settings,
  Zap,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useState } from 'react';
import { prospects, researchDossiers, outreachDrafts, trackingData } from '../../data/mockData';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/icp', icon: Target, label: 'ICP Setup' },
  { to: '/prospects', icon: Users, label: 'Prospects', badge: prospects.length },
  { to: '/research', icon: Search, label: 'Research', badge: researchDossiers.length },
  { to: '/outreach', icon: Send, label: 'Outreach', badge: outreachDrafts.length },
  { to: '/tracking', icon: BarChart3, label: 'Tracking', badge: trackingData.length },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

function NavItem({ to, icon: Icon, label, badge, collapsed }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150 group
        ${isActive
          ? 'bg-electric-blue text-white shadow-[3px_3px_0_var(--color-border-brutal)] border-2 border-border-brutal'
          : 'text-slate-500 hover:text-deep-blue hover:bg-sky-blue/10 border-2 border-transparent'
        }
        ${collapsed ? 'justify-center' : ''}`
      }
    >
      <Icon className="w-5 h-5 shrink-0" strokeWidth={2.5} />
      {!collapsed && (
        <>
          <span className="text-display">{label}</span>
          {badge !== undefined && (
            <span className="ml-auto bg-accent-yellow text-deep-blue text-xs font-bold px-2 py-0.5 rounded-md border border-border-brutal">
              {badge}
            </span>
          )}
        </>
      )}
    </NavLink>
  );
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 260 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      className="h-screen sticky top-0 flex flex-col bg-white border-r-[3px] border-border-brutal z-40 overflow-hidden"
    >
      <div className={`flex items-center gap-3 px-4 py-5 border-b-2 border-border-brutal ${collapsed ? 'justify-center' : ''}`}>
        <div className="w-9 h-9 rounded-xl bg-electric-blue border-2 border-border-brutal flex items-center justify-center shadow-[2px_2px_0_var(--color-border-brutal)]">
          <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <h1 className="text-base font-bold text-display text-deep-blue leading-tight">SalesAI</h1>
            <p className="text-[10px] text-slate-400 font-medium uppercase tracking-widest">Pipeline</p>
          </div>
        )}
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto scrollbar-thin">
        {navItems.map((item) => (
          <NavItem key={item.to} {...item} collapsed={collapsed} />
        ))}
      </nav>

      <div className="px-3 py-3 border-t-2 border-border-brutal">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-slate-400 hover:text-deep-blue hover:bg-slate-100 transition-colors cursor-pointer"
        >
          {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
          {!collapsed && <span className="text-xs font-medium">Collapse</span>}
        </button>
      </div>
    </motion.aside>
  );
}
