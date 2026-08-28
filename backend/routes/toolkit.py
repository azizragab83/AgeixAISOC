"""Cyber Toolkit Intelligence — Real tool recommendations mapped to MITRE ATT&CK techniques."""

import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("ageixaisoc.routes.toolkit")
router = APIRouter(tags=["toolkit"])

# Real tool mappings based on industry-standard red team / pentesting tools
TOOLKIT = {
    "T1110": {
        "technique": "Brute Force",
        "tools": [
            {"name": "Hydra", "url": "https://github.com/vanhauser-thc/thc-hydra", "category": "Credential Attack", "os": "Cross-platform"},
            {"name": "NetExec", "url": "https://github.com/Pennyw0rth/NetExec", "category": "Credential Attack", "os": "Linux"},
            {"name": "John the Ripper", "url": "https://github.com/openwall/john", "category": "Password Cracking", "os": "Cross-platform"},
            {"name": "Hashcat", "url": "https://github.com/hashcat/hashcat", "category": "Password Cracking", "os": "Cross-platform"},
        ]
    },
    "T1003": {
        "technique": "OS Credential Dumping",
        "tools": [
            {"name": "Mimikatz", "url": "https://github.com/gentilkiwi/mimikatz", "category": "Credential Dumping", "os": "Windows"},
            {"name": "Evil-WinRM", "url": "https://github.com/Hackplayers/evil-winrm", "category": "Remote Access", "os": "Linux"},
            {"name": "Impacket-secretsdump", "url": "https://github.com/fortra/impacket", "category": "Credential Dumping", "os": "Linux"},
            {"name": "LaZagne", "url": "https://github.com/AlessandroZ/LaZagne", "category": "Credential Recovery", "os": "Cross-platform"},
        ]
    },
    "T1059": {
        "technique": "Command and Scripting Interpreter",
        "tools": [
            {"name": "Metasploit Framework", "url": "https://github.com/rapid7/metasploit-framework", "category": "Exploitation Framework", "os": "Cross-platform"},
            {"name": "Sliver C2", "url": "https://github.com/BishopFox/sliver", "category": "C2 Framework", "os": "Cross-platform"},
            {"name": "Cobalt Strike", "url": "https://www.cobaltstrike.com/", "category": "C2 Framework", "os": "Windows"},
            {"name": "PowerShell Empire", "url": "https://github.com/BC-SECURITY/Empire", "category": "Post-Exploitation", "os": "Cross-platform"},
        ]
    },
    "T1046": {
        "technique": "Network Service Discovery",
        "tools": [
            {"name": "RustScan", "url": "https://github.com/RustScan/RustScan", "category": "Port Scanner", "os": "Cross-platform"},
            {"name": "Nmap", "url": "https://nmap.org", "category": "Network Scanner", "os": "Cross-platform"},
            {"name": "Masscan", "url": "https://github.com/robertdavidgraham/masscan", "category": "Mass Port Scanner", "os": "Linux"},
            {"name": "Zmap", "url": "https://github.com/zmap/zmap", "category": "Network Scanner", "os": "Linux"},
        ]
    },
    "T1048": {
        "technique": "Exfiltration Over Alternative Protocol",
        "tools": [
            {"name": "Impacket", "url": "https://github.com/fortra/impacket", "category": "Network Protocols", "os": "Linux"},
            {"name": "Chisel", "url": "https://github.com/jpillora/chisel", "category": "Tunneling", "os": "Cross-platform"},
            {"name": "DNSExfiltrator", "url": "https://github.com/Arno0x/DNSExfiltrator", "category": "DNS Exfiltration", "os": "Windows"},
            {"name": "Rsync", "url": "https://rsync.samba.org/", "category": "File Transfer", "os": "Linux"},
        ]
    },
    "T1078": {
        "technique": "Valid Accounts",
        "tools": [
            {"name": "CrackMapExec", "url": "https://github.com/byt3bl33d3r/CrackMapExec", "category": "Credential Abuse", "os": "Linux"},
            {"name": "BloodHound", "url": "https://github.com/BloodHoundAD/BloodHound", "category": "AD Enumeration", "os": "Cross-platform"},
            {"name": "Impacket-psexec", "url": "https://github.com/fortra/impacket", "category": "Remote Execution", "os": "Linux"},
        ]
    },
    "T1021": {
        "technique": "Remote Services",
        "tools": [
            {"name": "NetExec", "url": "https://github.com/Pennyw0rth/NetExec", "category": "Remote Access", "os": "Linux"},
            {"name": "Impacket-wmiexec", "url": "https://github.com/fortra/impacket", "category": "WMI Execution", "os": "Linux"},
            {"name": "PsExec", "url": "https://docs.microsoft.com/en-us/sysinternals/downloads/psexec", "category": "Remote Execution", "os": "Windows"},
        ]
    },
    "T1566": {
        "technique": "Phishing",
        "tools": [
            {"name": "GoPhish", "url": "https://github.com/gophish/gophish", "category": "Phishing Framework", "os": "Cross-platform"},
            {"name": "Social Engineering Toolkit", "url": "https://github.com/trustedsec/social-engineer-toolkit", "category": "Social Engineering", "os": "Linux"},
            {"name": "Evilginx2", "url": "https://github.com/kgretzky/evilginx2", "category": "Phishing Proxy", "os": "Linux"},
        ]
    },
    "T1190": {
        "technique": "Exploit Public-Facing Application",
        "tools": [
            {"name": "Metasploit Framework", "url": "https://github.com/rapid7/metasploit-framework", "category": "Exploitation", "os": "Cross-platform"},
            {"name": "Searchsploit", "url": "https://github.com/offensive-security/exploitdb", "category": "Exploit Search", "os": "Linux"},
            {"name": "Nuclei", "url": "https://github.com/projectdiscovery/nuclei", "category": "Vulnerability Scanner", "os": "Cross-platform"},
        ]
    },
    "T1547": {
        "technique": "Boot or Logon Autostart Execution",
        "tools": [
            {"name": "SharPersist", "url": "https://github.com/mandiant/SharPersist", "category": "Persistence", "os": "Windows"},
            {"name": "PersistenceSniper", "url": "https://github.com/last-byte/PersistenceSniper", "category": "Persistence Detection", "os": "Windows"},
        ]
    },
    "T1055": {
        "technique": "Process Injection",
        "tools": [
            {"name": "Cobalt Strike", "url": "https://www.cobaltstrike.com/", "category": "Process Injection", "os": "Windows"},
            {"name": "SharpInject", "url": "https://github.com/pwntester/SharpInject", "category": "Process Injection", "os": "Windows"},
        ]
    },
}

