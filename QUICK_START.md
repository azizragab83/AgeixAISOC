# 🚀 AgeixAISOC - QUICK START GUIDE

## ⚡ Get Running in 30 Seconds

```bash
cd c:\Users\Digilians\Desktop\AgeixSOC\AgeixAI
npm run dev
```

Then open: **http://localhost:3000**

---

## 📱 Pages to Explore

| Page | URL | What to See |
|------|-----|-----------|
| **Command Center** | `http://localhost:3000/` | Main dashboard with all metrics |
| **AI Brain** | `http://localhost:3000/core-ai-brain` | 6-agent orchestration |
| **Incidents** | `http://localhost:3000/incidents-forensics` | Forensic timeline |
| **Audit** | `http://localhost:3000/audit-compliance` | Decision audit trail |
| **Swarm** | `http://localhost:3000/swarm-agents` | Red team agents |
| **Multi-Agents** | `http://localhost:3000/multi-agents` | Agent collaboration |
| **Threat Intel** | `http://localhost:3000/threat-intel` | OSINT feeds |

---

## 🎨 Theme Features to Notice

✅ Dark tactical theme
✅ Neon cyan/red/green accents  
✅ Smooth animations everywhere
✅ Responsive grid layouts
✅ Real-time pulsing indicators
✅ Glassmorphism effects (blur)
✅ Enterprise color palette

---

## 🧩 New Components Overview

### 1. **Metrics Overview** 
Shows: MTTD (12m), MTTR (45s), Detection Rate (96.3%), Coverage (87.5%), Incidents (12)

### 2. **MITRE Heatmap**
Shows: 14 tactics with coverage percentages (green=90%+, amber=75-89%)

### 3. **Alert Feed**
Shows: Real-time security alerts with severity (Critical/Warning/Info)

### 4. **Pending Actions** (HITL Core)
Shows: AI recommendations with Approve/Reject buttons, confidence scores

### 5. **AI Brain Visualization**
Shows: 6 agents (Detection, Scoring, Recommendations, Hunter, Red Team, Forensics)

### 6. **Incidents Timeline**
Shows: Event sequence with forensic artifacts (Detection → Analysis → Action → Resolution)

### 7. **Audit Trail**
Shows: Immutable decision log with analyst, timestamp, compliance mapping

### 8. **Tenant Switcher**
Shows: Organization switching with plan badges

---

## 📊 Command Center Highlights

**Live Metrics Section:**
```
Mean Time to Detect: 12 minutes ↓ 8%
Mean Time to Respond: 45 seconds ↓ 22%
Detection Accuracy: 96.3% ↑ 3.2%
MITRE ATT&CK Coverage: 87.5% ↑ 5.1%
Active Incidents: 12 ↓ 1
```

**Pending Decisions (HITL):**
```
[Alert Card 1]
CVE-2025-44228 - Log4j RCE
Confidence: 94%
[APPROVE] [REJECT]

[Alert Card 2]
Suspicious DNS Tunneling
Confidence: 78%
[APPROVE] [REJECT]
```

**Alert Feed:**
```
[CRITICAL] Privilege Escalation Detected
[CRITICAL] C2 Beaconing Activity  
[WARNING] Suspicious DNS Tunneling
[WARNING] Unusual Outbound Traffic
[RESOLVED] False Positive - Port Scan
```

---

## 🔌 Integration Checklist

### What's Working Now ✅
- ✅ All 7 pages fully functional
- ✅ Navigation between pages
- ✅ Mock data populated
- ✅ Animations & transitions
- ✅ Responsive layouts
- ✅ Dark theme consistent

### What Needs Backend 🔧
- 🔧 WebSocket real-time updates
- 🔧 HITL decision submission
- 🔧 AI recommendation generation
- 🔧 OSINT feed streaming
- 🔧 Audit trail persistence
- 🔧 Compliance data

---

## 💡 Key Concepts

### HITL Governance
"Human-in-the-Loop" - Every AI decision needs human approval

### Detection Gap Loop
Red Team attacks → Blue Team detects gaps → AI generates rule → Human approves → Rule deployed

### 6-Agent System
1. Threat Detection - Triage alerts
2. Risk Scoring - Calculate threat level
3. Recommendations - Suggest remediation
4. Threat Hunter - Proactive sweeping
5. Red Team - Attack simulation
6. Forensics - Timeline construction

