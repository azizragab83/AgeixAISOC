# AgeixAISOC — Operationalization Final Report

## Summary

All features from both architectural diagrams have been wired to real data/logic or explicitly labeled as simulated. No silent fake data exists. Every data source has a visible UI badge (🟢 Live / 🟡 Cached / ⚪ Static Reference / 🔵 Simulated).

## PART 1 — RAG Knowledge Sources

| # | Feature | Category | Endpoint | Evidence |
|---|---------|----------|----------|----------|
| 1 | Past Incidents | 🟢 Live | `POST /webhook/wazuh-alert` → auto-ingest | `curl` test: "Ingested 1/1 documents into KB 'past_incidents'" after pipeline run |
| 2 | MITRE ATT&CK | 🟡 Cached | `POST /api/knowledge/mitre/refresh` | Downloads real STIX bundle from mitre/cti GitHub, caches to `backend/data/mitre_attack_cache.json`, ingests into `mitre_attack` KB. Startup task runs automatically. |
| 3 | Sigma Rules | 🟢 Live | Auto-ingest on gap_closure | `process_alert_background()` ingests every generated Sigma rule into `sigma_rules` KB after gap closure node writes the rule file |
| 4 | CVE Database | 🟡 Cached | `POST /api/knowledge/cve/ingest` | Queries real NVD API (`services.nvd.nist.gov`) for CVE IDs extracted from forensics output. Auto-triggered after pipeline completion. In-memory cache prevents repeated calls. |
| 5 | CMDB | ⚪ Static Reference | `GET /api/cmdb/assets` | `curl` output: 6 assets with hostname/role/criticality/department/os. Label: "⚪ Static Reference — Mock CMDB, not live discovery". File: `backend/data/cmdb.json` |
| 6 | NIST CSF / ISO 27001 | ⚪ Static Reference | `GET /api/compliance/mapping/{mitre_id}` | `curl` output for T1558: `{"mitre_id":"T1558","technique":"Kerberoasting","nist_csf":["PR.AC-1","DE.CM-1","DE.AE-2"],"iso27001":["A.9.2.3","A.9.4.2","A.16.1.1"]}`. Real control IDs, static mapping. |

## PART 2 — SOC Problem → Feature Mapping

| # | SOC Problem | Category | Endpoint / Component | Evidence |
|---|-------------|----------|---------------------|----------|
| 1 | Alert Fatigue | 🟢 Live | `GET /api/dashboard/alert-reduction-stats` | `curl` output: `{"raw_alerts_today":1,"alerts_reached_hitl":1,"noise_filtered":0,"reduction_pct":0.0}`. Real counters from pipeline runs. |
| 2 | Slow Response (MTTD/MTTR) | 🟢 Live | `GET /api/dashboard/kpis` | `curl` output: `{"mttd":"2.1 min","mttr":"0.5 min","mttd_samples":1,"mttr_samples":1}`. Computed from real pipeline timestamps (alert received → pipeline completed → human decision). |
| 3 | Multiple Tools | 🟢 Live | `GET /api/health/tools` + `ConnectedToolsStatus.jsx` | `curl` output: `{"ollama":{"status":"online","latency_ms":283},"n8n":{"status":"offline"},"fortigate":{"status":"online","latency_ms":1553},"wazuh":{"status":"online","latency_ms":5}}`. Real connectivity tests to all 4 tools. |
| 4 | Detection Gaps | 🟢 Live | `GET /api/dashboard/gap-closure-stats` | `curl` output: `{"gaps_detected":0,"gaps_closed":0,"gaps_open":0,"rules_on_disk":3}`. Real counters from gap loop + filesystem scan. |
| 5 | AD Attacks | 🔵 Simulated (Rule-Based) | `blue_team.py` + AnalystView badge | Rule-based detection for T1558 (Kerberoasting), T1550.002 (PtH), T1003.006 (DCSync). Labeled "🔵 AD Detection Logic — Rule-Based" in UI. NOT a full attack simulation. |
| 6 | Manual Pentesting | 🔵 Simulated (Validation) | `red_team.py` + AuditView badge | Labeled "🔵 AI-Assisted Detection Validation — not automated pentesting". Validates detection coverage, does NOT perform active exploitation. |
| 7 | Outdated Threat Intel | 🟢 Live (15min) | `POST /api/knowledge/threat-intel/refresh` + `GET /api/knowledge/threat-intel/status` | Pulls real abuse.ch Feodo Tracker CSV feed. Background task refreshes every 15 minutes. Status endpoint shows last_refresh timestamp + ingested_count. |
| 8 | No Human Approval | 🟢 Live (HITL) | `POST /api/human-decision` | Verified: no SOAR bypass path. NL query "block IP" now creates pending decision (not direct block). Pipeline → pending_decisions → HITL approval → SOAR execution. |

