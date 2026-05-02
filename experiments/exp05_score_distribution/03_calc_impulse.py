"""시험 5 — Step 3: Impulse Score 48,000쌍 계산.

600상품 × 80유저 = 48,000 쌍.
피쳐 기여도 분해도 함께 저장.
출력: outputs/impulse_scores.parquet
"""

import sys
from pathlib import Path
from math import log10

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shared.scoring.impulse import (
    compute_impulse_score,
    _get_discount_score,
    _get_m_score,
    REVIEW_M_TABLE,
    LIKE_M_TABLE,
    MAX_POSSIBLE,
)

OUTPUT_DIR = Path(__file__).parent / "outputs"


def decompose_impulse(product, user, use_improved_formula=False):
    """Impulse Score + 5개 피쳐 기여도 분해.

    use_improved_formula=True: 기본점수 +10, D유형 +5 적용
    """
    dr = product["discount_rate"]
    rc = product["review_count"]
    rt = product["rating"]
    lc = product["like_count"]
    th = product["trend_hype"]
    bd = product["bundle"]
    cf = product["confidence"]
    platform = product["platform"]

    is_D = user["is_D"]
    is_N = user["is_N"]
    is_U = user["is_U"]
    is_I = user["is_I"]
    is_T = user["is_T"]
    is_M = user["is_M"]
    is_E = user["is_E"]
    is_O = user["is_O"]

    # 피쳐 정규화 (impulse.py 로직 복제)
    discount_score = _get_discount_score(dr)

    if is_M:
        review_score = _get_m_score(rc, REVIEW_M_TABLE, platform)
    else:
        review_score = min(log10(rc + 1) / log10(5001), 1.0) ** 1.5

    if rc == 0:
        rating_score = 0.3
    else:
        rating_score = max((rt - 3.0) / 2.0, 0.0)

    if is_M:
        like_score = _get_m_score(lc, LIKE_M_TABLE, platform)
    else:
        like_score = min(log10(lc + 1) / log10(10001), 1.0) ** 1.5

    # title_marketing_score
    if is_M:
        w1 = 0.0
    elif is_T and is_U:
        w1 = 0.5
    elif is_T:
        w1 = 0.4
    elif is_U:
        w1 = 0.3
    else:
        w1 = 0.2
    w2 = 0.4 if is_E else 0.2
    w3 = 0.4 if is_O else 0.3
    w_total = w1 + w2 + w3
    if w_total > 0:
        title_marketing_score = (w1 * th + w2 * bd + w3 * cf) / w_total
    else:
        title_marketing_score = 0.0

    # Multiplier
    discount_m = 1.2 * (1.3 if is_E else (0.9 if is_O else 1.0))
    rating_m = (1.2 if is_U else 1.0) * (1.2 if is_O else 1.0)
    review_count_m = (1.3 if is_U else (0.7 if is_I else 1.0)) * (1.2 if is_T else 1.0)
    like_count_m = (1.2 if is_U else (0.7 if is_I else 1.0)) * (1.2 if is_T else 1.0)
    if is_M:
        title_marketing_m = 0.8
    elif is_D:
        title_marketing_m = 1.1
    elif is_N:
        title_marketing_m = 0.9
    else:
        title_marketing_m = 1.0

    # 기여도 분해 (raw 기준)
    discount_contrib = 0.35 * discount_score * discount_m
    rating_contrib = 0.20 * rating_score * rating_m
    review_contrib = 0.15 * review_score * review_count_m
    like_contrib = 0.10 * like_score * like_count_m
    marketing_contrib = 0.20 * title_marketing_score * title_marketing_m

    raw_score = discount_contrib + rating_contrib + review_contrib + like_contrib + marketing_contrib
    impulse_score = max(0, min(100, round((raw_score / MAX_POSSIBLE) * 100)))

    # 공식 개선 적용
    if use_improved_formula:
        impulse_score = impulse_score + 10  # 기본점수 +10
        if is_D:
            impulse_score = impulse_score + 5  # D유형 +5

    return {
        "impulse_score": impulse_score,
        "discount_contrib": round(discount_contrib, 6),
        "rating_contrib": round(rating_contrib, 6),
        "review_contrib": round(review_contrib, 6),
        "like_contrib": round(like_contrib, 6),
        "marketing_contrib": round(marketing_contrib, 6),
    }


