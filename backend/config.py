import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL_THREAT: str = os.getenv("OLLAMA_MODEL_THREAT", "qwen2.5:14b")
    OLLAMA_MODEL_CODER: str = os.getenv("OLLAMA_MODEL_CODER", "qwen2.5-coder:7b")
    OLLAMA_MODEL_GENERAL: str = os.getenv("OLLAMA_MODEL_GENERAL", "llama3.1")
    
    KALI_IP: str = os.getenv("KALI_IP", "192.168.56.10")
    KALI_USER: str = os.getenv("KALI_USER", "aziz")
    KALI_PASS: str = os.getenv("KALI_PASS", "8394")
    
    WAZUH_IP: str = os.getenv("WAZUH_IP", "192.168.56.30")
    WAZUH_USER: str = os.getenv("WAZUH_USER", "wazuh")
    WAZUH_PASS: str = os.getenv("WAZUH_PASS", "wazuh")
    
    FORTIGATE_IP: str = os.getenv("FORTIGATE_IP", "192.168.56.2")
    FORTIGATE_API_KEY: str = os.getenv("FORTIGATE_API_KEY", os.getenv("FORTIGATE_API_TOKEN", ""))
    
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/execute-soar")
    
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    WS_PING_INTERVAL: int = int(os.getenv("WS_PING_INTERVAL", "30"))

    # Extended lab topology
    WIN10_IP: str = os.getenv("WIN10_IP", "192.168.56.20")
    AD_IP: str = os.getenv("AD_IP", "192.168.56.100")
    METASPLOITABLE_IP: str = os.getenv("METASPLOITABLE_IP", "192.168.56.40")

    # Wazuh Manager API (rule deployment)
    WAZUH_API_URL: str = os.getenv("WAZUH_API_URL", "https://192.168.56.30:55000")
    WAZUH_API_USER: str = os.getenv("WAZUH_API_USER", "")
    WAZUH_API_PASS: str = os.getenv("WAZUH_API_PASS", "")
    WAZUH_API_KEY: str = os.getenv("WAZUH_API_KEY", "")

    # Cognitive Arsenal (Agent-Reach / gstack / awesome-osint-arsenal)
    ARSENAL_ENABLED: bool = os.getenv("ARSENAL_ENABLED", "true").lower() == "true"
    ARSENAL_MASTER_ROUNDS: int = int(os.getenv("ARSENAL_MASTER_ROUNDS", "3"))
    ARSENAL_TIMEOUT: float = float(os.getenv("ARSENAL_TIMEOUT", "8"))
    ABUSEIPDB_API_KEY: str = os.getenv("ABUSEIPDB_API_KEY", "")

settings = Settings()