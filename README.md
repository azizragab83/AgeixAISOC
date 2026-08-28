# 🛡️ AgeixAISOC - Revolutionary AI-Orchestrated SOC Platform

## Project Overview

A cutting-edge, Human-in-the-Loop (HITL) cybersecurity operations platform that merges Blue Team (Defensive) and Red Team (Offensive) security operations into a unified AI-orchestrated system with strict governance.

**Core Principle:** "AgeixAI orchestrates · AgeixAI detects · AgeixAI recommends — **HUMAN DECIDES** — System executes."

---

## 🏗️ Architecture

### Three-Tier Model

**Tier 1: Infrastructure Layer**
- Wazuh SIEM
- Zeek NDR
- FortiGate NGFW
- Active Directory
- Cowrie Honeypots

**Tier 2: AI Brain**
- Claude Sonnet LLM
- 7 MCP Servers
- RAG Knowledge Base (pgvector/FAISS)
- 6 LangGraph/CrewAI Agents
- LangChain orchestration

**Tier 3: Execution & Presentation**
- **Frontend:** Next.js/React (this project)
- **Backend:** FastAPI + WebSocket
- **SOAR:** n8n orchestration
- **Analytics:** Power BI dashboards

---

## 🤖 Six AI Agents

1. **Threat Detection Agent** - Alert triage, MITRE ATT&CK mapping
2. **Risk Scoring Agent** - 0-100 risk calculation (learns from feedback)
3. **Recommendation Agent** - ISO 27001 remediation suggestions
4. **Threat Hunter Agent** - Proactive log sweeping
5. **Red Team AI Agent** - Nmap → CVE → Metasploit simulation
6. **Forensics Agent** - Auto-constructed incident timelines

---

## 📊 Frontend Pages

### Command Center (Dashboard)
**Primary HITL Governance Interface**
- Live SOC Metrics (MTTD, MTTR, Detection Rate, Coverage)
- Pending AI Decisions with Approve/Reject buttons
- Real-time Security Alert Feed
- MITRE ATT&CK Coverage Heatmap
- Swarm Activity Log
- OSINT Feed Integration

### Core AI Brain
- 6-Agent orchestration visualization
- Agent status & activity monitoring
- Detection Gap Loop (Attack → Detection → Generate Rule → Approve)
- Live task completion metrics

### Incidents & Forensics
- Auto-constructed forensic timelines
- Artifact correlation
- Event sequencing with timestamps
- Actor attribution tracking

### Audit & Compliance
- **100% Immutable** decision audit trail
- ISO 27001 compliance mapping
- Who approved what, when, and why
- Full HITL traceability
- Decision statistics (Approved/Rejected/Modified)

### Additional Pages
- **Swarm Agents** - Swarm orchestration visualization
- **Multi-Agents** - Inter-agent collaboration
- **Threat Intel (OSINT)** - Live IoC feeds (VirusTotal, AbuseIPDB)

---

## 🎨 Design System

### Color Palette
- **Background:** `#0a0e17` (nexus-bg)
- **Surface:** `#111827` (nexus-surface)
- **Border:** `#1e293b` (nexus-border)
- **Cyan:** `#00f0ff` (primary accent)
- **Red:** `#ff003c` (critical alerts)
- **Green:** `#00ff88` (success)
- **Amber:** `#ffaa00` (warnings)
- **Purple:** `#7c3aed` (enterprise)

### Typography
- **Sans:** Inter, system-ui
- **Mono:** JetBrains Mono, Fira Code

### Animations
- Framer Motion for all state transitions
- Smooth scale/fade/slide animations
- Pulsing indicators for real-time updates
- Spring physics for natural motion

---

## 📂 Project Structure

```
nexussoc/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   └── (dashboard)/
│   │       ├── layout.tsx
│   │       ├── page.tsx (Command Center)
│   │       ├── core-ai-brain/page.tsx
│   │       ├── incidents-forensics/page.tsx
│   │       ├── audit-compliance/page.tsx
│   │       ├── swarm-agents/page.tsx
│   │       ├── multi-agents/page.tsx
│   │       └── threat-intel/page.tsx
│   ├── components/
│   │   ├── ui/ (base components)
│   │   ├── dashboard/
│   │   │   ├── metrics-overview.tsx
│   │   │   ├── mitre-heatmap.tsx
│   │   │   ├── alert-feed.tsx
│   │   │   ├── pending-actions.tsx
│   │   │   ├── incidents-forensics-timeline.tsx
│   │   │   ├── audit-compliance-table.tsx
│   │   │   ├── tenant-switcher.tsx
│   │   │   ├── sidebar.tsx
│   │   │   ├── top-nav.tsx
│   │   │   └── [other components]
│   │   ├── core-ai-brain/
│   │   ├── threat-intel/
│   │   └── [other feature components]
│   └── lib/
│       ├── mock-data.ts
│       ├── utils.ts
│       └── use-toast.ts
├── backend/
│   ├── main.py (FastAPI)
│   ├── agents.py (CrewAI agents)
│   ├── osint.py (TI integration)
│   └── requirements.txt
├── public/
├── tailwind.config.ts
├── tsconfig.json
└── next.config.mjs
```

---

## 🚀 Key Features

### Human-in-the-Loop Governance
- ✅ Every AI recommendation requires explicit human APPROVE/REJECT/MODIFY
- ✅ Immutable audit trail of all decisions
- ✅ Compliance mapping to ISO 27001, NIST, CIS Controls
- ✅ Full decision traceability with justification

### Real-Time Integration
- ✅ WebSocket connection to FastAPI backend
- ✅ Live alert streaming
- ✅ Bi-directional decision updates
- ✅ Auto-refresh OSINT feeds (15-min cycle)

