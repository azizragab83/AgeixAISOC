import { useState, useEffect, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Fingerprint, RefreshCw, Inbox, Loader2, Radar } from 'lucide-react';
import { getAlertsFeed, decisionApi } from '../api';
import { useWebSocket } from '../hooks/useWebSocket';
import { useLanguage } from '../context/LanguageContext';
import PendingHITLCard from './PendingHITLCard';

function ProcessingCard({ item }) {
  const ts = item.timestamp ? new Date(item.timestamp).toLocaleTimeString('en-US', { hour12: false }) : '--:--:--';
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-3 overflow-hidden relative"
    >
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/10 to-transparent animate-pulse pointer-events-none" />
      <div className="flex items-start gap-3">
        <div className="relative w-11 h-11 shrink-0 flex items-center justify-center">
          <Radar className="w-6 h-6 text-cyan-400" />
          <span className="absolute inset-0 rounded-full border border-cyan-500/40 animate-ping" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold text-cyan-300 flex items-center gap-1.5">
              <Loader2 className="w-3 h-3 animate-spin" /> SOC Pipeline Analyzing…
            </span>
            <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-[9px] font-mono font-bold">
              6 AI AGENTS
            </span>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap mb-1.5">
            <span className="text-[9px] font-mono text-slate-500 truncate max-w-[200px]" title={item.alert_id}>{item.alert_id}</span>
            <span className="text-[9px] font-mono text-slate-500">{ts}</span>
          </div>
          <div className="flex gap-1.5">
            <div className="skeleton h-2 w-24 rounded" />
            <div className="skeleton h-2 w-16 rounded" />
            <div className="skeleton h-2 w-20 rounded" />
          </div>
          <p className="text-[9px] text-slate-500 mt-1.5 font-mono">
            Threat detection → risk scoring → recommendation → threat hunting → forensics → red team
          </p>
        </div>
      </div>
    </motion.div>
  );
}

export default function HITLQueue() {
  const { t } = useLanguage();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(null);
  const [processing, setProcessing] = useState([]);
  const { addHandler } = useWebSocket();

  const fetchPending = useCallback(async () => {
    try {
      const res = await getAlertsFeed(50);
      const pending = (res.data.alerts || []).filter(a => a.status === 'pending');
      setAlerts(prev => {
        const merged = new Map(prev.map(a => [a.decision_id || a.alert_id, a]));
        pending.forEach(a => merged.set(a.decision_id || a.alert_id, a));
        return Array.from(merged.values());
      });
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPending();
    const interval = setInterval(fetchPending, 10000);
    return () => clearInterval(interval);
  }, [fetchPending]);

  // Live: pipeline_started -> "Analyzing..." card appears instantly;
  // decision_package -> swap to the real card; decision_result/error -> remove
  useEffect(() => {
    return addHandler((data) => {
      if (data.type === 'pipeline_started') {
        const key = data.alert_id || '';
        if (!key) return;
        setProcessing(prev =>
          prev.some(p => p.alert_id === key)
            ? prev
            : [...prev, { alert_id: key, timestamp: data.timestamp || new Date().toISOString() }]
        );
      } else if (data.type === 'decision_package') {
        if (data.alert_id) setProcessing(prev => prev.filter(p => p.alert_id !== data.alert_id));
        fetchPending();
      } else if (data.type === 'pipeline_error' || data.type === 'pipeline_failed') {
        if (data.alert_id) setProcessing(prev => prev.filter(p => p.alert_id !== data.alert_id));
      } else if (data.type === 'decision_result' && data.decision_id) {
        // Grace period: let the card show its resolution status + toast before fading out
        setTimeout(() => {
          setAlerts(prev => prev.filter(a => (a.decision_id || a.alert_id) !== data.decision_id));
          setProcessing(prev => prev.filter(p => (p.alert_id || '') !== data.decision_id));
        }, 1600);
        fetchPending();
      } else if (data.type === 'metrics_update') {
        fetchPending();
      }
    });
  }, [addHandler, fetchPending]);

  const handleDecision = async (alert, action, addToRag = true) => {
    const decisionId = alert.decision_id || alert.alert_id;
    setSubmitting(decisionId);
    try {
      await decisionApi.submit(decisionId, action, { source: 'hitl_queue' }, addToRag);
      // Grace period: the card shows "Closed (False Positive)" / "SOAR executing"
      // status + toast before the Framer Motion exit fade removes it.
      setTimeout(() => {
        setAlerts(prev => prev.filter(a => (a.decision_id || a.alert_id) !== decisionId));
      }, 1600);
    } catch {
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className="flex flex-col h-full min-h-[320px] rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 shrink-0">
        <Fingerprint className="w-3.5 h-3.5 text-yellow-400" />
        <span className="text-xs font-bold text-slate-700 dark:text-slate-200">{t('pending_hitl')}</span>
        <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full border ${
          alerts.length + processing.length > 0
            ? 'text-yellow-400 border-yellow-500/40 bg-yellow-500/10'
            : 'text-slate-500 border-slate-700 bg-slate-800/40'
        }`}>
          {alerts.length + processing.length}
        </span>
        <div className="flex-1" />
        <button
          onClick={fetchPending}
          className="p-1 rounded text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
          title="Refresh queue"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {loading && alerts.length === 0 && processing.length === 0 ? (
          <div className="space-y-2">
            {[0, 1].map(i => (
              <div key={i} className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3">
                <div className="flex gap-3">
                  <div className="skeleton w-11 h-11 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <div className="skeleton h-3 w-2/3" />
                    <div className="skeleton h-3 w-1/2" />
                    <div className="skeleton h-8 w-full rounded-lg" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : alerts.length === 0 && processing.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-slate-500 dark:text-slate-600">
            <Inbox className="w-7 h-7 mb-2 opacity-30" />
            <span className="text-xs font-mono">{t('no_pending_decisions')}</span>
          </div>
        ) : (
          <AnimatePresence mode="popLayout">
            {processing.map(item => (
              <ProcessingCard key={`proc-${item.alert_id}`} item={item} />
            ))}
            {alerts.map(alert => (
              <PendingHITLCard
                key={alert.decision_id || alert.alert_id}
                alert={alert}
                onDecision={handleDecision}
                disabled={submitting === (alert.decision_id || alert.alert_id)}
              />
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
