"""시험 5 — Step 2: 가상 유저 80명 생성.

16 S-BTI 유형 × 공통질문 조합에서 유형당 5개 선택.
출력: outputs/virtual_users.parquet
"""

import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shared.sbti_types import ALL_TYPES, parse_sbti_flags
from shared.survey_questions import (
    PRICE_REASONABLE,
    INTEREST_PERSISTENCE,
    DISCOVERY_STABILITY,
)

CONFIG = yaml.safe_load(
    (Path(__file__).parent / "configs" / "experiment_params.yaml").read_text(encoding="utf-8")
)
SEED = CONFIG["seed"]
USERS_PER_TYPE = CONFIG["users_per_type"]

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# contact_reason: 점수에 안 쓰이지만 프로필용
CONTACT_REASONS = [
    "그냥 이 옷 어떤가 궁금해서요",
    "사고 싶은데 고민돼서요",
    "오래 고민했는데 결정이 안 나서요",
]

def generate_all_combos():
    """모든 조합 생성."""
    combos = []
    for p_label, p_score in PRICE_REASONABLE.items():
        for i_label, i_score in INTEREST_PERSISTENCE.items():
            for d_label, d_score in DISCOVERY_STABILITY.items():
                for c_reason in CONTACT_REASONS:
                    combos.append({
                        "price_label": p_label,
                        "interest_label": i_label,
                        "discovery_label": d_label,
                        "contact_reason": c_reason,
                        "price_reasonable": p_score,
                        "interest_persistence": i_score,
                        "discovery_stability": d_score,
                        "match_subtotal": p_score + i_score + d_score,
                    })
    return combos


def select_diverse(combos, n, rng):
    """subtotal 범위 + 개별 피쳐값 커버를 모두 고려하는 n개 선택.

    1) subtotal 범위를 n개 구간으로 나눠 각 구간에서 1개씩 선택
    2) 아직 커버 안 된 피쳐값이 있으면 해당 값을 포함하는 조합으로 교체
    """
    import numpy as np

    df = pd.DataFrame(combos)
    subtotals = sorted(df["match_subtotal"].unique())
    st_min, st_max = subtotals[0], subtotals[-1]

    # Step 1: subtotal 범위 기반 선택
    target_values = np.linspace(st_min, st_max, n)
    selected_indices = []

    for target in target_values:
        best_st = min(subtotals, key=lambda s: abs(s - target))
        candidates = df[(df["match_subtotal"] == best_st) & (~df.index.isin(selected_indices))]
        if len(candidates) == 0:
            candidates = df[~df.index.isin(selected_indices)]
        pick = candidates.sample(n=1, random_state=rng)
        selected_indices.append(pick.index[0])

    # Step 2: 피쳐값 커버리지 확인 및 교체
    feature_cols = ["price_reasonable", "interest_persistence", "discovery_stability"]
    all_values = {col: set(df[col].unique()) for col in feature_cols}

    for _ in range(n):  # 최대 n번 교체 시도
        covered = {col: set(df.loc[selected_indices, col].unique()) for col in feature_cols}
        missing = {}
        for col in feature_cols:
            diff = all_values[col] - covered[col]
            if diff:
                missing[col] = diff

        if not missing:
            break

        # 가장 많은 missing을 커버하는 후보 찾기
        col, vals = next(iter(missing.items()))
        target_val = min(vals)  # 아무 missing 값
        candidates = df[(df[col] == target_val) & (~df.index.isin(selected_indices))]
        if len(candidates) == 0:
            break
        pick = candidates.sample(n=1, random_state=rng + 100)
        # 가장 덜 중요한 (중복 subtotal이 가장 많은) 기존 선택 교체
        sel_df = df.loc[selected_indices]
        dup_counts = sel_df["match_subtotal"].map(sel_df["match_subtotal"].value_counts())
        replace_idx = dup_counts.idxmax()
        selected_indices.remove(replace_idx)
        selected_indices.append(pick.index[0])

    return [df.loc[idx].to_dict() for idx in selected_indices]


def main():
    combos = generate_all_combos()
    print(f"전체 유효 조합 수: {len(combos)}")

    rng_base = SEED
    all_users = []
    user_id = 0

    for sbti in ALL_TYPES:
        flags = parse_sbti_flags(sbti)
        selected = select_diverse(combos, USERS_PER_TYPE, rng_base)
        rng_base += 1  # 유형마다 다른 시드

        for combo in selected:
            user = {
                "user_id": user_id,
                "sbti": sbti,
                **flags,
                **combo,
            }
            all_users.append(user)
            user_id += 1

    df = pd.DataFrame(all_users)
    out_path = OUTPUT_DIR / "virtual_users.parquet"
    df.to_parquet(out_path, index=False)
    print(f"생성: {len(df)}명 → {out_path}")

    # 요약
    print(f"\nSBTI 유형별 {USERS_PER_TYPE}명씩:")
    print(f"  총 유저 수: {len(df)}")
    print(f"\nmatch_subtotal 분포:")
    print(df["match_subtotal"].describe().to_string())
    print(f"\n  고유 subtotal 값: {df['match_subtotal'].nunique()}개")
    print(f"  범위: {df['match_subtotal'].min()} ~ {df['match_subtotal'].max()}")


if __name__ == "__main__":
    main()
