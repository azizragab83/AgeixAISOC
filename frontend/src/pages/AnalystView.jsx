import { useState } from 'react';
import { Search, Filter, AlertTriangle, Clock, Shield, Activity, ArrowUpRight } from 'lucide-react';
import { useAlerts } from '../hooks/useAlerts';
import { useLabHealth } from '../hooks/useLabHealth';
import DataSourceBadge from '../components/DataSourceBadge';

export default function AnalystView({ ws }) {
  const { alerts, loading } = useAlerts(100);
  const { labStatus } = useLabHealth();
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');

  const filtered = alerts.filter((a) => {
    if (severityFilter !== 'all' && a.risk_level !== severityFilter) return false;
    if (search && !a.summary?.toLowerCase().includes(search.toLowerCase()) && !a.source_ip?.includes(search)) return false;
    return true;
  });

  const severityColor = { critical: 'text-red-400 bg-red-500/10', high: 'text-orange-400 bg-orange-500/10', medium: 'text-amber-400 bg-amber-500/10', low: 'text-green-400 bg-green-500/10' };

  // AD attack technique IDs for labeling
  const AD_TECHNIQUES = ['T1558', 'T1550.002', 'T1003.006'];

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-y-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-white">SOC Analyst View</h1>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-3 py-1.5">
            <Search className="w-4 h-4 text-slate-500" />
            <input className="bg-transparent text-sm text-slate-300 outline-none w-48" placeholder="Search IP or alert..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-300">
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <div className="soc-card"><div className="text-xs text-slate-500">Total Alerts</div><div className="text-2xl font-bold text-white">{alerts.length}</div></div>
        <div className="soc-card"><div className="text-xs text-slate-500">Critical</div><div className="text-2xl font-bold text-red-400">{alerts.filter((a) => a.risk_level === 'critical').length}</div></div>
        <div className="soc-card"><div className="text-xs text-slate-500">Devices Online</div><div className="text-2xl font-bold text-green-400">{Object.values(labStatus).filter((v) => typeof v === 'object' && v.status === 'online').length}/6</div></div>
        <div className="soc-card"><div className="text-xs text-slate-500">Pending Review</div><div className="text-2xl font-bold text-amber-400">{alerts.filter((a) => a.status === 'pending').length}</div></div>
      </div>

      <div className="flex-1 bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
        <div className="p-3 border-b border-slate-800 flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-medium text-white">Alert Feed</span>
          <DataSourceBadge label="🟢 Live — real pipeline alerts" className="ml-1" />
        </div>
        <div className="overflow-y-auto max-h-[500px]">
          {loading ? (
            <div className="flex items-center justify-center h-32 text-slate-500">Loading alerts...</div>
          ) : filtered.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-slate-500">No alerts match your filters</div>
          ) : (
            filtered.map((alert, i) => {
              const isAD = AD_TECHNIQUES.includes(alert.mitre_id);
              return (
                <div key={alert.alert_id || i} className="flex items-start gap-3 p-3 border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                  <div className={`mt-0.5 p-1.5 rounded ${severityColor[alert.risk_level] || 'text-slate-400 bg-slate-500/10'}`}><AlertTriangle className="w-4 h-4" /></div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-medium text-white truncate">{alert.threat_type || 'Alert'}</span>
                      <span className="text-xs font-mono text-slate-500">{alert.mitre_id}</span>
                      <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${severityColor[alert.risk_level] || ''}`}>{alert.risk_level?.toUpperCase()}</span>
                      {isAD && <DataSourceBadge label="🔵 AD Detection Logic — Rule-Based" />}
                    </div>
                    <p className="text-xs text-slate-400 truncate">{alert.summary || 'No summary'}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-slate-600">
                      <span>{alert.source_ip || 'N/A'}</span>
                      <span>{alert.timestamp ? new Date(alert.timestamp).toLocaleString() : ''}</span>
                    </div>
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-slate-600 shrink-0" />
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}