import { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { LanguageProvider } from './context/LanguageContext';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import SOCDashboard from './components/SOCDashboard';
import AnalystView from './pages/AnalystView';
import ExecutiveView from './pages/ExecutiveView';
import TIView from './pages/TIView';
import AuditView from './pages/AuditView';
import DetectionView from './pages/DetectionView';
import ForensicsView from './components/ForensicsView';
import ToolkitView from './components/ToolkitView';
import AIEngineeringView from './pages/AIEngineeringView';
import DevOpsResourcesView from './pages/DevOpsResourcesView';
import MasterBrainChat from './components/MasterBrainChat';
import IOCManagementView from './pages/IOCManagementView';
import { SOCWebSocket } from './api';
import { handleWsIocEvent } from './utils/iocEvents';

function AppContent() {
  const [ws, setWs] = useState(null);

  useEffect(() => {
    const socket = new SOCWebSocket(
      (message) => {
        // Route IOC lifecycle events (ioc_progress / ioc_enforced / ioc_update)
        // into the IOC pub/sub bus for the IOC page + HITL checklist.
        if (message?.event_type) {
          handleWsIocEvent(message.event_type, message.data || message);
        } else if (message?.type?.startsWith?.('ioc_')) {
          handleWsIocEvent(message.type, message.data || message);
        }
      },
      () => {},
      () => {}
    );
    setWs(socket);
    return () => socket.disconnect();
  }, []);

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<SOCDashboard />} />
        <Route path="/analyst" element={<AnalystView ws={ws} />} />
        <Route path="/executive" element={<ExecutiveView />} />
        <Route path="/threat-intel" element={<TIView />} />
        <Route path="/toolkit" element={<ToolkitView />} />
        <Route path="/ai-engineering" element={<AIEngineeringView />} />
        <Route path="/devops" element={<DevOpsResourcesView />} />
        <Route path="/audit" element={<AuditView />} />
        <Route path="/detection" element={<DetectionView />} />
        <Route path="/forensics" element={<ForensicsView />} />
        <Route path="/ioc" element={<IOCManagementView />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AppContent />
        <MasterBrainChat />
      </LanguageProvider>
    </ThemeProvider>
  );
}