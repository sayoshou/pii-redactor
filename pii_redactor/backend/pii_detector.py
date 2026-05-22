import re
from llm_client import query_llm
from config import PII_PLACEHOLDERS

EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\d{2,4}[\s-]?){2,4}\d{2,4}")
ID_RE = re.compile(r"\b(?:\d{6,}|ID[:#]?\s*\w+)\b")
ADDRESS_RE = re.compile(r"\b(?:〒\d{3}-\d{4}|[0-9]{1,4}[\w\-]+町|[0-9]{1,4}[\w\-]+市|[0-9]{1,4}[\w\-]+区)\b")
NAME_LABEL_RE = re.compile(r"((?:名前|氏名|宛名|担当者|ご担当者|name|Name)[：:\s]*)([^,，。\n]+)")


def _replace_patterns(text: str) -> str:
    text = EMAIL_RE.sub(PII_PLACEHOLDERS["EMAIL"], text)
    text = PHONE_RE.sub(PII_PLACEHOLDERS["PHONE"], text)
    text = ID_RE.sub(PII_PLACEHOLDERS["ID"], text)
    text = ADDRESS_RE.sub(PII_PLACEHOLDERS["ADDRESS"], text)
    text = NAME_LABEL_RE.sub(lambda m: f"{m.group(1)}{PII_PLACEHOLDERS['NAME']}", text)
    return text


def _build_llm_prompt(text: str, sensitivity: float) -> str:
    if sensitivity <= 0.33:
        detail = (
            "以下のテキストから明確に個人情報と判断できるものだけを置き換えてください。"
            " 誤検知を避けつつ、明らかな個人情報は必ず置き換えてください。"
        )
    elif sensitivity <= 0.66:
        detail = (
            "以下のテキストから一般的に個人情報と考えられるものを置き換えてください。"
            " 名前・メールアドレス・電話番号・住所の候補を置き換えてください。"
        )
    else:
        detail = (
            "以下のテキスト内の個人情報または個人情報の可能性があるものはすべて置き換えてください。"
            " 情報漏洩防止を優先し、曖昧なものも含めて置き換えてください。"
        )

    return (
        f"{detail} プレースホルダ一覧: [NAME], [EMAIL], [PHONE], [ADDRESS], [ID]."
        " 出力は置き換えた全文のテキストのみとしてください。\n\n"
        f"テキスト:\n{text}\n"
    )


def _redact_with_llm(text: str, sensitivity: float) -> str:
    try:
        # テキスト長に応じてmax_tokensを設定（日本語は1文字≈0.3～0.5トークン）
        prompt = _build_llm_prompt(text, sensitivity)
        estimated_tokens = max(512, int(len(prompt) * 1.5))
        response = query_llm(prompt, max_tokens=estimated_tokens)
        if response:
            return response.strip()
    except Exception:
        pass
    return text


def redact_pii(text: str, sensitivity: float = 0.5) -> str:
    if not text:
        return text

    local = _replace_patterns(text)
    use_llm = len(text) > 80 or sensitivity > 0.66
    if use_llm:
        llm_result = _redact_with_llm(text, sensitivity)
        if llm_result and llm_result != text:
            return llm_result
    return local
