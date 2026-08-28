"""Pydantic models for the AgeixAISOC platform."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class WazuhAlert(BaseModel):
    alert_id: Optional[str] = None
    timestamp: Optional[str] = None
    rule_id: Optional[int] = None
    rule_description: Optional[str] = None
    severity: Optional[int] = None
    source_ip: Optional[str] = None
    source_port: Optional[int] = None
    destination_ip: Optional[str] = None
    destination_port: Optional[int] = None
    protocol: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    agent_ip: Optional[str] = None
    location: Optional[str] = None
    raw: Optional[str] = None
    decoded: Optional[Dict[str, Any]] = None


class HumanDecision(BaseModel):
    decision_id: str
    action: str
    metadata: Optional[Dict[str, Any]] = {}


class AttackRequest(BaseModel):
    attack_type: str = "atomic_red"
    target: str = "wazuh"
    parameters: Optional[Dict[str, Any]] = {}


class AttackResult(BaseModel):
    success: bool
    attack_id: str
    output: str
    timestamp: str


class TriggerAttackRequest(BaseModel):
    attack_type: str = "nmap_windows"
    custom_command: Optional[str] = None


class NLQuery(BaseModel):
    query: str
    alert_id: Optional[str] = None


class SigmaRule(BaseModel):
    title: str
    rule_id: Optional[str] = None
    description: Optional[str] = None
    logsource: Optional[Dict[str, Any]] = {}
    detection: Optional[Dict[str, Any]] = {}
    level: Optional[str] = "medium"
    mitre_id: Optional[List[str]] = []
