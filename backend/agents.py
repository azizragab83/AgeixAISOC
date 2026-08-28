"""
AgeixAISOC - AI Agents Definition
Lightweight version for cloud deployment - uses langchain-ollama directly (no crewai needed)
Supports Groq API as a cloud fallback for SaaS deployment.
"""

import os
import logging

try:
    from .config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# LLM Backends (Local Ollama or Groq API for cloud)
# ──────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
USE_GROQ = bool(GROQ_API_KEY)


class SimpleAgent:
    """Lightweight agent wrapper that calls an LLM directly without crewai."""
    
    def __init__(self, role: str, goal: str, backstory: str, llm, tools=None, **kwargs):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.llm = llm
        self.tools = tools or []
        self.max_iter = kwargs.get("max_iter", 3)
        self.verbose = kwargs.get("verbose", False)
    
    def execute_task(self, task) -> str:
        """Execute a task using the LLM directly."""
        prompt = f"""
Role: {self.role}
Goal: {self.goal}
Backstory: {self.backstory}

Task:
{task}
"""
        try:
            response = self.llm.invoke(prompt)
            if hasattr(response, "content"):
                return response.content
            return str(response)
        except Exception as e:
            logger.error(f"Agent {self.role} failed: {e}")
            raise


def _create_llm(model: str, temperature: float):
    """Create an LLM instance using Groq API if available, otherwise local Ollama."""
    if USE_GROQ:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model,
                api_key=GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
                temperature=temperature,
                max_tokens=4096,
            )
        except ImportError:
            logger.warning("langchain-openai not installed, falling back to Ollama")
    
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=temperature,
            num_predict=4096,
        )
    except ImportError:
        logger.warning("langchain-ollama not installed, using fallback LLM")
        # Fallback: simple mock LLM that returns structured JSON
        class _FallbackLLM:
            def invoke(self, prompt):
                return '{"is_threat": true, "threat_type": "unknown", "severity": "medium", "confidence": 0.5}'
        return _FallbackLLM()


def _get_tools(name: str) -> list:
    """Get tools for an agent (simplified for cloud)."""
    try:
        from ai_tools.cognitive_arsenal import get_cognitive_tools
        return get_cognitive_tools(name)
    except Exception:
        return []


threat_llm = _create_llm(settings.OLLAMA_MODEL_THREAT, 0.1)
coder_llm = _create_llm(settings.OLLAMA_MODEL_CODER, 0.2)
general_llm = _create_llm(settings.OLLAMA_MODEL_GENERAL, 0.3)

# ──────────────────────────────────────────────
# Agent Definitions
# ──────────────────────────────────────────────

threat_detection_agent = SimpleAgent(
    role="Threat Detection Analyst",
    goal="Analyze incoming Wazuh alerts and identify potential security threats with high accuracy.",
    backstory=(
        "You are a senior SOC analyst with 15 years of experience in threat detection. "
        "You specialize in analyzing SIEM alerts, correlating indicators of compromise, "
        "and identifying both known and zero-day attack patterns. You never miss a critical alert."
    ),
    llm=threat_llm,
    verbose=True,
    allow_delegation=False,
    max_iter=3,
)

risk_scoring_agent = SimpleAgent(
    role="Risk Scoring Specialist",
    goal="Assign a quantitative risk score (0-100) to each validated threat based on CVSS, asset criticality, and environmental context.",
    backstory=(
        "You are a risk assessment expert who quantifies cyber threats using industry-standard frameworks. "
        "You consider CVSS vectors, asset value, network exposure, and business impact to produce "
        "actionable risk scores that prioritize response efforts."
    ),
    llm=general_llm,
    verbose=True,
    allow_delegation=False,
    max_iter=3,
)

recommendation_agent = SimpleAgent(
    role="SOAR Recommendation Engineer",
    goal="Generate precise, executable SOAR playbook recommendations for each validated threat.",
    backstory=(
        "You are an automation engineer who designs incident response playbooks. "
        "You map threats to MITRE ATT&CK techniques and recommend specific actions "
        "such as IP blocking via FortiGate, endpoint isolation, or firewall rule updates. "
        "Your recommendations are always concrete and machine-executable."
    ),
    llm=coder_llm,
    verbose=True,
    allow_delegation=False,
    max_iter=3,
)

