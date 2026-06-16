"""Build eval/qrels.jsonl from manual relevance labels (graded 0/1/2).

Labels are keyed by the email's line index in data/emails.jsonl (as shown in
the labeling candidates report). This script maps each index to the email's
stable id and writes the qrels file the evaluator consumes.
"""
import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
DATA = BACKEND.parent / "data" / "emails.jsonl"
OUT = BACKEND.parent / "eval" / "qrels.jsonl"

rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]

# query -> {email line index: graded relevance (1 or 2)}
LABELS = {
    "餐补选择": {12: 2, 216: 2, 506: 2, 14: 1},
    "端午节活动安排": {172: 2, 28: 2, 329: 1},
    "六一儿童节礼金": {173: 2, 338: 2, 469: 2, 516: 2},
    "工会福利申请": {83: 2, 551: 1},
    "离职手续办理": {4: 2, 20: 2, 15: 2, 23: 2, 336: 2, 332: 1, 14: 1},
    "园区停水通知": {434: 2, 604: 2},
    "AI创新体验活动回顾": {76: 2, 662: 1, 521: 1},
    "MySQL Flex M44测试结果": {201: 2, 215: 2, 321: 2, 330: 2, 352: 2,
                              358: 2, 375: 2, 414: 2, 420: 2, 486: 2,
                              494: 2, 458: 1},
    "Geneva MDM容器刷新": {241: 2, 768: 2, 209: 2, 231: 2, 237: 2,
                          389: 1, 879: 1, 325: 1, 328: 1, 372: 1},
    "PostgreSQL Oracle迁移GA": {429: 2, 326: 2, 340: 2, 347: 2, 353: 2,
                               427: 2, 428: 2},
    "Azure容量shiproom notes": {109: 2, 135: 2, 186: 2, 233: 2, 307: 2,
                               346: 2, 384: 2, 451: 2, 481: 2, 566: 2,
                               632: 2, 671: 2, 713: 2, 820: 2,
                               102: 1, 144: 1, 175: 1, 296: 1, 331: 1,
                               398: 1, 479: 1, 581: 1, 682: 1},
    "灾备演练disaster recovery drill": {399: 2, 639: 2, 945: 2, 70: 2,
                                       111: 2, 736: 2, 138: 2, 401: 1},
    "India区域GA通知": {10: 2, 89: 2, 90: 2},
    "HA read replica回归修复": {711: 2, 333: 2, 348: 2, 422: 2, 509: 2,
                              594: 2, 647: 2, 695: 2},
    "上周的MySQL测试邮件": {201: 2, 215: 2},
    "Swikriti发的MySQL邮件": {215: 2, 352: 2, 361: 2, 402: 2, 420: 2,
                            458: 2, 494: 2},
    "Tulika请假的邮件": {86: 2, 121: 2},
    "本月的灾备演练通知": {70: 2, 111: 2, 399: 2, 138: 2, 401: 1},
    "失物招领": {432: 2},
    # Exact-keyword / proper-noun queries: the user recalls a distinctive term
    # that appears literally in the emails. Ground-truthed objectively with
    # eval.find_label (every email whose subject contains the term), without
    # consulting any retrieval system's output.
    "ServerStuck weekly automation report": {24: 2, 259: 2, 525: 2,
                                             783: 2, 1063: 2},
    "PITR tombstone server same name failure": {480: 2, 488: 2, 626: 2,
                                                650: 2, 663: 2, 694: 2},
    "MySQL Flexible Server quota self-service": {627: 2, 634: 2, 635: 2,
                                                 636: 2, 637: 2, 638: 2,
                                                 643: 2, 644: 2},
}

# Query category, used to group the evaluation report.
CATEGORIES = {
    "餐补选择": "Workplace / HR (Chinese)",
    "端午节活动安排": "Workplace / HR (Chinese)",
    "六一儿童节礼金": "Workplace / HR (Chinese)",
    "工会福利申请": "Workplace / HR (Chinese)",
    "离职手续办理": "Workplace / HR (Chinese)",
    "园区停水通知": "Workplace / HR (Chinese)",
    "AI创新体验活动回顾": "Workplace / HR (Chinese)",
    "失物招领": "Workplace / HR (Chinese)",
    "MySQL Flex M44测试结果": "Technical work (English)",
    "Geneva MDM容器刷新": "Technical work (English)",
    "PostgreSQL Oracle迁移GA": "Technical work (English)",
    "Azure容量shiproom notes": "Technical work (English)",
    "灾备演练disaster recovery drill": "Technical work (English)",
    "India区域GA通知": "Technical work (English)",
    "HA read replica回归修复": "Technical work (English)",
    "上周的MySQL测试邮件": "Time / sender filters",
    "Swikriti发的MySQL邮件": "Time / sender filters",
    "Tulika请假的邮件": "Time / sender filters",
    "本月的灾备演练通知": "Time / sender filters",
    "ServerStuck weekly automation report": "Exact keyword (English)",
    "PITR tombstone server same name failure": "Exact keyword (English)",
    "MySQL Flexible Server quota self-service": "Exact keyword (English)",
}


def main():
    lines = []
    for query, idx_grades in LABELS.items():
        relevant = []
        grades = {}
        for idx, grade in idx_grades.items():
            eid = rows[idx]["id"]
            relevant.append(eid)
            grades[eid] = grade
        lines.append(json.dumps({
            "query": query,
            "category": CATEGORIES.get(query, "Other"),
            "relevant": relevant,
            "grades": grades,
        }, ensure_ascii=False))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} queries to {OUT}")
    # quick summary
    for query, idx_grades in LABELS.items():
        print(f"  {len(idx_grades):2d} relevant  |  {query}")


if __name__ == "__main__":
    main()
