import logging
import re
import sys
from llm_client import query_llm
from config import PII_PLACEHOLDERS

logger = logging.getLogger(__name__)


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)

EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\d{2,4}[\s-]?){2,4}\d{2,4}")
ID_RE = re.compile(r"\b(?:\d{6,}|ID[:#]?\s*\w+)\b")

# 住所: 郵便番号 / 都道府県名 / 市区町村の組み合わせ
ADDRESS_RE = re.compile(
    r"〒\s*\d{3}[-－]\d{4}[^\n]{0,40}"  # 〒xxx-xxxx（後続住所も含む）
    r"|(?:東京都|大阪府|京都府|北海道|"  # 都道府県＋続く住所
    r"(?:青森|岩手|宮城|秋田|山形|福島|茨城|栃木|群馬|埼玉|千葉|神奈川|"
    r"新潟|富山|石川|福井|山梨|長野|岐阜|静岡|愛知|三重|滋賀|兵庫|奈良|"
    r"和歌山|鳥取|島根|岡山|広島|山口|徳島|香川|愛媛|高知|福岡|佐賀|長崎|"
    r"熊本|大分|宮崎|鹿児島|沖縄)県)[^\s、。\n]{2,40}"
    r"|[一-龥]{2,5}市[一-龥]{1,4}区"  # 〇〇市〇〇区（例: 福岡市東区）
    r"|[一-龥]{2,5}市[一-龥]{1,6}\d+[-－]\d+"  # 〇〇市〇〇+番地
)

# 企業・法人名: 株式会社などの法人格ワードを含む名称
COMPANY_RE = re.compile(
    r"[^\s、。,，\n「（(]{1,20}"
    r"(?:株式会社|有限会社|合同会社|合名会社|合資会社|社団法人|財団法人)"
    r"|(?:株式会社|有限会社|合同会社|合名会社|合資会社|社団法人|財団法人)"
    r"[^\s、。,，\n」）)]{1,20}"
)

NAME_LABEL_RE = re.compile(r"((?:名前|氏名|宛名|担当者|ご担当者|name|Name)[：:\s]*)([^,，。\n]+)")
NAME_HONORIFIC_RE = re.compile(
    r"(^|[ \t　、。！？\r\n])"
    r"([一-龥ぁ-んァ-ン]{1,5}(?:[ \t　][一-龥ぁ-んァ-ン]{1,5})?)"
    r"(さん|様|君|ちゃん)"
    r"(?=[ \t　、。！？\r\n]|$)"
)


def _replace_patterns(text: str) -> str:
    text = EMAIL_RE.sub(PII_PLACEHOLDERS["EMAIL"], text)
    text = PHONE_RE.sub(PII_PLACEHOLDERS["PHONE"], text)
    text = ID_RE.sub(PII_PLACEHOLDERS["ID"], text)
    text = ADDRESS_RE.sub(PII_PLACEHOLDERS["ADDRESS"], text)
    text = COMPANY_RE.sub(PII_PLACEHOLDERS["NAME"], text)
    text = NAME_LABEL_RE.sub(lambda m: f"{m.group(1)}{PII_PLACEHOLDERS['NAME']}", text)
    text = NAME_HONORIFIC_RE.sub(
        lambda m: f"{m.group(1)}{PII_PLACEHOLDERS['NAME']}{m.group(3)}",
        text,
    )
    return text


def _apply_name_patterns(text: str) -> str:
    """名前パターンの正規表現のみを適用する（LLM結果への後掛け補完用）"""
    text = NAME_LABEL_RE.sub(lambda m: f"{m.group(1)}{PII_PLACEHOLDERS['NAME']}", text)
    text = NAME_HONORIFIC_RE.sub(
        lambda m: f"{m.group(1)}{PII_PLACEHOLDERS['NAME']}{m.group(3)}",
        text,
    )
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
            " 人名・メールアドレス・電話番号・住所・会社名など明示的な個人情報を必ず置き換えてください。"
        )
    else:
        detail = (
            "以下のテキスト内の個人情報または個人情報の可能性があるものはすべて置き換えてください。"
            " 人名・メールアドレス・電話番号・住所・会社名など、個人を特定できる情報は曖昧でも置き換えてください。"
            " 情報漏洩防止を優先し、慎重に判定してください。"
        )

    return (
        f"{detail}\n"
        "置き換えに使用するプレースホルダ: [NAME], [EMAIL], [PHONE], [ADDRESS], [ID].\n"
        "重要: 人名は必ず[NAME]で置き換えてください。\n"
        "出力は置き換えた全文のテキストのみとしてください。余計な説明は不要です。\n\n"
        f"テキスト:\n{text}\n"
    )


_RESPONSE_PREFIX_RE = re.compile(
    r"^(?:"
    r"以下[はが][^\n]*[\n：:]\s*"
    r"|Sure[,!][^\n]*\n"
    r"|Here is[^\n]*\n"
    r"|注意[:：][^\n]*\n"
    r")",
    re.IGNORECASE,
)
_CODE_BLOCK_RE = re.compile(r"^```[^\n]*\n|```$", re.MULTILINE)


def _clean_llm_response(response: str) -> str:
    """マークダウンのコードブロックや前置き説明文を除去する"""
    response = _CODE_BLOCK_RE.sub("", response).strip()
    response = _RESPONSE_PREFIX_RE.sub("", response).strip()
    return response


def _redact_with_llm(text: str, sensitivity: float) -> str:
    _log(f"[LLM] 呼び出し開始 (テキスト長={len(text)}字)")
    try:
        prompt = _build_llm_prompt(text, sensitivity)
        estimated_tokens = max(512, int(len(text) * 2))
        response = query_llm(prompt, max_tokens=estimated_tokens)
        if response:
            cleaned = _clean_llm_response(response)
            _log(f"[LLM OK] レスポンス先頭200字: {cleaned[:200]}")
            return cleaned
        _log("[LLM] レスポンスが空でした → 正規表現結果を使用")
    except Exception as e:
        _log(f"[LLM ERROR] 例外発生: {e}")
    return text


def redact_pii(text: str, sensitivity: float = 0.5) -> str:
    if not text:
        return text

    # まず正規表現で処理し、LLMはその結果を引き継いで名前などを補完する (Issue 2)
    local = _replace_patterns(text)
    use_llm = len(text) >= 50 or sensitivity >= 0.3
    if use_llm:
        llm_result = _redact_with_llm(local, sensitivity)
        if llm_result and llm_result != local:
            # LLMが見逃したPIIを全パターンの正規表現で後掛け補完する
            return _replace_patterns(llm_result)
    return local
