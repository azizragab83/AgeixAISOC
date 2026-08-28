import { useState } from 'react';
import { motion } from 'framer-motion';
import TopBar from './TopBar';
import Sidebar from './Sidebar';
import { useLanguage } from '../context/LanguageContext';

export default function Layout({ children }) {
  const { dir } = useLanguage();
  const isRTL = dir === 'rtl';
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem('ageix_sidebar_collapsed') === '1';
    } catch {
      return false;
    }
  });

  const toggleCollapse = () => {
    setCollapsed(prev => {
      const next = !prev;
      try {
        localStorage.setItem('ageix_sidebar_collapsed', next ? '1' : '0');
      } catch {}
      return next;
    });
  };

  return (
    <div
      className="h-screen w-full flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100"
      style={{ direction: dir }}
    >
      <TopBar />
      <div className={`flex flex-1 min-h-0 ${isRTL ? 'flex-row-reverse' : ''}`}>
        <Sidebar collapsed={collapsed} onToggleCollapse={toggleCollapse} />
        <main className="flex-1 min-w-0 overflow-y-auto">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="w-full max-w-[1760px] mx-auto h-full min-h-full bg-tactical"
          >
            <div className="bg-grid-pattern min-h-full p-4 lg:p-6">{children}</div>
          </motion.div>
        </main>
      </div>
    </div>
  );
}
