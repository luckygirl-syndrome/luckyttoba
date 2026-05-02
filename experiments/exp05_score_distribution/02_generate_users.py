"""시험 5 — Step 2: 가상 유저 80명 생성.

모든 객관식 조합: price(4) × interest(4) × discovery(5) = 80개.
각 조합을 정확히 1명의 유저로 생성.
출력: outputs/virtual_users.parquet
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shared.survey_questions import get_all_survey_combinations

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    combos = get_all_survey_combinations()
    print(f"전체 객관식 조합 수: {len(combos)}")

    all_users = []
    for user_id, combo in enumerate(combos):
        user = {
            "user_id": user_id,
            "match_subtotal": combo["subtotal"],
            "price_reasonable": combo["price_reasonable"],
            "interest_persistence": combo["interest_persistence"],
            "discovery_stability": combo["discovery_stability"],
            "price_label": combo["price_label"],
            "interest_label": combo["interest_label"],
            "discovery_label": combo["discovery_label"],
        }
        all_users.append(user)

    df = pd.DataFrame(all_users)
    out_path = OUTPUT_DIR / "virtual_users.parquet"
    df.to_parquet(out_path, index=False)
    print(f"생성: {len(df)}명 → {out_path}")

    # 요약
    print(f"\n총 유저 수: {len(df)}")
    print(f"\nmatch_subtotal 분포 (0~65):")
    print(df["match_subtotal"].describe().to_string())
    print(f"\n  고유 subtotal 값: {df['match_subtotal'].nunique()}개")
    print(f"  범위: {df['match_subtotal'].min()} ~ {df['match_subtotal'].max()}")

    print(f"\n피쳐별 분포:")
    for col in ["price_reasonable", "interest_persistence", "discovery_stability"]:
        print(f"\n  {col}:")
        print(f"    고유값: {sorted(df[col].unique())}")
        print(f"    개수: {df[col].nunique()}개")


if __name__ == "__main__":
    main()
