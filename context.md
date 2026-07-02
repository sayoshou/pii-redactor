# PII Redactor — 開発コンテキスト

## プロジェクト概要

Flask + LM Studio（ローカルLLM）を使ったPII（個人情報）自動マスキングツール。  
CSV / Excel / EML ファイルをアップロードすると、個人情報を `[NAME]` などのプレースホルダに置換してダウンロードできる。

| コンポーネント | 役割 |
|---|---|
| `backend/app.py` | Flask APIサーバー。`/api/redact`（ファイル処理）と `/api/check`（テキスト処理）を提供 |
| `backend/llm_client.py` | LM Studio の OpenAI互換API を呼び出す薄いクライアント |
| `backend/pii_detector.py` | 正規表現 + LLM の2段階PIIマスキングロジック |
| `backend/processors/` | CSV / Excel / EML 各フォーマット用プロセッサ |
| `backend/config.py` | LM Studio URL・モデルID・プレースホルダ定数 |
| `frontend/` | HTML + CSS + JS のシンプルなUI |

## LLM設定

- **エンドポイント**: `http://localhost:1234/v1` （LM Studio）
- **モデル**: `google/gemma-4-e4b`
- **タイムアウト**: 60秒

---

## 初期コミット以降の主な改善内容

### 1. ログ整備（app.py / llm_client.py / pii_detector.py）

- `logging.basicConfig` を `app.py` に追加
- 各モジュールに `logger = logging.getLogger(__name__)` と `_log()` ヘルパーを追加
- LLMエラー時の詳細ログ（タイムアウト・接続失敗・例外メッセージ）を出力するよう改善
- `llm_client.py`：`except Exception` → `except Exception as e` に変更して例外内容を記録

### 2. LLMクライアントの堅牢化（llm_client.py）

- タイムアウトを **30秒 → 60秒** に延長（Gemmaなど重いモデル対応）
- `ConnectionError` の個別ハンドリングを追加（「LM Studioは起動していますか？」メッセージ）
- 予期しないレスポンス形式のワーニングログを追加

### 3. 住所・会社名の正規表現強化（pii_detector.py）

#### ADDRESS_RE の改善
旧: `〒xxx-xxxx` と市区町村の単純パターンのみ  
新: 以下を網羅
- `〒xxx-xxxx` + 後続の住所文字列（最大40文字）
- 都道府県名（47都道府県すべて）+ 続く住所
- `〇〇市〇〇区` 形式
- `〇〇市〇〇X-Y` 番地形式

#### COMPANY_RE の新規追加
- `株式会社〇〇` / `〇〇株式会社` など法人格ワードを含む名称を `[NAME]` に置換
- 対象: 株式会社・有限会社・合同会社・合名会社・合資会社・社団法人・財団法人

### 4. 名前パターンの精度向上（pii_detector.py）

#### NAME_HONORIFIC_RE の改善
旧: `[一-龥ぁ-んァ-ン]{2,8}` の連続文字列  
新: `[一-龥ぁ-んァ-ン]{1,5}（スペース）[一-龥ぁ-んァ-ン]{1,5}` — 姓と名の間のスペースを許容

#### _apply_name_patterns() 関数の追加
- LLM結果への「後掛け補完」専用関数
- NAME_LABEL_RE と NAME_HONORIFIC_RE のみを適用（他パターンの二重適用を避ける）

### 5. LLMレスポンスのクリーニング（pii_detector.py）

`_clean_llm_response()` を新規追加:
- マークダウンのコードブロック（` ``` `）を除去
- LLMが出力しがちな前置き文句を除去:
  - `以下はXXXです：`
  - `Sure, here is ...`
  - `注意: ...`

### 6. マスキングパイプラインの変更（pii_detector.py）

**変更前**: 生テキスト → 正規表現 → LLM（生テキストで独立処理） → LLM結果を採用  
**変更後**: 生テキスト → **正規表現** → **正規表現結果をLLMに渡す** → **LLM結果に再度正規表現を後掛け**

```
redact_pii(text)
  └─ _replace_patterns(text)          # 1. 正規表現で確実にマスク
       └─ _redact_with_llm(local)     # 2. LLMで名前等を補完（正規表現済みテキストを渡す）
            └─ _replace_patterns(llm) # 3. LLMが見逃したPIIを後掛け補完
```

**目的**: LLMが見逃したPIIを正規表現で確実に捕捉し、二重マスクによる品質向上

### 7. CSVプロセッサの修正（processors/csv_processor.py）

- **ヘッダ行をそのまま保持**: 旧実装はヘッダ行も `redact()` にかけていたため列名が消えるバグがあった
- **出力エンコーディングをUTF-8に統一**: 旧実装は `cp932` エンコードで返していた（文字化けの原因）

---

## プレースホルダ一覧

| 種別 | プレースホルダ |
|---|---|
| 人名・会社名 | `[NAME]` |
| メールアドレス | `[EMAIL]` |
| 電話番号 | `[PHONE]` |
| 住所 | `[ADDRESS]` |
| ID・番号 | `[ID]` |

---

## 2026-05-26 追加の改善内容

### 8. テキストファイル（.txt）対応（app.py）
`/api/redact` に `.txt` を追加。UTF-8読み込み・UTF-8出力。

> **訂正（2026-07-02）**: 上記は2026-05-26のセッションログに記載されていたが、実際には
> `pii_redactor/backend/app.py` に反映されておらず、`.txt` アップロード時に
> `unsupported file type` エラーが発生していた（未コミットのまま失われていたとみられる）。
> 2026-07-02に改めて実装・動作確認済み。詳細は `docs/sessions/2026-07-02.md` を参照。

### 9. LLM出力途中切れ対策（pii_detector.py）
- `max_tokens`: `max(512, len×2)` → `max(1024, len×4)` に拡大
- サニティチェック追加: 出力が入力の50%未満なら正規表現結果にフォールバック

### 10. 長文チャンク分割処理（pii_detector.py）
`_MAX_CHUNK_CHARS = 1000` でテキストを行単位に分割し、LLMを複数回呼び出して結合。
9891文字ファイルで処理がハングする問題を解決。

---

## 既知の設計上の注意点

- `query_llm()` はキャンセルフラグ (`_cancel_requested`) を持つが、現在のUIからは未使用
- `max_tokens` は `len(text) * 2` で概算（日本語は1文字≈2トークン想定）
- LLM呼び出し条件: テキスト50文字以上 **または** sensitivity 0.3以上
- EMLプロセッサはヘッダ（宛先・送信者）はマスクせず、本文のみを処理する
