#!/usr/bin/env python3
"""
Convert an Israeli bank-statement PDF to tidy CSV
──────────────────────────────────────────────────
Columns in the output:
    Date,Description,Amount,Balance
        · Date      – ISO  YYYY-MM-DD
        · Amount    – positive = credit, negative = debit
        · Balance   – account balance after the transaction
Requires: pdfplumber, pandas
Install:  pip install pdfplumber pandas
Run:      python pdf_to_csv.py input.pdf output.csv
"""

import sys
import re
from pathlib import Path

import pdfplumber
import pandas as pd


# Raw table columns as they appear in most Israeli bank PDFs
COLS_RAW = [
    "תאריך", "תאריך ערך", "תיאור",
    "אסמכתא", "חובה", "זכות", "יתרה"
]

# Final CSV columns
COLS_OUT = ["Date", "Description", "Amount", "Balance"]


def parse_number(val: str | None) -> float | None:
    """Turn  1,234.56  or  (1,234.56)  or  1234.56-  into a float, preserving sign."""
    if val is None or str(val).strip() == "":
        return None
    s = str(val).replace(",", "").strip()
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    elif s.endswith("-"):
        neg, s = True, s[:-1]
    elif s.startswith("-"):
        neg, s = True, s[1:]
    try:
        num = float(s)
        return -num if neg else num
    except ValueError:
        return None


def iso_date(raw: str) -> str | None:
    """Convert DD/MM/YY → YYYY-MM-DD (assume year <50 = 20xx, else 19xx)."""
    if not raw or not re.fullmatch(r"\d{2}/\d{2}/\d{2}", raw):
        return None
    d, m, y = map(int, raw.split("/"))
    y += 2000 if y < 50 else 1900
    return f"{y:04d}-{m:02d}-{d:02d}"


def rows_from_page(page) -> list[list[str]]:
    """
    Extract rows from one PDF page:
        ① try pdfplumber's built-in table extraction;
        ② if nothing recognised, fall back to regex on raw text.
    """
    rows: list[list[str]] = []

    # ① Table extraction
    for table in page.extract_tables():
        if not table:
            continue
        # If first row looks like a header row, drop it:
        if set(map(str.strip, table[0])) >= set(COLS_RAW[:4]):  # heuristic
            table = table[1:]
        rows.extend(table)

    if rows:
        return rows

    # ② Regex fallback (robust when the PDF isn't tagged well)
    text = page.extract_text() or ""
    # Balance  Debit   Credit  Ref  Description (...)  Value-Date   Tx-Date
    patt = re.compile(
        r"(?P<bal>[0-9,()\-]+)\s+"
        r"(?P<debit>[0-9,()\-]*)\s*"
        r"(?P<credit>[0-9,()\-]*)\s+"
        r"(?P<ref>\S+)\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<val>\d{2}/\d{2}/\d{2})\s+"
        r"(?P<tx>\d{2}/\d{2}/\d{2})$"
    )

    for line in text.splitlines():
        m = patt.search(line.strip())
        if not m:
            continue
        rows.append(
            [
                m.group("tx"),      # תאריך
                m.group("val"),     # תאריך ערך
                m.group("desc"),    # תיאור
                m.group("ref"),     # אסמכתא
                m.group("debit"),   # חובה
                m.group("credit"),  # זכות
                m.group("bal"),     # יתרה
            ]
        )
    return rows


def convert_pdf(pdf_path: Path) -> pd.DataFrame:
    """Read the whole PDF, return a tidy DataFrame ready to save."""
    raw_rows: list[list[str]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_rows.extend(rows_from_page(page))

    # Normalise into a DataFrame with the expected raw headers
    df_raw = (
        pd.DataFrame(raw_rows, columns=COLS_RAW)
        .applymap(lambda v: v.strip() if isinstance(v, str) else v)
    )

    # Build Amount column:  credit minus debit
    debit = df_raw["חובה"].apply(parse_number).fillna(0)
    credit = df_raw["זכות"].apply(parse_number).fillna(0)
    amount = credit - debit

    df = pd.DataFrame(
        {
            "Date": df_raw["תאריך"].apply(iso_date),
            "Description": df_raw["תיאור"],
            "Amount": amount,
            "Balance": df_raw["יתרה"].apply(parse_number),
        }
    ).dropna(subset=COLS_OUT)

    df.sort_values("Date", inplace=True)
    return df.reset_index(drop=True)


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("Usage:\n  pdf_to_csv.py <input.pdf> <output.csv>")
    pdf_file, csv_file = map(Path, sys.argv[1:])
    df = convert_pdf(pdf_file)
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print(f"✔ Wrote {len(df)} rows to {csv_file}")


if __name__ == "__main__":
    main()
