# IOC Management Module

End-to-end IOC (Indicator of Compromise) lifecycle integrated with the existing
Sigma → Wazuh → Core Brain → HITL → FortiGate SOAR pipeline.

## Flow

```
Sigma rule fires (Wazuh)
  → Core Brain recommends block_ip
  → Analyst APPROVES (HITL)
  → FortiGate block confirmed (n8n SOAR or direct API fallback)
  → IOC recorded (dedupe by value, blocked_on=["fortigate"])
  → Threat-intel enrichment (Feodo Tracker cross-check, +15 confidence if flagged)
  → EDR/AV enforcement fan-out (fault-tolerant)
  → WebSocket broadcasts: ioc_progress → ioc_enforced
  → TTL expiry job unblocks everywhere after ttl_hours
```

## Backend

| File | Purpose |
|------|---------|
| `backend/ioc_models.py` | `IOC` model + thread-safe JSON store (`backend/data/iocs.json`), dedupe by value, TTL expiry, lifecycle timeline |
| `backend/edr_connectors.py` | `EDRConnector` ABC + 4 connectors + fault-tolerant `enforce_ioc_everywhere()` / `unenforce_ioc_everywhere()` |
| `backend/routes/ioc.py` | REST API (below) |
| `backend/routes/hitl.py` | Auto-hook: after a confirmed FortiGate block, `_record_and_enforce_ioc()` runs the full IOC pipeline |
| `backend/main.py` | `_ioc_ttl_expiry_loop()` — sweeps expired IOCs every 15 min and unblocks them |

### Connectors

1. **Wazuh Active Response** (real) — `PUT /active-response?agents_list=*` with
   `firewall-drop` adds the IP to iptables/Windows Firewall on every agent.
2. **ClamAV** (real) — appends MD5→`local.hdb` / SHA-256→`local.hsb`, reloads
   clamd via TCP socket `RELOAD` (port 3310) with `clamdscan --reload` fallback.
3. **CrowdStrike Falcon** (stub) — set `CROWDSTRIKE_CLIENT_ID/SECRET` to activate.
4. **Defender ATP** (stub) — set `DEFENDER_ATP_TENANT_ID/CLIENT_ID/CLIENT_SECRET`.

### API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/ioc/from-sigma-block` | Ingest IOC after confirmed block (auto-triggers EDR enforcement) |
| GET | `/api/ioc` | List/filter (type, status, severity, mitre, search) |
| GET | `/api/ioc/stats` | Badge counters (active / enforced_edr / pending) |
| GET | `/api/ioc/{id}` | Full record incl. timeline |
| POST | `/api/ioc/{id}/enforce-edr` | Manual EDR/AV fan-out |
| POST | `/api/ioc/{id}/whitelist` | Whitelist (justification required) |
| POST | `/api/ioc/{id}/expire` | Force-expire + unblock everywhere |
| POST | `/api/ioc/expire-sweep` | Run TTL sweep now |

### WebSocket events

- `ioc_progress` — `{decision_id, ioc_id, step: fortigate|edr|recorded, status, message}`
- `ioc_enforced` — `{ioc_id, value, blocked_on, results: {connector: {...}}}`
- `ioc_update` — status changes (created / whitelisted / expired)

## Frontend

- **`/ioc` page** (`frontend/src/pages/IOCManagementView.jsx`) — filterable table,
  FortiGate/EDR/AV badges (greyed when not enforced), stat cards, CSV export,
  detail drawer with the Sigma→Wazuh→Brain→HITL→FortiGate→EDR kill-chain timeline,
  row actions (Enforce on EDR / Whitelist w/ justification / Force Expire).
  Falls back to demo data when the backend is offline.
- **`IOCEnforcementChecklist`** — live animated sub-status on the HITL card after
  approval: "Blocking on FortiGate... ✅ → Pushing to EDR... ✅ → IOC recorded ✅"
- **`utils/iocEvents.js`** — pub/sub bridging WS events to both UIs.

## Configuration (backend/.env)

```env
WAZUH_AR_COMMAND=firewall-drop
WAZUH_AR_BLOCK_MINUTES=0        # 0 = permanent
CLAMAV_HDB_PATH=/var/lib/clamav/local.hdb
CLAMAV_HSB_PATH=/var/lib/clamav/local.hsb
CLAMAV_HOST=localhost
CLAMAV_PORT=3310
# Optional commercial EDR (stubs until set)
CROWDSTRIKE_CLIENT_ID=
CROWDSTRIKE_CLIENT_SECRET=
DEFENDER_ATP_TENANT_ID=
DEFENDER_ATP_CLIENT_ID=
DEFENDER_ATP_CLIENT_SECRET=