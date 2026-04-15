"""키워드 기반 마케팅 트리거 검출.

시험 5에서 48,000개 상품의 marketing score 계산에 사용.
시험 1에서 LLM 추출 결과와 비교할 키워드 베이스라인으로도 사용.
"""

TREND_KEYWORDS = [
    "인기", "랭킹", "베스트", "HOT", "hot", "트렌드",
    "유행", "대세", "히트", "핫딜", "MD추천", "위클리",
]

BUNDLE_KEYWORDS = [
    "1+1", "세트", "묶음", "증정", "사은품", "추가할인",
    "2개", "3개", "+1", "덤", "같이구매",
]

CONFIDENCE_KEYWORDS = [
    "후기", "리얼", "검증", "입증", "보장", "추천",
    "누적판매", "재구매", "만족도", "품질보증",
]


def detect_triggers(product_name: str) -> tuple[int, int, int]:
    """상품명에서 마케팅 트리거 3종을 검출.

    Returns
    -------
    (trend_hype, bundle, confidence) — 각 0 또는 1
    """
    name = product_name.upper()

    trend = 1 if any(kw.upper() in name for kw in TREND_KEYWORDS) else 0
    bundle = 1 if any(kw.upper() in name for kw in BUNDLE_KEYWORDS) else 0
    conf = 1 if any(kw.upper() in name for kw in CONFIDENCE_KEYWORDS) else 0

    return (trend, bundle, conf)


def detect_triggers_detail(product_name: str) -> dict:
    """상품명에서 마케팅 트리거를 검출하고, 매칭된 키워드도 반환.

    Returns
    -------
    {"trend_hype": 0|1, "trend_phrases": [...],
     "bundle": 0|1, "bundle_phrases": [...],
     "confidence": 0|1, "confidence_phrases": [...]}
    """
    name = product_name.upper()

    trend_hits = [kw for kw in TREND_KEYWORDS if kw.upper() in name]
    bundle_hits = [kw for kw in BUNDLE_KEYWORDS if kw.upper() in name]
    conf_hits = [kw for kw in CONFIDENCE_KEYWORDS if kw.upper() in name]

    return {
        "trend_hype": 1 if trend_hits else 0,
        "trend_phrases": trend_hits,
        "bundle": 1 if bundle_hits else 0,
        "bundle_phrases": bundle_hits,
        "confidence": 1 if conf_hits else 0,
        "confidence_phrases": conf_hits,
    }
