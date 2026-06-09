from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


DEFAULT_CONFIG: Dict[str, Any] = {
    "siliconflow": {
        "enabled": True,
        "api_key": "",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "temperature": 0.35,
        "max_tokens": 650,
        "timeout_seconds": 30,
    },
    "system": {
        "app_name": "MSPC-GreenAI",
        "offline_fallback": True,
        "language": "zh-CN",
    },
}


def deep_update(base: Dict[str, Any], other: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in other.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_config(config_path: str | None = None) -> Dict[str, Any]:
    load_dotenv()
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    path = Path(os.getenv("MSPC_CONFIG_PATH") or config_path or "config.yaml")
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if isinstance(data, dict):
            deep_update(cfg, data)

    sf = cfg.setdefault("siliconflow", {})
    # Runtime secrets come only from the environment; config.yaml is non-sensitive defaults/docs.
    sf["api_key"] = os.getenv("SILICONFLOW_API_KEY", "")
    sf["base_url"] = os.getenv("SILICONFLOW_BASE_URL") or sf.get("base_url", DEFAULT_CONFIG["siliconflow"]["base_url"])
    sf["model"] = os.getenv("SILICONFLOW_MODEL") or sf.get("model", DEFAULT_CONFIG["siliconflow"]["model"])
    sf["max_tokens"] = int(os.getenv("SILICONFLOW_MAX_TOKENS") or sf.get("max_tokens", DEFAULT_CONFIG["siliconflow"]["max_tokens"]))
    sf["timeout_seconds"] = int(os.getenv("SILICONFLOW_TIMEOUT_SECONDS") or sf.get("timeout_seconds", DEFAULT_CONFIG["siliconflow"]["timeout_seconds"]))

    return cfg
