import { useState, useEffect, useCallback } from 'react';
import { Database, RefreshCw, Loader2, Filter, ShieldAlert, Server } from 'lucide-react';
import { dataApi } from '../api';
import DataSourceBadge from './DataSourceBadge';

function Section({ title, children, icon: Icon, color = 'text-cyan-500 dark:text-cyan-400' }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon className={`w-3 h-3 ${color}`} />
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">{title}</span>
      </div>
      {children}
    </div>
  );
}

export default function KnowledgeSourcesPanel() {
  const [sources, setSources] = useState([]);
  const [stats, setStats] = useState({ reduction: null, gap: null, intel: null, cmdb: null });
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [s, r, g, i, c] = await Promise.allSettled([
        dataApi.getKnowledgeSources(),
        dataApi.getAlertReduction(),
        dataApi.getGapClosure(),
        dataApi.getThreatIntelStatus(),
        dataApi.getCMDB(),
      ]);
      if (s.status === 'fulfilled') setSources(s.value.data?.sources || []);
      setStats({
        reduction: r.status === 'fulfilled' ? r.value.data : null,
        gap: g.status === 'fulfilled' ? g.value.data : null,
        intel: i.status === 'fulfilled' ? i.value.data : null,
        cmdb: c.status === 'fulfilled' ? c.value.data : null,
      });
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const assets = stats.cmdb?.assets ? Object.entries(stats.cmdb.assets) : [];

  return (
    <div className="bg-white dark:bg-gray-800/50 rounded-lg border border-slate-200 dark:border-slate-700/50 p-3">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-cyan-500 dark:text-cyan-400" />
          <span className="text-xs font-bold text-slate-900 dark:text-white">Knowledge Sources & AI Statistics</span>
        </div>
        <button onClick={fetchAll} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400">
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-3">
          <Section title="RAG Knowledge Bases" icon={Database}>
            <div className="space-y-1 max-h-44 overflow-y-auto pr-1">
              {sources.map((kb) => (
                <div key={kb.id} className="flex items-center justify-between gap-2 rounded bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 px-2 py-1">
                  <div className="min-w-0">
                    <div className="text-[10px] font-semibold text-slate-900 dark:text-white truncate">{kb.name}</div>
                    <div className="text-[9px] text-slate-500 dark:text-slate-400 truncate">{kb.description}</div>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">{kb.doc_count} docs</span>
                    <DataSourceBadge label={kb.label} />
                  </div>
                </div>
              ))}
            </div>
          </Section>

          <Section title="AI Pipeline Impact" icon={Filter}>
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 p-2">
                <div className="text-[9px] text-slate-500 dark:text-slate-400">Raw → HITL (noise filtered)</div>
                <div className="text-sm font-bold font-mono text-slate-900 dark:text-white">
                  {stats.reduction ? `${stats.reduction.reduction_pct}%` : '—'}
                </div>
                <div className="text-[9px] text-slate-500 dark:text-slate-400 font-mono">
                  {stats.reduction ? `${stats.reduction.raw_alerts_today} raw → ${stats.reduction.alerts_reached_hitl} HITL` : ''}
                </div>
                {stats.reduction?.label && <DataSourceBadge label={stats.reduction.label} className="mt-1" />}
              </div>
              <div className="rounded bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 p-2">
                <div className="text-[9px] text-slate-500 dark:text-slate-400">Detection gaps closed</div>
                <div className="text-sm font-bold font-mono text-slate-900 dark:text-white">
                  {stats.gap ? `${stats.gap.gaps_closed}/${stats.gap.gaps_detected}` : '—'}
                </div>
                <div className="text-[9px] text-slate-500 dark:text-slate-400 font-mono">
                  {stats.gap ? `${stats.gap.rules_on_disk} rules on disk` : ''}
                </div>
                {stats.gap?.label && <DataSourceBadge label={stats.gap.label} className="mt-1" />}
              </div>
            </div>
          </Section>

          <Section title="Live Threat Intel Feed" icon={ShieldAlert}>
            <div className="rounded bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 p-2 flex items-center justify-between">
              <div>
                <div className="text-[10px] font-semibold text-slate-900 dark:text-white">{stats.intel?.source || '—'}</div>
                <div className="text-[9px] text-slate-500 dark:text-slate-400 font-mono">
                  {stats.intel?.ingested_count != null ? `${stats.intel.ingested_count} C2 IPs ingested` : ''}
                  {stats.intel?.last_refresh ? ` · ${new Date(stats.intel.last_refresh).toLocaleTimeString()}` : ''}
                </div>
              </div>
              {stats.intel?.label && <DataSourceBadge label={stats.intel.label} />}
            </div>
          </Section>
        </div>

        <div className="space-y-3">
          <Section title="Asset Inventory (CMDB)" icon={Server}>
            <div className="max-h-44 overflow-y-auto pr-1">
              {assets.length === 0 && (
                <div className="text-[10px] text-slate-500 dark:text-slate-400">CMDB unavailable or empty</div>
              )}
              {assets.map(([ip, asset]) => (
                <div key={ip} className="flex items-center justify-between gap-2 rounded bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 px-2 py-1 mb-1">
                  <div className="min-w-0">
                    <div className="text-[10px] font-semibold text-slate-900 dark:text-white font-mono">{ip}</div>
                    <div className="text-[9px] text-slate-500 dark:text-slate-400 truncate">
                      {asset.hostname} · {asset.role} · {asset.os}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className={`text-[9px] font-bold uppercase ${asset.criticality === 'critical' ? 'text-red-500' : asset.criticality === 'high' ? 'text-orange-500' : 'text-slate-500'}`}>
                      {asset.criticality}
                    </span>
                    {stats.cmdb?.trust_level && <DataSourceBadge label={stats.cmdb.trust_level} />}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}
