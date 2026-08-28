"""Chapters 3-4: System Architecture; Methodology."""
from helpers import add_para, add_heading, add_table, add_code_block, add_page_break


def build():
    # ══════════════════════════════════════════════════
    # CHAPTER 3 — SYSTEM ARCHITECTURE
    # ══════════════════════════════════════════════════
    add_heading("Chapter 3 — System Architecture", 1)
    add_heading("3.1 Layered Overview", 2)
    add_para("AgeixAISOC is organized into layers that mirror the natural lifecycle of a security alert: from raw telemetry, through AI-driven analysis, to a human decision, to an executed and audited response. This layering is the single most important architectural decision in the project, because it is what allows the human-approval gate in Section 3.3 to sit as a clean, mandatory checkpoint between analysis and execution, rather than being scattered throughout the codebase as ad-hoc checks.")

    add_heading("3.1.1 Ingestion Layer", 3)
    add_para("The Ingestion Layer receives telemetry from Wazuh via a custom webhook integration (POST /webhook/wazuh-alert), normalizes the resulting JSON payload into a common alert schema, applies geo-enrichment to source IP addresses, and de-duplicates repeated alerts (same source IP, destination IP, and rule ID within a 120-second window) before passing the alert further down the pipeline.")

    add_heading("3.1.2 Normalization Layer", 3)
    add_para("The Normalization Layer maps heterogeneous log formats into a single common alert schema (WazuhAlert Pydantic model). This ensures that all downstream components — the agents, the orchestrator, and the dashboard — work with a consistent data model regardless of the originating source, which is what allows new telemetry sources to be added in future work without redesigning the agent layer.")

    add_heading("3.1.3 AI Orchestration Layer", 3)
    add_para("The AI Orchestration Layer is a LangGraph-based master orchestrator that sequences agent calls, manages shared state across the pipeline through explicit reducers, and produces the final decision package that is presented to the human analyst. This is the coordinating \"brain\" of the platform, and its internal structure is described in detail in Section 3.2 and again, at the implementation level, in Chapter 5.")

    add_heading("3.1.4 Agent Layer", 3)
    add_para("The Agent Layer consists of ten specialized CrewAI agents, each responsible for one well-defined analytical task: detection, scoring, recommendation, hunting, forensics, red-team validation, blue-team coverage checking, detection engineering, UEBA, and OSINT enrichment. Each agent has a specific role, goal, and backstory prompt, a defined input and output schema, and operates independently of the others, which keeps individual agents testable in isolation.")

    add_heading("3.1.5 Human-in-the-Loop Layer", 3)
    add_para("The Human-in-the-Loop Layer presents AI output to an analyst for approval or rejection before any response executes. This layer includes the decision-card presentation logic on the dashboard's Pending HITL panel, the Approve / Reject controls, analyst note capture, and a queryable decision history. It is described in full in Section 3.3.")

    add_heading("3.1.6 Execution Layer", 3)
    add_para("The Execution Layer carries out approved actions against integrated security controls. At the time of writing, SIEM rule deployment (pushing an approved Sigma rule into Wazuh via its REST API) is fully implemented; SOAR-driven firewall actions execute through an n8n webhook with a direct FortiGate REST API fallback, which currently fails authentication in the lab environment as described in Chapter 6.")

    add_heading("3.1.7 Audit / Governance Layer", 3)
    add_para("The Audit / Governance Layer records every agent output, every human decision, and every execution result for traceability. Decision packages are retained in an in-memory pending_decisions store plus a decision_history list exposed through the /api/alerts/history endpoint, and analyst decisions are additionally persisted into the learned_decisions RAG knowledge base when the analyst opts in.")

    add_heading("3.2 Orchestrator and Agent Layer", 2)
    add_para("At the core of the platform is a LangGraph Master Orchestrator that coordinates a set of specialized CrewAI agents. The orchestrator is responsible for sequencing agent calls in the correct order, running independent agents in parallel where their inputs do not depend on one another, isolating a failing agent from the rest of the pipeline so that a single agent error does not crash the whole analysis, and producing a complete decision package for the HITL checkpoint.")

    add_heading("3.2.1 Agent Descriptions", 3)
    add_table(["Agent", "Responsibility"], [
        ["Threat Detection Agent", "Classifies incoming alerts and maps observed behavior to MITRE ATT&CK techniques."],
        ["Risk Scoring Agent", "Produces a severity score combining threat confidence, asset context, and potential business impact."],
        ["Recommendation Agent", "Proposes executable SOAR playbook actions and explains the reasoning behind them."],
        ["Threat Hunter Agent", "Searches historical telemetry for related indicators and evidence of lateral movement."],
        ["Forensics Agent", "Assembles a chronological timeline of related events for an incident under investigation."],
        ["Red Team Validation Agent", "Operates only within the authorized lab scope to test whether a given attack technique is actually detected."],
        ["Blue Team Validation Agent", "Confirms whether existing Wazuh rules cover the identified threat pattern; flags detection gaps."],
        ["Detection Engineering Agent", "Generates new Sigma rules to close identified detection gaps."],
        ["UEBA Agent", "Analyzes user behavior (LLM-driven, with deterministic rule-engine fallback) to detect anomalies consistent with insider-threat activity."],
        ["OSINT Agent", "Gathers supplementary threat intelligence from open sources and enriches indicators."],
    ], "Table 3.1 — AgeixAISOC Agent Responsibilities")

    add_heading("3.2.2 Agent Workflow", 3)
    add_para("The orchestrator follows a fixed high-level sequence for every incoming alert:")
    for step in [
        "Alert Reception — the Wazuh alert is normalized and passed to the orchestrator as the initial pipeline state.",
        "Parallel Analysis — after Threat Detection completes, three branches launch concurrently: Branch A runs Risk Scoring → Recommendation → Threat Hunter → Forensics → Red Team → Blue Team sequentially; Branch B runs the UEBA agent; Branch C runs the OSINT agent.",
        "Gap Loop (conditional) — if the Blue Team agent finds no existing rule covers the threat pattern, the graph routes through Detection Engineering (Sigma generation) and Gap Closure (rule file write + Wazuh deployment attempt) before synthesis.",
        "Master Synthesis — all branch outputs converge on the Master Synthesis node, where a qwen2.5:14b LLM call synthesizes every agent's JSON output into a unified executive summary, correlated threat narrative, predicted next move, and final risk score.",
        "HITL Checkpoint — the resulting decision package is presented to a human analyst through the dashboard's Pending HITL panel.",
        "Execution — only upon explicit approval is the action executed via the appropriate adapter (n8n SOAR webhook or direct FortiGate API).",
    ]:
        add_para("• " + step)

    add_heading("3.2.3 Orchestrator State Management", 3)
    add_para("LangGraph manages state through a shared SOCState object that persists across every node in the graph. The state contains the current alert information, an append-only list of agent logs, the accumulated decision package, the current node name, and any errors. Because parallel branches write to the same decision_package key, the orchestrator defines custom reducers: a deep-merge reducer for the decision package (so the last-completing branch does not clobber earlier outputs) and a last-write-wins reducer for scalar keys. Passing state explicitly through the graph keeps the pipeline's behavior predictable and makes it straightforward to replay a given alert through the pipeline for debugging.")
    add_code_block(
        'class SOCState(TypedDict):\n'
        '    alert_id: str\n'
        '    raw_alert: Dict[str, Any]\n'
        '    agent_logs: Annotated[List[AgentLog], operator.add]\n'
        '    decision_package: Annotated[DecisionPackage, _merge_decision_packages]\n'
        '    current_node: Annotated[str, _last_write_wins]\n'
        '    errors: Annotated[List[str], operator.add]'
    )
    add_para("Code 3.1 — Orchestrator shared state definition (backend/orchestrator.py).")

    add_heading("3.3 Human-in-the-Loop Governance", 2)
    add_para("A guiding design principle of AgeixAISOC is that the AI orchestrates — it detects, correlates, scores, and recommends — but the human decides. Any action with real-world impact, such as blocking an IP address or deploying a new detection rule, is routed through an approval workflow with two possible outcomes: Approve or Reject. Every decision, along with the analyst's notes, a timestamp, the original AI recommendation, and the final action actually taken, is written to the audit trail described in Section 3.1.7.")

    add_heading("3.3.1 HITL Workflow", 3)
    for step in [
        "The AI generates a decision package containing a threat description, the mapped MITRE technique, a numeric risk score, recommended SOAR actions, and a Master Brain executive summary.",
        "The decision package is presented to the analyst through the dashboard's Pending HITL panel.",
        "The analyst reviews the underlying evidence and the AI's stated reasoning before making a decision.",
        "The analyst selects one of the two available actions: Approve or Reject (with optional analyst notes and an opt-in flag controlling whether the decision is stored in the RAG memory layer).",
        "If Approve is selected, block_ip recommendations are executed by the Execution Layer (n8n webhook first, direct FortiGate API fallback), and the full decision package is forwarded to the n8n SOAR webhook.",
        "If Reject is selected, the alert is closed as a False Positive and — critically — the outcome is ingested into the learned_decisions RAG knowledge base so that similar future alerts benefit from this analyst judgment.",
    ]:
        add_para("• " + step)

    add_heading("3.4 SIEM Integration", 2)
    add_para("AgeixAISOC integrates with a live Wazuh SIEM deployment as its primary source of security telemetry. This integration is used both to ingest alerts for the detection pipeline, via a custom webhook that forwards Wazuh alerts as JSON, and to deploy Sigma detection rules back into Wazuh once a rule generated by the Detection Engineering Agent has been reviewed and approved — closing part of the detection-gap loop.")
    add_para("This bidirectional relationship with the SIEM — consuming alerts and, separately, publishing new detection logic back into the same platform — is what distinguishes AgeixAISOC's SIEM integration from a purely read-only dashboard. It is also the integration point with the clearest evidence of working end-to-end behavior, as documented in Chapter 6.")

    add_heading("3.5 Security and Threat Model", 2)
    add_para("Because AgeixAISOC itself has the ability to trigger security-relevant actions once an analyst approves them, its own security posture matters. The following threat-model considerations informed the design of the HITL gate and the audit trail:")
    add_table(["Threat", "Mitigation in AgeixAISOC"], [
        ["An attacker manipulates telemetry to trigger a false automated response (e.g., a self-inflicted denial of service).",
         "No action executes without an explicit, logged human approval; the AI layer can only propose, never execute. Even natural-language block requests create a pending HITL decision rather than executing directly."],
        ["A compromised analyst account approves a malicious action.",
         "Every approval is bound to analyst notes and a timestamp in the audit trail, supporting after-the-fact accountability and review."],
        ["An LLM hallucinates a plausible-sounding but incorrect recommendation.",
         "Every agent output is accompanied by explicit reasoning and the underlying evidence, so the analyst can verify rather than blindly trust the suggestion."],
        ["Sensitive telemetry is exposed to a third-party cloud API.",
         "LLM inference runs locally via Ollama inside the isolated lab network rather than being sent to an external API."],
        ["A newly generated Sigma rule is deployed with unintended side effects.",
         "Generated rules pass through review endpoints (/api/rules/pending-review, /api/rules/{id}/review) that allow approve-or-remove decisions, including Wazuh rollback on removal."],
    ], "Table 3.2 — Threat Model Summary")

    add_heading("3.6 Scalability Considerations", 2)
    add_para("Although the delivered lab environment comprises six hosts, the layered architecture was deliberately designed with larger deployments in mind. The Ingestion and Normalization layers are stateless with respect to any single alert, which means additional Wazuh managers or additional telemetry sources can be added by extending the ingestion adapters without modifying the orchestrator or agent layer. Because the orchestrator's parallel-analysis step is itself the natural unit of horizontal scaling, running multiple orchestrator instances behind a queue is the intended path to handling higher alert volumes, though this has not yet been implemented or load-tested.")

    add_heading("3.7 Data Handling and Privacy Considerations", 2)
    add_para("Because AgeixAISOC processes security telemetry that may include internal IP addressing, usernames, and process command lines, two design choices were made specifically to limit unnecessary data exposure. First, LLM inference is performed locally via Ollama rather than being sent to a third-party cloud API, so raw telemetry never leaves the isolated lab network during agent reasoning. Second, the RAG memory layer stores embeddings and derived fields such as MITRE technique IDs rather than full raw payloads wherever possible, reducing the amount of sensitive raw data retained in the long-lived vector store.")

    add_heading("3.8 Design Rationale: Why LangGraph and CrewAI", 2)
    for p in [
        "Two frameworks were evaluated for the orchestration and agent layers before LangGraph and CrewAI were selected. A simpler, hand-rolled sequential-function-call pipeline was considered first, but was rejected because it could not cleanly express the parallel-analysis step described in Section 3.2.2, nor could it naturally represent conditional routing for the gap loop without significant custom state-machine code. LangGraph's explicit state graph provided both of these properties out of the box: nodes can run in parallel where the graph topology allows, and conditional edges route flow based on runtime state.",
        "CrewAI was chosen for the agent layer specifically because it treats each agent as an independently configurable unit with its own role, goal, and backstory prompt, and its own tool set, which matched the modularity requirement in Section 1.2.1 more directly than writing each agent as a bespoke LangChain chain would have. This separation is what allowed, for example, the Detection Engineering Agent to be added to the roster of agents after the core pipeline was already stable, without touching the other agents' code.",
    ]:
        add_para(p)

    add_heading("3.9 Functional and Non-Functional Requirements", 2)
    add_para("The requirements below formalize the objectives stated in Section 2.4 into a form suitable for verification against the results reported in Chapter 6. Each functional requirement is cross-referenced to the subsystem responsible for satisfying it.")
    add_table(["ID", "Functional Requirement", "Responsible Subsystem"], [
        ["FR-1", "Ingest alerts from a live SIEM in near real time.", "Ingestion Layer (§3.1.1)"],
        ["FR-2", "Classify each alert against MITRE ATT&CK.", "Detection Agent (§3.2.1)"],
        ["FR-3", "Produce a numeric risk score per alert.", "Risk Scoring Agent (§3.2.1)"],
        ["FR-4", "Search historical telemetry for related activity.", "Threat Hunter Agent (§3.2.1)"],
        ["FR-5", "Propose a remediation action with rationale.", "Recommendation Agent (§3.2.1)"],
        ["FR-6", "Block execution until a human decision is recorded.", "HITL Layer (§3.3)"],
        ["FR-7", "Execute an approved action against the SIEM or firewall.", "Execution Layer (§3.1.6)"],
        ["FR-8", "Record every decision for later audit.", "Audit / Governance Layer (§3.1.7)"],
        ["FR-9", "Reduce repeat false positives using analyst feedback.", "RAG Memory Layer (§5.5–5.6)"],
        ["FR-10", "Generate new detection rules to close coverage gaps.", "Detection Engineering Agent (§3.2.1)"],
    ], "Table 3.3 — Functional Requirements Traceability")
    add_table(["ID", "Non-Functional Requirement", "Status (Ch. 6)"], [
        ["NFR-1", "No high-impact action executes without an explicit, logged human decision.", "Confirmed working"],
        ["NFR-2", "Every automated and human decision is individually auditable.", "Confirmed working"],
        ["NFR-3", "LLM inference runs locally rather than via an external cloud API.", "Confirmed working"],
        ["NFR-4", "The pipeline recovers from a single failing agent without a full crash.", "Confirmed working (lab)"],
        ["NFR-5", "The system operates entirely within an isolated lab network during testing.", "Confirmed working"],
        ["NFR-6", "SOAR-driven firewall actions complete without authentication failure.", "Not yet met — see §6.2.1"],
        ["NFR-7", "All dashboard views reflect live backend state, not mock data.", "Partially met — see §6.2.2"],
    ], "Table 3.4 — Non-Functional Requirements and Current Status")

    # ══════════════════════════════════════════════════
    # CHAPTER 4 — METHODOLOGY
    # ══════════════════════════════════════════════════
    add_heading("Chapter 4 — Methodology", 1)
    add_heading("4.1 Development Approach", 2)
    for p in [
        "The platform was developed iteratively rather than as a single monolithic build. Each subsystem — SIEM integration, the orchestrator, individual agents, the HITL workflow, and the audit trail — was built and tested against the lab environment before being connected to the next subsystem in the chain. Priority was deliberately given to getting the detection-to-recommendation pipeline working end-to-end against real Wazuh alerts before extending breadth, for example by adding additional data sources or additional specialized agents beyond the core four.",
        "This iterative, integration-first approach was chosen specifically to avoid a common failure mode in multi-component AI projects, in which every individual component appears to work in isolation but the full pipeline fails the first time it is connected end-to-end. By validating the narrowest possible working pipeline first — Wazuh alert in, human decision package out — the team ensured that every subsequent addition (a new agent, a new data source, a new dashboard view) was extending a system that was already known to work, rather than being the first true integration test.",
    ]:
        add_para(p)

    add_heading("4.2 Lab Environment", 2)
    add_para("All detection logic, agent behavior, and orchestration flows were developed and validated inside an isolated lab network rather than against production infrastructure. This allowed representative attacks to be safely generated and observed end-to-end, without any risk of the training or testing process itself causing disruption to a live environment.")
    add_table(["Component", "Role"], [
        ["FortiGate VM", "Perimeter firewall and target for SOAR-driven response actions."],
        ["Kali Linux", "Attacker host used to generate representative attack traffic (scans, brute force, exploitation)."],
        ["Windows 10 Pro (Wazuh Agent + Sysmon)", "Monitored endpoint generating host-level telemetry for the SIEM."],
        ["Ubuntu (Wazuh Manager)", "SIEM — the central alert source and the Sigma rule deployment target."],
        ["Metasploitable 2", "Deliberately vulnerable host used for exploitation scenarios."],
        ["Windows Server 2022 (Domain Controller)", "Active Directory environment for identity-based attack scenarios."],
    ], "Table 4.1 — Lab Environment Components")

    add_heading("4.3 Testing Approach", 2)
    for p in [
        "Agent and orchestrator behavior was validated by generating alerts in Wazuh from actions performed on the lab hosts — for example, brute-force login attempts, exploitation of Metasploitable 2, and Sysmon-visible process activity on the Windows 10 endpoint — and confirming that the pipeline correctly ingested the alert, produced a coherent agent analysis, and surfaced the result for human approval within the dashboard. Sigma rule deployment was validated separately by confirming that an approved rule appeared and took effect inside the Wazuh manager, and by generating fresh matching traffic to confirm the newly deployed rule actually fired.",
        "In addition to manual scenario testing, the project includes an automated pytest suite covering the orchestrator graph structure, the HITL endpoint, the AI agents, the cognitive tools, the services layer, the REST routes, and edge cases such as malformed input and unreachable dependencies. Testing was organized around three questions asked of every scenario: did the alert reach the orchestrator at all; did the resulting decision package contain a reasonable, defensible recommendation given the underlying evidence; and did the HITL gate correctly block execution until an analyst decision was recorded.",
    ]:
        add_para(p)

    add_heading("4.4 Tools and Technologies", 2)
    add_table(["Category", "Tools"], [
        ["Orchestration", "LangGraph, LangChain"],
        ["Agent Framework", "CrewAI"],
        ["SIEM", "Wazuh"],
        ["Network Security", "FortiGate (FortiOS)"],
        ["Detection Rules", "Sigma"],
        ["Attack Framework", "MITRE ATT&CK"],
        ["Backend", "FastAPI, Python 3.11+"],
        ["Frontend", "React, Vite, Tailwind CSS"],
        ["Vector Database", "ChromaDB"],
        ["Automation", "n8n"],
        ["LLM Runtime", "Ollama (local models: qwen2.5:14b, qwen2.5-coder:7b, llama3.1, nomic-embed-text)"],
        ["External Intelligence", "DuckDuckGo search, abuse.ch Feodo Tracker, MITRE STIX bundle, NVD API"],
    ], "Table 4.2 — Tools and Technologies")

    add_heading("4.5 Ethical and Operational Considerations", 2)
    add_para("All offensive activity performed as part of this project — including the Nmap scans, brute-force attempts, and exploitation of Metasploitable 2 used to generate test telemetry — was conducted exclusively inside the isolated, host-only lab network described in Section 4.2 and Appendix A, with no route to production infrastructure or the public internet beyond the controlled NAT path used for software updates. The Red Team Validation Agent is explicitly scoped to this lab environment only, and its use outside an authorized lab context is out of scope for this project and is not supported by the current implementation.")

    add_heading("4.6 Risk Analysis During Development", 2)
    add_para("Three risks were identified and actively managed during development. First, the risk that LLM-generated recommendations would be unpredictable or inconsistent across runs was mitigated by constraining every agent's output to a defined structured schema and by preferring smaller, more deterministic models for the highest-frequency classification tasks on the critical path. Second, the risk that lab-generated attack traffic could inadvertently affect systems outside the isolated network was mitigated by strict host-only network segmentation. Third, the risk that the HITL gate could be silently bypassed by a bug in the orchestrator was mitigated by treating the Execution Layer as reachable only from the HITL decision handler, and by verifying this directly during testing — including converting natural-language block requests into pending HITL decisions rather than executing them directly.")

    add_heading("4.7 Team Roles and Contributions", 2)
    add_para("The graduation project was carried out by a four-person team under the supervision described on the title page. Responsibilities were divided along the layers described in Chapter 3 — SIEM and lab-network integration, orchestrator and agent-layer development, frontend dashboard implementation, and documentation and testing — with all four members contributing across layer boundaries during integration weeks, consistent with the iterative approach described in Section 4.1.")