"""从清洗后的 JSON 对局数据生成 CSV。

输入：data/battles_final.json
输出：data/battles.csv
"""
import csv
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE_DIR, "data", "battles_final.json")
DST = os.path.join(BASE_DIR, "data", "battles.csv")

FIELDS = ["date", "date_md", "mode", "win", "kills", "deaths", "assists", "honor"]


def main():
    with open(SRC, encoding="utf-8") as f:
        battles = json.load(f)

    # 按日期降序（与战绩页顺序一致）
    battles.sort(key=lambda x: x["date"], reverse=True)

    with open(DST, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for b in battles:
            writer.writerow({k: b.get(k, "") for k in FIELDS})

    print(f"wrote {len(battles)} rows to {DST}")


if __name__ == "__main__":
    main()
