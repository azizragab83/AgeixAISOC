import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal as TerminalIcon, Trash2, ArrowDown, ArrowUp } from 'lucide-react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useLanguage } from '../context/LanguageContext';

const MAX_LOGS = 300;

const AGENT_META = {
  threat_detection: { label: 'THREAT-DET', color: 'text-blue-400', type: 'agent' },
  risk_scoring: { label: 'RISK-SCORE', color: 'text-amber-400', type: 'agent' },
  recommendation: { label: 'RECOMMEND', color: 'text-purple-400', type: 'agent' },
  threat_hunter: { label: 'THREAT-HUNT', color: 'text-orange-400', type: 'agent' },
  forensics: { label: 'FORENSICS', color: 'text-cyan-400', type: 'agent' },
  red_team: { label: 'RED-TEAM', color: 'text-red-500', type: 'agent' },
  blue_team: { label: 'BLUE-TEAM', color: 'text-emerald-400', type: 'agent' },
  detection_engineer: { label: 'DETECT-ENG', color: 'text-teal-400', type: 'agent' },
  gap_closure: { label: 'GAP-CLOSE', color: 'text-sky-400', type: 'agent' },
  siem: { label: 'SIEM', color: 'text-slate-400', type: 'siem' },
  wazuh: { label: 'WAZUH', color: 'text-slate-400', type: 'siem' },
  system: { label: 'SYSTEM', color: 'text-slate-500', type: 'system' },
};

function classify(log) {
  const agent = (log.agent || 'system').toLowerCase();
  if (AGENT_META[agent]) return AGENT_META[agent];
  if (log.level === 'error' || log.level === 'critical') return { label: 'CRITICAL', color: 'text-red-500', type: 'critical' };
  return { label: agent.toUpperCase().slice(0, 10), color: 'text-cyan-400', type: 'agent' };
}

function TerminalRow({ log, isNew }) {
  const meta = classify(log);
  const ts = log.timestamp ? new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false }) : '--:--:--';

  const base = 'flex items-start gap-2 py-[3px] px-2 border-l-2 font-mono text-[10px] leading-snug';
  let rowClass;
  if (meta.type === 'siem') rowClass = 'border-l-slate-600 text-slate-400';
  else if (meta.type === 'system') rowClass = 'border-l-slate-700 text-slate-500';
  else if (meta.type === 'critical' || log.level === 'error') rowClass = 'border-l-red-500 text-red-500 font-bold';
  else rowClass = 'border-l-cyan-500/60 text-slate-300';

  return (
    <motion.div
      layout
      initial={isNew ? { opacity: 0, y: -6, backgroundColor: 'rgba(14,165,233,0.12)' } : false}
      animate={{ opacity: 1, y: 0, backgroundColor: 'rgba(14,165,233,0)' }}
      transition={{ duration: 0.4 }}
      className={`${base} ${rowClass} hover:bg-slate-800/40`}
    >
      <span className="text-slate-600 w-12 shrink-0 tabular-nums">{ts}</span>
      <span className={`${meta.color} w-[86px] shrink-0 font-bold`}>[{meta.label}]</span>
      <span className="min-w-0 break-words">{log.message || ''}</span>
    </motion.div>
  );
}

