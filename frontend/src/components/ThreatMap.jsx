import { useState, useEffect, useRef, useCallback } from 'react';
import { getAlertsFeed } from '../api';
import { useWebSocket } from '../hooks/useWebSocket';

const NODES = [
  { id: 'fortigate', label: 'FortiGate', ip: '192.168.56.2', x: 250, y: 30, color: '#f59e0b' },
  { id: 'kali', label: 'Kali Linux', ip: '192.168.56.10', x: 60, y: 100, color: '#ef4444' },
  { id: 'win10', label: 'Win 10 Victim', ip: '192.168.56.20', x: 140, y: 200, color: '#3b82f6' },
  { id: 'wazuh', label: 'Wazuh SIEM', ip: '192.168.56.30', x: 260, y: 150, color: '#10b981' },
  { id: 'metasploitable', label: 'Metasploitable 2', ip: '192.168.56.40', x: 60, y: 280, color: '#8b5cf6' },
  { id: 'win_server', label: 'Win Server DC', ip: '192.168.56.100', x: 380, y: 260, color: '#06b6d4' },
];

const EDGES = [
  ['fortigate', 'kali'], ['fortigate', 'wazuh'], ['fortigate', 'win10'],
  ['fortigate', 'win_server'], ['fortigate', 'metasploitable'],
  ['kali', 'win10'], ['kali', 'metasploitable'], ['kali', 'wazuh'],
  ['win10', 'win_server'], ['wazuh', 'win10'], ['wazuh', 'win_server'],
];

// Deterministic position for any source IP marker on the internal-network visual
function markerPosition(ip, index) {
  let h = 0;
  for (let i = 0; i < ip.length; i++) h = (h * 31 + ip.charCodeAt(i)) >>> 0;
  const angle = (h / 4294967296) * 2 * Math.PI;
  const radius = 40 + (h % 90);
  return { cx: 230 + radius * Math.cos(angle), cy: 160 + radius * Math.sin(angle) };
}

