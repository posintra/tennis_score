import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd


def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, f"Unsupported encoding: {path}")


def to_number(value, default=0.0) -> float:
    num = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(num):
        return default
    return float(num)


def calc_points(result1: str, score_gap: float) -> dict[str, float]:
    bonus = score_gap * 0.1
    result1 = str(result1).strip()

    if result1 == "승":
        return {"team1": 2.0 + bonus, "team2": 1.0}
    if result1 == "무":
        return {"team1": 1.5, "team2": 1.5}
    # 패(또는 기타값)는 team2 승리로 처리
    return {"team1": 1.0, "team2": 2.0 + bonus}


def add_score(rank_df: pd.DataFrame, name: str, add_point: float, today: str) -> None:
    name = str(name).strip()
    if not name:
        return

    idx_list = rank_df.index[rank_df["이름"] == name].tolist()
    if not idx_list:
        return

    idx = idx_list[0]
    games = to_number(rank_df.at[idx, "경기횟수"], default=0.0) + 1
    total = to_number(rank_df.at[idx, "합계점수"], default=0.0) + add_point
    avg = total / games if games else 0.0

    rank_df.at[idx, "경기횟수"] = int(games)
    rank_df.at[idx, "합계점수"] = round(total, 3)
    rank_df.at[idx, "평균점수"] = round(avg, 3)
    rank_df.at[idx, "갱신일자"] = today


def assign_rank(rank_df: pd.DataFrame) -> pd.DataFrame:
    work = rank_df.copy()
    work["_avg_num"] = pd.to_numeric(work["평균점수"], errors="coerce")
    work["_games_num"] = pd.to_numeric(work["경기횟수"], errors="coerce")
    work = work.sort_values(by=["_avg_num", "이름"], ascending=[False, True], na_position="last").reset_index(drop=True)

    rank_values: list[int | str] = []
    current_rank = 1
    for _, row in work.iterrows():
        if pd.isna(row["_avg_num"]) or pd.isna(row["_games_num"]) or float(row["_games_num"]) <= 10:
            rank_values.append("")
        else:
            rank_values.append(current_rank)
            current_rank += 1

    work["순위"] = rank_values
    work = work.drop(columns=["_avg_num", "_games_num"])
    return work


def main() -> None:
    parser = argparse.ArgumentParser(description="경기 결과 CSV를 기반으로 rank_score.csv 누적 갱신")
    parser.add_argument("--source", default="score_view/game_results_2026-05-09.csv", help="입력 경기결과 CSV")
    parser.add_argument("--rank", default="ranking/rank_score.csv", help="랭킹 CSV")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    source_path = (base / args.source).resolve()
    rank_path = (base / args.rank).resolve()

    source_df = read_csv_with_fallback(source_path)
    rank_df = read_csv_with_fallback(rank_path)
    rank_df["갱신일자"] = rank_df["갱신일자"].astype("string")

    today = datetime.now().strftime("%Y-%m-%d")

    for _, row in source_df.iterrows():
        name1 = str(row.get("성명1", "")).strip()
        name2 = str(row.get("성명2", "")).strip()
        name3 = str(row.get("성명3", "")).strip()
        name4 = str(row.get("성명4", "")).strip()
        result1 = str(row.get("승패여부1", "")).strip()
        score_gap = to_number(row.get("점수차", 0), default=0.0)

        points = calc_points(result1, score_gap)
        add_score(rank_df, name1, points["team1"], today)
        add_score(rank_df, name2, points["team1"], today)
        add_score(rank_df, name3, points["team2"], today)
        add_score(rank_df, name4, points["team2"], today)

    ranked_df = assign_rank(rank_df)
    ranked_df.to_csv(rank_path, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {rank_path}")


if __name__ == "__main__":
    main()
