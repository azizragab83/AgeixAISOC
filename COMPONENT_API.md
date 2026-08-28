# AgeixAISOC - Component API Reference

## Dashboard Components

### MetricsOverview
**Location:** `src/components/dashboard/metrics-overview.tsx`

Displays 5 key SOC metrics with trends and sparklines.

**Props:**
```tsx
interface MetricsProps {
  mttd?: number;           // Minutes to detect
  mttr?: number;           // Seconds to respond
  detectionRate?: number;  // Percentage
  coverage?: number;       // MITRE coverage %
  activeAlerts?: number;   // Count
}
```

**Metrics Shown:**
- Mean Time to Detect (MTTD)
- Mean Time to Respond (MTTR)
- Detection Accuracy
- MITRE ATT&CK Coverage
- Active Incidents

---

### MitreHeatmap
**Location:** `src/components/dashboard/mitre-heatmap.tsx`

Interactive MITRE ATT&CK framework coverage visualization.

**Features:**
- 14 tactics across top row
- Coverage color coding (green/amber/red)
- Hover tooltips showing percentages
- Summary stats at bottom
- Coverage breakdown by tactic

**Coverage Colors:**
- 🟢 Green: 90%+ coverage
- 🟡 Yellow: 75-89% coverage
- 🟠 Orange: 60-74% coverage
- 🔴 Red: Below 60% coverage

---

### AlertFeed
**Location:** `src/components/dashboard/alert-feed.tsx`

Real-time security alert stream with severity filtering.

**Features:**
- 5 Alert types: critical, warning, info, resolved
- Critical alerts show "IMMEDIATE ACTION" badge
- Source attribution (EDR, NDR, SIEM, etc.)
- Scrollable feed with max 400px height
- Count badges for critical/warning

**Alert Types:**
```tsx
type AlertType = 'critical' | 'warning' | 'info' | 'resolved';
```

---

### PendingActions
**Location:** `src/components/dashboard/pending-actions.tsx`

Core HITL governance component for approving/rejecting AI recommendations.

**Props:**
```tsx
interface Props {
  newDecisions?: AiDecision[];
  onDecisionAction?: (id: string, action: "approved" | "rejected") => void;
}
```

**Features:**
- Animated cards with confidence circles
- Approve/Reject/Dismiss buttons
- Real-time status updates
- Confidence score visualization (animated SVG)
- Source attribution & timestamp
- Recommended action display

**AI Decision Interface:**
```tsx
interface AiDecision {
  id: string;
  threat: string;
  description: string;
  recommendedAction: string;
  confidence: number;  // 0-100
  source: string;
  timestamp: string;
}
```

---

### IncidentsForensicsTimeline
**Location:** `src/components/dashboard/incidents-forensics-timeline.tsx`

Auto-constructed forensic timeline with artifact correlation.

**Features:**
- Vertical timeline with animated dots
- Event type icons (detection/analysis/action/resolution)
- Color-coded event cards
- Forensic artifacts listing
- Severity badges
- Actor attribution
- Clickable artifact files

**Event Types:**
- 🔴 Detection - Alert detection
- 🟠 Analysis - Forensic investigation
- 🔵 Action - Response executed
- 🟢 Resolution - Incident closed

---

### AuditComplianceTable
**Location:** `src/components/dashboard/audit-compliance-table.tsx`

Immutable audit trail of all HITL decisions with compliance mappings.

**Features:**
- Sortable table with 6 columns
- Timestamp, Decision, Action, Analyst, Compliance Ref, Justification
- 100% immutable records
- ISO 27001 compliance references
- Decision statistics at bottom
- Analyst email & name attribution

**Columns:**
1. **Timestamp** - ISO format with clock icon
2. **Decision** - Incident ID + description
3. **Action** - approved/rejected/modified badge
4. **Analyst** - User email & display name
5. **Compliance Ref** - ISO 27001 mapping (e.g., A.12.2.1)
6. **Justification** - 2-line text with reasoning

---

### TenantSwitcher
**Location:** `src/components/dashboard/tenant-switcher.tsx`

Multi-tenant organization switcher with plan management.

**Features:**
- Dropdown menu with 3 sample orgs
- Plan badges (Starter/Pro/Enterprise)
- Member counts
- Quick actions (Teams, Settings, Sign Out)
- Active org highlighting
- Smooth animations

**Tenant Data:**
```tsx
interface Tenant {
  id: string;
  name: string;
  plan: "Starter" | "Pro" | "Enterprise";
  users: number;
  active: boolean;
}
```

---

### AiBrainVisualization
**Location:** `src/components/core-ai-brain/ai-brain-visualization.tsx`

6-Agent orchestration visualization with Detection Gap Loop status.

