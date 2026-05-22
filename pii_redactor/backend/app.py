curl -X POST http://127.0.0.1:5000/api/check -H "Content-Type: application/json" -d "{\"text\":\"連絡先: test@example.com, 電話: 03-1234-5678, 名前: 山田太郎\"}"import io
import os
from flask import Flask, request, render_template, send_file, jsonify
from config import PII_PLACEHOLDERS
from llm_client import query_llm
from processors.csv_processor import process_csv
from processors.excel_processor import process_excel
from processors.email_processor import process_email
from pii_detector import redact_pii

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "..", "frontend"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/redact", methods=["POST"])
def api_redact():
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400

    file = request.files["file"]
    filename = file.filename or "output"
    content = file.read()
    suffix = filename.lower().split(".")[-1]

    if suffix in ["csv"]:
        redacted = process_csv(content, redact_pii)
        output_bytes = redacted.encode("utf-8")
        mimetype = "text/csv"
    elif suffix in ["xlsx"]:
        output_bytes = process_excel(content, redact_pii)
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif suffix in ["eml"]:
        redacted = process_email(content, redact_pii)
        output_bytes = redacted.encode("utf-8")
        mimetype = "message/rfc822"
    else:
        return jsonify({"error": "unsupported file type"}), 400

    output_name = f"redacted_{filename}"
    return send_file(
        io.BytesIO(output_bytes),
        download_name=output_name,
        mimetype=mimetype,
        as_attachment=True,
    )


def build_prompt(text: str) -> str:
    return (
        "以下のテキスト内から個人情報を検出し、種類ごとにプレースホルダに置き換えてください。"
        " 出力はJSON形式で、keysは NAME, EMAIL, PHONE, ADDRESS, ID のみとし、"
        " valueには置換後のテキスト全文を入れてください。\n\n"
        f"テキスト:\n{text}\n"
    )


@app.route("/api/check", methods=["POST"])
def api_check():
    data = request.json or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "text is required"}), 400

    prompt = (
        "与えられたテキストから個人情報を検出し、以下のプレースホルダに置き換えてください。"
        " プレースホルダ: [NAME], [EMAIL], [PHONE], [ADDRESS], [ID].\n"
        " 出力は文字列のみでお願いします。\n\n"
        f"テキスト:\n{text}\n"
    )
    result = query_llm(prompt)
    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(debug=True)
