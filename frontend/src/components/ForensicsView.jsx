import { useState } from 'react';
import { getForensics } from '../api';
import { Search, Clock, AlertTriangle, ArrowRight, FileText, Download } from 'lucide-react';

export default function ForensicsView() {
  const [incidentId, setIncidentId] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async () => {
    if (!incidentId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getForensics(incidentId.trim());
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-y-auto">
      <h1 className="text-lg font-bold text-white">Forensics Timeline</h1>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-3 py-2 flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500" />
          <input
            className="bg-transparent text-sm text-slate-300 outline-none w-full"
            placeholder="Incident ID (e.g. ALERT-XXXX or DEC-XXXX)"
            value={incidentId}
            onChange={(e) => setIncidentId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
        </div>
        <button
          onClick={handleSearch}
          disabled={loading || !incidentId.trim()}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-cyan-600/20 border border-cyan-500/30 text-cyan-400 text-sm font-medium hover:bg-cyan-600/30 transition-all disabled:opacity-50"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-4 gap-3">
            <div className="soc-card"><span className="text-xs text-slate-500">Threat Type</span><div className="text-sm font-bold text-white mt-1">{data.threat_type}</div></div>
            <div className="soc-card"><span className="text-xs text-slate-500">Risk Score</span><div className="text-sm font-bold text-white mt-1">{data.risk_score}/100</div></div>
            <div className="soc-card"><span className="text-xs text-slate-500">Root Cause</span><div className="text-sm font-bold text-white mt-1 truncate">{data.root_cause || 'N/A'}</div></div>
            <div className="soc-card"><span className="text-xs text-slate-500">Affected Systems</span><div className="text-sm font-bold text-white mt-1">{(data.affected_systems || []).length}</div></div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2"><Clock className="w-4 h-4 text-cyan-400" />Timeline</h3>
              <div className="space-y-0">
                {(data.timeline || []).map((evt, i) => (
                  <div key={i} className="flex items-start gap-3 pl-4 pb-3 relative">
                    {i < (data.timeline || []).length - 1 && <div className="absolute left-[7px] top-3 bottom-0 w-px bg-slate-700" />}
                    <div className="w-3 h-3 rounded-full bg-cyan-500/30 border-2 border-cyan-500 mt-0.5 shrink-0" />
                    <div>
                      <div className="text-xs text-slate-400 font-mono">{new Date(evt.timestamp).toLocaleString()}</div>
                      <div className="text-sm text-slate-200">{evt.event}</div>
                      {evt.evidence && <div className="text-xs text-slate-500 mt-0.5">{evt.evidence}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="space-y-3">
              <div className="soc-card">
                <h4 className="text-xs font-bold text-slate-400 uppercase mb-2">Containment Steps</h4>
                <div className="space-y-1">
                  {(data.containment_steps || []).map((s, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-slate-300"><ArrowRight className="w-3 h-3 text-green-400" />{s}</div>
                  ))}
                </div>
              </div>
              <div className="soc-card">
                <h4 className="text-xs font-bold text-slate-400 uppercase mb-2">Recovery Steps</h4>
                <div className="space-y-1">
                  {(data.recovery_steps || []).map((s, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-slate-300"><ArrowRight className="w-3 h-3 text-blue-400" />{s}</div>
                  ))}
                </div>
              </div>
              <div className="soc-card">
                <h4 className="text-xs font-bold text-slate-400 uppercase mb-2">Evidence Artifacts</h4>
                <div className="flex flex-wrap gap-2">
                  {(data.evidence_artifacts || []).map((a, i) => (
                    <span key={i} className="px-2 py-1 bg-slate-800 rounded text-xs font-mono text-slate-400">{a}</span>
                  ))}
                  {(!data.evidence_artifacts || data.evidence_artifacts.length === 0) && <span className="text-xs text-slate-500">No artifacts recorded</span>}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
