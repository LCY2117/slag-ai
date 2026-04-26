from __future__ import annotations

from typing import Any, Dict, List, Optional
import requests


class LLMResult(dict):
    @property
    def content(self) -> str:
        return self.get("content", "")


def _format_api_error(exc: Exception) -> str:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        status_code = exc.response.status_code
        if status_code == 401:
            return "硅基流动 API 鉴权失败：API Key 无效、过期或未开通权限。请在 SILICONFLOW_API_KEY 或 config.yaml 中配置有效 Key；当前已使用离线规则模板。"
        if status_code == 403:
            return "硅基流动 API 权限不足：当前 Key 无权调用该模型或服务。请检查账号权限、余额和模型名称；当前已使用离线规则模板。"
        if status_code == 429:
            return "硅基流动 API 请求过于频繁或额度不足。请稍后重试或检查账户额度；当前已使用离线规则模板。"
        return f"硅基流动 API 调用失败：HTTP {status_code}。当前已使用离线规则模板。"
    if isinstance(exc, requests.Timeout):
        return "硅基流动 API 请求超时。请检查网络或稍后重试；当前已使用离线规则模板。"
    if isinstance(exc, requests.RequestException):
        return f"硅基流动 API 网络请求失败：{exc}。当前已使用离线规则模板。"
    return f"硅基流动 API 调用失败：{exc}。当前已使用离线规则模板。"


def siliconflow_chat(messages: List[Dict[str, str]], config: Dict[str, Any], fallback: str = "") -> LLMResult:
    sf = config.get("siliconflow", {})
    enabled = bool(sf.get("enabled", True))
    api_key = str(sf.get("api_key") or "").strip()
    if not enabled or not api_key:
        return LLMResult({
            "ok": False,
            "mode": "offline_fallback",
            "content": fallback,
            "error": "未配置 SILICONFLOW_API_KEY，已使用离线模板。",
        })

    base_url = str(sf.get("base_url") or "https://api.siliconflow.cn/v1").rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": sf.get("model") or "Qwen/Qwen2.5-7B-Instruct",
        "messages": messages,
        "temperature": float(sf.get("temperature", 0.35)),
        "max_tokens": int(sf.get("max_tokens", 1400)),
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=int(sf.get("timeout_seconds", 60)))
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            content = fallback or "模型返回为空。"
        return LLMResult({
            "ok": True,
            "mode": "siliconflow",
            "content": content,
            "raw_usage": data.get("usage", {}),
            "model": data.get("model", payload["model"]),
        })
    except Exception as exc:  # noqa: BLE001
        return LLMResult({
            "ok": False,
            "mode": "offline_fallback",
            "content": fallback,
            "error": _format_api_error(exc),
        })