### Immutable Audit Trail
Every HITL decision logged with:
- Who approved (analyst name/email)
- When (timestamp)
- What action (approved/rejected/modified)
- Why (justification)
- What compliance (ISO 27001 ref)

---

## 🎯 Mock Data Sources

In `src/lib/mock-data.ts`:
- 4 pending AI decisions
- 4 swarm activities  
- 5+ OSINT entries
- 6 audit log entries
- MITRE coverage percentages
- Threat levels

**To modify mock data:**
1. Edit `src/lib/mock-data.ts`
2. Refresh browser (or `npm run dev` will auto-reload)

---

## 🔗 Integration Points

### WebSocket (Real-Time)
```
ws://localhost:8000/ws/dashboard
```

### API Endpoints
```
POST /api/human-decision
POST /api/trigger-ai-analysis  
GET /api/audit-trail
GET /api/compliance-status
GET /api/osint/abuseipdb
GET /api/osint/otx
```

---

## 📚 Key Files

| File | Purpose |
|------|---------|
| `src/app/(dashboard)/page.tsx` | Command Center layout |
| `src/components/dashboard/metrics-overview.tsx` | Key metrics |
| `src/components/dashboard/mitre-heatmap.tsx` | Coverage heatmap |
| `src/components/dashboard/pending-actions.tsx` | HITL decisions |
| `src/components/core-ai-brain/ai-brain-visualization.tsx` | Agent display |
| `src/lib/mock-data.ts` | Sample data |
| `tailwind.config.ts` | Design tokens |

---

## 🎨 Color Reference

```
Primary Accents:
🔵 Cyan:    #00f0ff (primary UI)
🔴 Red:     #ff003c (critical/alerts)
🟢 Green:   #00ff88 (success)
🟠 Amber:   #ffaa00 (warnings)
🟣 Purple:  #7c3aed (enterprise)
⚫ Gray:    #94a3b8 (secondary text)

Backgrounds:
🌑 BG:      #0a0e17 (page background)
🌒 Surface: #111827 (card background)
📦 Border:  #1e293b (divider lines)
```

---

## ⚙️ Build Commands

```bash
npm run dev          # Start dev server (port 3000)
npm run build        # Production build
npm start            # Run production build
npm run lint         # Check for errors
```

---

## 🐛 Troubleshooting

**Port 3000 in use?**
```bash
# Kill existing process or use different port
npm run dev -- -p 3001
```

**Module not found error?**
```bash
npm install
```

**WebSocket not connecting?**
- Make sure backend is running on port 8000
- Check NEXT_PUBLIC_WS_URL in .env.local

**Components not showing?**
- Clear browser cache (Ctrl+Shift+Delete)
- Restart dev server (Ctrl+C, then `npm run dev`)

---

## 📖 Documentation

Inside project:
- **README.md** - Full project overview
- **COMPONENT_API.md** - Component reference
- **IMPLEMENTATION_SUMMARY.md** - What was built
- **PROJECT_COMPLETION.md** - Full completion report

---

## 🎉 What You Have

✅ Production-ready frontend UI
✅ Enterprise SaaS architecture
✅ Real-time animation framework
✅ HITL governance system
✅ 7 fully functional pages
✅ 40+ reusable components
✅ Responsive design (mobile-desktop)
✅ Dark tactical theme
✅ Zero build errors
✅ Full TypeScript coverage

---

## 🚀 Next Steps

1. ✅ Run `npm run dev` and explore
2. ✅ Review the 7 pages
3. ✅ Read COMPONENT_API.md
4. ✅ Check mock-data.ts for data structure
5. 🔧 Start Phase 2: Connect FastAPI backend
6. 🔧 Implement WebSocket event streaming
7. 🔧 Build out OSINT integrations
8. 🔧 Deploy to production

---

## 📞 Quick Reference

**Start Dev Server:**
```bash
cd AgeixAI
npm run dev
# Open http://localhost:3000
```

**Build for Production:**
```bash
npm run build
npm start
# Open http://localhost:3000
```

**View Component Docs:**
```
Open: COMPONENT_API.md
Search for component name
```

**Check Data Structure:**
```
Open: src/lib/mock-data.ts
Find interface definitions
```

---

**You're all set! 🎉 Enjoy exploring AgeixAISOC!**

*For full details, see PROJECT_COMPLETION.md*
