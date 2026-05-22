import requests
from config import LM_BASE_URL, LLM_MODEL_ID

# グローバルなキャンセルフラグ
_cancel_requested = False


def cancel_processing():
    """処理のキャンセルをリクエスト"""
    global _cancel_requested
    _cancel_requested = True


def reset_cancel():
    """キャンセルフラグをリセット"""
    global _cancel_requested
    _cancel_requested = False


def query_llm(prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
    global _cancel_requested

    if _cancel_requested:
        return ""

    url = f"{LM_BASE_URL}/chat/completions"
    payload = {
        "model": LLM_MODEL_ID,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0].get("message", {}).get("content", "").strip()

        return ""
    except requests.exceptions.Timeout:
        return ""
    except Exception:
        return ""