export default function LiveFeedTerminal() {
  const { t } = useLanguage();
  const { wsConnected, addHandler } = useWebSocket();
  const [logs, setLogs] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [paused, setPaused] = useState(false);
  const scrollRef = useRef(null);
  const lastNewIdRef = useRef(null);
  const pausedCountRef = useRef(0);

  const appendLogs = useCallback((incoming) => {
    setLogs(prev => {
      const next = [...prev, ...incoming].slice(-MAX_LOGS);
      if (incoming.length > 0) lastNewIdRef.current = incoming[incoming.length - 1]._id;
      return next;
    });
  }, []);

  const handleWsMessage = useCallback((data) => {
    switch (data.type) {
      case 'agent_log':
        appendLogs((data.logs || []).map(l => ({
          ...l,
          timestamp: l.timestamp || data.timestamp,
          _id: `ag-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        })));
        break;
      case 'pipeline_status':
        if (data.status === 'running') {
          appendLogs([{
            agent: 'system', message: `SOC pipeline initiated — alert ${data.alert_id}`,
            timestamp: data.timestamp, level: 'info',
            _id: `ps-${Date.now()}`,
          }]);
        }
        break;
      case 'node_transition':
        appendLogs([{
          agent: 'system', message: `Pipeline → ${String(data.node || '').replace(/_/g, ' ')}`,
          timestamp: data.timestamp, level: 'info',
          _id: `nt-${Date.now()}`,
        }]);
        break;
      case 'pipeline_complete':
        appendLogs([{
          agent: 'system', message: `Pipeline complete — ${data.decision_id || ''}`,
          timestamp: data.timestamp, level: 'success',
          _id: `pc-${Date.now()}`,
        }]);
        break;
      case 'pipeline_error':
        appendLogs([{
          agent: 'system', message: `Pipeline ERROR: ${data.error}`,
          timestamp: data.timestamp, level: 'error',
          _id: `pe-${Date.now()}`,
        }]);
        break;
      case 'decision_result':
        appendLogs([{
          agent: 'system',
          message: `HITL decision ${data.action || ''} — ${data.decision_id || ''}`,
          timestamp: data.timestamp, level: data.action === 'approved' ? 'success' : 'warning',
          _id: `dr-${Date.now()}`,
        }]);
        break;
      case 'attack_result':
        appendLogs([{
          agent: 'red_team',
          message: `Attack ${data.success ? 'completed' : 'failed'}: ${data.attack_type || ''} → ${data.target || ''}`,
          timestamp: data.timestamp, level: data.success ? 'success' : 'error',
          _id: `ar-${Date.now()}`,
        }]);
        break;
      case 'soar_execution':
        appendLogs([{
          agent: 'recommendation',
          message: `SOAR ${data.status || ''}: ${data.decision_id || ''}`,
          timestamp: data.timestamp, level: 'info',
          _id: `se-${Date.now()}`,
        }]);
        break;
      case 'decision_package':
        appendLogs([{
          agent: 'system',
          message: `New decision package: ${data.decision_id || data.alert_id || ''} — awaiting human review`,
          timestamp: data.timestamp, level: 'warning',
          _id: `dp-${Date.now()}`,
        }]);
        break;
      default:
        break;
    }
  }, [appendLogs]);

  useEffect(() => {
    return addHandler(handleWsMessage);
  }, [addHandler, handleWsMessage]);

  useEffect(() => {
    if (wsConnected) {
      setLogs(prev => {
        if (prev.some(l => l._id === 'ws-up')) return prev;
        const entry = {
          agent: 'system', message: 'WebSocket connected — listening on /ws/dashboard',
          timestamp: new Date().toISOString(), level: 'success', _id: 'ws-up',
        };
        lastNewIdRef.current = entry._id;
        return [...prev, entry];
      });
    }
  }, [wsConnected]);

  useEffect(() => {
    if (autoScroll && !paused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll, paused]);

  const handleScroll = (e) => {
    const el = e.currentTarget;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 32;
    setAutoScroll(atBottom);
    setPaused(!atBottom);
    if (!atBottom && pausedCountRef.current === 0) pausedCountRef.current = logs.length;
    if (atBottom) pausedCountRef.current = 0;
  };

  const newSincePause = paused ? Math.max(0, logs.length - pausedCountRef.current) : 0;

  return (
    <div className="flex flex-col h-full min-h-[320px] rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 shrink-0">
        <div className="flex gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
          <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
          <span className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
        </div>
        <span className="text-xs font-bold text-slate-700 dark:text-slate-200">{t('terminal')}</span>
        <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${
          wsConnected ? 'text-green-400 border-green-500/30 bg-green-500/5' : 'text-red-500 border-red-500/30 bg-red-500/5'
        }`}>
          {wsConnected ? 'LIVE' : 'OFFLINE'}
        </span>
        <div className="flex-1" />
        <span className="text-[9px] font-mono text-slate-500 dark:text-slate-500 tabular-nums">{logs.length} events</span>
        {paused && (
          <button
            onClick={() => { setPaused(false); setAutoScroll(true); pausedCountRef.current = 0; }}
            className="flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
            title="Resume auto-scroll"
          >
            <ArrowDown className="w-3 h-3" /> {newSincePause > 0 ? `${newSincePause} new` : 'resume'}
          </button>
        )}
        <button
          onClick={() => setLogs([])}
          className="p-1 rounded text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
          title="Clear terminal"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>

      {/* Body */}
      <div ref={scrollRef} onScroll={handleScroll} className="flex-1 overflow-y-auto px-1 py-1 bg-slate-50/50 dark:bg-slate-950/60">
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-slate-500 dark:text-slate-600">
            <TerminalIcon className="w-7 h-7 mb-2 opacity-30" />
            <span className="text-xs font-mono">{t('searching')}</span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {logs.map(log => (
              <TerminalRow key={log._id} log={log} isNew={log._id === lastNewIdRef.current} />
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Footer status bar */}
      <div className="flex items-center gap-2 px-3 py-1 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 shrink-0">
        <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-green-400 animate-pulse' : 'bg-red-500'}`} />
        <span className="text-[9px] font-mono text-slate-500 dark:text-slate-500">
          {wsConnected ? 'REALTIME STREAM ACTIVE' : 'RECONNECTING...'}
        </span>
        <div className="flex-1" />
        <span className="text-[9px] font-mono text-slate-500 dark:text-slate-600 flex items-center gap-1">
          <ArrowUp className="w-2.5 h-2.5" /> {autoScroll ? 'AUTO-SCROLL' : 'PAUSED'}
        </span>
      </div>
    </div>
  );
}
