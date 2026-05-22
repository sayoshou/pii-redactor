import logging
import sys
import requests
from config import LM_BASE_URL, LLM_MODEL_ID

logger = logging.getLogger(__name__)


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)

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
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "").strip()
            return content

        _log(f"[LLM WARN] 予期しないレスポンス形式: {data}")
        return ""
    except requests.exceptions.Timeout:
        _log(f"[LLM ERROR] タイムアウト (url={url})")
        return ""
    except requests.exceptions.ConnectionError:
        _log(f"[LLM ERROR] 接続失敗 (url={url}) — LM Studioは起動していますか？")
        return ""
    except Exception as e:
        _log(f"[LLM ERROR] リクエスト失敗: {e}")
        return ""
