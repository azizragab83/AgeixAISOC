import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Check, X, ShieldAlert, Clock, Sparkles, Zap, Brain, Loader2, AlertTriangle,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { showToast } from '../utils/toast';

const MAX_EVALUATION_ATTEMPTS = 5;

const RISK_STYLES = {
  critical: { ring: '#ef4444', text: 'text-red-500', chip: 'bg-red-500/10 border-red-500/30 text-red-400' },
  high: { ring: '#f97316', text: 'text-orange-400', chip: 'bg-orange-500/10 border-orange-500/30 text-orange-400' },
  medium: { ring: '#eab308', text: 'text-yellow-400', chip: 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400' },
  low: { ring: '#22c55e', text: 'text-green-400', chip: 'bg-green-500/10 border-green-500/30 text-green-400' },
  informational: { ring: '#22c55e', text: 'text-green-400', chip: 'bg-green-500/10 border-green-500/30 text-green-400' },
  unknown: { ring: '#64748b', text: 'text-slate-400', chip: 'bg-slate-500/10 border-slate-500/30 text-slate-400' },
};

function RiskRing({ score, ringColor }) {
  const clamped = Math.max(0, Math.min(100, Number(score) || 0));
  const r = 16;
  const c = 2 * Math.PI * r;
  const offset = c - (clamped / 100) * c;

  return (
    <div className="relative w-11 h-11 shrink-0">
      <svg viewBox="0 0 40 40" className="w-11 h-11 -rotate-90">
        <circle cx="20" cy="20" r={r} fill="none" strokeWidth="3.5" className="stroke-slate-800" />
        <motion.circle
          cx="20" cy="20" r={r} fill="none" stroke={ringColor} strokeWidth="3.5"
          strokeLinecap="round" strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[10px] font-mono font-bold text-slate-100">
        {clamped}
      </span>
    </div>
  );
}

/** Full-card overlay shown while the backend processes the analyst decision. */
function DecisionOverlay({ phase }) {
  const config = phase === 'learning'
    ? { text: '🧠 AI is learning from your feedback...', color: 'text-cyan-300', border: 'border-cyan-500/40', bg: 'bg-cyan-500/10' }
    : { text: 'Executing SOAR...', color: 'text-green-300', border: 'border-green-500/40', bg: 'bg-green-500/10' };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className={`absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 rounded-xl backdrop-blur-[2px] ${config.bg}`}
    >
      <div className={`absolute inset-0 rounded-xl border ${config.border} pointer-events-none`} />
      <Loader2 className={`w-5 h-5 animate-spin ${config.color}`} />
      <span className={`text-[10px] font-mono font-bold ${config.color} px-2 text-center`}>
        {config.text}
      </span>
    </motion.div>
  );
}

