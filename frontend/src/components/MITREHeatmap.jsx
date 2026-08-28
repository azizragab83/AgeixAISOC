import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Crosshair } from 'lucide-react';
import { tiApi } from '../api';
import { useLanguage } from '../context/LanguageContext';

function TechniqueCell({ technique, delay }) {
  const [hovered, setHovered] = useState(false);
  const coverage = technique.coverage;
  const covered = coverage === true || (typeof coverage === 'number' && coverage > 0) || (typeof coverage === 'string' && coverage.toLowerCase() !== '0' && coverage.toLowerCase() !== 'false');
  const id = technique.id || technique.technique_id;
  const name = technique.name || technique.technique_name || id;

  return (
    <div
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.7 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: delay * 0.02 }}
        className={`h-9 rounded-md flex items-center justify-center cursor-crosshair border transition-all ${
          covered
            ? 'bg-green-500/15 border-green-500/40 text-green-400'
            : 'bg-red-500/10 border-red-500/40 text-red-500/80'
        }`}
      >
        <span className="text-[9px] font-mono font-bold">{id || technique.id}</span>
      </motion.div>

      {hovered && (
        <div className="absolute z-40 bottom-full left-1/2 -translate-x-1/2 mb-2 w-44 rounded-lg border border-slate-700 bg-slate-900 p-2 shadow-2xl">
          <div className="text-[10px] font-mono font-bold text-cyan-400">{technique.id}</div>
          <div className="text-[10px] text-slate-200 font-medium leading-snug">{technique.name}</div>
          <div className="text-[9px] text-slate-500 mt-1">{technique.tactic}</div>
          <div className={`text-[9px] font-mono font-bold mt-1 ${covered ? 'text-green-400' : 'text-red-500'}`}>
            {covered ? 'COVERED' : 'DETECTION GAP'}
          </div>
        </div>
      )}
    </div>
  );
}

export default function MITREHeatmap() {
  const { t } = useLanguage();
  const [coverage, setCoverage] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchCoverage = useCallback(async () => {
    try {
      const res = await tiApi.getCoverage();
      setCoverage(res.data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCoverage();
    const interval = setInterval(fetchCoverage, 30000);
    return () => clearInterval(interval);
  }, [fetchCoverage]);

  const techniques = coverage?.techniques || [];
  const pct = coverage?.coverage_pct ?? 0;

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 shrink-0">
        <Crosshair className="w-3.5 h-3.5 text-cyan-400" />
        <span className="text-xs font-bold text-slate-700 dark:text-slate-200">{t('mitre_coverage')}</span>
        <div className="flex-1" />
        {!loading && coverage && (
          <span className="text-[10px] font-mono font-bold text-cyan-400">{pct}%</span>
        )}
      </div>

      <div className="p-2">
        {loading && !coverage ? (
          <div className="grid grid-cols-10 gap-1.5">
            {Array.from({ length: 20 }).map((_, i) => (
              <div key={i} className="skeleton h-9 rounded-md" />
            ))}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-5 sm:grid-cols-10 gap-1.5">
              {techniques.map((tech, i) => (
                <TechniqueCell key={tech.id} technique={tech} delay={i} />
              ))}
            </div>
            <div className="flex items-center gap-3 mt-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              <span className="flex items-center gap-1 text-[9px] font-mono text-slate-500">
                <span className="w-2 h-2 rounded-sm bg-green-500/60" /> COVERED
              </span>
              <span className="flex items-center gap-1 text-[9px] font-mono text-slate-500">
                <span className="w-2 h-2 rounded-sm bg-red-500/60" /> GAP
              </span>
              <div className="flex-1" />
              <span className="text-[9px] font-mono text-slate-500">
                {coverage?.covered}/{coverage?.total} TECHNIQUES · {coverage?.iocs?.length || 0} IOCS
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
