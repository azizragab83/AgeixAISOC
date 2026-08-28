# Skill: Review — Detection & Code Quality (distilled from garrytan/gstack)

## Iron Law
A detection that never fires, or fires on everything, is worse than no detection.
Every rule must state its expected true-positive and false-positive profile.

## Methodology (applied by AgeixAISOC Detection Engineering agent)

1. **Intent Statement**: What adversary behavior does this catch? Map to MITRE technique.
2. **Signal Quality**:
   - Is the selection field stable (not easily bypassed by rename/path swap)?
   - Does it use wildcard overuse? (`*\powershell*` = weak)
3. **Noise Budget**:
   - Estimate daily hit volume in this environment.
   - If > 20/day without aggregation → add correlation or condition filters.
4. **Bypass Review**:
   - Can attacker evade by encoding, obfuscation, alternate tool?
   - Prefer behavior-level fields (CommandLine, ScriptBlockLogging) over binary names.
5. **Testability**: Provide one benign event + one malicious event that must be
   distinguished. If impossible, the rule is too broad.

## Output Contract (JSON)
{
  "verdict": "ship|fix|reject",
  "issues": [{"severity":"high|med|low","issue":"...","fix":"..."}],
  "expected_fp_rate": "low|medium|high",
  "bypass_risks": ["..."]
}
