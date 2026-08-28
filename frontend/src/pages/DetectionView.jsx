import { useState, useEffect, useCallback } from 'react';
import { Shield, Plus, CheckCircle2, AlertTriangle, FileText, Target, RefreshCw, Loader2, Sparkles, Trash2, Eye } from 'lucide-react';
import { rulesApi, api, getPendingReviewRules, reviewRule, deleteRule } from '../api';

export default function DetectionView() {
  const [deploying, setDeploying] = useState(null);
  const [results, setResults] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [stats, setStats] = useState({ active_rules: 0, coverage_pct: 0, gaps: 0, pending_approval: 0 });
  const [pendingRules, setPendingRules] = useState([]);
  const [reviewBusy, setReviewBusy] = useState(null);
  const [ruleDraft, setRuleDraft] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [ragStats, setRagStats] = useState(null);

  const fetchPendingRules = useCallback(async () => {
    try {
      const res = await getPendingReviewRules();
      setPendingRules(res.data.rules || []);
    } catch {}
  }, []);

  const fetchData = async () => {
    try {
      const res = await rulesApi.getRules();
      setTemplates(res.data.templates);
      setStats(res.data.stats);
    } catch {}
    try {
      const ragRes = await api.get('/api/rag/stats');
      setRagStats(ragRes.data);
    } catch {}
    fetchPendingRules();
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await fetchData();
      setLoading(false);
    };
    init();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRefreshRules = async () => {
    setRefreshing(true);
    try {
      const res = await api.get('/api/alerts', { params: { filter: 'detection', limit: 20 } });
      if (res.data.alerts?.length > 0) {
        setResults(prev => [
          ...res.data.alerts.map(a => ({
            title: a.threat_type || a.alert_id,
            status: a.status,
            rule_id: a.alert_id?.slice(0, 8) || '--',
          })),
          ...prev,
        ].slice(0, 20));
      }
    } catch {}
    await fetchData();
    setRefreshing(false);
  };

  const handleDeploy = async (tmpl) => {
    setDeploying(tmpl.title);
    try {
      const res = await rulesApi.deploy({ rule_name: tmpl.title });
      setResults((prev) => [{ title: tmpl.title, status: res.data.status, rule_id: res.data.rule_id }, ...prev]);
      fetchPendingRules();
    } catch {
      setResults((prev) => [{ title: tmpl.title, status: 'error', rule_id: '--' }, ...prev]);
    } finally {
      setDeploying(null);
    }
  };

  const handleReview = async (ruleId, action) => {
    setReviewBusy(ruleId);
    try {
      await reviewRule(ruleId, action);
      await fetchPendingRules();
    } catch {}
    setReviewBusy(null);
  };

  const handleDeleteRule = async (ruleId) => {
    setReviewBusy(ruleId);
    try {
      await deleteRule(ruleId);
      await fetchPendingRules();
    } catch {}
    setReviewBusy(null);
  };

  const pendingCount = results.filter((r) => r.status === 'pending_approval').length;

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-y-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-white">Detection Coverage — Sigma Rule Management</h1>
        <button
          onClick={handleRefreshRules}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 text-xs font-medium hover:bg-slate-700 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing...' : 'Refresh Rules'}
        </button>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <div className="soc-card"><Shield className="w-4 h-4 text-green-400 mb-1" /><div className="text-xs text-slate-500">Active Rules</div><div className="text-2xl font-bold text-white">{stats.active_rules}</div></div>
        <div className="soc-card"><Target className="w-4 h-4 text-cyan-400 mb-1" /><div className="text-xs text-slate-500">Coverage</div><div className="text-2xl font-bold text-white">{stats.coverage_pct}%</div></div>
        <div className="soc-card"><AlertTriangle className="w-4 h-4 text-amber-400 mb-1" /><div className="text-xs text-slate-500">Gaps Found</div><div className="text-2xl font-bold text-white">{stats.gaps}</div></div>
        <div className="soc-card"><FileText className="w-4 h-4 text-purple-400 mb-1" /><div className="text-xs text-slate-500">Pending Approval</div><div className="text-2xl font-bold text-white">{pendingCount + (results.length > 0 ? 0 : stats.pending_approval)}</div></div>
      </div>

      {ragStats && (
        <div className="bg-slate-800/30 rounded-lg px-4 py-2 text-xs text-slate-400 flex items-center gap-4">
          <span>RAG KB: <span className="text-cyan-400 font-mono">{ragStats.total_documents || 0}</span> docs</span>
          <span>Provider: <span className="text-slate-300">{ragStats.provider || 'N/A'}</span></span>
          <span>Chroma: <span className={ragStats.chroma_ready ? 'text-green-400' : 'text-red-400'}>{ragStats.chroma_ready ? 'Ready' : 'Offline'}</span></span>
        </div>
      )}

      {pendingRules.length > 0 && (
        <>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider mt-2 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-violet-400" /> AI-Generated Rules Awaiting Review ({pendingRules.length})
          </h2>
          <div className="space-y-2">
            {pendingRules.map((r) => (
              <div key={r.rule_id} className="bg-slate-800/50 rounded-lg px-4 py-3 border border-violet-500/20">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm text-slate-200 font-semibold">{r.title}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-violet-500/10 border border-violet-500/30 text-violet-400">AI-GENERATED</span>
                      <span className="text-[10px] font-mono text-slate-500">rule {r.rule_id}</span>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap mt-1">
                      {(r.mitre_ids || []).map((m) => (
                        <span key={m} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">{m}</span>
                      ))}
                      <span className="text-[10px] font-mono text-slate-500">{r.level?.toUpperCase()}</span>
                      <span className="text-[10px] font-mono text-slate-500">Source: {r.source}</span>
                    </div>
                    {r.description && <p className="text-xs text-slate-500 mt-1 line-clamp-2">{r.description}</p>}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => setRuleDraft(r.content || null)}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-700/60 border border-slate-600 text-slate-300 text-xs hover:bg-slate-700 transition-all"
                      title="Preview rule XML"
                    >
                      <Eye className="w-3.5 h-3.5" /> Preview
                    </button>
                    <button
                      onClick={() => handleReview(r.rule_id, 'approve')}
                      disabled={reviewBusy === r.rule_id}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-green-600/15 border border-green-500/40 text-green-400 text-xs font-bold hover:bg-green-600/25 transition-all disabled:opacity-40"
                    >
                      {reviewBusy === r.rule_id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} Approve &amp; Deploy
                    </button>
                    <button
                      onClick={() => handleDeleteRule(r.rule_id)}
                      disabled={reviewBusy === r.rule_id}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-red-600/15 border border-red-500/40 text-red-400 text-xs font-bold hover:bg-red-600/25 transition-all disabled:opacity-40"
                      title="Remove this generated rule"
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Remove
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {ruleDraft && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6" onClick={() => setRuleDraft(null)}>
          <div className="w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-xl p-4 max-h-[70vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono font-bold text-violet-400">Rule XML Preview</span>
              <button onClick={() => setRuleDraft(null)} className="text-slate-500 hover:text-slate-300 text-sm">✕</button>
            </div>
            <pre className="text-[10px] font-mono text-slate-300 whitespace-pre-wrap bg-slate-950 rounded-lg p-3">{ruleDraft}</pre>
          </div>
        </div>
      )}

      <h2 className="text-sm font-bold text-white uppercase tracking-wider mt-2">Sigma Rule Templates</h2>
      <div className="grid grid-cols-2 gap-3">
        {loading ? (
          <div className="col-span-2 flex items-center justify-center h-32 text-slate-500 gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading templates...
          </div>
        ) : templates.length === 0 ? (
          <div className="col-span-2 flex items-center justify-center h-32 text-slate-500 font-mono text-xs">
            No Sigma templates available from backend
          </div>
        ) : (
          templates.map((tmpl) => (
            <div key={tmpl.title} className="soc-card">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-sm font-semibold text-white">{tmpl.title}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs font-mono text-cyan-400">{(tmpl.mitre || []).join(', ')}</span>
                    <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${tmpl.level === 'critical' ? 'text-red-400 bg-red-500/10' : tmpl.level === 'high' ? 'text-orange-400 bg-orange-500/10' : 'text-amber-400 bg-amber-500/10'}`}>{tmpl.level.toUpperCase()}</span>
                  </div>
                </div>
                <button
                  onClick={() => handleDeploy(tmpl)}
                  disabled={deploying === tmpl.title}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600/20 border border-cyan-500/30 text-cyan-400 text-xs font-medium hover:bg-cyan-600/30 transition-all disabled:opacity-50"
                >
                  <Plus className="w-3.5 h-3.5" />
                  {deploying === tmpl.title ? 'Deploying...' : 'Deploy'}
                </button>
              </div>
              <div className="text-xs text-slate-500">Logsource: {tmpl.logsource?.category}/{tmpl.logsource?.product}</div>
            </div>
          ))
        )}
      </div>

      {results.length > 0 && (
        <>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider mt-2">Deployment Results</h2>
          <div className="space-y-2">
            {results.map((r, i) => (
              <div key={i} className="flex items-center gap-3 bg-slate-800/50 rounded-lg px-4 py-2">
                {r.status === 'pending_approval' ? <CheckCircle2 className="w-4 h-4 text-green-400" /> : <AlertTriangle className="w-4 h-4 text-red-400" />}
                <span className="text-sm text-slate-300 flex-1">{r.title}</span>
                <span className="text-xs text-green-400 capitalize">{r.status}</span>
                <span className="text-xs font-mono text-slate-500">{r.rule_id}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}