export default function PendingHITLCard({ alert, onDecision, disabled }) {
  const { t } = useLanguage();
  const [addToRag, setAddToRag] = useState(true);
  const [phase, setPhase] = useState('idle'); // idle | learning | executing | learned | executed
  const risk = RISK_STYLES[alert.risk_level] || RISK_STYLES.unknown;
  const mitreId = alert.mitre_id || 'N/A';
  const threatName = alert.threat_type && alert.threat_type !== 'unknown'
    ? alert.threat_type
    : (alert.mitre_technique || 'Unknown threat');
  const summary = alert.summary || 'No analysis summary.';
  const decisionId = alert.decision_id || alert.alert_id || '';
  const gapClosed = alert.gap_detected && alert.gap_closed;
  const learnedRule = alert.learned_rule || (alert.rule_id && alert.rule_id >= 100000);

  // ── Master Brain Cognitive Synthesis fields ──
  const threatStory = alert.correlated_threat_narrative || '';
  const predictedMove = alert.predicted_next_move || '';
  const evaluationAttempt = Math.min(
    MAX_EVALUATION_ATTEMPTS,
    Math.max(1, Number(alert.evaluation_attempt) || 1),
  );

  const busy = phase === 'learning' || phase === 'executing';
  const resolved = phase === 'learned' || phase === 'executed';

  const handleDecision = async (action) => {
    if (busy || resolved || disabled) return;
    setPhase(action === 'rejected' ? 'learning' : 'executing');
    try {
      const result = await onDecision(alert, action, addToRag);
      if (action === 'rejected') {
        // Natural Adaptive Learning: card fades out as "Closed (False Positive)"
        setPhase('learned');
        showToast('Feedback recorded. AI will auto-suppress similar alerts.', 'success');
      } else {
        setPhase('executed');
        showToast('SOAR actions dispatched.', 'info');
      }
      return result;
    } catch {
      setPhase('idle');
      showToast('Decision failed. Try again.', 'error');
      return undefined;
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.96, y: 8 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{
        opacity: 0,
        scale: 0.92,
        x: 40,
        filter: 'blur(4px)',
        transition: { duration: 0.35, ease: 'easeInOut' },
      }}
      className={`relative rounded-xl border p-3 transition-colors overflow-hidden ${
        resolved
          ? 'border-slate-700/60 bg-gray-900/60'
          : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-gray-900 hover:border-cyan-500/30'
      }`}
    >
      {/* Decision processing overlay */}
      <AnimatePresence>
        {busy && <DecisionOverlay phase={phase} />}
      </AnimatePresence>

      <div className="flex items-start gap-3">
        <RiskRing score={alert.risk_score} ringColor={risk.ring} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold text-slate-800 dark:text-slate-100 truncate">{threatName}</span>
            <span className={`shrink-0 px-1.5 py-0.5 rounded border text-[9px] font-mono font-bold ${risk.chip}`}>
              {String(alert.risk_level || 'unknown').toUpperCase()}
            </span>
            {/* Feedback loop counter */}
            <span
              className="shrink-0 px-1.5 py-0.5 rounded bg-violet-500/10 border border-violet-500/30 text-violet-400 text-[9px] font-mono font-bold"
              title="Natural Adaptive Learning evaluation attempt (max 5 before auto-suppression)"
            >
              EVAL {evaluationAttempt}/{MAX_EVALUATION_ATTEMPTS}
            </span>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap mb-1.5">
            <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-[9px] font-mono font-bold">
              {mitreId}
            </span>
            {gapClosed && (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-green-500/10 border border-green-500/30 text-green-400 text-[9px] font-mono font-bold" title="Coverage gap detected and auto-closed with a new rule">
                <Zap className="w-2.5 h-2.5" /> GAP AUTO-CLOSED
              </span>
            )}
            {learnedRule && (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-violet-500/10 border border-violet-500/30 text-violet-400 text-[9px] font-mono font-bold" title="Detected by an AI-generated (learned) rule, not a manual one">
                <Sparkles className="w-2.5 h-2.5" /> AI-LEARNED RULE
              </span>
            )}
            <span className="flex items-center gap-1 text-[9px] font-mono text-slate-500">
              <Clock className="w-2.5 h-2.5" />
              {alert.timestamp ? new Date(alert.timestamp).toLocaleTimeString('en-US', { hour12: false }) : '--:--:--'}
            </span>
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-snug line-clamp-2 mb-1">
            {summary}
          </p>
          <p className="text-[9px] font-mono text-slate-400 dark:text-slate-600 truncate" title={decisionId}>
            <ShieldAlert className="w-2.5 h-2.5 inline mr-1" />
            {decisionId}
          </p>
        </div>
      </div>

      {/* ── Master Brain: Threat Story (correlated narrative) ── */}
      <AnimatePresence>
        {threatStory && !resolved && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="mt-2 rounded-lg border border-cyan-500/30 bg-cyan-500/5 overflow-hidden"
          >
            <div className="flex items-center gap-1.5 px-2 pt-1.5">
              <Brain className="w-3 h-3 text-cyan-400" />
              <span className="text-[9px] font-mono font-bold text-cyan-400 tracking-wider">
                THREAT STORY
              </span>
              <span className="text-[8px] font-mono text-cyan-500/50">MASTER BRAIN SYNTHESIS</span>
            </div>
            <p className="px-2 pb-1.5 pt-0.5 text-[10px] leading-snug text-cyan-100/80 dark:text-cyan-200/70">
              {threatStory}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Master Brain: Predicted Next Move ── */}
      <AnimatePresence>
        {predictedMove && !resolved && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, delay: 0.05 }}
            className="mt-1.5 rounded-lg border border-amber-500/30 bg-amber-500/5 px-2 py-1.5 flex items-start gap-1.5 overflow-hidden"
          >
            <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0 mt-0.5" />
            <p className="text-[10px] leading-snug text-amber-200/80 dark:text-amber-300/70">
              <span className="font-mono font-bold text-amber-400">⚠️ AI PREDICTS NEXT MOVE:</span>{' '}
              {predictedMove}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Resolution status (shown briefly before card fades out) ── */}
      <AnimatePresence>
        {resolved && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={`mt-2 rounded-lg border px-2 py-1.5 flex items-center gap-1.5 ${
              phase === 'learned'
                ? 'border-cyan-500/40 bg-cyan-500/10'
                : 'border-green-500/40 bg-green-500/10'
            }`}
          >
            {phase === 'learned' ? (
              <>
                <Brain className="w-3 h-3 text-cyan-400" />
                <span className="text-[10px] font-mono font-bold text-cyan-300">
                  Closed (False Positive) — AI memory updated
                </span>
              </>
            ) : (
              <>
                <Check className="w-3 h-3 text-green-400" />
                <span className="text-[10px] font-mono font-bold text-green-300">
                  Approved — SOAR executing
                </span>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Action buttons ── */}
      <div className="flex gap-2 mt-3 items-center">
        <motion.button
          whileTap={{ scale: 0.96 }}
          onClick={() => handleDecision('approved')}
          disabled={disabled || busy || resolved}
          className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg bg-green-600/15 border border-green-500/40 text-green-400 text-[10px] font-bold hover:bg-green-600/25 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Check className="w-3 h-3" /> {t('approve')}
        </motion.button>
        <motion.button
          whileTap={{ scale: 0.96 }}
          onClick={() => handleDecision('rejected')}
          disabled={disabled || busy || resolved}
          className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg bg-red-600/15 border border-red-500/40 text-red-500 text-[10px] font-bold hover:bg-red-600/25 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <X className="w-3 h-3" /> {t('reject')}
        </motion.button>
      </div>
      <label className="flex items-center gap-1.5 mt-2 text-[9px] font-mono text-slate-500 dark:text-slate-500 cursor-pointer select-none" title="Save this decision (and generated rule) to the RAG knowledge base for future threat correlation">
        <input
          type="checkbox"
          checked={addToRag}
          onChange={(e) => setAddToRag(e.target.checked)}
          disabled={busy || resolved}
          className="accent-cyan-500 w-3 h-3"
        />
        🧠 Save to RAG knowledge base
      </label>
    </motion.div>
  );
}