def compute_all_versions():
    """원본 + 개선 공식 두 버전 모두 계산."""
    products = pd.read_parquet(OUTPUT_DIR / "products_600.parquet")
    users = pd.read_parquet(OUTPUT_DIR / "virtual_users.parquet")
    print(f"상품: {len(products)}개, 유저: {len(users)}명")
    print(f"계산할 쌍: {len(products) * len(users):,}개\n")

    # v0: 원본 공식
    print("[v0] 원본 공식 계산 중...")
    rows_v0 = []
    for _, user in users.iterrows():
        user_dict = user.to_dict()
        for _, prod in products.iterrows():
            prod_dict = prod.to_dict()
            result = decompose_impulse(prod_dict, user_dict, use_improved_formula=False)
            rows_v0.append({
                "product_id": prod_dict["product_id"],
                "user_id": user_dict["user_id"],
                "sbti": user_dict["sbti"],
                "platform": prod_dict["platform"],
                **result,
            })

    df_v0 = pd.DataFrame(rows_v0)
    out_path_v0 = OUTPUT_DIR / "impulse_scores.parquet"
    df_v0.to_parquet(out_path_v0, index=False)
    print(f"  저장: {out_path_v0}")
    print(f"  분포: min={df_v0['impulse_score'].min()}, max={df_v0['impulse_score'].max()}, "
          f"mean={df_v0['impulse_score'].mean():.1f}, median={df_v0['impulse_score'].median():.1f}")

    # v1: 개선 공식
    print("\n[v1] 공식 개선 계산 중...")
    rows_improved = []
    for _, user in users.iterrows():
        user_dict = user.to_dict()
        for _, prod in products.iterrows():
            prod_dict = prod.to_dict()
            result = decompose_impulse(prod_dict, user_dict, use_improved_formula=True)
            rows_improved.append({
                "product_id": prod_dict["product_id"],
                "user_id": user_dict["user_id"],
                "sbti": user_dict["sbti"],
                "platform": prod_dict["platform"],
                **result,
            })

    df_improved = pd.DataFrame(rows_improved)
    out_path_improved = OUTPUT_DIR / "impulse_scores_v1.parquet"
    df_improved.to_parquet(out_path_improved, index=False)
    print(f"  저장: {out_path_improved}")
    print(f"  분포: min={df_improved['impulse_score'].min()}, max={df_improved['impulse_score'].max()}, "
          f"mean={df_improved['impulse_score'].mean():.1f}, median={df_improved['impulse_score'].median():.1f}")

    # 비교 분석
    print("\n[비교 분석]")
    print(f"  전체 변화: {df_v0['impulse_score'].mean():.1f} → {df_improved['impulse_score'].mean():.1f}")

    # D/N 유형별 비교
    d_v0 = df_v0[df_v0['sbti'].str[0] == 'D']['impulse_score'].mean()
    d_improved = df_improved[df_improved['sbti'].str[0] == 'D']['impulse_score'].mean()
    n_v0 = df_v0[df_v0['sbti'].str[0] == 'N']['impulse_score'].mean()
    n_improved = df_improved[df_improved['sbti'].str[0] == 'N']['impulse_score'].mean()
    print(f"  D유형: {d_v0:.1f} → {d_improved:.1f} (Δ={d_improved - d_v0:.1f})")
    print(f"  N유형: {n_v0:.1f} → {n_improved:.1f} (Δ={n_improved - n_v0:.1f})")
    print(f"  D-N 차이: {abs(d_v0 - n_v0):.1f} → {abs(d_improved - n_improved):.1f}")

    return df_v0, df_improved


def main():
    df_v0, df_improved = compute_all_versions()

    # v0 검증
    print("\n[v0 검증]")
    products = pd.read_parquet(OUTPUT_DIR / "products_600.parquet")
    users = pd.read_parquet(OUTPUT_DIR / "virtual_users.parquet")
    sample = df_v0.sample(n=10, random_state=42)
    mismatches = 0
    for _, row in sample.iterrows():
        prod = products[products["product_id"] == row["product_id"]].iloc[0]
        usr = users[users["user_id"] == row["user_id"]].iloc[0]
        expected = compute_impulse_score(
            discount_rate=prod["discount_rate"],
            review_count=prod["review_count"],
            rating=prod["rating"],
            like_count=prod["like_count"],
            trend_hype=prod["trend_hype"],
            bundle=prod["bundle"],
            confidence=prod["confidence"],
            is_D=usr["is_D"], is_N=usr["is_N"],
            is_U=usr["is_U"], is_I=usr["is_I"],
            is_T=usr["is_T"], is_M=usr["is_M"],
            is_E=usr["is_E"], is_O=usr["is_O"],
            platform=prod["platform"],
        )
        if expected != row["impulse_score"]:
            mismatches += 1
            print(f"  불일치: product={row['product_id']}, user={row['user_id']}: {expected} vs {row['impulse_score']}")
    print(f"  10개 샘플 중 불일치 {mismatches}개")

    # v0 요약
    print(f"\n[v0] Impulse Score 분포:")
    print(df_v0["impulse_score"].describe().to_string())

    print(f"\n[v0_improved] Impulse Score 분포:")
    print(df_improved["impulse_score"].describe().to_string())


if __name__ == "__main__":
    main()
