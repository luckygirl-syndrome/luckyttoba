"""Impulse Score 계산 — docs/Impulse Score & Match Score.md 기반."""

from math import log10


# ==============================================
# M형 플랫폼별 임계값 테이블
# ==============================================

REVIEW_M_TABLE = {
    "무신사":     (100,   650,   0.0,  -0.4,  -0.9),
    "에이블리":   (800,   3000,  0.0,  -0.4,  -0.9),
    "지그재그":   (600,   2500,  0.0,  -0.4,  -0.9),
    "default":    (100,   650,   0.0,  -0.4,  -0.9),
}

LIKE_M_TABLE = {
    "무신사":     (4000,  13000,  0.0,  -0.3,  -0.6),
    "에이블리":   (10000, 30000,  0.0,  -0.3,  -0.6),
    "지그재그":   (None,  None,   0.0,   0.0,   0.0),
    "default":    (4000,  13000,  0.0,  -0.3,  -0.6),
}

DISCOUNT_TABLE = [
    (0,   0,   0.00),
    (1,   10,  0.15),
    (11,  20,  0.35),
    (21,  35,  0.65),
    (36,  50,  1.00),
    (51,  60,  0.75),
    (61,  70,  0.45),
    (71,  100, 0.25),
]

MAX_POSSIBLE = 1.384  # DUTE 기준 이론적 최댓값


def _get_m_score(count, table, platform):
    row = table.get(platform, table["default"])
    n, n2, score_low, score_mid, score_high = row
    if n is None:
        return 0.0
    if count <= n:
        return score_low
    elif count <= n2:
        return score_mid
    else:
        return score_high


def _get_discount_score(discount_rate):
    if discount_rate is None:
        return 0.00
    for lo, hi, score in DISCOUNT_TABLE:
        if lo <= discount_rate <= hi:
            return score
    return 0.00


def compute_impulse_score(
    # 상품 데이터
    discount_rate,
    review_count,
    rating,
    like_count,
    trend_hype,      # 0 or 1
    bundle,          # 0 or 1
    confidence,      # 0 or 1
    # 유저 SBTI 플래그
    is_D, is_N,
    is_U, is_I,
    is_T, is_M,
    is_E, is_O,
    # 플랫폼
    platform="default",
    # 마케팅 트리거 연속 스코어 (0.0~1.0, None이면 0/1 사용)
    trend_hype_score=None,
    bundle_score=None,
    confidence_score=None,
) -> int:
    """Impulse Score (0~100) 계산."""

    # Step 1: 피쳐 정규화
    discount_score = _get_discount_score(discount_rate)

    if is_M:
        review_score = _get_m_score(review_count, REVIEW_M_TABLE, platform)
    else:
        review_score = min(log10(review_count + 1) / log10(5001), 1.0) ** 1.5

    if review_count == 0:
        rating_score = 0.3
    else:
        rating_score = max((rating - 3.0) / 2.0, 0.0)

    if is_M:
        like_score = _get_m_score(like_count, LIKE_M_TABLE, platform)
    else:
        like_score = min(log10(like_count + 1) / log10(10001), 1.0) ** 1.5

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

    # 연속 스코어가 주어지면 0/1 대신 사용
    th = trend_hype if trend_hype_score is None else trend_hype_score
    bd = bundle if bundle_score is None else bundle_score
    cf = confidence if confidence_score is None else confidence_score

    w_total = w1 + w2 + w3
    if w_total > 0:
        title_marketing_score = (w1 * th + w2 * bd + w3 * cf) / w_total
    else:
        title_marketing_score = 0.0

    # Step 2: SBTI Multiplier
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

    # Step 3: 가중합
    raw_score = (
        0.35 * discount_score         * discount_m
      + 0.20 * rating_score           * rating_m
      + 0.15 * review_score           * review_count_m
      + 0.10 * like_score             * like_count_m
      + 0.20 * title_marketing_score  * title_marketing_m
    )

    # Step 4: 0~100 변환 (기본 점수 가산)
    base = 10 + (5 if is_D else 0)
    return max(0, min(100, round((raw_score / MAX_POSSIBLE) * 100) + base))
