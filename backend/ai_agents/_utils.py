"""Shared utilities for all AI agents - JSON parsing and timed execution."""

import json
import re
import logging
from functools import partial

try:
    from crewai import Task
except ImportError:
    from crewai import Task

logger = logging.getLogger(__name__)


def execute_agent_task(agent, task_description: str, expected_output: str = "JSON object", timeout: int = 30):
    import concurrent.futures
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        fn = partial(agent.execute_task, Task(description=task_description, expected_output=expected_output))
        fut = pool.submit(fn)
        result = fut.result(timeout=timeout)
        if not result or (isinstance(result, str) and not result.strip()):
            raise ValueError("Empty response from agent")
        return result
    except concurrent.futures.TimeoutError:
        logger.warning(f"Agent task timed out after {timeout}s")
        raise
    finally:
        pool.shutdown(wait=False)


def parse_json(text) -> dict:
    if isinstance(text, dict):
        return text
    text = text.strip()
    if not text:
        return {}
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    logger.warning(f"Could not parse agent output as JSON, len={len(text)}")
    return {}
