import csv
import io
import re
from typing import Callable

NAME_HEADER_PATTERN = re.compile(r'^(?:[おご]?(?:名前|氏名)|姓名|name)$', re.IGNORECASE)


def _find_name_columns(header_row):
    return {i for i, cell in enumerate(header_row) if isinstance(cell, str) and NAME_HEADER_PATTERN.search(cell.strip())}


def process_csv(content: bytes, redact: Callable[[str], str]) -> bytes:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("cp932", errors="replace")

    reader = csv.reader(io.StringIO(text))
    rows = []
    name_cols = set()
    for row_index, row in enumerate(reader):
        if row_index == 0:
            name_cols = _find_name_columns(row)
            rows.append(row)  # ヘッダ行はそのまま保持
            continue

        processed_row = []
        for col_index, cell in enumerate(row):
            if col_index in name_cols and isinstance(cell, str) and cell.strip():
                processed_row.append("[NAME]")
            else:
                processed_row.append(redact(cell))
        rows.append(processed_row)

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerows(rows)
    return output.getvalue()
