"""Standalone test for deploy_sigma_rule_real() against the real Wazuh API (XML path)."""

import asyncio
import sys

sys.path.insert(0, ".")

try:
    from config import settings
except ImportError:
    from backend.config import settings

try:
    from services.wazuh_deploy import deploy_sigma_rule_real, sigma_dict_to_wazuh_xml
except ImportError:
    from backend.services.wazuh_deploy import deploy_sigma_rule_real, sigma_dict_to_wazuh_xml

SIGMA_DICT = {
    "title": "Test Rule — SSH Lateral Movement",
    "rule_id": "sigma-test-rule-001",
    "description": "Detects SSH-based lateral movement (standalone connectivity test)",
    "level": "high",
    "mitre_id": ["T1021.001"],
    "detection": {"selection": {"EventID": 4624, "LogonType": 10}, "condition": "selection"},
}


async def main():
    print(f"WAZUH_API_URL  = {settings.WAZUH_API_URL}")
    print(f"WAZUH_API_USER = {settings.WAZUH_API_USER}")
    print(f"WAZUH_API_PASS = {'*' * len(settings.WAZUH_API_PASS)}")
    print("-" * 60)
    xml_content = sigma_dict_to_wazuh_xml(SIGMA_DICT)
    print("Generated Wazuh XML:")
    print(xml_content)
    print("-" * 60)
    result = await deploy_sigma_rule_real(
        rule_content=xml_content,
        rule_id="sigma-test-rule-001",
        wazuh_base_url=settings.WAZUH_API_URL,
        wazuh_user=settings.WAZUH_API_USER,
        wazuh_password=settings.WAZUH_API_PASS,
        wazuh_api_key=settings.WAZUH_API_KEY,
    )
    print("RESULT:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
