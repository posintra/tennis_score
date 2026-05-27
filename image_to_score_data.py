import argparse
import csv
import re
from pathlib import Path
from difflib import SequenceMatcher

import pandas as pd


OUTPUT_COLUMNS = [
    "경기일자",
    "성명1",
    "성명2",
    "점수1",
    "승패여부1",
    "성명3",
    "성명4",
    "점수2",
    "승패여부2",
    "점수차",
]


# 대진표_006.jpg (2026-05-04) 기준 데이터
PRESET_ROWS_20260504 = [
    ["2026-05-04", "추승호", "", 6, "승", "이기용", "이상한", 4, "패"],
    ["2026-05-04", "전홍진", "정세현", 6, "승", "정영구", "김수현", 2, "패"],
    ["2026-05-04", "정영구", "김수현", 4, "패", "이기용", "이상한", 6, "승"],
    ["2026-05-04", "김영희", "박태기", 0, "패", "김세현", "김영신", 6, "승"],
    ["2026-05-04", "추승호", "전홍진", 6, "승", "양희봉", "", 3, "패"],
    ["2026-05-04", "김형록", "박태기", 6, "승", "정세현", "김영신", 1, "패"],
    ["2026-05-04", "추승호", "황규옥", 6, "승", "김영희", "이상현", 1, "패"],
    ["2026-05-04", "추승호", "전홍진", 6, "승", "이기용", "김영신", 2, "패"],
    ["2026-05-04", "양희봉", "김영희", 6, "승", "정영구", "", 3, "패"],
    ["2026-05-04", "이상한", "정세현", 6, "승", "전홍진", "조성희", 3, "패"],
    ["2026-05-04", "김수현", "양희봉", 5, "승", "정영구", "전홍진", 3, "패"],
]


def load_member_names(member_csv_path: Path) -> list[str]:
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            with member_csv_path.open("r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                if "선수 명단" not in (reader.fieldnames or []):
                    continue
                names = [
                    row["선수 명단"].strip()
                    for row in reader
                    if row.get("선수 명단") and row["선수 명단"].strip()
                ]
                if names:
                    return names
        except Exception:
            continue
    raise ValueError("member.csv를 읽지 못했거나 '선수 명단' 컬럼이 없습니다.")


def best_match_name(raw_name: str, member_names: list[str], threshold: float = 0.55) -> str:
    candidate = re.sub(r"\s+", "", str(raw_name or ""))
    if not candidate:
        return ""
    if candidate in member_names:
        return candidate

    best = ""
    best_score = -1.0
    for name in member_names:
        score = SequenceMatcher(None, candidate, name).ratio()
        if score > best_score:
            best_score = score
            best = name
    return best if best_score >= threshold else candidate


def normalize_result(value: str) -> str:
    t = str(value or "").strip()
    if t in {"승", "숭"}:
        return "승"
    if t in {"패", "퍠", "폐"}:
        return "패"
    if t in {"무", "무승부"}:
        return "무"
    return t


def validate_and_normalize_rows(rows: list[list], member_names: list[str]) -> pd.DataFrame:
    normalized = []
    for row in rows:
        game_date, p11, p12, s1, r1, p21, p22, s2, r2 = row
        n_p11 = best_match_name(p11, member_names)
        n_p12 = best_match_name(p12, member_names)
        n_p21 = best_match_name(p21, member_names)
        n_p22 = best_match_name(p22, member_names)

        normalized.append(
            {
                "경기일자": game_date,
                "성명1": n_p11,
                "성명2": n_p12,
                "점수1": int(s1),
                "승패여부1": normalize_result(r1),
                "성명3": n_p21,
                "성명4": n_p22,
                "점수2": int(s2),
                "승패여부2": normalize_result(r2),
                "점수차": abs(int(s1) - int(s2)),
            }
        )

    return pd.DataFrame(normalized, columns=OUTPUT_COLUMNS)


def main() -> None:
    parser = argparse.ArgumentParser(description="게임성적표 데이터파일 생성")
    parser.add_argument("--member", default="member.csv", help="선수 명단 CSV 경로")
    parser.add_argument("--output", default="score_view/game_results_2026-05-04.csv", help="출력 CSV 경로")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    member_path = Path(args.member)
    output_path = Path(args.output)

    if not member_path.is_absolute():
        member_path = base_dir / member_path
    if not output_path.is_absolute():
        output_path = base_dir / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    member_names = load_member_names(member_path)
    df = validate_and_normalize_rows(PRESET_ROWS_20260504, member_names)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"저장 완료: {output_path.resolve()}")
    print(df)


if __name__ == "__main__":
    main()