**Features:**
- Grid display of 6 agents
- Status indicators (active/idle/processing)
- Task completion counts
- Last activity text
- Animated borders for active agents
- Detection Gap Loop status section

**Agents:**
1. Threat Detection - Red, active
2. Risk Scoring - Amber, active
3. Recommendations - Cyan, processing
4. Threat Hunter - Green, idle
5. Red Team - Purple, active
6. Forensics - Cyan, processing

**Agent Interface:**
```tsx
interface Agent {
  id: string;
  name: string;
  icon: React.ReactNode;
  status: 'active' | 'idle' | 'processing';
  tasksCompleted: number;
  lastActivity: string;
  color: string;
}
```

---

## UI Base Components

### Card
Base card container with backdrop blur effect.

```tsx
<Card className="border-nexus-border">
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>
    {/* Content here */}
  </CardContent>
</Card>
```

### Button
Multiple variants with color schemes.

**Variants:**
- `default` - Cyan primary
- `destructive` - Red
- `success` - Green
- `outline` - Bordered
- `ghost` - Text only

**Sizes:**
- `default` - h-9
- `sm` - h-8 text-xs
- `lg` - h-10
- `icon` - h-9 w-9

### Badge
Status badges with color variants.

**Variants:**
- `default` - Cyan
- `critical` - Red
- `high` - Orange
- `medium` - Amber
- `low` - Green
- `info` - Gray
- `outline` - Bordered

---

## State Management

### useToast Hook
Toast notification system.

```tsx
const { toasts, toast, dismiss } = useToast();

toast({
  title: "Success",
  description: "Action completed",
  variant: "success"  // success | destructive
});
```

---

## WebSocket Integration

### Dashboard Connection
Real-time event streaming from backend.

```
ws://localhost:8000/ws/dashboard
```

**Expected Message Format:**
```json
{
  "type": "ai_decision|system_log|alert",
  "data": { /* event data */ },
  "timestamp": "2026-07-11T13:45:22Z"
}
```

---

## Animation Patterns

### Entry Animations
```tsx
initial={{ opacity: 0, y: 20 }}
animate={{ opacity: 1, y: 0 }}
transition={{ delay: idx * 0.05 }}
```

### Pulse/Glow
```tsx
animate={{ opacity: [1, 0.7, 1] }}
transition={{ duration: 2, repeat: Infinity }}
```

### Scale on Hover
```tsx
whileHover={{ scale: 1.05 }}
```

### Exit Animations
```tsx
exit={{ opacity: 0, x: 200, scale: 0.9 }}
```

---

## Color Tokens

### Primary Colors
```css
--nexus-bg: #0a0e17
--nexus-surface: #111827
--nexus-border: #1e293b
```

### Accent Colors
```css
--nexus-cyan: #00f0ff
--nexus-red: #ff003c
--nexus-green: #00ff88
--nexus-amber: #ffaa00
--nexus-purple: #7c3aed
--nexus-gray: #94a3b8
```

---

## Mock Data Structures

### PendingAction
```tsx
interface PendingAction {
  id: string;
  threat: string;
  description: string;
  recommendedAction: string;
  confidence: number;
  source: string;
  timestamp: string;
}
```

### SwarmActivity
```tsx
interface SwarmActivity {
  id: string;
  agent: string;
  action: string;
  target: string;
  result: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  timestamp: string;
}
```

### TimelineEvent
```tsx
interface TimelineEvent {
  id: string;
  timestamp: string;
  type: 'detection' | 'analysis' | 'action' | 'resolution';
  title: string;
  description: string;
  actor: string;
  artifacts: string[];
  severity: 'critical' | 'high' | 'medium';
}
```

### AuditEntry
```tsx
interface AuditEntry {
  id: string;
  timestamp: string;
  decision: string;
  action: 'approved' | 'rejected' | 'modified';
  analyst: string;
  description: string;
  justification: string;
  incidentId: string;
  complianceRef: string;
}
```

---

## Responsive Breakpoints

- **Mobile:** < 640px
- **Tablet:** 640px - 1024px
- **Desktop:** > 1024px

Grid layouts use Tailwind's responsive prefixes:
- `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`

---

## Performance Optimizations

1. **Lazy Loading** - Components render only when visible
2. **Memo Optimization** - Prevent unnecessary re-renders
3. **Animation Performance** - GPU-accelerated with Framer Motion
4. **Bundle Size** - Optimized with Next.js tree-shaking
5. **Code Splitting** - Page-based splitting for faster loads

---

## Testing & Development

### Build
```bash
npm run build
```

### Dev Server
```bash
npm run dev
# http://localhost:3000
```

### Linting
```bash
npm run lint
```

---

*API Reference v1.0 - Last Updated: 2026-07-11*
