import { useState, useEffect } from 'react';
import { Wrench, ExternalLink, Globe, Search, Loader2, AlertTriangle, Terminal, Shield, Crosshair } from 'lucide-react';
import { api } from '../api';

const MITRE_TECHNIQUES = [
  { id: 'T1110', name: 'Brute Force' },
  { id: 'T1003', name: 'Credential Dumping' },
  { id: 'T1059', name: 'Command & Scripting' },
  { id: 'T1046', name: 'Network Service Discovery' },
  { id: 'T1048', name: 'Exfiltration' },
  { id: 'T1078', name: 'Valid Accounts' },
  { id: 'T1021', name: 'Remote Services' },
  { id: 'T1566', name: 'Phishing' },
  { id: 'T1190', name: 'Exploit Public App' },
  { id: 'T1547', name: 'Boot/Logon Autostart' },
  { id: 'T1055', name: 'Process Injection' },
];

export default function ToolkitView() {
  const [selectedTechnique, setSelectedTechnique] = useState('T1110');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.get(`/api/toolkit/recommend/${selectedTechnique}`);
        setData(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
        setData(null);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [selectedTechnique]);

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-y-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-white flex items-center gap-2">
          <Wrench className="w-5 h-5 text-cyan-400" />
          Cyber Toolkit Intelligence
        </h1>
        <div className="flex items-center gap-2">
          <Crosshair className="w-4 h-4 text-slate-500" />
          <select
            value={selectedTechnique}
            onChange={(e) => setSelectedTechnique(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-300 min-w-[200px]"
          >
            {MITRE_TECHNIQUES.map((t) => (
              <option key={t.id} value={t.id}>{t.id} — {t.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Selected Technique Tools */}
      <div className="soc-card">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold text-white">
            {data ? `${data.mitre_id} — ${data.technique}` : selectedTechnique}
          </h2>
          {data && <span className="text-xs text-slate-500 ml-auto">{data.tool_count} tools</span>}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-32 text-slate-500 gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading tools...
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-32 text-red-400 gap-2">
            <AlertTriangle className="w-4 h-4" />
            {error}
          </div>
        ) : data ? (
          <div className="grid grid-cols-2 gap-3">
            {data.tools.map((tool, idx) => (
              <a
                key={idx}
                href={tool.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 hover:bg-slate-800 hover:border-cyan-500/30 transition-all group"
              >
                <div className="p-2 rounded-lg bg-cyan-600/10 shrink-0">
                  <Terminal className="w-4 h-4 text-cyan-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white group-hover:text-cyan-400 transition-colors">{tool.name}</span>
                    <ExternalLink className="w-3 h-3 text-slate-500 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400">{tool.category}</span>
                    <span className="text-xs text-slate-600">{tool.os}</span>
                  </div>
                </div>
              </a>
            ))}
          </div>
        ) : null}
      </div>

      {/* OSINT & Recon Tools */}
      <div className="soc-card">
        <div className="flex items-center gap-2 mb-4">
          <Globe className="w-5 h-5 text-green-400" />
          <h2 className="text-sm font-bold text-white">OSINT & Reconnaissance Tools</h2>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {data?.osint_tools?.map((tool, idx) => (
            <a
              key={idx}
              href={tool.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 hover:bg-slate-800 hover:border-green-500/30 transition-all group"
            >
              <div className="p-2 rounded-lg bg-green-600/10 shrink-0">
                <Search className="w-4 h-4 text-green-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-white group-hover:text-green-400 transition-colors">{tool.name}</span>
                  <ExternalLink className="w-3 h-3 text-slate-500 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400">{tool.category}</span>
                  <span className="text-xs text-slate-600">{tool.os}</span>
                </div>
              </div>
            </a>
          ))}
        </div>
      </div>

      {/* Quick Reference */}
      <div className="soc-card">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-bold text-white">All Available Techniques</h2>
        </div>
        <div className="grid grid-cols-4 gap-2">
          {MITRE_TECHNIQUES.map((t) => (
            <button
              key={t.id}
              onClick={() => setSelectedTechnique(t.id)}
              className={`text-left px-3 py-2 rounded-lg text-xs transition-all ${
                selectedTechnique === t.id
                  ? 'bg-cyan-600/20 border border-cyan-500/30 text-cyan-400'
                  : 'bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:bg-slate-800 hover:text-slate-300'
              }`}
            >
              <span className="font-mono block">{t.id}</span>
              <span className="text-slate-500 text-[10px]">{t.name}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}