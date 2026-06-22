# PII Redactor Tool

ローカルLLM (LM Studio / Google Gemma 4 E4B) と連携して、CSV/Excel/EML ファイル内の個人情報を検出し、プレースホルダで置換するツールです。

---

## このツールについて

業務・個人用途での生成AI活用を想定し、
ローカルLLMと連携した個人情報マスキングツールを個人開発しました。
Claude（生成AI）を活用したAIアシスト型の開発手法で実装しています。

---

## 課題：なぜ作ったか

**背景1：業務でのAI活用ジレンマ**
メール返信・Excel処理・レポーティングの省力化、案件分析など、
生成AIを活用できる場面は多数あるにもかかわらず、
個人情報・企業情報の入力禁止により活用できないケースが生じていた。
「使えるはずのAIが使えない」という状況の打開策を検証する目的で開発。

**背景2：個人用途での実需**
転職活動・業務相談など、AIへの入力前に個人情報を除去したい場面が
実際に存在しており、自分自身でも使用するツールとして開発した。

---

## 技術選定の判断理由

| 選定項目 | 選んだ理由 |
|---|---|
| ローカルLLM（LM Studio） | 情報の外部流出を回避するため。クラウドAPIでは解決しない問題への対処 |
| Google Gemma 4 E4B | ローカル動作する軽量モデルとして選定。活用方法の検証も兼ねる |
| Flask（Python） | バックエンドAPIとして最小構成で実装できるため |

---

## 実際に使ってみた結果

- 音声データの文字起こしテキストをAIに渡す前処理として使用
- マスキング作業の手作業工数を削減できることを確認
- ローカルLLMによる名前検出の精度課題も把握（既知の問題に記載）

---

## 開発プロセス

- 課題発見・要件定義・仕様決定：自分
- 実装：Claude（生成AI）を活用したAIアシスト型開発
- テスト・検証・改善判断：自分
- ローカルLLM環境構築（LM Studio + Gemma）：自分

---

## 仕様

### 機能概要
- **ファイル入力**: CSV / Excel (.xlsx) / EML（メールファイル）
- **個人情報の検出と置換**:
  - 正規表現による自動検出: メールアドレス、電話番号、住所、ID
  - LLM による名前検出（感度に応じて）
- **感度スライダー**: 0～100% で検出精度を調整
- **保存先指定**: ブラウザのファイルピッカーで出力先を指定
- **進捗表示**: 処理状況をプログレスバーで表示
- **キャンセル機能**: 処理中止時はフロントエンドが即座に中断

### プレースホルダ
置換に使用される標準プレースホルダ:
- `[NAME]` - 人名
- `[EMAIL]` - メールアドレス
- `[PHONE]` - 電話番号
- `[ADDRESS]` - 住所
- `[ID]` - ID番号

### 感度レベル
- **低（0～33%）**: 明確な個人情報のみ置換、誤検知回避
- **中（34～66%）**: 一般的な個人情報を置換（デフォルト: 50%）
- **高（67～100%）**: 可能性のある全ての個人情報を置換

### 技術スタック
- **バックエンド**: Flask (Python 3.13)
- **フロントエンド**: HTML5 / Vanilla JavaScript / CSS
- **LLM**: LM Studio (Google Gemma 4 E4B) @ `http://localhost:1234/v1`
- **ファイル処理**:
  - CSV: `openpyxl` で読み書き（CP932/UTF-8 対応）
  - Excel: `openpyxl`
  - EML: Python標準 `email` モジュール

## セットアップ

### 前提条件
- Python 3.10+
- LM Studio インストール済み（Gemma 4 E4B ロード済み）

### インストール手順

```powershell
# 1. ルートで仮想環境作成
python -m venv venv
venv\Scripts\Activate.ps1

# 2. backend フォルダの依存関係インストール
pip install -r pii_redactor\backend\requirements.txt

# 3. 設定確認（オプション）
# pii_redactor\backend\config.py の LM_BASE_URL と LLM_MODEL_ID を確認
```

## 実行

```powershell
# backend フォルダへ移動
cd pii_redactor\backend

# 環境有効化（backend の venv を使用）
.\venv\Scripts\Activate.ps1

# Flask サーバー起動
python app.py
```

ブラウザで `http://127.0.0.1:5000` を開き、ファイルをアップロードして処理します。

## API エンドポイント

| エンドポイント | メソッド | 説明 |
|---|---|---|
| `/` | GET | Web UI（HTML） |
| `/api/redact` | POST | ファイルアップロード・処理 |
| `/api/check` | POST | テキスト直接置換（JSON） |
| `/api/cancel` | POST | 処理キャンセル（実装中） |

