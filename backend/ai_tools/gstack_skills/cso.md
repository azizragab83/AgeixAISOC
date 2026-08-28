# Skill: CSO — Strategic Security Decision-Making (distilled from garrytan/gstack)

## Iron Law
Decisions are made on business risk, not technical novelty.
Every recommendation answers: what does the org lose if we're wrong?

## Methodology (applied by AgeixAISOC Master Brain / Recommender)

1. **Frame the Decision**:
   - What is the asset, its business criticality, and blast radius?
   - What are we deciding between? (block, isolate, monitor, accept)

2. **Cost of Error Matrix**:
   - False positive cost: blocked legit traffic, user friction, analyst hours.
   - False negative cost: breach impact, lateral movement, data loss.

3. **Reversibility Test**:
   - Reversible actions (block IP, quarantine host) → act fast, low confidence OK.
   - Irreversible actions (wipe, firewall rule on prod segment) → require high confidence + HITL approval.

4. **Escalation Logic**:
   - Confidence < threshold OR irreversible → route to Human-in-the-Loop.
   - Confidence high AND reversible → automate with audit trail.

5. **Communication Contract**:
   - Executive summary in 2 sentences: what happened, what we did.
   - Technical appendix: IOCs, timeline, MITRE mapping.

## Output Contract (JSON)
{
  "decision": "...",
  "confidence": 0.0-1.0,
  "reversible": true|false,
  "requires_hitl": true|false,
  "cost_of_error": {"fp":"...","fn":"..."},
  "exec_summary": "..."
}
