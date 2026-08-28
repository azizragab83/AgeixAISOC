import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Radio, TrendingUp, Search, Globe2, Wrench,
  ShieldCheck, BrainCircuit, Terminal, ScrollText, ChevronsLeft, ChevronsRight, Sparkles,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useLanguage } from '../context/LanguageContext';
import { getPendingReviewRules } from '../api';

const NAV_SECTIONS = [
  {
    key: 'nav_command_center',
    items: [
      { path: '/', labelKey: 'dashboard', icon: LayoutDashboard },
      { path: '/analyst', labelKey: 'nav_analyst_feed', icon: Radio },
      { path: '/executive', labelKey: 'nav_executive', icon: TrendingUp },
      { path: '/forensics', labelKey: 'nav_forensics', icon: Search },
    ],
  },
  {
    key: 'nav_threat_intel',
    items: [
      { path: '/threat-intel', labelKey: 'nav_threat_intel', icon: Globe2 },
      { path: '/toolkit', labelKey: 'nav_toolkit', icon: Wrench },
    ],
  },
  {
    key: 'nav_detection_eng',
    items: [
      { path: '/detection', labelKey: 'detection_engineering', icon: ShieldCheck },
    ],
  },
  {
    key: 'nav_ai_hub',
    items: [
      { path: '/ai-engineering', labelKey: 'ai_engineering', icon: BrainCircuit },
      { path: '/devops', labelKey: 'devops_resources', icon: Terminal },
    ],
  },
  {
    key: 'nav_audit_trail',
    items: [
      { path: '/audit', labelKey: 'audit_trail', icon: ScrollText },
    ],
  },
];

function NavButton({ item, collapsed }) {
  const location = useLocation();
  const { t, dir } = useLanguage();
  const isActive = location.pathname === item.path;
  const Icon = item.icon;

  return (
    <div className={`relative group ${collapsed ? 'flex justify-center' : ''}`}>
      <NavLink
        to={item.path}
        className={`relative flex items-center gap-3 rounded-lg text-xs font-medium transition-all ${
          collapsed ? 'w-10 h-10 justify-center' : 'w-full px-3 py-2'
        } ${
          isActive
            ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
            : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60'
        }`}
      >
        {isActive && (
          <motion.span
            layoutId="sidebar-active"
            className={`absolute inset-0 rounded-lg bg-cyan-500/5 border border-cyan-500/20`}
            transition={{ type: 'spring', stiffness: 500, damping: 40 }}
          />
        )}
        <span className={`relative z-10 shrink-0 ${isActive ? 'text-cyan-400' : ''}`}>
          <Icon className="w-4 h-4" />
        </span>
        {!collapsed && <span className="relative z-10 truncate">{t(item.labelKey)}</span>}
      </NavLink>

      {collapsed && (
        <div className="pointer-events-none absolute left-full top-1/2 -translate-y-1/2 ml-3 z-50 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-[10px] font-mono font-bold text-slate-200 shadow-xl">
          {t(item.labelKey)}
        </div>
      )}
    </div>
  );
}

export default function Sidebar({ collapsed, onToggleCollapse }) {
  const { t, dir } = useLanguage();
  const navigate = useNavigate();
  const isRTL = dir === 'rtl';
  const [pendingRules, setPendingRules] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await getPendingReviewRules();
        if (!cancelled) setPendingRules((res.data.rules || []).length);
      } catch {}
    };
    poll();
    const interval = setInterval(poll, 15000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  return (
    <nav
      className={`shrink-0 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950/95 ${isRTL ? 'border-l' : 'border-r'} flex flex-col transition-[width] duration-200 ${collapsed ? 'w-16' : 'w-56'}`}
      style={{ direction: isRTL ? 'rtl' : 'ltr' }}
    >
      <div className="flex-1 py-3 px-2 space-y-4 overflow-y-auto">
        {NAV_SECTIONS.map(section => (
          <div key={section.key}>
            {!collapsed && (
              <div className={`px-3 pb-1.5 text-[9px] font-mono font-bold uppercase tracking-widest text-slate-400 dark:text-slate-600 ${isRTL ? 'text-right' : ''}`}>
                {t(section.key)}
              </div>
            )}
            <div className="space-y-1">
              {section.items.map(item => (
                <NavButton key={item.path} item={item} collapsed={collapsed} />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="p-2 space-y-1 border-t border-slate-200 dark:border-slate-800">
        {pendingRules > 0 && (
          <button
            onClick={() => navigate('/detection')}
            className={`relative flex items-center gap-3 rounded-lg text-xs font-medium transition-all ${
              collapsed ? 'w-10 h-10 justify-center mx-auto' : 'w-full px-3 py-2'
            } bg-violet-500/10 text-violet-400 border border-violet-500/30 hover:bg-violet-500/20`}
            title={`${pendingRules} AI-generated rule${pendingRules === 1 ? '' : 's'} awaiting review`}
          >
            <Sparkles className="w-4 h-4" />
            {!collapsed && (
              <>
                <span className="flex-1 truncate text-left">Review New Rules</span>
                <span className="min-w-[18px] h-[18px] px-1 rounded-full bg-violet-500 text-white text-[9px] font-bold flex items-center justify-center">
                  {pendingRules}
                </span>
              </>
            )}
          </button>
        )}
      </div>
      <div className="p-2 border-t border-slate-200 dark:border-slate-800">
        {collapsed ? (
          <button
            onClick={onToggleCollapse}
            className="w-10 h-10 flex items-center justify-center rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
            title="Expand sidebar"
          >
            {isRTL ? <ChevronsLeft className="w-4 h-4 rotate-180" /> : <ChevronsRight className="w-4 h-4" />}
          </button>
        ) : (
          <div className="flex items-center justify-between px-2">
            <div className="text-[9px] font-mono text-slate-400 dark:text-slate-600">AgeixAISOC v2.1</div>
            <button
              onClick={onToggleCollapse}
              className="w-7 h-7 flex items-center justify-center rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
              title="Collapse sidebar"
            >
              {isRTL ? <ChevronsRight className="w-4 h-4 rotate-180" /> : <ChevronsLeft className="w-4 h-4" />}
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