# OSINT & Recon tools that are technique-agnostic
OSINT_TOOLS = [
    {"name": "SpiderFoot", "url": "https://github.com/smicallef/spiderfoot", "category": "OSINT Automation", "os": "Cross-platform"},
    {"name": "Sherlock", "url": "https://github.com/sherlock-project/sherlock", "category": "Username Search", "os": "Linux"},
    {"name": "theHarvester", "url": "https://github.com/laramies/theHarvester", "category": "Email/Subdomain Enumeration", "os": "Linux"},
    {"name": "Recon-ng", "url": "https://github.com/lanmaster53/recon-ng", "category": "Web Reconnaissance", "os": "Linux"},
    {"name": "Shodan", "url": "https://www.shodan.io/", "category": "Internet Device Search", "os": "Web"},
    {"name": "Amass", "url": "https://github.com/owasp-amass/amass", "category": "Attack Surface Mapping", "os": "Cross-platform"},
    {"name": "Maltego", "url": "https://www.maltego.com/", "category": "Link Analysis", "os": "Cross-platform"},
]

ALL_TECHNIQUES = sorted(TOOLKIT.keys())


@router.get("/api/toolkit")
async def list_techniques():
    """List all MITRE techniques available in the toolkit."""
    return {
        "techniques": ALL_TECHNIQUES,
        "count": len(ALL_TECHNIQUES),
        "osint_tools": OSINT_TOOLS,
    }


@router.get("/api/toolkit/recommend/{mitre_technique}")
async def recommend_tools(mitre_technique: str):
    """Get real tool recommendations for a given MITRE ATT&CK technique."""
    mitre_upper = mitre_technique.upper()

    if mitre_upper not in TOOLKIT:
        raise HTTPException(
            status_code=404,
            detail=f"MITRE technique '{mitre_upper}' not found in toolkit. Available: {', '.join(ALL_TECHNIQUES)}"
        )

    entry = TOOLKIT[mitre_upper]
    return {
        "mitre_id": mitre_upper,
        "technique": entry["technique"],
        "tools": entry["tools"],
        "tool_count": len(entry["tools"]),
        "osint_tools": OSINT_TOOLS,
    }