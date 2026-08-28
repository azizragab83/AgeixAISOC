import { useState, useEffect } from 'react';
import { Shield, TrendingUp, Clock, AlertTriangle, CheckCircle2, XCircle, Server, Zap } from 'lucide-react';
import { useAlerts } from '../hooks/useAlerts';
import { useLabHealth } from '../hooks/useLabHealth';
import { dashboardApi, getAlertsHistory } from '../api';
import DataSourceBadge from '../components/DataSourceBadge';

function KPIBox({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3.5 transition-colors duration-300">
      <div className="flex items-center gap-2 mb-2">
        <div className={`p-1.5 rounded-lg ${color || 'bg-slate-100 dark:bg-slate-800'}`}><Icon className={`w-4 h-4 ${color ? '' : 'text-slate-400'}`} /></div>
        <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">{label}</span>
      </div>
      <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-white mb-0.5">{value}</div>
      {sub && <div className="text-[10px] text-slate-500 dark:text-slate-500">{sub}</div>}
    </div>
  );
}

function calculateMTTD(history) {
  const resolved = history.filter(a => a.status === 'approved' || a.status === 'rejected');
  if (resolved.length === 0) return null;

  const diffs = resolved.map(a => {
    const alertTime = a.timestamp || a.executed_at || a.alert_id;
    const decisionTime = a.human_decision_timestamp || a.executed_at;
    if (!alertTime || !decisionTime) return null;
    const diffMs = new Date(decisionTime) - new Date(alertTime);
    return diffMs > 0 ? diffMs : null;
  }).filter(Boolean);

  if (diffs.length === 0) return null;
  const avgMs = diffs.reduce((s, d) => s + d, 0) / diffs.length;
  const minutes = Math.round(avgMs / 60000);
  return minutes < 60 ? `${minutes} min` : `${Math.round(minutes / 60)}h ${minutes % 60}m`;
}

export default function ExecutiveView() {
  const { alerts } = useAlerts();
  const { labStatus } = useLabHealth();
  const [kpis, setKpis] = useState({ mttd: '', mttr: '', containment_rate: '', mitre_coverage: '', false_positive_rate: '', alerts_today: 0 });
  const [metrics, setMetrics] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await dashboardApi.getKPIs();
        setKpis(res.data);
      } catch {}
    };
    fetch();
    const interval = setInterval(fetch, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await dashboardApi.getMetrics();
        setMetrics(res.data);
      } catch {}
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await getAlertsHistory(100);
        setHistory(res.data.alerts || []);
      } catch {}
    };
    fetchHistory();
    const interval = setInterval(fetchHistory, 30000);
    return () => clearInterval(interval);
  }, []);

  const mttd = calculateMTTD(history) || kpis.mttd || 'Calculating...';
  const mttr = kpis.mttr || 'Calculating...';
  const activeAlerts = metrics?.active_alerts ?? null;
  const pendingDecisions = metrics?.pending_decisions ?? null;
  const critical = alerts.filter((a) => a.risk_level === 'critical').length;
  const high = alerts.filter((a) => a.risk_level === 'high').length;
  const online = Object.values(labStatus).filter((v) => typeof v === 'object' && v.status === 'online').length;

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-y-auto">
      <h1 className="text-lg font-bold text-white">Executive Dashboard — C-Suite KPIs</h1>

      <div className="grid grid-cols-4 gap-4">
        <div>
          <KPIBox icon={Clock} label="MTTD" value={mttd} sub={`Mean Time To Detect · ${kpis.mttd_samples || 0} samples`} color="bg-cyan-600/20" />
          {kpis.mttd_mttr_label && <div className="mt-1"><DataSourceBadge label={kpis.mttd_mttr_label} /></div>}
        </div>
        <div>
          <KPIBox icon={Zap} label="MTTR" value={mttr} sub={`Mean Time To Respond · ${kpis.mttr_samples || 0} samples`} color="bg-purple-600/20" />
          {kpis.mttd_mttr_label && <div className="mt-1"><DataSourceBadge label={kpis.mttd_mttr_label} /></div>}
        </div>
        <KPIBox icon={AlertTriangle} label="Active Threats" value={activeAlerts ?? 'Calculating...'} sub={`${critical} critical, ${high} high`} color="bg-red-600/20" />
        <KPIBox icon={CheckCircle2} label="Pending Decisions" value={pendingDecisions ?? 'Calculating...'} sub="Awaiting HITL review" color="bg-yellow-600/20" />
        <KPIBox icon={TrendingUp} label="Alerts Today" value={kpis.alerts_today || alerts.length} sub="All severities" color="bg-blue-600/20" />
        <KPIBox icon={Server} label="Infra Health" value={`${online}/6`} sub="Devices online" color="bg-green-600/20" />
        <KPIBox icon={Shield} label="MITRE Coverage" value={kpis.mitre_coverage} sub="Techniques monitored" color="bg-amber-600/20" />
        <KPIBox icon={XCircle} label="False Positive Rate" value={kpis.false_positive_rate} sub="Target: < 10%" color="bg-green-600/20" />
      </div>

      <div className="grid grid-cols-2 gap-4 flex-1">
        <div className="soc-card">
          <h3 className="text-sm font-bold text-white mb-3">Alert Distribution</h3>
          <div className="space-y-2">
            {['critical', 'high', 'medium', 'low'].map((level) => {
              const count = alerts.filter((a) => a.risk_level === level).length;
              const max = Math.max(alerts.length, 1);
              const pct = (count / max) * 100;
              const colors = { critical: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-amber-500', low: 'bg-green-500' };
              return (
                <div key={level} className="flex items-center gap-3">
                  <span className="text-xs font-medium w-16 text-slate-400 uppercase">{level}</span>
                  <div className="flex-1 h-3 bg-slate-800 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${colors[level]} transition-all`} style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs font-mono text-slate-400 w-8 text-right">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
        <div className="soc-card">
          <h3 className="text-sm font-bold text-white mb-3">System Status</h3>
          <div className="space-y-2">
            {Object.entries(labStatus).filter(([k]) => k !== 'timestamp').map(([name, data]) => {
              if (typeof data !== 'object') return null;
              const isOnline = data.status === 'online';
              return (
                <div key={name} className="flex items-center justify-between py-1.5 border-b border-slate-800/50 last:border-0">
                  <span className="text-sm text-slate-300 capitalize">{name.replace('_', ' ')}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs ${isOnline ? 'text-green-400' : 'text-red-400'}`}>{isOnline ? 'Online' : 'Offline'}</span>
                    <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'}`} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}