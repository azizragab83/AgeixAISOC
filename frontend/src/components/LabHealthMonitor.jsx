import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Skull, Shield, Lock, Monitor, RefreshCw, CheckCircle2, XCircle } from 'lucide-react';
import { labApi } from '../api';
import { useLanguage } from '../context/LanguageContext';

const NODES = [
  { key: 'kali', name: 'Kali Linux', icon: Skull, accent: 'text-red-500' },
  { key: 'wazuh', name: 'Wazuh SIEM', icon: Shield, accent: 'text-cyan-400' },
  { key: 'fortigate', name: 'FortiGate FW', icon: Lock, accent: 'text-amber-400' },
  { key: 'win10', name: 'Win10 Victim', icon: Monitor, accent: 'text-blue-400' },
];

function NodeCard({ node, data }) {
  const online = data?.status === 'online';
  const services = data?.services || {};
  const serviceCount = Object.values(services).filter(Boolean).length;
  const Icon = node.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3 hover:border-cyan-500/30 transition-colors"
    >
      <div className="flex items-center gap-2.5">
        <div className={`p-2 rounded-lg bg-slate-100 dark:bg-slate-800/60 ${online ? '' : 'opacity-50'}`}>
          <Icon className={`w-4 h-4 ${node.accent}`} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-bold text-slate-800 dark:text-slate-100 truncate">{node.name}</div>
          <div className="text-[9px] font-mono text-slate-500 dark:text-slate-500 truncate">{data?.ip || '--'}</div>
        </div>
        <div className="relative flex items-center justify-center w-5 h-5">
          <span className={`absolute w-3 h-3 rounded-full ${online ? 'bg-green-400' : 'bg-red-500'}`} />
          {online && (
            <span className="absolute w-3 h-3 rounded-full bg-green-400 animate-ping opacity-60" />
          )}
        </div>
      </div>

      <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-1.5">
          {Object.keys(services).length === 0 ? (
            <span className="text-[9px] font-mono text-slate-500">NO SERVICES REPORTED</span>
          ) : (
            Object.entries(services).slice(0, 3).map(([svc, up]) => (
              <span key={svc} className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800/60 text-[8px] font-mono text-slate-600 dark:text-slate-400">
                {up ? <CheckCircle2 className="w-2.5 h-2.5 text-green-400" /> : <XCircle className="w-2.5 h-2.5 text-red-500" />}
                {svc}
              </span>
            ))
          )}
        </div>
        <span className={`text-[9px] font-mono font-bold ${online ? 'text-green-400' : 'text-red-500'}`}>
          {online ? 'ONLINE' : 'OFFLINE'}
        </span>
      </div>
    </motion.div>
  );
}

function NodeCardSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3">
      <div className="flex items-center gap-2.5">
        <div className="skeleton w-8 h-8 rounded-lg" />
        <div className="flex-1 space-y-1.5">
          <div className="skeleton h-3 w-24" />
          <div className="skeleton h-2 w-16" />
        </div>
      </div>
      <div className="skeleton h-5 w-full mt-2.5" />
    </div>
  );
}

export default function LabHealthMonitor() {
  const { t } = useLanguage();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await labApi.getStatus();
      setStatus(res.data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 shrink-0">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-200">{t('lab_health')}</span>
        <div className="flex-1" />
        <button
          onClick={fetchStatus}
          className="p-1 rounded text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
          title="Refresh lab status"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-2 p-2">
        {loading && !status ? (
          NODES.map(n => <NodeCardSkeleton key={n.key} />)
        ) : (
          NODES.map(node => (
            <NodeCard key={node.key} node={node} data={status?.[node.key]} />
          ))
        )}
      </div>
    </div>
  );
}
