import { useState, useEffect, useRef } from 'react';
import { AreaChart, Area } from 'recharts';
import { Siren, ShieldCheck, Fingerprint, BrainCircuit, TrendingUp, TrendingDown } from 'lucide-react';
import { motion } from 'framer-motion';
import { useLanguage } from '../context/LanguageContext';

const HISTORY_MAX = 40;

function KPIWidget({ icon: Icon, label, value, suffix, history, color, accent }) {
  const { t } = useLanguage();
  const prev = history.length > 1 ? history[history.length - 2] : null;
  const delta = prev !== null && prev !== undefined ? value - prev : null;
  const displayValue = value === null || value === undefined ? 'N/A' : value;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3.5 transition-colors duration-300"
    >
      <div className="flex items-center gap-2 mb-2">
        <div className={`p-1.5 rounded-lg ${accent}`}>
          <Icon className={`w-4 h-4 ${color}`} />
        </div>
        <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
          {label}
        </span>
        {delta !== null && delta !== 0 && (
          <span className={`ml-auto flex items-center gap-0.5 text-[9px] font-mono font-bold ${delta > 0 ? 'text-red-500' : 'text-green-400'}`}>
            {delta > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {Math.abs(delta)}
          </span>
        )}
      </div>
      <div className="flex items-end justify-between gap-2">
        <div>
          <span className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-white">{displayValue}</span>
          {suffix && value !== null && value !== undefined && <span className="text-xs font-mono text-slate-500 dark:text-slate-400 ml-1">{suffix}</span>}
        </div>
        <div className="w-20 h-8">
          {history.length > 1 && (
            <AreaChart width={80} height={32} data={history.map((v, i) => ({ i, v }))} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
              <Area type="monotone" dataKey="v" stroke={color.replace('text-', '#')} strokeWidth={1.5} fill={color.replace('text-', '#')} fillOpacity={0.15} isAnimationActive={false} />
            </AreaChart>
          )}
        </div>
      </div>
      <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-cyan-400/20 to-transparent" />
    </motion.div>
  );
}

function KPIWidgetSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3.5">
      <div className="flex items-center gap-2 mb-3">
        <div className="skeleton w-7 h-7 rounded-lg" />
        <div className="skeleton h-2.5 w-24" />
      </div>
      <div className="flex items-end justify-between">
        <div className="skeleton h-7 w-16" />
        <div className="skeleton h-8 w-20 rounded" />
      </div>
    </div>
  );
}

export default function KPIWidgets({ metrics = null }) {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const historyRef = useRef({ active: [], blocked: [], hitl: [], agents: [] });

  // Track metric history for sparklines whenever the parent passes new metrics
  useEffect(() => {
    if (!metrics) return;
    const h = historyRef.current;
    h.active.push(metrics.active_alerts ?? null);
    h.blocked.push(metrics.threats_blocked ?? null);
    h.hitl.push(metrics.pending_decisions ?? null);
    h.agents.push(metrics.agents_active ?? null);
    Object.values(h).forEach(arr => { if (arr.length > HISTORY_MAX) arr.shift(); });
    setLoading(false);
  }, [metrics]);

  if (loading && !metrics) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        {[0, 1, 2, 3].map(i => <KPIWidgetSkeleton key={i} />)}
      </div>
    );
  }

  const { active: activeHist, blocked: blockedHist, hitl: hitlHist, agents: agentsHist } = historyRef.current;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
      <KPIWidget
        icon={Siren}
        label={t('kpi_active_threats')}
        value={metrics?.active_alerts ?? null}
        color="text-red-500"
        accent="bg-red-500/10 border border-red-500/20"
        history={activeHist}
      />
      <KPIWidget
        icon={ShieldCheck}
        label={t('kpi_threats_blocked')}
        value={metrics?.threats_blocked ?? null}
        suffix="24h"
        color="text-green-400"
        accent="bg-green-500/10 border border-green-500/20"
        history={blockedHist}
      />
      <KPIWidget
        icon={Fingerprint}
        label={t('kpi_pending_hitl')}
        value={metrics?.pending_decisions ?? null}
        color="text-yellow-400"
        accent="bg-yellow-500/10 border border-yellow-500/20"
        history={hitlHist}
      />
      <KPIWidget
        icon={BrainCircuit}
        label={t('kpi_agents_active')}
        value={metrics?.agents_active ?? null}
        color="text-cyan-400"
        accent="bg-cyan-500/10 border border-cyan-500/20"
        history={agentsHist}
      />
    </div>
  );
}