export default function ThreatMap() {
  const [status, setStatus] = useState({});
  const [activeEdge, setActiveEdge] = useState(null);
  const [alertIps, setAlertIps] = useState([]);
  const [loading, setLoading] = useState(true);
  const liveMarkersRef = useRef([]);
  const { addHandler, wsConnected } = useWebSocket();

  // Live markers: added the instant a pipeline starts or an attack is launched (WS)
  const handleWsMessage = useCallback((data) => {
    if (data.type === 'pipeline_started' && data.source_ip && data.source_ip !== 'unknown') {
      const ts = data.timestamp || new Date().toISOString();
      liveMarkersRef.current = [
        { ip: data.source_ip, timestamp: ts, kind: 'pipeline' },
        ...liveMarkersRef.current.filter(m => m.ip !== data.source_ip),
      ].slice(0, 10);
      setAlertIps([...liveMarkersRef.current]);
    }
    if (data.type === 'attack_launched' && (data.target_ip || data.source_ip)) {
      const ip = data.target_ip || data.source_ip;
      const ts = data.timestamp || new Date().toISOString();
      liveMarkersRef.current = [
        { ip, timestamp: ts, kind: 'attack', attack: data.attack_type || '' },
        ...liveMarkersRef.current.filter(m => m.ip !== ip),
      ].slice(0, 10);
      setAlertIps([...liveMarkersRef.current]);
    }
  }, []);

  useEffect(() => {
    return addHandler(handleWsMessage);
  }, [addHandler, handleWsMessage]);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/lab/status');
        const data = await res.json();
        setStatus(data);
      } catch {}
    };
    fetchStatus();
    const statusInterval = setInterval(fetchStatus, 10000);
    return () => clearInterval(statusInterval);
  }, []);

  useEffect(() => {
    const fetchAlerts = async () => {
      setLoading(true);
      try {
        const res = await getAlertsFeed(20);
        const alerts = res.data.alerts || [];
        const ips = alerts
          .filter(a => a.source_ip && a.source_ip !== 'unknown' && a.source_ip !== '')
          .map(a => ({ ip: a.source_ip, timestamp: a.timestamp, kind: 'alert' }));
        const merged = new Map();
        [...ips, ...liveMarkersRef.current].forEach(m => merged.set(m.ip, m));
        setAlertIps(Array.from(merged.values()).slice(0, 10));
      } catch {
        setAlertIps(prev => (liveMarkersRef.current.length ? prev : []));
      } finally {
        setLoading(false);
      }
    };
    fetchAlerts();
    const alertInterval = setInterval(fetchAlerts, 10000);
    return () => clearInterval(alertInterval);
  }, []);

  const nodeStatus = (id) => {
    const d = status[id];
    if (!d) return 'unknown';
    return d.status === 'online' ? 'online' : 'offline';
  };

  const statusColor = (s) => s === 'online' ? '#22c55e' : s === 'offline' ? '#ef4444' : '#64748b';

  return (
    <div className="soc-card relative">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-bold text-white">Internal Network Topology</h3>
        <div className="flex items-center gap-2">
          {wsConnected && (
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-green-500/10 border border-green-500/30 text-green-400">
              LIVE · {alertIps.length} THREAT{alertIps.length === 1 ? '' : 'S'}
            </span>
          )}
        </div>
      </div>
      <p className="text-[9px] text-slate-500 mb-2 font-mono">Lab network — markers appear the moment a pipeline starts or an attack launches (WebSocket)</p>
      {!loading && alertIps.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/60 rounded-xl z-10">
          <div className="text-center">
            <div className="text-4xl mb-2">🛡️</div>
            <div className="text-sm text-slate-400 font-medium">No active threats detected</div>
            <div className="text-xs text-slate-600 mt-1">All clear — monitoring for suspicious activity</div>
          </div>
        </div>
      )}
      <svg viewBox="0 0 460 320" className="w-full h-auto" style={{ minHeight: 260 }}>
        {EDGES.map(([from, to], i) => {
          const f = NODES.find((n) => n.id === from);
          const t = NODES.find((n) => n.id === to);
          if (!f || !t) return null;
          const isActive = activeEdge === i;
          return (
            <line
              key={i}
              x1={f.x} y1={f.y} x2={t.x} y2={t.y}
              stroke={isActive ? '#22d3ee' : '#334155'}
              strokeWidth={isActive ? 2 : 1}
              strokeDasharray={isActive ? 'none' : '4,3'}
              className="transition-all cursor-pointer"
              onMouseEnter={() => setActiveEdge(i)}
              onMouseLeave={() => setActiveEdge(null)}
            />
          );
        })}
        {NODES.map((node) => {
          const s = nodeStatus(node.id);
          return (
            <g key={node.id} className="cursor-pointer">
              <circle cx={node.x} cy={node.y} r={18} fill={node.color} fillOpacity={0.15} stroke={statusColor(s)} strokeWidth={2} />
              <circle cx={node.x} cy={node.y} r={6} fill={statusColor(s)}>
                {s === 'online' && <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite" />}
              </circle>
              <text x={node.x} y={node.y + 32} textAnchor="middle" fill="#94a3b8" fontSize="9" fontFamily="monospace">{node.label}</text>
              <text x={node.x} y={node.y + 43} textAnchor="middle" fill="#64748b" fontSize="7" fontFamily="monospace">{node.ip}</text>
            </g>
          );
        })}
        {/* Threat markers from real alert source IPs (live via WS, seeded by API) */}
        {alertIps.slice(0, 10).map((m, idx) => {
          const { cx, cy } = markerPosition(m.ip, idx);
          return (
            <g key={`threat-${m.ip}-${idx}`}>
              <circle cx={cx} cy={cy} r={8} fill="#ef4444" fillOpacity={0.3} stroke="#ef4444" strokeWidth={1.5}>
                <animate attributeName="r" values="8;12;8" dur="2s" repeatCount="indefinite" />
                <animate attributeName="fillOpacity" values="0.3;0.6;0.3" dur="2s" repeatCount="indefinite" />
              </circle>
              <circle cx={cx} cy={cy} r={3} fill="#ef4444" />
              <text x={cx} y={cy + 18} textAnchor="middle" fill="#ef4444" fontSize="6" fontFamily="monospace">{m.ip}</text>
              {m.kind === 'attack' && m.attack && (
                <text x={cx} y={cy - 10} textAnchor="middle" fill="#f97316" fontSize="5.5" fontFamily="monospace">⚡{m.attack}</text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
