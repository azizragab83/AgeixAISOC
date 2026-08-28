"""Chapters 1-2: Introduction; Problem Definition, Motivation and Objectives."""
from helpers import add_para, add_heading, add_table, add_page_break


def build():
    # ══════════════════════════════════════════════════
    # CHAPTER 1 — INTRODUCTION
    # ══════════════════════════════════════════════════
    add_heading("Chapter 1 — Introduction", 1)
    add_heading("1.1 Background and Context", 2)
    for p in [
        "Modern organizations generate an overwhelming volume of security telemetry from firewalls, endpoints, identity systems, cloud workloads, and network sensors. A typical Security Operations Center (SOC) analyst is expected to triage this telemetry, correlate it against threat intelligence, judge its severity, and decide on a response — often within minutes, and often for dozens of alerts within a single shift. In practice, this responsibility routinely exceeds what a human team can sustain, and this leads to well-documented failure modes: alert fatigue, missed or delayed detections, inconsistent triage quality between analysts of differing experience levels, and detection rules that fall out of date as adversary techniques evolve faster than signatures can be written and reviewed.",
        "According to industry reports, the average SOC handles over ten thousand alerts per day, of which roughly seventy percent are false positives. This volume of noise causes analyst burnout, high turnover, and — critically — leads to missed real threats buried among routine, low-value alerts. The Mean Time to Detect (MTTD) in some organizations reaches as high as two hundred and seven days, a window that gives attackers ample opportunity to move laterally, escalate privileges, and exfiltrate sensitive data long before a human analyst becomes aware that anything is wrong.",
        "This gap between the volume of telemetry that must be reviewed and the capacity of human analysts to review it meaningfully is the starting point for this thesis. Rather than treating the volume problem as something to be solved purely by hiring more staff — an approach that does not scale given the well-documented global shortage of cybersecurity professionals — this project explores how a carefully governed set of AI agents can absorb the triage and correlation burden while a human analyst remains the final authority on any action with real-world consequences.",
    ]:
        add_para(p)

    add_heading("1.1.1 The SOC Crisis", 3)
    for p in [
        "The cybersecurity industry faces a critical and persistent shortage of skilled professionals. With more than 3.5 million unfilled cybersecurity positions estimated globally, organizations cannot simply hire their way out of the alert-fatigue problem. This shortage, combined with the increasing sophistication and speed of modern attacks, creates an urgent need for intelligent automation that augments — rather than replaces — human analysts.",
        "The shortage is not evenly distributed: it is most acute at the tier-1 analyst level, precisely the role most exposed to alert-fatigue and burnout. Analysts in this role are commonly expected to make an initial threat-vs-noise judgment on every incoming alert, a task that is repetitive, high-volume, and cognitively demanding in a way that is well suited to augmentation by a reasoning system, provided that system's output remains explainable and reviewable.",
    ]:
        add_para(p)

    add_heading("1.1.2 The Rise of AI in Security", 3)
    for p in [
        'Artificial Intelligence has made significant inroads into cybersecurity, with applications ranging from malware detection and user-behavior analytics to automated phishing classification. However, many AI security solutions operate as "black boxes" — they detect a threat but cannot explain why, which erodes analyst trust and makes the tool difficult to audit or improve. Furthermore, fully autonomous AI systems that take action without human approval pose legal, operational, and reputational risks. A single false positive resulting in a critical production server being isolated can cause a business-disruption incident that costs far more than the security incident it was meant to prevent.',
        "This tension — between the clear need for automation at scale, and the equally clear risk of ungoverned automation — is the central design problem that AgeixAISOC was built to address.",
    ]:
        add_para(p)

    add_heading("1.2 The Need for a Human-Governed AI Platform", 2)
    add_para("AgeixAISOC is a graduation project that explores how a coordinated set of AI agents, operating under an explicit Human-in-the-Loop (HITL) governance model, can absorb much of the triage and correlation burden while leaving consequential decisions — blocking an IP address, isolating a host, disabling a compromised account — with a human analyst. The project treats the AI as a force multiplier for the SOC analyst, not a replacement for their judgment, and this framing is reflected in every architectural decision described in Chapter 3.")

    add_heading("1.2.1 Key Requirements for a Modern SOC Platform", 3)
    for req in [
        "Explainability — every AI recommendation must include clear, human-readable reasoning that references the underlying evidence.",
        "Human Governance — no high-impact action executes without explicit human approval, recorded against a named analyst.",
        "Auditability — every decision, automated or human, must be logged in a form suitable for compliance review and post-incident analysis.",
        "Adaptability — the system must be able to learn from analyst feedback rather than requiring constant manual rule maintenance.",
        "Local Deployment — data sovereignty and confidentiality requirements favor on-premise, self-hosted operation over sending sensitive telemetry to third-party cloud APIs.",
        "Modularity — the platform must integrate cleanly with existing security tools (SIEM, firewall, EDR) rather than requiring a wholesale replacement of the SOC stack.",
    ]:
        add_para("• " + req)

    add_heading("1.3 Project Vision and Scope", 2)
    add_para("The vision of AgeixAISOC is to create a self-improving security platform in which AI agents handle the heavy lifting of detection, correlation, and recommendation; human analysts make the final decision on any high-impact action; a Retrieval-Augmented Generation (RAG) memory layer enables continuous learning from analyst feedback; and a SOAR integration automates response execution once — and only once — that response has been approved.")
    add_para("The scope of this graduation project, as delivered, includes:")
    for item in [
        "Building a live, isolated VMware-based lab environment representative of a small enterprise network.",
        "Integrating Wazuh SIEM as the primary telemetry source and detection-rule deployment target.",
        "Developing a LangGraph-based orchestrator that coordinates a set of specialized AI agents.",
        "Implementing a Human-in-the-Loop approval workflow with Approve / Reject outcomes and analyst notes.",
        "Creating an auditable trail covering every automated and human decision.",
        "Building a RAG-backed memory layer over ChromaDB that reduces repeat false positives over time.",
    ]:
        add_para("• " + item)
    add_para("Items explicitly outside the delivered scope of this graduation project — but retained as prioritized future work in Chapter 7 — include full SOAR execution against production-grade firewalls beyond the lab FortiGate instance, a broad multi-source threat-intelligence fusion layer, and network detection and response (NDR) via Zeek or Arkime.")

    add_heading("1.4 Contributions of this Thesis", 2)
    for item in [
        "A layered reference architecture for an AI-orchestrated SOC that cleanly separates ingestion, detection, orchestration, human decision, and execution concerns, so that any one layer can be extended or replaced without redesigning the others.",
        "A working implementation of that architecture, built on open-source tooling (Wazuh, LangGraph, CrewAI, Ollama, ChromaDB, n8n, FastAPI, React), validated against a live SIEM inside an isolated lab network.",
        "A concrete, auditable Human-in-the-Loop workflow, with defined outcomes (Approve, Reject) and an accompanying audit-trail schema.",
        "A Retrieval-Augmented-Generation feedback loop that converts analyst overrides into a persistent, queryable memory of false positives and confirmed incidents, directly reducing repeat alert fatigue.",
        "An honest, subsystem-level account of current implementation status (Chapter 6), distinguishing confirmed-working functionality from partially implemented and target-design components.",
    ]:
        add_para("• " + item)

    add_heading("1.5 Document Structure", 2)
    add_para("The remainder of this document is organized as follows. Chapter 2 defines the problem being addressed in more depth, reviews related industry and academic work, and states the motivation and objectives of the project. Chapter 3 presents the target and as-built system architecture, including the orchestrator, the agent layer, and the human-approval workflow. Chapter 4 describes the design methodology, the lab environment used to build and validate the platform, and the testing approach. Chapter 5 reports implementation details for each subsystem, including the orchestration graph, the agent-to-LLM mapping, and the RAG memory architecture. Chapter 6 presents results obtained to date and is explicit about which components are confirmed working, which are partially implemented, and which remain design work. Chapter 7 discusses prioritized future work. Chapter 8 concludes the document. References and appendices follow, including lab network addressing, alert decision-state definitions, sample integration code, and a sample generated Sigma rule.")

    add_heading("1.6 The SOC Tiering Model and Where AgeixAISOC Fits", 2)
    for p in [
        "Most conventional SOCs organize analysts into tiers. Tier-1 analysts perform initial triage: they review incoming alerts, discard obvious false positives, and escalate anything that looks genuinely suspicious. Tier-2 analysts investigate escalated incidents in depth, correlating multiple data sources and determining root cause. Tier-3 analysts and threat hunters handle the most complex incidents and proactively search for threats that automated detection has not yet surfaced.",
        "AgeixAISOC is positioned primarily as a Tier-1 augmentation layer: its Detection, Risk Scoring, and Threat Hunter agents perform the same category of work a Tier-1 analyst performs — reading an alert, classifying it, and deciding whether it warrants further attention — but at machine speed and across every incoming alert rather than a manually prioritized subset. The HITL gate then hands the resulting, pre-analyzed decision package to a human analyst for the judgment call that closes out the alert.",
    ]:
        add_para(p)

    add_heading("1.7 Typical Attack Lifecycle and Platform Touchpoints", 2)
    add_para("An attacker first performs reconnaissance against the target network, for example through port scanning. If the attempt escalates to active exploitation — a brute-force credential attack or exploitation of a known vulnerability — that activity generates traffic and log events at the network and host layers. A properly tuned FortiGate IPS and Wazuh SIEM deployment observes this traffic and raises a correlated alert. From that point, the alert enters the AgeixAISOC pipeline: it is analyzed by the agent layer, scored, and presented to a human analyst as a decision package. Only once the analyst approves a response does the Execution Layer act, ideally before the attacker completes lateral movement or achieves their objective.")

    # ══════════════════════════════════════════════════
    # CHAPTER 2 — PROBLEM DEFINITION
    # ══════════════════════════════════════════════════
    add_heading("Chapter 2 — Problem Definition, Motivation and Objectives", 1)
    add_heading("2.1 Problem Definition", 2)
    add_para("Conventional SOC tooling is largely reactive and rule-based. SIEM platforms centralize log collection but leave correlation and triage almost entirely to human analysts; SOAR platforms can automate response, but only for scenarios an engineer has already anticipated and explicitly scripted. Neither layer reasons about a novel alert the way an experienced analyst does — by weighing context, asset criticality, and known adversary behavior together, in real time. This produces three concrete gaps that AgeixAISOC directly targets.")

    add_heading("2.1.1 Gap 1: Triage Bottleneck", 3)
    add_para("Analysts spend the majority of their working time separating benign noise from genuine threats rather than investigating confirmed incidents. With ten thousand or more alerts per day and a seventy-percent false-positive rate, analysts are overwhelmed before they even begin meaningful investigative work. This leads to critical alerts being buried in noise and missed outright, inconsistent triage quality between analysts depending on experience and fatigue level, and, ultimately, burnout and high turnover across SOC teams.")

    add_heading("2.1.2 Gap 2: Static Detection", 3)
    add_para("Signature- and rule-based detections do not adapt automatically when a red-team exercise or a real incident reveals a coverage gap. The process of writing, testing, and deploying a new detection rule is manual, slow, and requires specialized expertise in the target SIEM's rule syntax. This means new attack techniques can go undetected for extended periods, and detection coverage silently erodes over time as the environment and the threat landscape both change.")

    add_heading("2.1.3 Gap 3: Fragmented Accountability", 3)
    add_para("When automation is introduced into a SOC without a coherent governance model, it is often difficult to reconstruct why a given action was taken, by which component, and under whose approval. This fragmentation creates compliance and audit challenges during regulatory review, an inability to learn systematically from past decisions, and — perhaps most damaging in practice — reduced analyst trust in the automation itself.")

    add_heading("2.2 Literature and Industry Review", 2)
    for p in [
        "The idea of applying machine learning to security alert triage is not new; anomaly-detection and user-behavior-analytics (UEBA) systems have been part of commercial SIEM offerings for over a decade. What has changed more recently is the availability of large language models capable of reading unstructured alert context, correlating it against known frameworks such as MITRE ATT&CK, and producing a human-readable rationale — a capability that earlier rule-based and purely statistical systems lacked.",
        "Prior academic work on Explainable AI (XAI) has established that a system's usefulness to a human operator depends heavily on the operator's ability to understand and verify its reasoning, not merely on the system's raw accuracy [1]. This finding directly informed the decision to make every AgeixAISOC agent output an explicit natural-language rationale rather than a bare classification label.",
        "Separately, research on automated detection-rule generation has shown that mapping observed behavior to MITRE ATT&CK techniques can meaningfully accelerate the process of turning a novel detection into a deployable Sigma rule [2], while studies on false-positive rates in SIEM environments confirm that the seventy-percent figure commonly cited in industry reports is broadly consistent with SIEM deployments observed in academic evaluations [3]. Finally, work specifically addressing human-in-the-loop design for security automation has argued that analyst trust — and therefore real-world adoption — depends on a system that can be overridden, not merely one that is statistically accurate [4]. AgeixAISOC's HITL approval gate is a direct architectural response to this finding.",
    ]:
        add_para(p)

    add_heading("2.3 Motivation", 2)
    add_para("The motivation for AgeixAISOC is to demonstrate, in a controlled lab environment, that an orchestrated set of specialized AI agents can perform the detection-to-recommendation portion of the SOC workflow reliably enough to be genuinely useful, while a strict human-approval gate prevents the well-known risks of fully autonomous security response — namely, false positives triggering business-impacting actions, or an attacker manipulating the automation pipeline itself to cause a denial-of-service against the organization's own infrastructure.")

    add_heading("2.3.1 Academic Motivation", 3)
    add_para("The project serves as a practical, hands-on integration of the skills developed throughout the Digilians Cybersecurity track: SIEM operation using Wazuh, network security device configuration on FortiGate, Active Directory administration, offensive-security fundamentals used to generate realistic lab traffic, secure software architecture, and the integration of AI and machine-learning components into a live security workflow.")

    add_heading("2.3.2 Industry Motivation", 3)
    add_para("The cybersecurity industry is at a crossroads. The shortage of skilled analysts, combined with the increasing volume and sophistication of attacks, demands genuinely useful automation rather than incremental tooling improvements. AgeixAISOC explores a path in which AI handles the volume and combinatorial complexity of triage while humans retain control and accountability.")

    add_heading("2.4 Objectives", 2)
    for item in [
        "Design a layered SOC architecture that clearly separates ingestion, detection, orchestration, human decision, and execution concerns.",
        "Implement a central orchestrator that coordinates specialized AI agents for detection, risk scoring, threat hunting, and recommendation generation.",
        "Integrate a live SIEM (Wazuh) as the primary telemetry and detection-rule deployment source.",
        "Implement a Human-in-the-Loop approval workflow so that no high-impact action executes without explicit analyst sign-off.",
        "Build an isolated, realistic lab network in which detection and orchestration logic can be exercised safely against representative attack scenarios.",
        "Produce an auditable record of every automated decision and every human decision made against it.",
        "Implement a Retrieval-Augmented-Generation memory layer that reduces repeat false positives based on analyst feedback.",
        "Identify, honestly, which components are fully working, which are partially working, and which remain future work.",
    ]:
        add_para("• " + item)

    add_heading("2.5 Comparative Analysis with Existing Approaches", 2)
    add_para("To situate AgeixAISOC relative to existing SOC tooling, Table 2.1 compares four categories of solution against the requirements identified in Section 1.2.1: traditional rule-based SIEM, commercial SOAR platforms, fully autonomous \"AI SOC\" offerings, and AgeixAISOC's own human-governed multi-agent design.")
    add_table(["Requirement", "Rule-based SIEM", "Commercial SOAR", "Autonomous AI SOC", "AgeixAISOC"], [
        ["Explainable recommendations", "No", "Partial", "Often opaque", "Yes — rationale on every output"],
        ["Human override before action", "N/A (no action)", "Yes, if configured", "Often optional/bypassable", "Mandatory HITL gate"],
        ["Adapts from analyst feedback", "No", "No", "Varies", "Yes — RAG feedback loop"],
        ["Full audit trail of AI + human decisions", "Partial", "Yes", "Varies", "Yes"],
        ["On-premise / local LLM inference", "N/A", "Varies", "Usually cloud-hosted", "Yes — Ollama, local"],
        ["Self-generates new detection rules", "No", "No", "Rare", "Yes — Detection Engineering Agent"],
    ], "Table 2.1 — Comparative Positioning of AgeixAISOC Against Existing SOC Tooling Categories")

    add_heading("2.6 Assumptions and Constraints", 2)
    for item in [
        "The platform was developed and tested against a lab network of modest scale (six hosts); its behavior at production alert volumes (thousands of alerts per day) has not yet been empirically validated.",
        "LLM inference runs locally via Ollama on commodity hardware; response latency under heavier concurrent load has not been benchmarked as part of this thesis.",
        "The Red Team Validation Agent is restricted, by policy and by network isolation, to the authorized lab environment described in Section 4.2 and Appendix A.",
        "Analyst feedback used to populate the RAG memory layer was generated by the project team acting in the analyst role during testing, not by independent third-party SOC analysts.",
    ]:
        add_para("• " + item)