"""Full 8-node pipeline end-to-end test with timing."""

import json
import sys
import time

sys.path.insert(0, ".")

try:
    from orchestrator import soc_runner
except ImportError:
    from backend.orchestrator import soc_runner

ALERT = {
    "alert_id": "TEST-004",
    "timestamp": "2026-08-01T15:00:00Z",
    "rule_id": 41004,
    "rule_description": "Audit: Linux auditd rule matched",
    "severity": 8,
    "source_ip": "192.168.56.10",
    "destination_ip": "192.168.56.20",
    "protocol": "ssh",
    "agent_id": "001",
    "agent_name": "win10-victim",
    "location": "win10-victim",
}


async def main():
    print("Starting full 8-node pipeline for TEST-004...")
    t0 = time.monotonic()
    pkg = await soc_runner.run(ALERT["alert_id"], ALERT)
    elapsed = time.monotonic() - t0
    print(f"\n=== PIPELINE COMPLETED in {elapsed:.2f}s ===")

    fields = {
        "decision_id": pkg.get("decision_id"),
        "blue_team_result": pkg.get("blue_team_result"),
        "gap_detected": pkg.get("gap_detected"),
        "sigma_rule_generated": pkg.get("sigma_rule_generated"),
        "deployment_status": pkg.get("deployment_status"),
        "gap_closed": pkg.get("gap_closed"),
        "new_rule_id": pkg.get("new_rule_id"),
    }
    print("\n=== REQUESTED FIELDS ===")
    print(json.dumps(fields, indent=2, default=str))

    print("\n=== FULL DECISION PACKAGE KEYS ===")
    print(json.dumps(list(pkg.keys()), indent=2))

    return pkg


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
