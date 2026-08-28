import { useState, useEffect } from 'react';
import { Shield, Globe, AlertTriangle, Search, ExternalLink, Hash, Fingerprint } from 'lucide-react';
import { tiApi } from '../api';

export default function TIView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTech, setSearchTech] = useState('');

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await tiApi.getCoverage();
        setData(res.data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetch();
    const interval = setInterval(fetch, 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-slate-400 text-sm">Loading threat intelligence...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2">
        <AlertTriangle className="w-6 h-6 text-red-400" />
        <div className="text-slate-400 text-sm">Failed to load coverage data</div>
      </div>
    );
  }

  const { techniques, coverage_pct, covered, total, observed, iocs } = data;

  const filtered = techniques.filter((t) =>
    t.id.toLowerCase().includes(searchTech.toLowerCase()) ||
    t.name.toLowerCase().includes(searchTech.toLowerCase()) ||
    t.tactic.toLowerCase().includes(searchTech.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-y-auto">
      <h1 className="text-lg font-bold text-white">Threat Intelligence</h1>

      <div className="grid grid-cols-4 gap-3">
        <div className="soc-card"><Fingerprint className="w-4 h-4 text-purple-400 mb-1" /><div className="text-xs text-slate-500">MITRE Coverage</div><div className="text-2xl font-bold text-white">{coverage_pct}%</div><div className="text-xs text-slate-500">{covered}/{total} techniques</div></div>
        <div className="soc-card"><Hash className="w-4 h-4 text-cyan-400 mb-1" /><div className="text-xs text-slate-500">Techniques Observed</div><div className="text-2xl font-bold text-white">{observed.length}</div><div className="text-xs text-slate-500">in active alerts</div></div>
        <div className="soc-card"><Globe className="w-4 h-4 text-red-400 mb-1" /><div className="text-xs text-slate-500">IOCs Collected</div><div className="text-2xl font-bold text-white">{iocs.length}</div><div className="text-xs text-slate-500">unique IPs</div></div>
        <div className="soc-card"><AlertTriangle className="w-4 h-4 text-amber-400 mb-1" /><div className="text-xs text-slate-500">Detection Gaps</div><div className="text-2xl font-bold text-white">{total - covered}</div><div className="text-xs text-slate-500">uncovered techniques</div></div>
      </div>

      <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-3 py-2 max-w-sm">
        <Search className="w-4 h-4 text-slate-500" />
        <input className="bg-transparent text-sm text-slate-300 outline-none w-full" placeholder="Search technique, ID, or tactic..." value={searchTech} onChange={(e) => setSearchTech(e.target.value)} />
      </div>

      <div className="grid grid-cols-5 gap-2 text-xs font-bold text-slate-500 uppercase px-2 pb-1 border-b border-slate-800">
        <span>ID</span><span className="col-span-2">Technique</span><span>Tactic</span><span>Coverage</span>
      </div>
      <div className="space-y-1 flex-1 overflow-y-auto">
        {filtered.map((t) => {
          const color = t.coverage >= 70 ? 'bg-green-500' : t.coverage >= 50 ? 'bg-amber-500' : 'bg-red-500';
          return (
            <div key={t.id} className={`grid grid-cols-5 gap-2 items-center px-2 py-2 rounded-lg text-sm ${t.observed ? 'bg-slate-800/50' : 'opacity-60'}`}>
              <span className="font-mono text-cyan-400">{t.id}</span>
              <span className="col-span-2 text-white">{t.name}</span>
              <span className="text-slate-400">{t.tactic}</span>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${t.coverage}%` }} />
                </div>
                <span className="text-xs font-mono text-slate-400 w-8 text-right">{t.coverage}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
