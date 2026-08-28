# AgeixAISOC — Claude Code Project Context

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

## gstack

Use /browse from gstack for all web browsing. Never use mcp__claude-in-chrome__* tools.
Available skills: /office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review,
/design-consultation, /design-shotgun, /design-html, /review, /ship, /land-and-deploy,
/canary, /benchmark, /browse, /open-gstack-browser, /qa, /qa-only, /design-review,
/setup-browser-cookies, /setup-deploy, /setup-gbrain, /sync-gbrain, /retro, /investigate,
/document-release, /document-generate, /codex, /cso, /autoplan, /pair-agent, /careful, /freeze,
/guard, /unfreeze, /gstack-upgrade, /learn.

## Recommended gstack workflow for this SOC project

- **Security audit:** `/gstack-cso` — OWASP Top 10 + STRIDE on the FastAPI backend and API endpoints
- **Code review before merge:** `/gstack-review` — catches bugs that pass CI but break in prod
- **Plan a new feature:** `/gstack-office-hours` then `/gstack-autoplan` — reframe the idea, then lock architecture
- **Debug a pipeline failure:** `/gstack-investigate` — systematic root-cause on the LangGraph orchestrator
- **QA the dashboard:** `/gstack-qa http://localhost:5173` — opens a real browser, clicks through the SOC UI
- **Ship a change:** `/gstack-ship` — run tests, coverage audit, push, open PR

## Run-everything prompt (paste once into Claude Code)

To run the entire gstack pipeline on this project, paste this single prompt:

```
Load gstack skills for this repo.
Then run, in order, WITHOUT asking me for confirmation first:
1. /office-hours          — reframe product intent using repo context
2. /plan-ceo-review       — strategic scope review
3. /plan-eng-review       — architecture, data flow, edge cases, tests
4. /review                — code review of current working-tree diff
5. /cso                   — OWASP Top 10 + STRIDE security audit
6. /ship                  — run tests, push, open PR
Save a summary of each step to GSTACK_RUNS/<date>.md.
```

Claude Code will chain all six skills in sequence, feeding each output into the next.

## Running one skill per prompt

Use the gstack trigger phrases in any natural-language prompt and the skill activates automatically:

| Want to do | Prompt example |
|-----------|----------------|
| Security audit | "security audit للـ backend" |
| Code review | "review this PR" / "افحص الديف" |
| Debug | "روت كوز اناليسيس. ليه/متى fail" |
| QA dashboard | "QA http://localhost:5173" |
| Full plan | "brainstorm this + autoplan" |
| Ship | "ship this" |
| Retro | "weekly retro" |
| Learnings | "what have we learned" |
| PDF | "make pdf من ملف markdown" |
| Diagram | "diagram للـ pipelines" |
