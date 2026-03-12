"""Connectivity and environment diagnostics for episode_draft."""

from __future__ import annotations

import os
from typing import Any

import requests

from .env_utils import load_project_env


def run_doctor() -> dict[str, Any]:
    env_path = load_project_env()
    local_base = os.getenv("EPISODE_DRAFT_LOCAL_API_BASE", "").strip()
    local_model = os.getenv("EPISODE_DRAFT_LOCAL_MODEL", "").strip()
    local_key = os.getenv("EPISODE_DRAFT_LOCAL_API_KEY", "").strip()
    remote_base = os.getenv("EPISODE_DRAFT_API_BASE", "").strip()
    remote_model = os.getenv("EPISODE_DRAFT_API_MODEL", "").strip()
    remote_key = os.getenv("EPISODE_DRAFT_API_KEY", "").strip()

    return {
        "env": {
            "env_file_found": bool(env_path),
            "env_file": str(env_path) if env_path else "",
            "modelscope_cache": os.getenv("MODELSCOPE_CACHE", ""),
            "ollama_models": os.getenv("OLLAMA_MODELS", ""),
        },
        "local": {
            "base_url": local_base,
            "model": local_model,
            "api_key_present": bool(local_key),
            "ready": bool(local_base and local_model),
            "connectivity": _check_openai_compatible_endpoint(local_base, local_key) if local_base else _missing_endpoint(),
        },
        "remote": {
            "base_url": remote_base,
            "model": remote_model,
            "api_key_present": bool(remote_key),
            "ready": bool(remote_base and remote_model and remote_key),
            "connectivity": _check_openai_compatible_endpoint(remote_base, remote_key) if remote_base else _missing_endpoint(),
        },
    }


def format_doctor_report(report: dict[str, Any]) -> str:
    env = report["env"]
    local = report["local"]
    remote = report["remote"]

    return "\n".join(
        [
            "episode_draft doctor",
            "",
            "Environment:",
            f"- .env found: {'yes' if env['env_file_found'] else 'no'}",
            f"- .env path: {env['env_file'] or '(missing)'}",
            f"- MODELSCOPE_CACHE: {env['modelscope_cache'] or '(unset)'}",
            f"- OLLAMA_MODELS: {env['ollama_models'] or '(unset)'}",
            "",
            "Local model:",
            f"- base_url: {local['base_url'] or '(unset)'}",
            f"- model: {local['model'] or '(unset)'}",
            f"- api_key_present: {'yes' if local['api_key_present'] else 'no'}",
            f"- ready: {'yes' if local['ready'] else 'no'}",
            f"- connectivity: {_format_connectivity(local['connectivity'])}",
            "",
            "Remote model:",
            f"- base_url: {remote['base_url'] or '(unset)'}",
            f"- model: {remote['model'] or '(unset)'}",
            f"- api_key_present: {'yes' if remote['api_key_present'] else 'no'}",
            f"- ready: {'yes' if remote['ready'] else 'no'}",
            f"- connectivity: {_format_connectivity(remote['connectivity'])}",
        ]
    )


def _check_openai_compatible_endpoint(base_url: str, api_key: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/models"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.get(url, headers=headers, timeout=5)
        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "detail": "reachable" if response.ok else f"http_{response.status_code}",
        }
    except requests.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "detail": str(exc.__class__.__name__),
        }


def _missing_endpoint() -> dict[str, Any]:
    return {"ok": False, "status_code": None, "detail": "base_url_missing"}


def _format_connectivity(connectivity: dict[str, Any]) -> str:
    if connectivity["ok"]:
        return f"ok ({connectivity['status_code']})"
    if connectivity["status_code"] is None:
        return connectivity["detail"]
    return f"failed ({connectivity['status_code']}, {connectivity['detail']})"
