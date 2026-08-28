import { useState, useEffect } from 'react';
import { Clock, CheckCircle2, XCircle, Eye, User, Filter, Loader2 } from 'lucide-react';
import { getAlertsHistory } from '../api';
import DataSourceBadge from '../components/DataSourceBadge';

export default function AuditView() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const res = await getAlertsHistory(50);
        setHistory(res.data.alerts || []);
      } catch {
        setHistory([]);
      } finally {
        setLoading(false);
      }
    };
    fetch();
    const interval = setInterval(fetch, 30000);
    return () => clearInterval(interval);
  }, []);

  const decisions = history.filter((a) => a.status !== 'pending');
  const filtered = filter === 'all' ? decisions : decisions.filter((a) => a.status === filter);

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-y-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-white">Audit Trail</h1>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <select value={filter} onChange={(e) => setFilter(e.target.value)} className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-300">
            <option value="all">All Decisions</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="soc-card"><Eye className="w-4 h-4 text-cyan-400 mb-1" /><div className="text-xs text-slate-500">Total Decisions</div><div className="text-2xl font-bold text-white">{decisions.length}</div></div>
        <div className="soc-card"><CheckCircle2 className="w-4 h-4 text-green-400 mb-1" /><div className="text-xs text-slate-500">Approved</div><div className="text-2xl font-bold text-green-400">{decisions.filter((a) => a.status === 'approved').length}</div></div>
        <div className="soc-card"><XCircle className="w-4 h-4 text-red-400 mb-1" /><div className="text-xs text-slate-500">Rejected</div><div className="text-2xl font-bold text-red-400">{decisions.filter((a) => a.status === 'rejected').length}</div></div>
      </div>

      <div className="flex items-center gap-2">
        <DataSourceBadge label="🟢 Live — real HITL decisions" />
        <DataSourceBadge label="🔵 AI-Assisted Detection Validation — not automated pentesting" />
      </div>

      <div className="flex-1 bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
        <div className="grid grid-cols-6 gap-2 p-3 border-b border-slate-800 text-xs font-bold text-slate-500 uppercase sticky-table-header">
          <span>Timestamp</span><span>Alert ID</span><span>Threat Type</span><span>Risk</span><span>Decision</span><span>Analyst</span>
        </div>
        <div className="overflow-y-auto max-h-[500px]">
          {loading ? (
            <div className="flex items-center justify-center h-32 text-slate-500 gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading audit trail...
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-slate-500">No audit records found</div>
          ) : (
            filtered.map((a, i) => (
              <div key={a.decision_id || a.alert_id || i} className="grid grid-cols-6 gap-2 p-3 border-b border-slate-800/50 text-sm table-row-hover">
                <span className="text-slate-400 text-xs">{a.timestamp || a.executed_at ? new Date(a.timestamp || a.executed_at).toLocaleString() : '--'}</span>
                <span className="font-mono text-xs text-cyan-400">{(a.alert_id || a.decision_id || '').slice(0, 12) || '--'}</span>
                <span className="text-slate-300">{a.threat_type || a.threat_analysis?.threat_type || 'Alert'}</span>
                <span className={`text-xs font-bold ${a.risk_level === 'critical' ? 'text-red-400' : a.risk_level === 'high' ? 'text-orange-400' : 'text-slate-400'}`}>{a.risk_level || '--'}</span>
                <span className={`flex items-center gap-1 text-xs ${a.status === 'approved' ? 'text-green-400' : a.status === 'rejected' ? 'text-red-400' : 'text-slate-400'}`}>
                  {a.status === 'approved' ? <CheckCircle2 className="w-3 h-3" /> : a.status === 'rejected' ? <XCircle className="w-3 h-3" /> : null}
                  {a.status || 'pending'}
                </span>
                <span className="text-slate-500 flex items-center gap-1"><User className="w-3 h-3" />{a.human_decision || 'analyst'}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}