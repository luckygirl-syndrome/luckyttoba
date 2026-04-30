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


def decompose_impulse(product, user):
    """Impulse Score + 5개 피쳐 기여도 분해."""
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

    return {
        "impulse_score": impulse_score,
        "discount_contrib": round(discount_contrib, 6),
        "rating_contrib": round(rating_contrib, 6),
        "review_contrib": round(review_contrib, 6),
        "like_contrib": round(like_contrib, 6),
        "marketing_contrib": round(marketing_contrib, 6),
    }


def main():
    products = pd.read_parquet(OUTPUT_DIR / "products_600.parquet")
    users = pd.read_parquet(OUTPUT_DIR / "virtual_users.parquet")
    print(f"상품: {len(products)}개, 유저: {len(users)}명")
    print(f"계산할 쌍: {len(products) * len(users):,}개")

    rows = []
    for _, user in users.iterrows():
        user_dict = user.to_dict()
        for _, prod in products.iterrows():
            prod_dict = prod.to_dict()
            result = decompose_impulse(prod_dict, user_dict)
            rows.append({
                "product_id": prod_dict["product_id"],
                "user_id": user_dict["user_id"],
                "sbti": user_dict["sbti"],
                "platform": prod_dict["platform"],
                **result,
            })

    df = pd.DataFrame(rows)
    out_path = OUTPUT_DIR / "impulse_scores.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\n저장: {out_path}")

    # 검증: compute_impulse_score와 일치하는지 샘플 체크
    sample = df.sample(n=10, random_state=42)
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
    print(f"\n검증: 10개 샘플 중 불일치 {mismatches}개")

    # 요약
    print(f"\nImpulse Score 분포:")
    print(df["impulse_score"].describe().to_string())

    print(f"\n피쳐 기여도 평균 (raw):")
    for col in ["discount_contrib", "rating_contrib", "review_contrib", "like_contrib", "marketing_contrib"]:
        print(f"  {col}: {df[col].mean():.4f}")


if __name__ == "__main__":
    main()