threat_hunter_agent = SimpleAgent(
    role="Proactive Threat Hunter",
    goal="Search for additional indicators of compromise and lateral movement indicators across the environment.",
    backstory=(
        "You are a threat hunter who proactively searches for hidden threats. "
        "You analyze network logs, endpoint telemetry, and authentication events to "
        "uncover attacker footholds, persistence mechanisms, and data exfiltration signs. "
        "You think like an adversary to find what others miss."
    ),
    llm=threat_llm,
    verbose=True,
    allow_delegation=False,
    max_iter=3,
    tools=_get_tools("threat_hunter"),
)

forensics_agent = SimpleAgent(
    role="Digital Forensics Investigator",
    goal="Conduct deep forensic analysis on affected systems to determine root cause, timeline, and impact.",
    backstory=(
        "You are a certified forensic investigator (GCFE/GCFA) who reconstructs attack timelines "
        "from system artifacts, memory dumps, and log sources. You provide detailed root cause "
        "analysis with evidence chains suitable for incident reports and legal proceedings."
    ),
    llm=general_llm,
    verbose=True,
    allow_delegation=False,
    max_iter=3,
    tools=_get_tools("forensics"),
)

red_team_agent = SimpleAgent(
    role="Red Team Operator",
    goal="Simulate adversary TTPs to validate detection coverage and test defensive controls.",
    backstory=(
        "You are an offensive security expert who emulates real-world threat actors. "
        "You design and execute controlled attack simulations to test the SOC's detection "
        "and response capabilities. Your goal is to improve defenses by finding gaps "
        "before real adversaries do."
    ),
    llm=coder_llm,
    verbose=True,
    allow_delegation=False,
    max_iter=3,
)

# ──────────────────────────────────────────────
# Agent Registry
# ──────────────────────────────────────────────

detection_engineer_agent = SimpleAgent(
    role="Detection Engineer",
    goal="Generate Sigma detection rules to close coverage gaps based on threat analysis.",
    backstory=(
        "You are a detection engineer who writes high-quality Sigma rules for SIEM platforms. "
        "You translate threat intelligence into precise detection logic, ensuring rules are "
        "performant, accurate, and have minimal false positives."
    ),
    llm=coder_llm,
    verbose=True,
    allow_delegation=False,
    max_iter=3,
    tools=_get_tools("detection_engineer"),
)

blue_team_agent = SimpleAgent(
    role="Blue Team Detection Validator",
    goal="Validate whether an existing Wazuh detection rule covers the threat pattern identified by the Red Team.",
    backstory=(
        "You are a Blue Team detection engineer who maintains the Wazuh rulebase. "
        "You review threat intelligenceand cross-reference it against deployed detection rules "
        "to determine if the SOC can already detect a given attack. "
        "You identify detection gaps so the team can write new Sigma rules to close them."
    ),
    llm=general_llm,
    verbose=True,
    allow_delegation=False,
    max_iter=3,
)

# ── Agent 8: UEBA (User & Entity Behavior Analytics) ──
ueba_agent = SimpleAgent(
    role="UEBA Behavior Analyst",
    goal="Identify anomalous user and entity behavior: impossible travel, off-hours access, privilege spikes, and repetitive failures.",
    backstory="You build behavioral baselinesand flag deviations that indicate compromised accounts, insider threats, or lateral movement.",
    llm=general_llm, verbose=True, allow_delegation=False, max_iter=3,
)



# ── Agent 9: OSINT (Open Source Intelligence) ──
osint_agent = SimpleAgent(
    role="OSINT Intelligence Analyst",
    goal="Enrich alert indicators (IPs, hashes, domains)with threat intelligence: reputation, malware families, botnet membership, actor attribution.",
    backstory="You track emerging threats across botnet feeds, dark web forums, and malware sandboxes, correlating indicators to known actors.",
    llm=general_llm, verbose=True, allow_delegation=False, max_iter=3,
    tools=_get_tools("osint"),
)

AGENT_REGISTRY = {
    "threat_detection": threat_detection_agent,
    "risk_scoring": risk_scoring_agent,
    "recommendation": recommendation_agent,
    "threat_hunter": threat_hunter_agent,
    "forensics": forensics_agent,
    "red_team": red_team_agent,
    "blue_team": blue_team_agent,
    "detection_engineer": detection_engineer_agent,
    "ueba": ueba_agent,
    "osint": osint_agent,
}

def get_agent(name: str):
    """Retrieve an agent by name from the registry."""
    agent = AGENT_REGISTRY.get(name)
    if not agent:
        raise ValueError(f"Unknown agent: {name}. Available: {list(AGENT_REGISTRY.keys())}")
    return agent