import { createContext, useContext, useState, useCallback, useEffect } from 'react';

const translations = {
  en: {
    dashboard: 'Command Center',
    live_feed: 'Live Feed',
    pending_decisions: 'Pending Decisions',
    lab_health: 'Lab Health',
    launch_attack: 'Launch Attack',
    approve: 'Approve',
    reject: 'Reject',
    threat_map: 'Threat Map',
    audit_trail: 'Audit Trail',
    detection_engineering: 'Detection Engineering',
    ai_engineering: 'AI Engineering',
    devops_resources: 'DevOps Resources',
    active_alerts: 'Active Alerts',
    critical_high: 'Critical/High',
    pending_hitl: 'Pending HITL',
    soar_actions: 'SOAR Actions',
    agents_online: 'Agents Online',
    system_status: 'System Status',
    online: 'Online',
    offline: 'Offline',
    searching: 'Searching...',
    no_alerts: 'No active threats detected',
    all_clear: 'All clear — monitoring for suspicious activity',
    terminal: 'Live Agent Terminal',
    mitre_coverage: 'MITRE ATT&CK Coverage',
    pipeline: 'AI Pipeline',
    attack_simulation: 'Attack Simulation',
    command_center: 'Tactical SOC Command',
    nav_command_center: 'Command Center',
    nav_analyst_feed: 'Analyst Feed',
    nav_executive: 'Executive KPIs',
    nav_forensics: 'Forensics',
    nav_threat_intel: 'Threat Intel',
    nav_toolkit: 'Toolkit',
    nav_detection_eng: 'Detection Engineering',
    nav_ai_hub: 'AI Hub',
    nav_audit_trail: 'Audit Trail',
    kpi_active_threats: 'Active Threats',
    kpi_threats_blocked: 'Threats Blocked',
    kpi_pending_hitl: 'Pending HITL',
    kpi_agents_active: 'AI Agents Active',
    no_pending_decisions: 'No decisions pending human review',
  },
  ar: {
    dashboard: 'مركز القيادة',
    live_feed: 'البث المباشر',
    pending_decisions: 'القرارات المعلقة',
    lab_health: 'صحة المختبر',
    launch_attack: 'شن هجوم',
    approve: 'موافقة',
    reject: 'رفض',
    threat_map: 'خريطة التهديدات',
    audit_trail: 'سجل التدقيق',
    detection_engineering: 'هندسة الكشف',
    ai_engineering: 'هندسة الذكاء الاصطناعي',
    devops_resources: 'موارد ديف أوبس',
    active_alerts: 'التنبيهات النشطة',
    critical_high: 'حرجة/عالية',
    pending_hitl: 'معلق للبشر',
    soar_actions: 'إجراءات SOAR',
    agents_online: 'العوامل المتصلة',
    system_status: 'حالة النظام',
    online: 'متصل',
    offline: 'غير متصل',
    searching: 'جارٍ البحث...',
    no_alerts: 'لا توجد تهديدات نشطة',
    all_clear: 'كل شيء آمن — مراقبة النشاط المشبوه',
    terminal: 'محطة العامل المباشر',
    mitre_coverage: 'تغطية MITRE ATT&CK',
    pipeline: 'خط أنابيب الذكاء الاصطناعي',
    attack_simulation: 'محاكاة الهجوم',
    command_center: 'قيادة SOC التكتيكية',
    nav_command_center: 'مركز القيادة',
    nav_analyst_feed: 'تغذية المحلل',
    nav_executive: 'مؤشرات تنفيذية',
    nav_forensics: 'الطب الشرعي',
    nav_threat_intel: 'استخبارات التهديدات',
    nav_toolkit: 'أدوات',
    nav_detection_eng: 'هندسة الكشف',
    nav_ai_hub: 'مركز الذكاء الاصطناعي',
    nav_audit_trail: 'سجل التدقيق',
    kpi_active_threats: 'تهديدات نشطة',
    kpi_threats_blocked: 'تهديدات محجوبة',
    kpi_pending_hitl: 'معلق للبشر',
    kpi_agents_active: 'عوامل ذكاء نشطة',
    no_pending_decisions: 'لا توجد قرارات تنتظر المراجعة البشرية',
  },
};

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    try {
      return localStorage.getItem('ageix_lang') || 'en';
    } catch {
      return 'en';
    }
  });

  useEffect(() => {
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = lang;
    try {
      localStorage.setItem('ageix_lang', lang);
    } catch {}
  }, [lang]);

  const toggleLang = useCallback(() => {
    setLang(prev => prev === 'en' ? 'ar' : 'en');
  }, []);

  const t = useCallback((key) => {
    return translations[lang]?.[key] || translations.en[key] || key;
  }, [lang]);

  const dir = lang === 'ar' ? 'rtl' : 'ltr';

  return (
    <LanguageContext.Provider value={{ lang, toggleLang, t, dir }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}