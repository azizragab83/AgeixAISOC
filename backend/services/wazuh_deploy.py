"""Wazuh rule deployment service — uploads custom XML rules to Wazuh Manager API."""

import hashlib
import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

WAZUH_API_TIMEOUT = 15

# Custom rule ID base. Wazuh reserves 0-99999 for built-in rules;
# 100000+ is the documented range for custom/local rules.
WAZUH_CUSTOM_RULE_ID_BASE = 100000
WAZUH_CUSTOM_RULE_ID_MAX = 100499


def _xml_escape(text: str) -> str:
    """Escape special characters for XML content."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _level_to_wazuh_level(level: str) -> int:
    """Map Sigma level strings to Wazuh rule levels (3-15)."""
    mapping = {
        "informational": 3,
        "low": 5,
        "medium": 7,
        "high": 10,
        "critical": 13,
    }
    return mapping.get(str(level).lower(), 7)


def _rule_id_from_title(rule_id: str) -> int:
    """
    Deterministic Wazuh rule ID derived from the Sigma rule_id string.
    Ensures the same Sigma rule always maps to the same Wazuh rule ID,
    and stays inside the custom range (100000-100499).
    """
    digest = hashlib.md5(str(rule_id).encode("utf-8")).hexdigest()
    num = int(digest[:8], 16)
    return WAZUH_CUSTOM_RULE_ID_BASE + (num % (WAZUH_CUSTOM_RULE_ID_MAX - WAZUH_CUSTOM_RULE_ID_BASE))


def sigma_dict_to_wazuh_xml(sigma_rule: dict) -> str:
    """
    Convert a Sigma-style rule dict into a minimal valid Wazuh XML rule file.

    The XML uses:
      - <group name="local,custom_ai_generated,">  (local + custom groups)
      - <rule id="100XXX" level="N">  (custom range, deterministic from rule_id)
      - <if_sid>5716</if_sid>  (parent: any rule — minimal dependency)
      - <description>, <mitre>, and detection fields extracted from the dict.
    """
    title = sigma_rule.get("title", "AI-generated detection rule")
    rule_id = sigma_rule.get("rule_id", "ai_generated_rule")
    wazuh_rule_id = _rule_id_from_title(rule_id)
    level = _level_to_wazuh_level(sigma_rule.get("level", "medium"))

    mitre_ids = sigma_rule.get("mitre_id", [])
    if isinstance(mitre_ids, str):
        mitre_ids = [mitre_ids]
    mitre_xml = ""
    for mid in mitre_ids:
        mitre_xml += f"      <id>{_xml_escape(mid)}</id>\n"

    detection = sigma_rule.get("detection", {})
    selection = detection.get("selection", {}) if isinstance(detection, dict) else {}
    field_xml = ""
    if isinstance(selection, dict):
        for key, value in selection.items():
            field_xml += f"      <field name=\"{_xml_escape(str(key))}\">{_xml_escape(str(value))}</field>\n"

    description = sigma_rule.get("description", "") or title

    xml = (
        "<group name=\"local,custom_ai_generated,\">\n"
        f"  <rule id=\"{wazuh_rule_id}\" level=\"{level}\">\n"
        "    <if_sid>5716</if_sid>\n"
        f"    <description>{_xml_escape(description)}</description>\n"
    )
    if mitre_xml:
        xml += "    <mitre>\n" + mitre_xml + "    </mitre>\n"
    if field_xml:
        xml += field_xml
    xml += "  </rule>\n</group>\n"

    return xml


def _build_auth_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


async def get_wazuh_token(base_url: str, user: str, password: str) -> Optional[str]:
    """Authenticate to Wazuh API and return a JWT token."""
    try:
        url = f"{base_url}/security/user/authenticate"
        async with httpx.AsyncClient(timeout=WAZUH_API_TIMEOUT, verify=False) as client:
            resp = await client.post(url, auth=(user, password))
            resp.raise_for_status()
            token = resp.json().get("data", {}).get("token")
            if token:
                logger.info("Wazuh API authentication successful")
                return token
            logger.error(f"Wazuh auth response missing token: {resp.text[:200]}")
            return None
    except httpx.HTTPStatusError as e:
        logger.error(f"Wazuh auth failed: HTTP {e.response.status_code} — {e.response.text[:200]}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Wazuh auth connection failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Wazuh auth unexpected error: {e}")
        return None


async def deploy_sigma_rule_real(
    rule_content: str,
    rule_id: str,
    wazuh_base_url: str,
    wazuh_user: str,
    wazuh_password: str,
    wazuh_api_key: str = "",
) -> dict:
    """
    Upload a Wazuh XML rule to the Wazuh Manager API as a custom rule file.

    Uses PUT /rules/files/{filename} with an .xml filename (Wazuh 4.7 validates
    filenames against the 'xml_filename_path' format — .yml is rejected with HTTP 400).

    NOTE (Wazuh 4.7 behavior): per the API docs, uploading a rule file via
    PUT /rules/files/{filename} does NOT automatically reload the manager.
    A follow-up PUT /manager/restart is normally required for rules to take
    effect. The restart call is attempted after a successful upload; if it
    fails, the rule is uploaded but not yet active — logged for user review.

    Returns dict with status, message, and any error details.
    """
    token = None
    if wazuh_user and wazuh_password:
        token = await get_wazuh_token(wazuh_base_url, wazuh_user, wazuh_password)

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif wazuh_api_key:
        headers["Authorization"] = f"Bearer {wazuh_api_key}"
    else:
        return {
            "status": "manual_review_required",
            "message": "No Wazuh API credentials configured. Set WAZUH_API_USER/WAZUH_API_PASS or WAZUH_API_KEY in .env",
            "rule_id": rule_id,
        }

    filename = f"{rule_id}.xml"
    url = f"{wazuh_base_url}/rules/files/{filename}"

    # Wazuh 4.7: PUT /rules/files/{filename} expects the RAW rule file content
    # with Content-Type: application/octet-stream. Sending {"content": "..."}
    # JSON yields HTTP 406 (error 6002: body type mismatch).
    content_headers = {**headers, "Content-Type": "application/octet-stream"}
    payload = rule_content.encode("utf-8")

    try:
        async with httpx.AsyncClient(timeout=WAZUH_API_TIMEOUT, verify=False) as client:
            resp = await client.put(url, content=payload, headers=content_headers)

        if resp.status_code in (200, 201):
            logger.info(f"Wazuh rule uploaded successfully: {filename}")

            restart_result = None
            try:
                restart_url = f"{wazuh_base_url}/manager/restart"
                async with httpx.AsyncClient(timeout=WAZUH_API_TIMEOUT, verify=False) as restart_client:
                    restart_resp = await restart_client.put(restart_url, headers=headers)
                restart_result = {
                    "status_code": restart_resp.status_code,
                    "body": restart_resp.text[:200],
                }
                logger.info(f"Wazuh manager restart request: HTTP {restart_resp.status_code}")
            except Exception as e:
                restart_result = {"error": str(e)}
                logger.warning(f"Wazuh manager restart failed (rule uploaded but not active yet): {e}")

            return {
                "status": "deployed",
                "message": f"Wazuh XML rule {rule_id} uploaded as {filename}. Manager restart: {restart_result}",
                "rule_id": rule_id,
                "wazuh_response": resp.json() if resp.text else {},
                "manager_restart": restart_result,
            }

        if resp.status_code == 401:
            logger.error(f"Wazuh API auth failed (401) for PUT /rules/files/{filename}")
            return {
                "status": "manual_review_required",
                "message": f"Wazuh API authentication failed (HTTP 401). Check credentials in .env. Rule saved locally for manual deployment.",
                "rule_id": rule_id,
                "wazuh_status_code": 401,
            }

        logger.error(f"Wazuh API error: HTTP {resp.status_code} — {resp.text[:300]}")
        return {
            "status": "manual_review_required",
            "message": f"Wazuh API returned HTTP {resp.status_code}: {resp.text[:200]}",
            "rule_id": rule_id,
            "wazuh_status_code": resp.status_code,
        }

    except httpx.RequestError as e:
        logger.error(f"Wazuh API connection failed for {url}: {e}")
        return {
            "status": "manual_review_required",
            "message": f"Wazuh API unreachable at {wazuh_base_url}: {e}",
            "rule_id": rule_id,
        }
    except Exception as e:
        logger.error(f"Wazuh deploy unexpected error: {e}")
        return {
            "status": "manual_review_required",
            "message": f"Unexpected error deploying to Wazuh: {e}",
            "rule_id": rule_id,
        }


async def delete_wazuh_rule_file(rule_id: str, wazuh_base_url: str, wazuh_user: str, wazuh_password: str, wazuh_api_key: str = "") -> dict:
    """Remove a custom rule file from the Wazuh manager (DELETE /rules/files/{filename})."""
    token = None
    if wazuh_user and wazuh_password:
        token = await get_wazuh_token(wazuh_base_url, wazuh_user, wazuh_password)

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif wazuh_api_key:
        headers["Authorization"] = f"Bearer {wazuh_api_key}"
    else:
        return {"status": "skipped", "message": "No Wazuh credentials — rule file removed locally only."}

    filename = f"{rule_id}.xml"
    url = f"{wazuh_base_url}/rules/files/{filename}"
    try:
        async with httpx.AsyncClient(timeout=WAZUH_API_TIMEOUT, verify=False) as client:
            resp = await client.delete(url, headers=headers)
        if resp.status_code in (200, 201, 404):
            logger.info(f"Wazuh rule {filename} removed (HTTP {resp.status_code})")
            return {"status": "removed", "message": f"Wazuh rule {filename} removed (HTTP {resp.status_code})"}
        logger.error(f"Wazuh DELETE {filename}: HTTP {resp.status_code} — {resp.text[:200]}")
        return {"status": "failed", "message": f"Wazuh DELETE returned HTTP {resp.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"Wazuh DELETE connection failed for {url}: {e}")
        return {"status": "failed", "message": f"Wazuh API unreachable: {e}"}
