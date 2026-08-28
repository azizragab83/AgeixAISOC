import { useState, useEffect, useCallback } from 'react';
import { Globe2, MapPin, Activity } from 'lucide-react';
import { getAlertsFeed, labApi } from '../api';
import { useLanguage } from '../context/LanguageContext';

const WORLD_PATH =
  '<path d="M 38.9 69.4 L 69.4 55.6 L 111.1 55.6 L 144.4 52.8 L 194.4 50.0 L 238.9 55.6 L 272.2 72.2 L 294.4 88.9 L 311.1 111.1 L 316.7 125.0 L 311.1 138.9 L 294.4 155.6 L 283.3 166.7 L 277.8 177.8 L 269.4 172.2 L 258.3 166.7 L 250.0 169.4 L 238.9 177.8 L 230.6 172.2 L 219.4 169.4 L 202.8 163.9 L 186.1 169.4 L 177.8 155.6 L 169.4 147.2 L 158.3 138.9 L 155.6 125.0 L 150.0 113.9 L 138.9 102.8 L 122.2 91.7 L 100.0 86.1 L 77.8 80.6 L 55.6 75.0 L 38.9 69.4 Z" />' +
  '<path d="M 375.0 83.3 L 355.6 69.4 L 347.2 55.6 L 366.7 41.7 L 388.9 36.1 L 416.7 38.9 L 433.3 55.6 L 425.0 66.7 L 408.3 75.0 L 388.9 83.3 L 375.0 83.3 Z" />' +
  '<path d="M 283.3 227.8 L 305.6 222.2 L 333.3 227.8 L 361.1 233.3 L 383.3 244.4 L 394.4 261.1 L 402.8 272.2 L 394.4 288.9 L 386.1 305.6 L 372.2 319.4 L 352.8 327.8 L 338.9 338.9 L 327.8 350.0 L 316.7 361.1 L 305.6 375.0 L 297.2 394.4 L 305.6 402.8 L 316.7 400.0 L 327.8 388.9 L 341.7 372.2 L 352.8 355.6 L 361.1 338.9 L 366.7 316.7 L 377.8 294.4 L 388.9 272.2 L 394.4 250.0 L 383.3 236.1 L 366.7 233.3 L 338.9 230.6 L 305.6 225.0 L 283.3 227.8 Z" />' +
  '<path d="M 475.0 144.4 L 475.0 130.6 L 483.3 127.8 L 494.4 130.6 L 505.6 127.8 L 513.9 130.6 L 522.2 127.8 L 527.8 133.3 L 538.9 138.9 L 550.0 136.1 L 561.1 144.4 L 572.2 138.9 L 577.8 147.2 L 597.2 150.0 L 611.1 150.0 L 625.0 147.2 L 638.9 144.4 L 652.8 144.4 L 666.7 138.9 L 680.6 138.9 L 694.4 138.9 L 708.3 133.3 L 722.2 130.6 L 736.1 127.8 L 750.0 125.0 L 763.9 127.8 L 777.8 127.8 L 791.7 125.0 L 805.6 125.0 L 819.4 130.6 L 833.3 133.3 L 847.2 133.3 L 861.1 138.9 L 875.0 144.4 L 888.9 147.2 L 902.8 138.9 L 916.7 125.0 L 930.6 111.1 L 938.9 102.8 L 944.4 94.4 L 944.4 83.3 L 930.6 77.8 L 916.7 69.4 L 902.8 61.1 L 888.9 55.6 L 875.0 50.0 L 861.1 47.2 L 847.2 44.4 L 833.3 41.7 L 819.4 44.4 L 805.6 41.7 L 791.7 38.9 L 777.8 44.4 L 763.9 38.9 L 750.0 36.1 L 736.1 41.7 L 722.2 38.9 L 708.3 36.1 L 694.4 38.9 L 680.6 44.4 L 666.7 47.2 L 652.8 50.0 L 638.9 52.8 L 625.0 55.6 L 611.1 58.3 L 597.2 55.6 L 583.3 52.8 L 577.8 58.3 L 569.4 52.8 L 561.1 55.6 L 550.0 55.6 L 541.7 61.1 L 533.3 66.7 L 527.8 72.2 L 522.2 77.8 L 513.9 80.6 L 508.3 88.9 L 500.0 97.2 L 494.4 102.8 L 486.1 105.6 L 477.8 108.3 L 472.2 116.7 L 475.0 125.0 L 475.0 144.4 Z" />' +
  '<path d="M 597.2 172.2 L 616.7 166.7 L 633.3 166.7 L 652.8 172.2 L 661.1 180.6 L 652.8 188.9 L 633.3 194.4 L 619.4 188.9 L 605.6 180.6 L 597.2 172.2 Z" />' +
  '<path d="M 688.9 180.6 L 700.0 194.4 L 713.9 208.3 L 722.2 222.2 L 722.2 233.3 L 736.1 233.3 L 744.4 216.7 L 750.0 200.0 L 744.4 188.9 L 727.8 180.6 L 708.3 172.2 L 688.9 180.6 Z" />' +
  '<path d="M 483.3 152.8 L 472.2 166.7 L 461.1 172.2 L 455.6 183.3 L 452.8 194.4 L 458.3 208.3 L 463.9 216.7 L 469.4 225.0 L 475.0 236.1 L 477.8 250.0 L 477.8 263.9 L 472.2 277.8 L 466.7 291.7 L 461.1 305.6 L 452.8 319.4 L 444.4 333.3 L 438.9 344.4 L 450.0 344.4 L 458.3 333.3 L 466.7 316.7 L 472.2 300.0 L 475.0 283.3 L 472.2 266.7 L 466.7 255.6 L 461.1 241.7 L 455.6 227.8 L 450.0 213.9 L 444.4 200.0 L 438.9 188.9 L 433.3 177.8 L 422.2 172.2 L 411.1 166.7 L 402.8 161.1 L 416.7 152.8 L 433.3 147.2 L 444.4 150.0 L 458.3 147.2 L 466.7 152.8 L 472.2 147.2 L 480.6 150.0 L 483.3 152.8 Z" />' +
  '<path d="M 605.6 216.7 L 611.1 216.7 L 625.0 222.2 L 633.3 216.7 L 638.9 227.8 L 641.7 236.1 L 633.3 244.4 L 619.4 244.4 L 611.1 236.1 L 605.6 227.8 L 605.6 216.7 Z" />' +
  '<path d="M 816.7 311.1 L 827.8 305.6 L 838.9 300.0 L 852.8 294.4 L 866.7 291.7 L 880.6 288.9 L 894.4 286.1 L 905.6 294.4 L 916.7 300.0 L 925.0 311.1 L 927.8 325.0 L 925.0 338.9 L 916.7 347.2 L 908.3 355.6 L 897.2 361.1 L 883.3 355.6 L 869.4 350.0 L 855.6 347.2 L 841.7 344.4 L 830.6 341.7 L 822.2 333.3 L 816.7 322.2 L 816.7 311.1 Z" />' +
  '<path d="M 861.1 161.1 L 866.7 155.6 L 875.0 152.8 L 880.6 147.2 L 886.1 144.4 L 891.7 138.9 L 894.4 130.6 L 888.9 127.8 L 883.3 133.3 L 877.8 141.7 L 869.4 147.2 L 863.9 152.8 L 861.1 161.1 Z" />' +
  '<path d="M 486.1 111.1 L 491.7 108.3 L 497.2 105.6 L 500.0 100.0 L 502.8 94.4 L 500.0 91.7 L 494.4 88.9 L 488.9 91.7 L 486.1 97.2 L 483.3 102.8 L 486.1 111.1 Z" />' +
  '<path d="M 622.2 286.1 L 630.6 288.9 L 638.9 294.4 L 638.9 305.6 L 630.6 316.7 L 625.0 319.4 L 622.2 311.1 L 619.4 300.0 L 622.2 286.1 Z" />' +
  '<path d="M 763.9 236.1 L 769.4 241.7 L 777.8 244.4 L 786.1 250.0 L 794.4 255.6 L 802.8 258.3 L 811.1 261.1 L 819.4 261.1 L 827.8 258.3 L 836.1 255.6 L 844.4 252.8 L 852.8 250.0 L 861.1 247.2 L 863.9 241.7 L 855.6 238.9 L 847.2 238.9 L 838.9 241.7 L 830.6 244.4 L 822.2 244.4 L 813.9 247.2 L 805.6 247.2 L 797.2 244.4 L 788.9 241.7 L 780.6 238.9 L 772.2 236.1 L 763.9 236.1 Z" />';

