import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield, Search, RefreshCw, Ban, CheckCircle, Clock, Globe, Hash as FileHash,
  Fingerprint, X, ChevronRight, ShieldCheck, ShieldOff, Timer, Activity,
  Server, Lock, Database, AlertTriangle, Check, Loader2, Download,
} from 'lucide-react';
import { iocApi } from '../api';
import { subscribeIocEvents } from '../utils/iocEvents';
import { showToast } from '../utils/toast';

// ── Constants ────────────────────────────────────────────────────────────────

const TYPE_META = {
  ip: { icon: Globe, label: 'IP', color: 'text-cyan-400', chip: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400' },
  domain: { icon: Server, label: 'DOMAIN', color: 'text-violet-400', chip: 'bg-violet-500/10 border-violet-500/30 text-violet-400' },
  hash_sha256: { icon: FileHash, label: 'SHA256', color: 'text-amber-400', chip: 'bg-amber-500/10 border-amber-500/30 text-amber-400' },
  hash_md5: { icon: Fingerprint, label: 'MD5', color: 'text-orange-400', chip: 'bg-orange-500/10 border-orange-500/30 text-orange-400' },
};

const SEVERITY_STYLES = {
  critical: 'bg-red-500/10 border-red-500/40 text-red-400',
  high: 'bg-orange-500/10 border-orange-500/40 text-orange-400',
  medium: 'bg-yellow-500/10 border-yellow-500/40 text-yellow-400',
  low: 'bg-green-500/10 border-green-500/40 text-green-400',
};

const STATUS_STYLES = {
  active: 'bg-cyan-500/10 border-cyan-500/40 text-cyan-400',
  expired: 'bg-slate-500/10 border-slate-500/40 text-slate-400',
  whitelisted: 'bg-green-500/10 border-green-500/40 text-green-400',
};

const LAYER_META = {
  fortigate: { icon: Shield, label: 'FortiGate' },
  edr: { icon: ShieldCheck, label: 'EDR' },
  av: { icon: Lock, label: 'AV' },
};

const TIMELINE_STEPS = [
  'Sigma rule fired',
  'Wazuh alert ingested',
  'Core Brain recommendation',
  'Human approval',
  'FortiGate block',
  'EDR/AV push',
];

// ── Mock data (used when the backend is unreachable) ─────────────────────────

const MOCK_IOCS = [
  {
    id: 'ioc-demo-001', type: 'ip', value: '45.155.205.233',
    source_sigma_rule_id: 'ageix_ssh_bruteforce_001', source_alert_id: 'wazuh-57321',
    source_decision_id: 'dec-8f3a21', first_seen: '2026-08-29T09:12:00Z', last_seen: '2026-08-29T14:44:00Z',
    confidence: 92, severity: 'critical', status: 'active', blocked_on: ['fortigate', 'edr'],
    mitre_technique: 'T1110.001', approved_by: 'aziz', ttl_hours: 72,
    timeline: [
      { step: 'Sigma rule fired', status: 'success', detail: 'Rule ageix_ssh_bruteforce_001', timestamp: '2026-08-29T09:12:00Z' },
      { step: 'Wazuh alert ingested', status: 'success', detail: 'Alert wazuh-57321', timestamp: '2026-08-29T09:12:04Z' },
      { step: 'Core Brain recommendation', status: 'success', detail: 'block_ip recommended', timestamp: '2026-08-29T09:13:10Z' },
      { step: 'Human approval', status: 'success', detail: 'Decision dec-8f3a21 approved by aziz', timestamp: '2026-08-29T09:14:02Z' },
      { step: 'FortiGate block', status: 'success', detail: 'Blocked at perimeter', timestamp: '2026-08-29T09:14:08Z' },
      { step: 'EDR/AV push', status: 'success', detail: 'Wazuh AR dispatched to 4 agent(s)', timestamp: '2026-08-29T09:14:15Z' },
    ],
    enrichment: { threat_intel: { source: 'feodo_tracker', flagged: true } },
  },
  {
    id: 'ioc-demo-002', type: 'hash_sha256', value: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    source_sigma_rule_id: 'ageix_malware_drop_007', source_alert_id: 'wazuh-57340',
    source_decision_id: 'dec-9b4c88', first_seen: '2026-08-29T10:02:00Z', last_seen: '2026-08-29T13:20:00Z',
    confidence: 78, severity: 'high', status: 'active', blocked_on: ['fortigate', 'av'],
    mitre_technique: 'T1204.002', approved_by: 'aziz', ttl_hours: 72,
    timeline: [
      { step: 'Sigma rule fired', status: 'success', detail: 'Rule ageix_malware_drop_007', timestamp: '2026-08-29T10:02:00Z' },
      { step: 'Wazuh alert ingested', status: 'success', detail: 'Alert wazuh-57340', timestamp: '2026-08-29T10:02:03Z' },
      { step: 'Core Brain recommendation', status: 'success', detail: 'block_hash recommended', timestamp: '2026-08-29T10:03:00Z' },
      { step: 'Human approval', status: 'success', detail: 'Decision dec-9b4c88 approved by aziz', timestamp: '2026-08-29T10:04:12Z' },
      { step: 'FortiGate block', status: 'success', detail: 'Blocked at perimeter', timestamp: '2026-08-29T10:04:20Z' },
      { step: 'EDR/AV push', status: 'success', detail: 'ClamAV local.hsb updated + reloaded', timestamp: '2026-08-29T10:04:31Z' },
    ],
    enrichment: {},
  },
  {
    id: 'ioc-demo-003', type: 'domain', value: 'malware-c2.example.top',
    source_sigma_rule_id: 'ageix_dns_tunnel_003', source_alert_id: 'wazuh-57355',
    source_decision_id: 'dec-77aa10', first_seen: '2026-08-28T22:41:00Z', last_seen: '2026-08-29T08:15:00Z',
    confidence: 64, severity: 'medium', status: 'active', blocked_on: ['fortigate'],
    mitre_technique: 'T1071.004', approved_by: 'analyst', ttl_hours: 72,
    timeline: [
      { step: 'Sigma rule fired', status: 'success', detail: 'Rule ageix_dns_tunnel_003', timestamp: '2026-08-28T22:41:00Z' },
      { step: 'Wazuh alert ingested', status: 'success', detail: 'Alert wazuh-57355', timestamp: '2026-08-28T22:41:05Z' },
      { step: 'Core Brain recommendation', status: 'success', detail: 'block_domain recommended', timestamp: '2026-08-28T22:42:00Z' },
      { step: 'Human approval', status: 'success', detail: 'Decision dec-77aa10 approved', timestamp: '2026-08-28T22:43:30Z' },
      { step: 'FortiGate block', status: 'success', detail: 'DNS blocked at perimeter', timestamp: '2026-08-28T22:43:38Z' },
      { step: 'EDR/AV push', status: 'pending', detail: 'Awaiting endpoint enforcement', timestamp: '2026-08-28T22:43:40Z' },
    ],
    enrichment: {},
  },
  {
    id: 'ioc-demo-004', type: 'ip', value: '192.168.56.40',
    source_sigma_rule_id: 'ageix_lab_scan_002', source_alert_id: 'wazuh-57360',
    source_decision_id: 'dec-11bb22', first_seen: '2026-08-27T11:00:00Z', last_seen: '2026-08-28T11:00:00Z',
    confidence: 40, severity: 'low', status: 'whitelisted', blocked_on: [],
    mitre_technique: 'T1046', approved_by: 'aziz', ttl_hours: 24,
    timeline: [
      { step: 'Sigma rule fired', status: 'success', detail: 'Rule ageix_lab_scan_002', timestamp: '2026-08-27T11:00:00Z' },
      { step: 'Wazuh alert ingested', status: 'success', detail: 'Alert wazuh-57360', timestamp: '2026-08-27T11:00:02Z' },
      { step: 'Core Brain recommendation', status: 'success', detail: 'block_ip recommended', timestamp: '2026-08-27T11:01:00Z' },
      { step: 'Human approval', status: 'success', detail: 'Decision dec-11bb22 approved', timestamp: '2026-08-27T11:02:00Z' },
      { step: 'FortiGate block', status: 'success', detail: 'Blocked at perimeter', timestamp: '2026-08-27T11:02:10Z' },
      { step: 'Whitelisted', status: 'success', detail: 'by aziz: lab asset — authorized vuln scanning', timestamp: '2026-08-28T11:00:00Z' },
    ],
    enrichment: {},
  },
];

// ── Small components ─────────────────────────────────────────────────────────

function LayerBadge({ layer, enforced }) {
  const meta = LAYER_META[layer] || { icon: Shield, label: layer };
  const Icon = meta.icon;
  return (
    <span
      title={enforced ? `Enforced on ${meta.label}` : `${meta.label}: not yet enforced`}
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[9px] font-mono font-bold ${
        enforced
          ? 'bg-green-500/10 border-green-500/40 text-green-400'
          : 'bg-slate-500/5 border-slate-600/40 text-slate-600'
      }`}
    >
      <Icon className="w-2.5 h-2.5" /> {meta.label}
    </span>
  );
}

function ConfidenceBar({ value }) {
  const clamped = Math.max(0, Math.min(100, value));
  const color = clamped >= 80 ? 'bg-red-500' : clamped >= 60 ? 'bg-orange-400' : clamped >= 40 ? 'bg-yellow-400' : 'bg-green-400';
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-12 h-1.5 rounded-full bg-slate-700/60 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${clamped}%` }} />
      </div>
      <span className="text-[9px] font-mono text-slate-400 w-6">{clamped}</span>
    </div>
  );
}

