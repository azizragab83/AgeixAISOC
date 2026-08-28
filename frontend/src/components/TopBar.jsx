import { useState, useEffect, useCallback } from 'react';
import { Shield, Skull, Loader2, Globe, Sun, Moon, Wifi, WifiOff, Fingerprint, Bot } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { triggerAttack, toggleAutoAttack } from '../api';

const ATTACK_TYPES = [
  { id: 'port_scan', label: 'Port Scan', icon: '🔎' },
  { id: 'ssh_brute_force', label: 'SSH Brute Force', icon: '🔑' },
  { id: 'web_scan', label: 'Web Scan', icon: '🌐' },
  { id: 'smb_enum', label: 'SMB Enumeration', icon: '🗂️' },
  { id: 'nmap_windows', label: 'Windows Recon (Nmap)', icon: '🪟' },
  { id: 'full_scan', label: 'Full Vulnerability Scan', icon: '💥' },
];

const ATTACK_TARGETS = [
  { id: 'win10', label: 'Win10 Victim' },
  { id: 'metasploitable', label: 'Metasploitable2' },
  { id: 'wazuh', label: 'Wazuh SIEM' },
  { id: 'kali', label: 'Kali' },
  { id: 'win_server', label: 'Win Server DC' },
];

const DEFCON_LEVELS = [
  { level: 1, label: 'DEFCON 1', name: 'Severe', color: 'text-red-500', bg: 'bg-red-500/10 border-red-500/40', glow: 'shadow-[0_0_12px_rgba(239,68,68,0.4)]', min: 6 },
  { level: 2, label: 'DEFCON 2', name: 'High', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30', glow: 'shadow-[0_0_10px_rgba(239,68,68,0.3)]', min: 4 },
  { level: 3, label: 'DEFCON 3', name: 'Elevated', color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30', glow: 'shadow-[0_0_10px_rgba(249,115,22,0.3)]', min: 2 },
  { level: 4, label: 'DEFCON 4', name: 'Guarded', color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30', glow: 'shadow-[0_0_8px_rgba(234,179,8,0.25)]', min: 1 },
  { level: 5, label: 'DEFCON 5', name: 'Normal', color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30', glow: 'shadow-[0_0_8px_rgba(34,197,94,0.25)]', min: 0 },
];

function getDefcon(pendingCount) {
  return DEFCON_LEVELS.find(d => pendingCount >= d.min) || DEFCON_LEVELS[DEFCON_LEVELS.length - 1];
}

export default function TopBar() {
  const [backendHealthy, setBackendHealthy] = useState(false);
  const [attacking, setAttacking] = useState(false);
  const [attackType, setAttackType] = useState('nmap_windows');
  const [target, setTarget] = useState('win10');
  const [autoAttack, setAutoAttack] = useState(false);
  const [autoBusy, setAutoBusy] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [utcNow, setUtcNow] = useState(() => new Date());
  const { lang, toggleLang, t } = useLanguage();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const timer = setInterval(() => setUtcNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/health');
      setBackendHealthy(res.ok);
    } catch {
      setBackendHealthy(false);
    }
  }, []);

  const checkPending = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/metrics');
      if (res.ok) {
        const data = await res.json();
        setPendingCount(data.pending_decisions ?? 0);
      }
    } catch {}
  }, []);

  useEffect(() => {
    checkHealth();
    checkPending();
    const interval = setInterval(() => {
      checkHealth();
      checkPending();
    }, 15000);
    return () => clearInterval(interval);
  }, [checkHealth, checkPending]);

  const defcon = getDefcon(pendingCount);

  const handleLaunchAttack = async () => {
    setAttacking(true);
    try {
      await triggerAttack(attackType);
    } catch {}
    setTimeout(() => setAttacking(false), 2000);
  };

  const handleAutoToggle = async () => {
    setAutoBusy(true);
    try {
      const res = await toggleAutoAttack(!autoAttack);
      setAutoAttack(res.data.enabled);
    } catch {}
    setAutoBusy(false);
  };

  const utcTime = utcNow.toISOString().slice(11, 19);
  const utcDate = utcNow.toISOString().slice(0, 10);

  return (
    <header className="sticky top-0 z-40 h-14 shrink-0 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-950/85 backdrop-blur-md flex items-center justify-between px-3 lg:px-4 gap-2 transition-colors duration-300">
      {/* Left: Logo + DEFCON */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="relative w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/25 shrink-0">
          <Shield className="w-5 h-5 text-white" />
          <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-green-400 border border-slate-950" />
        </div>
        <div className="hidden md:block min-w-0">
          <h1 className="text-sm font-bold tracking-tight text-slate-900 dark:text-white leading-tight">AgeixAISOC</h1>
          <p className="text-[9px] text-cyan-600 dark:text-cyan-400 font-mono leading-tight opacity-90">{t('command_center')}</p>
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={defcon.level}
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.2 }}
            className={`flex items-center gap-2 px-2.5 py-1 rounded-lg border ${defcon.bg} ${defcon.glow} shrink-0`}
            title={`${defcon.label} — ${defcon.name}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${defcon.color.replace('text-', 'bg-')} animate-pulse`} />
            <span className={`text-[10px] font-mono font-bold ${defcon.color}`}>{defcon.label}</span>
            <span className={`text-[10px] hidden sm:inline ${defcon.color}`}>· {defcon.name}</span>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Center: UTC Clock */}
      <div className="hidden lg:flex items-center gap-2 px-4 py-1 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
        <span className="text-[10px] font-mono font-bold text-cyan-600 dark:text-cyan-400">UTC</span>
        <span className="text-sm font-mono font-bold tabular-nums text-slate-800 dark:text-slate-100">{utcTime}</span>
        <span className="text-[9px] font-mono text-slate-500 dark:text-slate-500 tabular-nums">{utcDate}</span>
      </div>

      {/* Right: Status + Actions */}
      <div className="flex items-center gap-1.5 lg:gap-2 shrink-0">
        {/* Connection Status */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border transition-all ${
            backendHealthy
              ? 'bg-green-500/5 border-green-500/30'
              : 'bg-red-500/5 border-red-500/30'
          }`}
          title={backendHealthy ? 'Backend Online' : 'Backend Offline'}
        >
          {backendHealthy ? (
            <Wifi className="w-3.5 h-3.5 text-green-400" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-red-500" />
          )}
          <span className={`w-1.5 h-1.5 rounded-full ${backendHealthy ? 'bg-green-400 shadow-[0_0_8px_rgba(34,197,94,0.8)]' : 'bg-red-500 animate-pulse'}`} />
          <span className="hidden xl:inline text-[10px] font-mono font-bold text-slate-600 dark:text-slate-300">
            {backendHealthy ? 'API ONLINE' : 'API OFFLINE'}
          </span>
        </div>

        {/* Pending HITL badge */}
        <button
          onClick={() => (window.location.href = '/')}
          className={`relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border transition-all ${
            pendingCount > 0
              ? 'bg-red-500/10 border-red-500/40'
              : 'bg-slate-100 dark:bg-slate-900 border-slate-200 dark:border-slate-800'
          }`}
          title="Pending human decisions"
        >
          <Fingerprint className={`w-3.5 h-3.5 ${pendingCount > 0 ? 'text-red-500' : 'text-slate-500 dark:text-slate-400'}`} />
          <AnimatePresence>
            {pendingCount > 0 && (
              <motion.span
                key={pendingCount}
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.5, opacity: 0 }}
                className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center shadow-[0_0_10px_rgba(239,68,68,0.6)]"
              >
                {pendingCount}
              </motion.span>
            )}
          </AnimatePresence>
          <span className="hidden xl:inline text-[10px] font-mono font-bold text-slate-600 dark:text-slate-300">{t('pending_hitl')}</span>
        </button>

        {/* Language Toggle */}
        <button
          onClick={toggleLang}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 text-[10px] font-bold hover:bg-slate-200 dark:hover:bg-slate-800 transition-all"
          title="Toggle Language"
        >
          <Globe className="w-3.5 h-3.5" />
          {lang === 'en' ? 'AR' : 'EN'}
        </button>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="flex items-center justify-center w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 transition-all"
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {theme === 'dark' ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5" />}
        </button>

        {/* Auto Red Team toggle */}
        <button
          onClick={handleAutoToggle}
          disabled={autoBusy}
          className={`relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border transition-all text-[10px] font-bold ${
            autoAttack
              ? 'bg-purple-500/15 border-purple-500/50 text-purple-400'
              : 'bg-slate-100 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800'
          }`}
          title="Auto red team: periodically launch randomized attacks every 60–120s to demo the full pipeline"
        >
          <Bot className={`w-3.5 h-3.5 ${autoAttack ? 'animate-pulse' : ''}`} />
          <span className="hidden xl:inline">AUTO RED TEAM</span>
          {autoAttack && (
            <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-purple-400" />
            </span>
          )}
        </button>

        {/* Attack type selector */}
        <select
          value={attackType}
          onChange={(e) => setAttackType(e.target.value)}
          className="hidden lg:block px-2 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-[10px] font-mono text-slate-700 dark:text-slate-300 focus:outline-none focus:border-red-500/50"
          title="Attack type"
        >
          {ATTACK_TYPES.map(a => (
            <option key={a.id} value={a.id}>{a.icon} {a.label}</option>
          ))}
        </select>

        {/* Target selector */}
        <select
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          className="hidden xl:block px-2 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-[10px] font-mono text-slate-700 dark:text-slate-300 focus:outline-none focus:border-red-500/50"
          title="Target host"
        >
          {ATTACK_TARGETS.map(t => (
            <option key={t.id} value={t.id}>{t.label}</option>
          ))}
        </select>

        {/* Launch Attack */}
        <button
          onClick={handleLaunchAttack}
          disabled={attacking}
          className="relative flex items-center gap-1.5 px-3 lg:px-4 py-1.5 rounded-lg bg-red-600 border border-red-500/50 text-white text-[11px] font-bold hover:bg-red-500 transition-all disabled:opacity-60 disabled:cursor-not-allowed overflow-hidden"
          title={`Launch ${ATTACK_TYPES.find(a => a.id === attackType)?.label || 'attack'} against ${ATTACK_TARGETS.find(t => t.id === target)?.label || 'target'}`}
        >
          {attacking ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span className="animate-pulse">{t('launch_attack')}...</span>
            </>
          ) : (
            <>
              <Skull className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{t('launch_attack')}</span>
              <span className="absolute inset-0 bg-red-400/30 animate-pulse pointer-events-none" />
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-300 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-red-300" />
              </span>
            </>
          )}
        </button>
      </div>
    </header>
  );
}
