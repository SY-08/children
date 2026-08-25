#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子供のAI利用に関するアンケート集計スクリプト

Google スプレッドシート(フォーム回答)を CSV としてダウンロードし、
テスト行を除外して各設問を集計、survey/data.json を生成する。

GitHub Actions から1日1回実行される想定。
ローカル検証時は LOCAL_CSV に CSV パスを指定すると
ネットワークを使わずにその CSV を読み込む。
"""

import os
import csv
import io
import json
import sys
import datetime
import urllib.request

# --- 設定 -------------------------------------------------------------
SHEET_ID = "1vpfE2O0Bs1tIhnzwFQ5Bkuc1wxXKlb1a8rx3Etvfeos"
CSV_URL = os.environ.get(
    "CSV_URL",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv",
)
LOCAL_CSV = os.environ.get("LOCAL_CSV")  # ローカル検証用
OUT_PATH = os.environ.get("OUT_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "survey", "data.json"))

# 列インデックス（スプレッドシートの列順）
# A=0 回答日時 / B〜K=Q1〜Q10 / L=11 子どもの人数 / M以降=連絡先・パートナー等（可視化には使わない＝個人情報のため）
COL_TS, COL_Q1, COL_Q2, COL_Q3, COL_Q4, COL_Q5, COL_Q6, COL_Q7, COL_Q8, COL_Q9, COL_Q10 = range(11)
COL_CHILDCOUNT = 11

# 「子どもの人数」の有効な選択肢（これ以外の値＝旧データ等は集計しない）
CHILDCOUNT_VALID = ["1人", "2人", "3人", "4人以上"]

# 表示順（未知ラベルは末尾に回す）
ORDER_Q1 = [
    "積極的に使ってよいと思う",
    "ルールや大人の見守りがあれば使ってよいと思う",
    "あまり使わせたくない",
    "使わせたくない",
    "わからない",
]
ORDER_Q2 = [
    "とても必要だと思う",
    "ある程度必要だと思う",
    "どちらともいえない",
    "あまり必要ないと思う",
    "必要ないと思う",
]
ORDER_Q3 = [
    "未就学児（〜6歳頃）から",
    "小学校低学年（1〜2年生）から",
    "小学校中学年（3〜4年生）から",
    "小学校高学年（5〜6年生）から",
    "中学生から",
    "高校生から",
    "特に年齢は決めなくてよい",
    "使わせないほうがよい",
]


def fetch_rows():
    if LOCAL_CSV:
        with open(LOCAL_CSV, encoding="utf-8") as f:
            text = f.read()
    else:
        req = urllib.request.Request(CSV_URL, headers={"User-Agent": "children-survey-bot"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    return rows


def is_test_or_empty(row):
    if len(row) <= COL_Q1:
        return True
    ts = (row[COL_TS] or "").strip()
    if not ts:
        return True
    q1 = row[COL_Q1] if len(row) > COL_Q1 else ""
    q10 = row[COL_Q10] if len(row) > COL_Q10 else ""
    # 動作確認の送信を除外
    if "テスト" in q1 or "テスト" in q10:
        return True
    return False


def count_single(rows, col):
    counts = {}
    for r in rows:
        v = (r[col] if len(r) > col else "").strip()
        if not v:
            continue
        counts[v] = counts.get(v, 0) + 1
    return counts


def count_multi(rows, col):
    counts = {}
    for r in rows:
        v = (r[col] if len(r) > col else "").strip()
        if not v:
            continue
        for part in v.split("/"):
            part = part.strip()
            if part:
                counts[part] = counts.get(part, 0) + 1
    return counts


def ordered(counts, order):
    out = []
    seen = set()
    for label in order:
        if label in counts:
            out.append({"label": label, "count": counts[label]})
            seen.add(label)
    # 未知ラベル（count 降順）
    for label, c in sorted(counts.items(), key=lambda x: -x[1]):
        if label not in seen:
            out.append({"label": label, "count": c})
    return out


def by_count(counts):
    return [{"label": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]


def main():
    rows = fetch_rows()
    if not rows:
        print("No rows fetched", file=sys.stderr)
        sys.exit(1)

    # ヘッダー行を除外
    data_rows = rows[1:]
    valid = [r for r in data_rows if not is_test_or_empty(r)]

    comments = []
    for r in valid:
        c = (r[COL_Q10] if len(r) > COL_Q10 else "").strip()
        if c:
            comments.append(c)

    q7 = count_single(valid, COL_Q7)

    # 子どもの人数（有効な選択肢のみ・「いる」方の回答）
    cc_counts = {}
    for r in valid:
        v = (r[COL_CHILDCOUNT] if len(r) > COL_CHILDCOUNT else "").strip()
        if v in CHILDCOUNT_VALID:
            cc_counts[v] = cc_counts.get(v, 0) + 1
    child_count = [{"label": k, "count": cc_counts[k]} for k in CHILDCOUNT_VALID if k in cc_counts]

    jst = datetime.timezone(datetime.timedelta(hours=9))
    result = {
        "updated_at": datetime.datetime.now(jst).strftime("%Y-%m-%dT%H:%M:%S%z"),
        "updated_display": datetime.datetime.now(jst).strftime("%Y年%-m月%-d日"),
        "total": len(valid),
        "q1": ordered(count_single(valid, COL_Q1), ORDER_Q1),
        "q2": ordered(count_single(valid, COL_Q2), ORDER_Q2),
        "q3": ordered(count_single(valid, COL_Q3), ORDER_Q3),
        "q4": by_count(count_multi(valid, COL_Q4)),
        "q5": by_count(count_multi(valid, COL_Q5)),
        "q6": by_count(count_multi(valid, COL_Q6)),
        "q7": q7,
        "childCount": child_count,
        "q9": by_count(count_single(valid, COL_Q9)),
        "comments": comments,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_PATH}: total={result['total']}, comments={len(comments)}")


if __name__ == "__main__":
    main()