function StatusPill({ status }) {
  return (
    <span className={`px-1.5 py-0.5 rounded border text-[9px] font-mono font-bold uppercase ${STATUS_STYLES[status] || STATUS_STYLES.expired}`}>
      {status}
    </span>
  );
}

function SeverityPill({ severity }) {
  return (
    <span className={`px-1.5 py-0.5 rounded border text-[9px] font-mono font-bold uppercase ${SEVERITY_STYLES[severity] || SEVERITY_STYLES.medium}`}>
      {severity}
    </span>
  );
}

/** Mini kill-chain / pipeline visualization for the detail drawer. */
function IOCTimeline({ timeline }) {
  const byStep = useMemo(() => {
    const map = {};
    (timeline || []).forEach((ev) => {
      // match backend step names to canonical steps (prefix-tolerant)
      const canonical = TIMELINE_STEPS.find(
        (s) => ev.step === s || ev.step.startsWith(s.split(' ')[0]) || ev.step.includes(s.split(' ')[0]),
      );
      const key = canonical || ev.step;
      if (!map[key] || ev.status === 'success') map[key] = ev;
    });
    return map;
  }, [timeline]);

  return (
    <div className="relative pl-5">
      {/* vertical connector */}
      <div className="absolute left-[7px] top-2 bottom-2 w-px bg-slate-700/60" />
      {TIMELINE_STEPS.map((step, idx) => {
        const ev = byStep[step];
        const status = ev?.status || 'pending';
        const isLast = idx === TIMELINE_STEPS.length - 1;
        return (
          <div key={step} className="relative pb-4 last:pb-0">
            <span
              className={`absolute -left-5 top-0.5 w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                status === 'success'
                  ? 'bg-green-500/20 border-green-400'
                  : status === 'failed'
                  ? 'bg-red-500/20 border-red-400'
                  : status === 'running'
                  ? 'bg-cyan-500/20 border-cyan-400 animate-pulse'
                  : 'bg-slate-800 border-slate-600'
              }`}
            >
              {status === 'success' && <Check className="w-2.5 h-2.5 text-green-400" />}
              {status === 'failed' && <X className="w-2.5 h-2.5 text-red-400" />}
              {status === 'running' && <Loader2 className="w-2.5 h-2.5 text-cyan-400 animate-spin" />}
            </span>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-[11px] font-bold ${status === 'pending' ? 'text-slate-500' : 'text-slate-200'}`}>
                {step}
              </span>
              {isLast && ev?.status === 'pending' && (
                <span className="text-[8px] font-mono text-cyan-500/70 uppercase tracking-wider">in progress</span>
              )}
            </div>
            {ev?.detail && <p className="text-[9px] font-mono text-slate-500 mt-0.5">{ev.detail}</p>}
            {ev?.timestamp && (
              <p className="text-[8px] font-mono text-slate-600">
                {new Date(ev.timestamp).toLocaleString('en-US', { hour12: false })}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** Animated enforcement checklist shown in the drawer while EDR push is live. */
function EnforcementChecklist({ iocId }) {
  const [steps, setSteps] = useState({});

  useEffect(() => {
    return subscribeIocEvents((event) => {
      if (event.ioc_id !== iocId) return;
      if (event.type === 'ioc_progress') {
        setSteps((prev) => ({ ...prev, [event.step]: { status: event.status, message: event.message } }));
      } else if (event.type === 'ioc_enforced') {
        setSteps((prev) => ({
          ...prev,
          fortigate: { status: 'success', message: 'Blocking on FortiGate... ✅' },
          edr: { status: 'success', message: 'Pushing to EDR... ✅' },
          recorded: { status: 'success', message: 'IOC recorded ✅' },
        }));
      }
    });
  }, [iocId]);

  const entries = Object.entries(steps);
  if (!entries.length) return null;

  return (
    <div className="mt-3 rounded-lg border border-cyan-500/30 bg-cyan-500/5 p-2 space-y-1">
      <div className="text-[9px] font-mono font-bold text-cyan-400 tracking-wider mb-1">LIVE ENFORCEMENT</div>
      <AnimatePresence>
        {entries.map(([step, info]) => (
          <motion.div
            key={step}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2 text-[10px] font-mono"
          >
            {info.status === 'success' ? (
              <Check className="w-3 h-3 text-green-400" />
            ) : info.status === 'failed' ? (
              <AlertTriangle className="w-3 h-3 text-amber-400" />
            ) : (
              <Loader2 className="w-3 h-3 text-cyan-400 animate-spin" />
            )}
            <span className={info.status === 'success' ? 'text-green-300' : 'text-cyan-300'}>{info.message || step}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

/** Detail drawer: full IOC record + kill-chain timeline + actions. */
function IOCDrawer({ ioc, onClose, onAction, actionBusy }) {
  const [justification, setJustification] = useState('');
  const [showWhitelist, setShowWhitelist] = useState(false);
  const typeMeta = TYPE_META[ioc.type] || TYPE_META.ip;
  const TypeIcon = typeMeta.icon;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', stiffness: 320, damping: 34 }}
        onClick={(e) => e.stopPropagation()}
        className="absolute right-0 top-0 h-full w-full max-w-md bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col"
        role="dialog"
        aria-label={`IOC details for ${ioc.value}`}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-start gap-3">
          <div className={`p-2 rounded-lg border ${typeMeta.chip}`}>
            <TypeIcon className="w-5 h-5" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-mono font-bold text-slate-100 break-all">{ioc.value}</p>
            <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
              <span className={`px-1.5 py-0.5 rounded border text-[9px] font-mono font-bold ${typeMeta.chip}`}>{typeMeta.label}</span>
              <SeverityPill severity={ioc.severity} />
              <StatusPill status={ioc.status} />
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800" aria-label="Close drawer">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Meta grid */}
          <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
            <div className="rounded-lg bg-slate-900 border border-slate-800 p-2">
              <p className="text-slate-500">Source Rule</p>
              <p className="text-slate-200 truncate" title={ioc.source_sigma_rule_id}>{ioc.source_sigma_rule_id || '—'}</p>
            </div>
            <div className="rounded-lg bg-slate-900 border border-slate-800 p-2">
              <p className="text-slate-500">MITRE</p>
              <p className="text-cyan-400">{ioc.mitre_technique || '—'}</p>
            </div>
            <div className="rounded-lg bg-slate-900 border border-slate-800 p-2">
              <p className="text-slate-500">Approved By</p>
              <p className="text-slate-200">{ioc.approved_by || '—'}</p>
            </div>
            <div className="rounded-lg bg-slate-900 border border-slate-800 p-2">
              <p className="text-slate-500">TTL</p>
              <p className="text-slate-200">{ioc.ttl_hours}h from last seen</p>
            </div>
            <div className="rounded-lg bg-slate-900 border border-slate-800 p-2">
              <p className="text-slate-500">First Seen</p>
              <p className="text-slate-200">{ioc.first_seen ? new Date(ioc.first_seen).toLocaleString('en-US', { hour12: false }) : '—'}</p>
            </div>
            <div className="rounded-lg bg-slate-900 border border-slate-800 p-2">
              <p className="text-slate-500">Last Seen</p>
              <p className="text-slate-200">{ioc.last_seen ? new Date(ioc.last_seen).toLocaleString('en-US', { hour12: false }) : '—'}</p>
            </div>
          </div>

          {/* Blocked-on badges */}
          <div>
            <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-1.5">Enforcement Layers</p>
            <div className="flex gap-1.5 flex-wrap">
              {Object.keys(LAYER_META).map((layer) => (
                <LayerBadge key={layer} layer={layer} enforced={(ioc.blocked_on || []).includes(layer)} />
              ))}
            </div>
          </div>

          {/* Confidence */}
          <div>
            <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-1.5">Confidence</p>
            <ConfidenceBar value={ioc.confidence} />
          </div>

          {/* Threat intel enrichment */}
          {ioc.enrichment?.threat_intel && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-2 flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
              <div className="text-[10px] font-mono text-amber-300/90">
                <span className="font-bold">THREAT INTEL MATCH:</span>{' '}
                {ioc.enrichment.threat_intel.source || 'external feed'} flagged this indicator.
              </div>
            </div>
          )}

          {/* Live enforcement checklist (WS-driven) */}
          <EnforcementChecklist iocId={ioc.id} />

          {/* Kill-chain timeline */}
          <div>
            <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-2">
              Lifecycle — Sigma → Wazuh → Brain → HITL → FortiGate → EDR
            </p>
            <IOCTimeline timeline={ioc.timeline} />
          </div>

          {/* Whitelist justification */}
          <AnimatePresence>
            {showWhitelist && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="rounded-lg border border-green-500/30 bg-green-500/5 p-2 overflow-hidden"
              >
                <label className="text-[9px] font-mono font-bold text-green-400 uppercase tracking-wider">
                  Justification (required)
                </label>
                <textarea
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  placeholder="e.g. internal lab asset — authorized scanning host"
                  rows={2}
                  className="mt-1 w-full rounded bg-slate-900 border border-slate-700 text-[10px] font-mono text-slate-200 p-1.5 focus:outline-none focus:border-green-500/50"
                />
                <button
                  onClick={() => {
                    if (justification.trim().length < 3) {
                      showToast('Justification is required (min 3 chars).', 'error');
                      return;
                    }
                    onAction('whitelist', justification.trim());
                    setShowWhitelist(false);
                    setJustification('');
                  }}
                  disabled={actionBusy}
                  className="mt-1.5 w-full flex items-center justify-center gap-1 rounded bg-green-600/20 border border-green-500/40 text-green-400 text-[10px] font-bold py-1.5 hover:bg-green-600/30 disabled:opacity-40"
                >
                  <CheckCircle className="w-3 h-3" /> Confirm Whitelist
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer actions */}
        {ioc.status === 'active' && (
          <div className="p-3 border-t border-slate-800 flex gap-2">
            <button
              onClick={() => onAction('enforce')}
              disabled={actionBusy}
              className="flex-1 flex items-center justify-center gap-1 rounded-lg bg-cyan-600/15 border border-cyan-500/40 text-cyan-400 text-[10px] font-bold py-2 hover:bg-cyan-600/25 disabled:opacity-40"
            >
              {actionBusy === 'enforce' ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
              Enforce on EDR now
            </button>
            <button
              onClick={() => setShowWhitelist((v) => !v)}
              disabled={actionBusy}
              className="flex-1 flex items-center justify-center gap-1 rounded-lg bg-green-600/15 border border-green-500/40 text-green-400 text-[10px] font-bold py-2 hover:bg-green-600/25 disabled:opacity-40"
            >
              <CheckCircle className="w-3 h-3" /> Whitelist
            </button>
            <button
              onClick={() => onAction('expire')}
              disabled={actionBusy}
              className="flex-1 flex items-center justify-center gap-1 rounded-lg bg-red-600/15 border border-red-500/40 text-red-400 text-[10px] font-bold py-2 hover:bg-red-600/25 disabled:opacity-40"
            >
              <Timer className="w-3 h-3" /> Force Expire
            </button>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function IOCManagementView() {
  const [iocs, setIocs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [usingMock, setUsingMock] = useState(false);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [selected, setSelected] = useState(null);
  const [actionBusy, setActionBusy] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);
  const pollRef = useRef(null);

  const fetchAll = useCallback(async () => {
    try {
      const [listRes, statsRes] = await Promise.all([
        iocApi.list({ limit: 500 }),
        iocApi.stats(),
      ]);
      setIocs(listRes.data.items || []);
      setStats(statsRes.data);
      setUsingMock(false);
      setLastRefresh(new Date());
    } catch {
      if (!usingMock) {
        setIocs(MOCK_IOCS);
        setStats({
          total: MOCK_IOCS.length, active: 3, expired: 0, whitelisted: 1,
          enforced_edr: 2, pending_enforcement: 1,
          by_type: { ip: 2, domain: 1, hash_sha256: 1, hash_md5: 0 },
        });
        setUsingMock(true);
      }
    } finally {
      setLoading(false);
    }
  }, [usingMock]);

  useEffect(() => {
    fetchAll();
    pollRef.current = setInterval(fetchAll, 15000);
    return () => clearInterval(pollRef.current);
  }, [fetchAll]);

  // Live WS updates: refresh on ioc events
  useEffect(() => {
    return subscribeIocEvents((event) => {
      if (event.type === 'ioc_enforced' || event.type === 'ioc_update') {
        fetchAll();
      }
    });
  }, [fetchAll]);

  const filtered = useMemo(() => {
    let items = iocs;
    if (search) {
      const s = search.toLowerCase();
      items = items.filter(
        (i) => i.value.toLowerCase().includes(s) || (i.mitre_technique || '').toLowerCase().includes(s),
      );
    }
    if (typeFilter) items = items.filter((i) => i.type === typeFilter);
    if (statusFilter) items = items.filter((i) => i.status === statusFilter);
    if (severityFilter) items = items.filter((i) => i.severity === severityFilter);
    return items;
  }, [iocs, search, typeFilter, statusFilter, severityFilter]);

  const handleAction = useCallback(async (ioc, action, justification) => {
    setActionBusy(action);
    try {
      if (action === 'enforce') {
        await iocApi.enforceEdr(ioc.id);
        showToast(`EDR enforcement dispatched for ${ioc.value}`, 'success');
      } else if (action === 'whitelist') {
        await iocApi.whitelist(ioc.id, justification);
        showToast(`${ioc.value} whitelisted`, 'success');
      } else if (action === 'expire') {
        await iocApi.forceExpire(ioc.id);
        showToast(`${ioc.value} expired; unblocking in background`, 'info');
      }
      await fetchAll();
    } catch (e) {
      showToast(`Action failed: ${e.response?.data?.detail || e.message}`, 'error');
    } finally {
      setActionBusy(null);
    }
  }, [fetchAll]);

  const exportCsv = useCallback(() => {
    const rows = [
      ['id', 'type', 'value', 'severity', 'status', 'confidence', 'mitre', 'blocked_on', 'source_rule', 'approved_by', 'first_seen', 'last_seen'],
      ...filtered.map((i) => [
        i.id, i.type, i.value, i.severity, i.status, i.confidence, i.mitre_technique,
        (i.blocked_on || []).join('|'), i.source_sigma_rule_id, i.approved_by, i.first_seen, i.last_seen,
      ]),
    ];
    const csv = rows.map((r) => r.map((c) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ageixaisoc-iocs-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [filtered]);

  const statCards = [
    { label: 'Active IOCs', value: stats?.active ?? '—', color: 'text-cyan-400', icon: Activity },
    { label: 'Enforced on EDR', value: stats?.enforced_edr ?? '—', color: 'text-green-400', icon: ShieldCheck },
    { label: 'Pending Enforcement', value: stats?.pending_enforcement ?? '—', color: 'text-amber-400', icon: Clock },
    { label: 'Whitelisted', value: stats?.whitelisted ?? '—', color: 'text-slate-400', icon: ShieldOff },
  ];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 shrink-0">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-cyan-400" />
            <h1 className="text-base font-bold text-slate-100">IOC Management</h1>
            {usingMock && (
              <span className="px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[9px] font-mono font-bold">
                DEMO DATA — backend offline
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={exportCsv}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700 text-slate-300 text-[10px] font-mono font-bold hover:bg-slate-800"
              title="Export filtered IOCs as CSV"
            >
              <Download className="w-3 h-3" /> Export CSV
            </button>
            <button
              onClick={fetchAll}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700 text-slate-300 text-[10px] font-mono font-bold hover:bg-slate-800"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
          </div>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-3">
          {statCards.map(({ label, value, color, icon: Icon }) => (
            <div key={label} className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 flex items-center gap-2.5">
              <Icon className={`w-4 h-4 ${color}`} />
              <div>
                <p className={`text-lg font-bold font-mono leading-none ${color}`}>{value}</p>
                <p className="text-[9px] font-mono uppercase tracking-wider text-slate-500 mt-0.5">{label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          <div className="relative flex-1 min-w-[180px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search value or MITRE technique…"
              className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50"
              aria-label="Search IOCs"
            />
          </div>
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} aria-label="Filter by type"
            className="rounded-lg bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-300 px-2 py-1.5 focus:outline-none focus:border-cyan-500/50">
            <option value="">All Types</option>
            <option value="ip">IP</option>
            <option value="domain">Domain</option>
            <option value="hash_sha256">SHA-256</option>
            <option value="hash_md5">MD5</option>
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filter by status"
            className="rounded-lg bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-300 px-2 py-1.5 focus:outline-none focus:border-cyan-500/50">
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="expired">Expired</option>
            <option value="whitelisted">Whitelisted</option>
          </select>
          <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} aria-label="Filter by severity"
            className="rounded-lg bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-300 px-2 py-1.5 focus:outline-none focus:border-cyan-500/50">
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto px-4 pb-4">
        <div className="rounded-lg border border-slate-800 bg-slate-900/40 overflow-hidden">
          <table className="w-full text-left">
            <thead className="sticky top-0 bg-slate-900 border-b border-slate-800 z-10">
              <tr className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500">
                <th className="px-3 py-2">Value</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2 hidden md:table-cell">Source Rule</th>
                <th className="px-3 py-2 hidden lg:table-cell">MITRE</th>
                <th className="px-3 py-2">Confidence</th>
                <th className="px-3 py-2">Severity</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Blocked On</th>
                <th className="px-3 py-2 w-8"></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-t border-slate-800/60">
                    <td colSpan={9} className="px-3 py-3">
                      <div className="h-3 rounded bg-slate-800 animate-pulse" style={{ width: `${60 + (i % 3) * 15}%` }} />
                    </td>
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-3 py-10 text-center">
                    <Shield className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                    <p className="text-[11px] font-mono text-slate-500">No IOCs match the current filters.</p>
                    <p className="text-[9px] font-mono text-slate-600 mt-0.5">
                      IOCs are recorded automatically when an approved block succeeds.
                    </p>
                  </td>
                </tr>
              ) : (
                filtered.map((ioc) => {
                  const typeMeta = TYPE_META[ioc.type] || TYPE_META.ip;
                  const TypeIcon = typeMeta.icon;
                  return (
                    <tr
                      key={ioc.id}
                      onClick={() => setSelected(ioc)}
                      className="border-t border-slate-800/60 hover:bg-slate-800/30 cursor-pointer transition-colors"
                    >
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          <TypeIcon className={`w-3.5 h-3.5 shrink-0 ${typeMeta.color}`} />
                          <span className="text-[11px] font-mono text-slate-200 truncate max-w-[220px]" title={ioc.value}>
                            {ioc.value}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`px-1.5 py-0.5 rounded border text-[9px] font-mono font-bold ${typeMeta.chip}`}>
                          {typeMeta.label}
                        </span>
                      </td>
                      <td className="px-3 py-2 hidden md:table-cell">
                        <span className="text-[10px] font-mono text-slate-400 truncate block max-w-[160px]" title={ioc.source_sigma_rule_id}>
                          {ioc.source_sigma_rule_id || '—'}
                        </span>
                      </td>
                      <td className="px-3 py-2 hidden lg:table-cell">
                        <span className="text-[10px] font-mono text-cyan-400">{ioc.mitre_technique || '—'}</span>
                      </td>
                      <td className="px-3 py-2"><ConfidenceBar value={ioc.confidence} /></td>
                      <td className="px-3 py-2"><SeverityPill severity={ioc.severity} /></td>
                      <td className="px-3 py-2"><StatusPill status={ioc.status} /></td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1 flex-wrap">
                          {Object.keys(LAYER_META).map((layer) => (
                            <LayerBadge key={layer} layer={layer} enforced={(ioc.blocked_on || []).includes(layer)} />
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        {lastRefresh && (
          <p className="mt-2 text-[9px] font-mono text-slate-600 text-right">
            Last refreshed {lastRefresh.toLocaleTimeString('en-US', { hour12: false })} · auto-poll 15s
          </p>
        )}
      </div>

      {/* Detail drawer */}
      <AnimatePresence>
        {selected && (
          <IOCDrawer
            ioc={selected}
            onClose={() => setSelected(null)}
            onAction={(action, justification) => handleAction(selected, action, justification)}
            actionBusy={actionBusy}
          />
        )}
      </AnimatePresence>
    </div>
  );
}