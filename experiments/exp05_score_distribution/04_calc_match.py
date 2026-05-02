"""시험 5 — Step 4: Match Score 3피쳐 소계 계산.

style_similarity 제외, 80명의 소계 분포.
출력: outputs/match_subtotals.parquet
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shared.scoring.match import compute_match_score_without_style

OUTPUT_DIR = Path(__file__).parent / "outputs"


def main():
    users = pd.read_parquet(OUTPUT_DIR / "virtual_users.parquet")
    print(f"유저: {len(users)}명")

    # 소계 계산
    users["match_subtotal_calc"] = users.apply(
        lambda r: compute_match_score_without_style(
            r["price_reasonable"],
            r["interest_persistence"],
            r["discovery_stability"],
        ),
        axis=1,
    )

    # 검증: 이미 저장된 subtotal과 일치 확인
    mismatches = (users["match_subtotal"] != users["match_subtotal_calc"]).sum()
    print(f"검증: subtotal 불일치 {mismatches}개")

    # 결과 저장
    result = users[["user_id", "price_reasonable", "interest_persistence",
                     "discovery_stability", "match_subtotal",
                     "price_label", "interest_label", "discovery_label"]].copy()
    out_path = OUTPUT_DIR / "match_subtotals.parquet"
    result.to_parquet(out_path, index=False)
    print(f"저장: {out_path}")

    # 요약
    print(f"\nMatch 3피쳐 소계 분포 (0~65):")
    print(result["match_subtotal"].describe().to_string())
    print(f"\n고유값: {sorted(result['match_subtotal'].unique())}")

    print(f"\n피쳐별 분포:")
    for col in ["price_reasonable", "interest_persistence", "discovery_stability"]:
        print(f"\n  {col}:")
        print(f"    값: {sorted(users[col].unique())}")
        print(f"    평균: {users[col].mean():.1f}")


if __name__ == "__main__":
    main()