## Frontend Badges

| Badge | Meaning | Where Used |
|-------|---------|------------|
| 🟢 Live | Real-time data from real system | Alert feed, HITL decisions, MTTD/MTTR, Connected Tools, Knowledge Sources (past_incidents, threat_intel, sigma_rules, learned_decisions) |
| 🟡 Cached | Real data, refreshed periodically | MITRE ATT&CK (STIX bundle), CVE Database (NVD on-demand), CVE/KEV |
| ⚪ Static Reference | Real but non-live | CMDB, NIST CSF / ISO 27001 compliance mappings |
| 🔵 Simulated | Clearly fake for demo | AD Detection Logic (rule-based), AI-Assisted Detection Validation |

## Files Modified

### Backend
- `backend/routes/dashboard.py` — Added CVE ingest from forensics, fixed NL query SOAR bypass (now creates HITL pending decision)
- `backend/routes/health.py` — Added `GET /api/health/tools` live health check for Ollama/n8n/FortiGate/Wazuh
- `backend/ai_agents/red_team.py` — Added "AI-Assisted Detection Validation" label + disclaimer

### Frontend
- `frontend/src/api.js` — Added `getComplianceMapping()` and `getToolsHealth()` API functions
- `frontend/src/components/ConnectedToolsStatus.jsx` — Rewired to use live `/api/health/tools` endpoint with latency display
- `frontend/src/pages/ExecutiveView.jsx` — Added DataSourceBadge for MTTD/MTTR with sample counts
- `frontend/src/pages/AnalystView.jsx` — Added AD detection badge for T1558/T1550.002/T1003.006 alerts
- `frontend/src/pages/AuditView.jsx` — Added "AI-Assisted Detection Validation" badge

## End-to-End Test Evidence

```
1. Alert sent: POST /webhook/wazuh-alert → ALERT-ACEBB50E accepted
2. Pipeline ran: threat_detection → risk_scoring → recommendation → threat_hunter → forensics → red_team → blue_team → END
3. past_incidents RAG: "Ingested 1/1 documents into KB 'past_incidents'"
4. Alert in HITL queue: risk_score=65.0, risk_level=high, MITRE T1110
5. HITL decision: POST /api/human-decision → approved
6. learned_decisions RAG: "Ingested 1/1 documents into KB 'learned_decisions'"
7. SOAR execution: n8n webhook (offline) → FortiGate fallback (401, expected in lab)
8. MTTD: 2.1 min (1 sample) — real timestamp computation
9. MTTR: 0.5 min (1 sample) — real timestamp computation

## Cognitive Arsenal Integration (Agent-Reach / gstack / OSINT Arsenal)

The Master Brain was upgraded with live external intelligence capabilities from three open-source repos, wrapped as custom CrewAI tools in backend/ai_tools/cognitive_arsenal.py:

- agent_reach_search: Deep web search + content extraction via DuckDuckGo (Agent-Reach concept)
- gstack_analyze_code: Suspicious script/Sigma/PowerShell analysis via local qwen2.5-coder + gstack skills library
- osint_arsenal_lookup: Multi-source IOC enrichment (AlienVault OTX, AbuseIPDB) with a 753-tool OSINT catalog

Tool assignments:
- Threat Hunter Agent: agent_reach_search + osint_arsenal_lookup
- Forensics Agent: gstack_analyze_code
- OSINT/Swarm Agent: all three tools
- Detection Engineering Agent: gstack_analyze_code

The master_synthesis node prompt now instructs qwen2.5:14b to integrate external intelligence findings into the final correlated threat narrative and predicted next move.

Dependencies added to requirements.txt: duckduckgo-search, beautifulsoup4.
