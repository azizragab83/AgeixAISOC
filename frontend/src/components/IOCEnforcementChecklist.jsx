import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, Loader2, AlertTriangle } from 'lucide-react';
import { subscribeIocEvents } from '../utils/iocEvents';

/**
 * Live sub-status line shown on the HITL decision card after approval:
 *   "Blocking on FortiGate... ✅ → Pushing to EDR... ✅ → IOC recorded ✅"
 *
 * Driven by `ioc_progress` / `ioc_enforced` WebSocket events, matched by
 * decision_id. Renders nothing until the first progress event arrives.
 */
export default function IOCEnforcementChecklist({ decisionId }) {
  const [steps, setSteps] = useState({});

  useEffect(() => {
    if (!decisionId) return undefined;
    return subscribeIocEvents((event) => {
      if (event.decision_id && event.decision_id !== decisionId) return;
      if (event.type === 'ioc_progress') {
        setSteps((prev) => ({
          ...prev,
          [event.step]: { status: event.status, message: event.message },
        }));
      } else if (event.type === 'ioc_enforced') {
        setSteps((prev) => ({
          ...prev,
          fortigate: { status: 'success', message: 'Blocking on FortiGate... ✅' },
          edr: { status: 'success', message: 'Pushing to EDR... ✅' },
          recorded: { status: 'success', message: 'IOC recorded ✅' },
        }));
      }
    });
  }, [decisionId]);

  const entries = Object.entries(steps);
  if (!entries.length) return null;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.25 }}
      className="mt-2 rounded-lg border border-cyan-500/30 bg-cyan-500/5 p-2 overflow-hidden"
    >
      <div className="text-[9px] font-mono font-bold text-cyan-400 tracking-wider mb-1">
        IOC ENFORCEMENT PIPELINE
      </div>
      <div className="space-y-1">
        <AnimatePresence>
          {entries.map(([step, info]) => (
            <motion.div
              key={step}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-1.5 text-[10px] font-mono"
            >
              {info.status === 'success' ? (
                <Check className="w-3 h-3 text-green-400 shrink-0" />
              ) : info.status === 'failed' ? (
                <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0" />
              ) : (
                <Loader2 className="w-3 h-3 text-cyan-400 animate-spin shrink-0" />
              )}
              <span className={info.status === 'success' ? 'text-green-300' : 'text-cyan-300'}>
                {info.message || step}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}