const LAB_NODES = [
  { id: 'fortigate', label: 'FortiGate', ip: '192.168.56.2', x: 78, y: 28, color: '#f59e0b' },
  { id: 'kali', label: 'Kali Linux', ip: '192.168.56.10', x: 22, y: 35, color: '#ef4444' },
  { id: 'wazuh', label: 'Wazuh SIEM', ip: '192.168.56.30', x: 72, y: 55, color: '#10b981' },
  { id: 'win10', label: 'Win 10 Victim', ip: '192.168.56.20', x: 45, y: 70, color: '#3b82f6' },
  { id: 'metasploitable', label: 'Metasploitable', ip: '192.168.56.40', x: 20, y: 75, color: '#8b5cf6' },
  { id: 'win_server', label: 'Win Server DC', ip: '192.168.56.100', x: 88, y: 72, color: '#06b6d4' },
];

function hashStr(str) {
  let h = 5381;
  for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) >>> 0;
  return h;
}

function projectIp(ip) {
  const h = hashStr(ip);
  const lat = (h % 10000) / 10000 * 150 - 75;
  const lon = (h % 10000) / 10000 * 320 - 160;
  return {
    x: ((lon + 180) / 360) * 100,
    y: ((90 - lat) / 180) * 100,
  };
}

export default function ThreatGeoMap() {
  const { t } = useLanguage();
  const [alerts, setAlerts] = useState([]);
  const [labStatus, setLabStatus] = useState({});
  const [loading, setLoading] = useState(true);

  const fetchAlerts = useCallback(async () => {
    try {
      const [alertsRes, labRes] = await Promise.all([
        getAlertsFeed(20),
        labApi.getStatus(),
      ]);
      setAlerts((alertsRes.data.alerts || []).filter(a => a.source_ip));
      setLabStatus(labRes.data || {});
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 15000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const uniqueIps = [...new Map(alerts.map(a => [a.source_ip, a])).values()];
  const nodeOnline = (id) => labStatus[id]?.status === 'online';

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 shrink-0">
        <Globe2 className="w-3.5 h-3.5 text-red-500" />
        <span className="text-xs font-bold text-slate-700 dark:text-slate-200">{t('threat_map')}</span>
        <div className="flex-1" />
        <span className="text-[9px] font-mono text-slate-500">
          {uniqueIps.length} THREAT · {LAB_NODES.filter(n => nodeOnline(n.id)).length}/{LAB_NODES.length} NODES
        </span>
      </div>

      <div className="relative m-2 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800 bg-[#020617]">
        <svg viewBox="0 0 1000 500" preserveAspectRatio="xMidYMid meet" className="w-full h-auto opacity-30 dark:opacity-40" dangerouslySetInnerHTML={{ __html: WORLD_PATH.replace(/<path /g, '<path fill="#334155" ') }} />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_30%,rgba(2,6,23,0.9))]" />

        {/* Lab nodes always visible */}
        {LAB_NODES.map((node) => {
          const online = nodeOnline(node.id);
          return (
            <g key={node.id}>
              <circle cx={`${node.x}%`} cy={`${node.y}%`} r={12} fill={node.color} fillOpacity={online ? 0.25 : 0.08} stroke={online ? '#22c55e' : '#64748b'} strokeWidth={2} />
              <circle cx={`${node.x}%`} cy={`${node.y}%`} r={4} fill={online ? '#22c55e' : '#475569'}>
                {online && <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite" />}
              </circle>
              <text x={`${node.x}%`} y={`${node.y + 6}%`} textAnchor="middle" fill="#94a3b8" fontSize="7" fontFamily="monospace">{node.label}</text>
            </g>
          );
        })}

        {/* Threat dots from real alert source IPs */}
        {uniqueIps.map((alert) => {
          const point = projectIp(alert.source_ip);
          return (
            <g key={alert.source_ip}>
              <circle cx={`${point.x}%`} cy={`${point.y}%`} r={8} fill="#ef4444" fillOpacity={0.3} stroke="#ef4444" strokeWidth={1.5}>
                <animate attributeName="r" values="8;12;8" dur="2s" repeatCount="indefinite" />
                <animate attributeName="fillOpacity" values="0.3;0.6;0.3" dur="2s" repeatCount="indefinite" />
              </circle>
              <circle cx={`${point.x}%`} cy={`${point.y}%`} r={3} fill="#ef4444" />
            </g>
          );
        })}

        {!loading && uniqueIps.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-600">
            <Activity className="w-6 h-6 mb-1 opacity-40" />
            <span className="text-[10px] font-mono">MONITORING — AWAITING THREATS</span>
          </div>
        )}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="skeleton h-40 w-72 rounded-lg" />
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 px-3 pb-2">
        <span className="flex items-center gap-1 text-[9px] font-mono text-slate-500">
          <span className="w-2 h-2 rounded-full bg-green-500" /> NODE ONLINE
        </span>
        <span className="flex items-center gap-1 text-[9px] font-mono text-slate-500">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" /> THREAT IP
        </span>
        <div className="flex-1" />
        <span className="text-[9px] font-mono text-slate-500">🟢 LIVE</span>
      </div>
    </div>
  );
}