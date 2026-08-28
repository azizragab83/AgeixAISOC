import { useState, useEffect, useCallback } from 'react';
import { Wifi, WifiOff, Cpu, Shield, Zap, Network, RefreshCw, Loader2 } from 'lucide-react';
import { dataApi } from '../api';
import DataSourceBadge from './DataSourceBadge';

const TOOLS = [
  { key: 'wazuh', label: 'Wazuh SIEM', icon: Shield, color: 'text-orange-400', sub: 'SIEM / Detection' },
  { key: 'fortigate', label: 'FortiGate', icon: Network, color: 'text-amber-400', sub: 'Firewall' },
  { key: 'n8n', label: 'n8n', icon: Zap, color: 'text-red-400', sub: 'SOAR Automation' },
  { key: 'ollama', label: 'Ollama', icon: Cpu, color: 'text-purple-400', sub: 'LLM Runtime' },
];

export default function ConnectedToolsStatus() {
  const [toolsHealth, setToolsHealth] = useState({});
  const [loading, setLoading] = useState(true);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    try {
      const res = await dataApi.getToolsHealth();
      setToolsHealth(res.data?.tools || {});
    } catch {
      // Fallback: all offline
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  return (
    <div className="bg-white dark:bg-gray-800/50 rounded-lg border border-slate-200 dark:border-slate-700/50 p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Network className="w-3.5 h-3.5 text-cyan-500 dark:text-cyan-400" />
          <span className="text-xs font-bold text-slate-900 dark:text-white">Connected Tools</span>
          <DataSourceBadge label="🟢 Live — real health checks" />
        </div>
        <button onClick={fetchHealth} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400">
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
        </button>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {TOOLS.map((tool) => {
          const health = toolsHealth[tool.key] || {};
          const online = health.status === 'online';
          return (
            <div key={tool.key} className="rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 p-2 text-center">
              <tool.icon className={`w-4 h-4 mx-auto mb-1 ${tool.color}`} />
              <div className="text-[10px] font-semibold text-slate-900 dark:text-white">{tool.label}</div>
              <div className="text-[9px] text-slate-500 dark:text-slate-400 mb-1">{tool.sub}</div>
              <div className={`flex items-center justify-center gap-1 text-[9px] font-medium ${online ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'}`}>
                {online ? <Wifi className="w-2.5 h-2.5" /> : <WifiOff className="w-2.5 h-2.5" />}
                {online ? `${health.latency_ms || 0}ms` : 'Offline'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}