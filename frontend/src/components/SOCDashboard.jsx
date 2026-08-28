import { useState, useEffect } from 'react';
import KPIWidgets from './KPIWidgets';
import LiveFeedTerminal from './LiveFeedTerminal';
import HITLQueue from './HITLQueue';
import LabHealthMonitor from './LabHealthMonitor';
import MITREHeatmap from './MITREHeatmap';
import ThreatGeoMap from './ThreatGeoMap';
import ConnectedToolsStatus from './ConnectedToolsStatus';
import KnowledgeSourcesPanel from './KnowledgeSourcesPanel';
import { dashboardApi } from '../api';

export default function SOCDashboard() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await dashboardApi.getMetrics();
        setMetrics(res.data);
      } catch {}
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col gap-4 min-h-full">
      {/* Row 1: Global KPIs — 4 cards */}
      <section className="grid grid-cols-12 gap-4">
        <div className="col-span-12">
          <KPIWidgets metrics={metrics} />
        </div>
      </section>

      {/* Row 2: Core Operations — Live Feed (8) + HITL Queue (4) */}
      <section className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-8 h-[480px]">
          <LiveFeedTerminal />
        </div>
        <div className="col-span-12 lg:col-span-4 h-[480px]">
          <HITLQueue />
        </div>
      </section>

      {/* Row 3: Intelligence & Infrastructure — Lab (4) + MITRE (4) + Geo (4) */}
      <section className="grid grid-cols-12 gap-4">
        <div className="col-span-12 md:col-span-6 xl:col-span-4">
          <LabHealthMonitor />
        </div>
        <div className="col-span-12 md:col-span-6 xl:col-span-4">
          <MITREHeatmap />
        </div>
        <div className="col-span-12 xl:col-span-4">
          <ThreatGeoMap />
        </div>
      </section>

      {/* Row 4: Knowledge Sources (8) + Connected Tools (4) */}
      <section className="grid grid-cols-12 gap-4">
        <div className="col-span-12 xl:col-span-8">
          <KnowledgeSourcesPanel />
        </div>
        <div className="col-span-12 xl:col-span-4">
          <ConnectedToolsStatus />
        </div>
      </section>
    </div>
  );
}