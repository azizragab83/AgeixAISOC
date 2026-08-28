# AgeixAISOC

Full-stack SOC (Security Operations Center) platform with AI agent pipeline, HITL (Human-in-the-Loop) workflows, n8n SOAR automation, FortiGate integration, and containerized deployment.

## Architecture

```
frontend/  (React + Vite + Tailwind, port 5173)
backend/   (FastAPI + LangGraph + ChromaDB, port 8000)
  ai_agents/ (7 individual agent modules + shared _utils.py)
rag_engine/ (ChromaDB + Ollama RAG server)
.github/workflows/ (CI.yml - GitHub Actions)
```

**External services:** n8n (5678), Ollama (11434), ChromaDB (8002)

## Key Design Decisions

- **Import guards:** All files use `try: from X import Y / except ImportError: from backend.X import Y` to support both `uvicorn main:app` (run from `backend/`) and `uvicorn backend.main:app` (run from root).
- **No mock data:** Every frontend component calls real API endpoints. No hardcoded fixtures.
- **Relative URLs in frontend:** `api.js` uses relative paths (`/api/...`) and `window.location.host` for WebSocket, with Vite proxy in dev and nginx proxy in Docker.
- **Fallback logic:** Every AI agent has a try/except with fallback return values, so the pipeline never crashes on agent failure.
- **State merging:** Orchestrator nodes explicitly merge `decision_package` via `{**state["decision_package"], **result["decision_package"]}` to preserve accumulated state through LangGraph's replace-default reducer.

## Lab Topology (5 VMs)

| Device | IP | Role |
|--------|-----|------|
| Kali | 192.168.56.10 | Attack machine (ssh aziz:8394) |
| Win10 Victim | 192.168.56.20 | Target |
| Wazuh | 192.168.56.30 | SIEM (wazuh:wazuh) |
| Metasploitable2 | 192.168.56.40 | Vulnerable target |
| FortiGate | 192.168.56.2 | Firewall (token: H5HO7hxk567gjQnn6qh4xc7j8k7htj) |
| Win Server DC | 192.168.56.100 | Domain controller |

## How to Run

```powershell
# Dev mode
.\start.ps1              # starts backend(8000) + frontend(5173) + n8n(5678)

# Docker
docker compose build      # builds backend + frontend images
docker compose up -d      # starts all 5 services

# Manual (from project root)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
# From frontend/:
npm run dev
```

## File Structure

```
backend/
  main.py              # FastAPI app factory, CORS, startup/shutdown
  orchestrator.py      # 6-node LangGraph StateGraph, SOCGraphRunner
  config.py            # Pydantic Settings from .env
  state.py             # ConnectionManager + pending_decisions
  fortigate_soar.py    # block_ip_real() - direct FortiGate API
  lab_bridge.py        # LabBridge SSH class + run_ssh_command()
  wazuh_connector.py   # WazuhConnector async REST client
  agents.py            # Old agent abstraction (used by ai_agents internally)

  routes/
    health.py          # GET /api/health
    lab.py             # lab/status, lab/launch-attack, trigger-attack
    hitl.py            # POST /api/human-decision (n8n -> FortiGate fallback)
    dashboard.py       # metrics, alerts, forensics, query/nl, rules/deploy, soar/execute
    ws.py              # WebSocket /ws/dashboard

  services/
    mitigation.py      # block_ip() (FortiGate REST), execute_n8n_webhook()

  models/
    schemas.py         # All Pydantic models (WazuhAlert, HumanDecision, etc.)

  ai_agents/
    __init__.py        # Exports 7 run() functions
    threat_detection.py
    risk_scorer.py
    recommender.py
    threat_hunter.py
    forensics_agent.py
    red_team.py
    detection_eng.py   # Sigma rule generation (alt 5b)

  rag_engine/
    knowledge_base.py  # 5 KB registry (past_incidents, threat_intel, sigma_rules, cve_kev, learned_decisions)
    rag_server.py      # RAGServer with ChromaDB + Ollama embeddings

frontend/src/
  api.js               # axios client + SOCWebSocket + all API functions
  main.jsx             # BrowserRouter entry
  App.jsx              # Collapsible sidebar, 6 routes, header with WS/API dots
  hooks/
    useWebSocket.js    # WS connection hook with reconnect
    useLabHealth.js    # Lab status polling hook
    useAlerts.js       # Alert fetching + polling hook
  pages/
    AnalystView.jsx    # Alert feed with filters
    ExecutiveView.jsx  # C-Suite KPI metrics
    TIView.jsx         # MITRE ATT&CK coverage matrix
    AuditView.jsx      # Decision audit trail
    DetectionView.jsx  # Sigma rule deployment
  components/
    ThreatMap.jsx      # SVG network topology (6 lab nodes, animated attacks)
    MITREHeatmap.jsx   # MITRE coverage grid heatmap
    ForensicsView.jsx  # Forensics timeline search
    KPIWidgets.jsx     # MTTD/MTTR metric cards
    SOCDashboard.jsx   # Main dashboard (top alerts, WS status)

docker-compose.yml     # 5 services: ollama, chroma, n8n, backend, frontend
```

## API Endpoints (14 total)

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/health | System health + configured services |
| GET | /api/lab/status | Lab VM reachability check |
| POST | /api/lab/launch-attack | Launch attack from Kali |
| POST | /api/trigger-attack | Trigger + pipeline |
| GET | /api/dashboard/metrics | Aggregate metrics |
| GET | /api/alerts | Recent alerts (paginated) |
| GET | /api/alerts/history | Historical alerts |
| GET | /api/forensics/{id} | Forensics by incident |
| POST | /api/query/nl | Natural language RAG query |
| POST | /api/rules/deploy | Deploy Sigma rule |
| POST | /api/human-decision | HITL decision (n8n -> FortiGate) |
| POST | /api/soar/execute | Execute SOAR actions |
| WS | /ws/dashboard | Real-time dashboard updates |
| POST | /webhook/wazuh-alert | Wazuh alert webhook |

## Orchestrator Pipeline (6 nodes)

```
threat_detection -> risk_scoring -> recommendation -> threat_hunter -> forensics -> red_team
```

Each node delegates to its corresponding `ai_agents/<name>.py` module's `run(alert_id, raw_alert, decision_package) -> dict` function. The `decision_package` accumulates through explicit merge. Final output has `decision_id`, `status: "pending"`, `human_decision: None`.

## Frontend Pages

| Route | Page | Purpose |
|-------|------|---------|
| / | Dashboard | WS status, top alerts, ThreatMap |
| /analyst | AnalystView | Alert feed with severity/type filters |
| /executive | ExecutiveView | KPI widgets, MTTD/MTTR |
| /ti | TIView | MITRE ATT&CK coverage heatmap |
| /audit | AuditView | Decision audit trail table |
| /detection | DetectionView | Sigma rule form + deployment |

## Key Credentials

- **Kali SSH:** aziz / 8394
- **FortiGate API:** H5HO7hxk567gjQnn6qh4xc7j8k7htj
- **n8n webhook:** http://localhost:5678/webhook/execute-soar
- **Ollama model:** nomic-embed-text (embeddings), qwen2.5:14b (threat), llama3.1 (general)
