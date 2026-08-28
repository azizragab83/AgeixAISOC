# Skill: Investigate — Root-Cause Debugging (distilled from garrytan/gstack)

## Iron Law
No fix without investigation. Never guess — trace evidence first.
Stop after 3 failed hypotheses and re-collect data.

## Methodology (applied by AgeixAISOC Forensics & Red Team agents)

1. **Reproduce / Anchor**: Identify the exact observable event (alert, log line, process).
   - What fired? Which rule ID, EventID, or signature?
   - On which host, at what timestamp?

2. **Trace Data Flow Backwards**:
   - Process tree: parent -> child chain before the event.
   - Network flow: source IP reputation, destination contacted, protocol, bytes.
   - Authentication: who logged in, from where, with what credential type.

3. **Form Hypotheses** (max 3):
   - H1: Known malware family / commodity attack.
   - H2: Living-off-the-Land (LOLBAS) abuse of legitimate tooling.
   - H3: Insider / credential misuse.

4. **Test Each Hypothesis Against Evidence**:
   - Does the artifact hash match known intel? (OSINT lookup)
   - Is the parent process expected for this user/host baseline?
   - Do timeline events correlate across endpoint + network?

5. **Root Cause Statement Format**:
   "Because [evidence A], and [evidence B], the root cause is [X],
    not [Y] because [contradicting evidence]."

6. **Confidence Scoring**:
   - 0.9+ : multiple independent artifacts confirm same root cause.
   - 0.6-0.9: strong single-source evidence.
   - <0.6: hypothesis only — flag for further hunting.

## Output Contract (JSON)
{
  "root_cause": "...",
  "hypotheses_tested": [{"id":"H1","verdict":"confirmed|rejected","evidence":"..."}],
  "confidence": 0.0-1.0,
  "evidence_gaps": ["..."],
  "next_investigation_step": "..."
}