### /api/redact (POST)
**リクエスト**: multipart/form-data
```
file: (binary) - CSV / Excel / EML ファイル
sensitivity: (float) - 感度 0.0～1.0
```

**レスポンス**: ファイル（適切な MIME type で返却）

## ディレクトリ構成

```
pii_redactor/
├── backend/
│   ├── app.py                    # Flask メインアプリケーション
│   ├── config.py                 # LM Studio 設定
│   ├── llm_client.py             # LM Studio API クライアント
│   ├── pii_detector.py           # 正規表現 + LLM による PII 検出
│   ├── processors/
│   │   ├── csv_processor.py      # CSV ファイル処理
│   │   ├── excel_processor.py    # Excel ファイル処理
│   │   ├── email_processor.py    # EML ファイル処理
│   │   └── __init__.py
│   ├── venv/                     # 仮想環境（backend 専用）
│   ├── requirements.txt          # Python 依存パッケージ
│   └── __pycache__/
├── frontend/
│   ├── index.html                # Web UI
│   ├── app.js                    # UI ロジック（DOMContentLoaded 初期化）
│   ├── styles.css                # プログレスバー等スタイル
├── README.md                     # このファイル
```

## 既知の問題・制限事項

### 1. 名前の置換精度が低い
**現状**: LLM による名前検出が確実ではない場合がある
- **原因**: ローカルLLM（Gemma）の能力限界、プロンプト設計の課題
- **対策案**:
  - プロンプトをさらに改善（例：「山田太郎」のような日本名フォーマットを明示）
  - より高精度なモデルを使用（商用LLMなど）
  - 辞書ベースの名前検出を並用

### 2. 感度スライダーの実装が不完全
**現状**: スライダーが UI に表示されていても、バックエンド側で適切に反映されない場合がある
- **原因**: `sensitivity` パラメータの受け取りと LLM プロンプトの結合が不明確
- **対策**: バックエンド側で感度ごとのプロンプト切り分けを強化

### 3. キャンセル機能が実装中
**現状**: フロントエンド側では AbortController で HTTP 要求を中止、バックエンド側では `/api/cancel` エンドポイントが用意されているが、LM API 呼び出しの完全な中断は保証されない
- **原因**: LM Studio への HTTP リクエストが一度送信されたら、クライアント側からの中断では LM プロセスは継続実行
- **対策**: タイムアウト設定（現在 30秒）やスレッドプール制御など

### 4. EML ファイル出力の改行崩れ（修正済み）
**状態**: ✅ 修正完了 - `email_processor.py` で `as_string()` を使用して正しい形式で出力

### 5. ファイル選択が反応しない場合がある
**現状**: ページ読み込み時に UI 要素が見つからないと `app.js` が失敗
- **対策**: `DOMContentLoaded` イベント内で全てのイベント登録を行うように修正済み

### 6. 文字エンコード対応が限定的
**現状**: CSV は CP932 (Shift-JIS)、Excel は UTF-8 で処理
- **制限**: 他のエンコーディング（EUC-JP など）には非対応
- **対策案**: 言語別エンコーディング自動検出ライブラリ（`chardet` など）の導入

### 7. LM Studio 接続不可時のエラーハンドリング
**現状**: LM Studio が起動していない場合、処理は失敗する
- **対策**: バックエンドで例外を catch して、正規表現フォールバックのみで処理するように改善

## トラブルシューティング

### サーバー起動時に "No module named 'flask'"
→ `backend\venv\Scripts\Activate.ps1` で backend の仮想環境を有効化してから実行してください

### "アップロードして置換" を押しても何も起こらない
→ ブラウザのコンソール（F12）と Flask サーバーのログを確認してください
- `app.js` が 404 で読み込まれていないか確認
- `GET /styles.css` / `GET /app.js` が 200 OK か確認

### LM Studio が応答しない
→ `http://localhost:1234/v1/chat/completions` に curl でテスト

```powershell
curl -X POST http://localhost:1234/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{"model":"google/gemma-4-e4b","messages":[{"role":"user","content":"test"}]}'
```

## デプロイメント注意

本番環境での利用を想定する場合：
1. `app.py` の `debug=True` を `False` に変更
2. 環境変数で LM_BASE_URL を管理
3. ファイルサイズ制限の設定
4. CORS 対応（必要に応じて）
5. HTTPS 設定

## ライセンス

MIT

## 参考資料

- [LM Studio 公式ドキュメント](https://lmstudio.ai/)
- [Flask 公式ドキュメント](https://flask.palletsprojects.com/)
- [openpyxl ドキュメント](https://openpyxl.readthedocs.io/)
