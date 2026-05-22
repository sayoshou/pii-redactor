# PII Redactor Tool

ローカルLLM (LM Studio) と連携して、CSV/Excel/EML ファイル内の個人情報を検出し、プレースホルダで置換したファイルを生成するサンプルプロジェクトです。

## セットアップ

1. Python 3.10+ をインストール
2. LM Studio を起動し、`Gemma 4 E4B` を読み込む
3. このフォルダで仮想環境を作成し、有効化

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

4. `config.py` 内の `LM_BASE_URL` と `LLM_MODEL_ID` を必要に応じて調整

## 実行

```powershell
cd pii_redactor\backend
python app.py
```

ブラウザで `http://127.0.0.1:5000` を開き、ファイルをアップロードして処理します。

## 対応形式

- CSV
- Excel (.xlsx)
- EML

## 注意

- メールファイルやスプレッドシートに含まれる個人情報の検出精度は、LMの応答に依存します。
- 本番では入力ファイルをバックアップしてからご利用ください。