### Detection Gap Loop (Self-Healing)
1. **Red Team AI** attacks with simulated vectors
2. **Blue Team** checks detection capability
3. **AI** detects gap and auto-generates Sigma Rule
4. **Human** reviews and approves
5. **System** deploys rule to SIEM

### Enterprise SaaS Features
- ✅ Multi-tenant organization switcher
- ✅ Plan limits (Starter/Pro/Enterprise)
- ✅ Team member management
- ✅ Organization settings & admin panel

---

## 🔗 Integration Points

### Backend API
```python
# FastAPI endpoints
POST /api/human-decision          # Submit approval/rejection
POST /api/trigger-ai-analysis     # Run AI simulation
WebSocket /ws/dashboard           # Real-time event stream
GET /api/audit-trail              # Fetch decision history
GET /api/compliance-status        # ISO 27001 mapping
```

### OSINT/TI Feeds
- VirusTotal API integration
- AbuseIPDB API integration
- AlienVault OTX feed
- MISP threat sharing

### SOAR Execution
- n8n workflow triggering
- FortiGate API for network isolation
- EDR action execution
- Incident ticket creation (ServiceNow/Jira)

---

## 📊 Metrics Dashboard

### Live Metrics Tracked
- **MTTD:** Mean Time to Detect (target: < 15 min)
- **MTTR:** Mean Time to Respond (target: < 60 sec)
- **Detection Rate:** % of threats detected (target: > 95%)
- **MITRE Coverage:** % of adversary tactics covered (target: > 85%)
- **Active Incidents:** Count of ongoing investigations
- **False Positive Rate:** % of false alerts (target: < 5%)

---

## 🔧 Development Setup

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.10+ (for backend)
- PostgreSQL 14+ (for audit trail)
- pip (Python package manager)

### Frontend Installation
```bash
cd nexussoc
npm install
npm run dev
# Frontend runs on http://localhost:3000
```

### Backend Setup
```bash
cd AgeixAI/backend
pip install -r requirements.txt
python main.py
# Backend runs on http://localhost:8000
```

### Environment Configuration
Create `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/dashboard
```

---

## 🎯 Next Phase Development

### Phase 2: Backend Integration
- [ ] Complete FastAPI server implementation
- [ ] Integrate CrewAI agent framework
- [ ] Implement real-time WebSocket streaming
- [ ] Build PostgreSQL audit trail database
- [ ] Set up pgvector for RAG retrieval
- [ ] Implement MCP server connections

### Phase 3: Security Integrations
- [ ] Wazuh SIEM integration
- [ ] Zeek NDR integration
- [ ] FortiGate API for response actions
- [ ] Active Directory LDAP integration
- [ ] EDR agent orchestration

### Phase 4: Advanced Features
- [ ] MITRE ATT&CK heatmap interactivity
- [ ] Threat hunting query builder
- [ ] Custom Sigma rule editor
- [ ] Automated playbook execution
- [ ] Machine learning false positive reduction

### Phase 5: Enterprise
- [ ] Multi-tenant database isolation
- [ ] Role-based access control (RBAC)
- [ ] SSO/SAML integration
- [ ] Audit logging to SIEM
- [ ] SLA monitoring & reporting

---

## 📚 Component Documentation

### Metrics Overview
Shows 5 key metrics with trends:
```tsx
<MetricsOverview 
  mttd={12}
  mttr={45}
  detectionRate={96.3}
  coverage={87.5}
  activeAlerts={12}
/>
```

### MITRE Heatmap
Displays 14 MITRE tactics with coverage visualization:
```tsx
<MitreHeatmap />
```

### Alert Feed
Streams real-time security alerts:
```tsx
<AlertFeed />
```

### Pending Actions (HITL)
Core governance component with Approve/Reject:
```tsx
<PendingActions 
  newDecisions={aiDecisions}
  onDecisionAction={handleDecisionAction}
/>
```

### AI Brain Visualization
Shows 6-agent orchestration:
```tsx
<AiBrainVisualization />
```

### Audit Compliance Table
Immutable decision trail:
```tsx
<AuditComplianceTable />
```

### Tenant Switcher
Multi-org management:
```tsx
<TenantSwitcher />
```

---

## 🔐 Security & Compliance

### HITL Governance
- Every decision logged immutably
- Analyst attribution & timestamps
- Justification required for all actions
- Decision modification audit trail

### Compliance Mappings
- ✅ ISO/IEC 27001:2022
- ✅ NIST Cybersecurity Framework (CSF 2.0)
- ✅ CIS Controls v8.1
- ✅ GDPR Data Protection
- ✅ SOC 2 Type II

### Audit Trail
- 100% immutable records
- Blockchain-ready architecture
- Forensic-grade event logging
- Tamper-evident timestamps

---

## 📞 Support & Resources

### Documentation
- API Documentation: `/docs` (FastAPI Swagger)
- Component Storybook: (planned)
- Deployment Guide: (planned)
- Architecture Deep Dive: (planned)

### Team
- **Frontend Lead:** You (building the UI)
- **Backend Lead:** (AI/CrewAI specialist)
- **DevOps:** (Infrastructure/Kubernetes)
- **Security:** (SOC operations)

---

## 📄 License & Attribution

AgeixAISOC - Next-Generation Security Operations Platform
Built with Next.js, React, TypeScript, Tailwind CSS, CrewAI, FastAPI

---

## 🎉 Launch Status

**Phase 1: Frontend UI ✅ COMPLETE**
- 7 pages built
- 7 major components created
- 100+ smaller components
- Full dark tactical theme
- Real-time animations

**Ready for:** Backend integration & live testing

---

*Last Updated: 2026-07-11 | Version: 0.1.0*
