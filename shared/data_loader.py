"""3개 플랫폼 크롤링 데이터 정규화 로더.

출력 스키마 (dict):
    product_name    str
    platform        "에이블리" | "무신사" | "지그재그"
    discount_rate   int | None      0~100
    review_count    int              0 이상
    rating          float | None    0.0~5.0
    like_count      int | None      0 이상, 지그재그는 None
    original_price  int | None      원 단위, 에이블리는 None
    sale_price      int | None      원 단위
    category        str | None
    source_url      str | None
"""

import json
import re
from pathlib import Path


# ── 한글 숫자 파서 ──────────────────────────────────────

_UNIT_MAP = {"만": 10_000, "천": 1_000}
_KOREAN_NUM_RE = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)\s*(만|천)?",
)


def parse_korean_number(raw) -> int | None:
    """한글 혼합 숫자 문자열을 int로 변환.

    "9.2만" → 92000, "후기 4,826개" → 4826, "59,900원" → 59900,
    "10%" → 10, None/빈문자열 → None
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)

    s = str(raw).strip()
    if not s:
        return None

    # 콤마 제거, 부가 텍스트(후기, 개, 원, %) 제거
    cleaned = s.replace(",", "")
    cleaned = re.sub(r"[후기개원%\s]", "", cleaned)
    if not cleaned:
        return None

    m = _KOREAN_NUM_RE.search(cleaned)
    if not m:
        return None

    num = float(m.group(1))
    unit = m.group(2)
    if unit and unit in _UNIT_MAP:
        num *= _UNIT_MAP[unit]

    return round(num)


def _safe_float(val) -> float | None:
    """숫자로 변환 가능하면 float, 아니면 None."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# ── 플랫폼별 정규화 ────────────────────────────────────

def _normalize_ably(item: dict) -> dict:
    return {
        "product_name": item["product_name"],
        "platform": "에이블리",
        "discount_rate": parse_korean_number(item.get("discount_rate")),
        "review_count": int(item.get("review_count") or 0),
        "rating": float(item["review_score"]) if item.get("review_score") is not None else None,
        "like_count": parse_korean_number(item.get("product_likes")),
        "original_price": None,
        "sale_price": None,
        "category": None,
        "source_url": item.get("source_url"),
    }


def _normalize_musinsa(item: dict) -> dict:
    discount = parse_korean_number(item.get("discount_rate"))
    original = parse_korean_number(item.get("original_price"))
    sale = parse_korean_number(item.get("sale_price"))

    # sale_price는 항상 있지만 original은 없을 수 있음
    # original이 없고 discount도 없으면 sale_price가 정가
    if original is None and sale is not None and discount is None:
        original = sale

    return {
        "product_name": item["product_name"],
        "platform": "무신사",
        "discount_rate": discount,
        "review_count": parse_korean_number(item.get("review_count")) or 0,
        "rating": _safe_float(item.get("rating")),
        "like_count": parse_korean_number(item.get("product_likes")),
        "original_price": original,
        "sale_price": sale,
        "category": item.get("top_category_parsed"),
        "source_url": item.get("url"),
    }


def _normalize_zigzag(item: dict) -> dict:
    return {
        "product_name": item["name"],
        "platform": "지그재그",
        "discount_rate": parse_korean_number(item.get("discount_rate")),
        "review_count": parse_korean_number(item.get("review_count")) or 0,
        "rating": float(item["review_rating"]) if item.get("review_rating") is not None else None,
        "like_count": None,
        "original_price": parse_korean_number(item.get("original_price")),
        "sale_price": parse_korean_number(item.get("sale_price")),
        "category": item.get("parsed_category"),
        "source_url": item.get("url"),
    }


# ── 로드 함수 ──────────────────────────────────────────

_NORMALIZERS = {
    "에이블리": _normalize_ably,
    "무신사": _normalize_musinsa,
    "지그재그": _normalize_zigzag,
}

_FILE_PATTERNS = {
    "에이블리": "ably",
    "무신사": "musinsa",
    "지그재그": None,  # 나머지 하나
}


def _find_json(data_dir: Path, keyword: str | None) -> Path | None:
    import os
    known_prefixes = {"ably", "musinsa"}
    candidates = [f for f in os.listdir(data_dir) if f.endswith(".json")]
    if keyword is not None:
        for fname in candidates:
            if keyword in fname:
                return data_dir / fname
    else:
        # 에이블리·무신사가 아닌 나머지 = 지그재그
        others = [f for f in candidates if not any(k in f for k in known_prefixes)]
        if len(others) == 1:
            return data_dir / others[0]
        elif len(others) > 1:
            raise ValueError(
                f"data/ 폴더에 ably/musinsa가 아닌 JSON이 {len(others)}개 있어 "
                f"지그재그 파일을 특정할 수 없습니다: {others}"
            )
    return None


def load_platform(data_dir: Path, platform: str) -> list[dict]:
    """단일 플랫폼 데이터 로드 + 정규화."""
    keyword = _FILE_PATTERNS[platform]
    path = _find_json(data_dir, keyword)
    if path is None:
        raise FileNotFoundError(f"{platform} JSON not found in {data_dir}")

    with open(path, "r", encoding="utf-8") as f:
        raw_list = json.load(f)

    normalize = _NORMALIZERS[platform]
    return [normalize(item) for item in raw_list]


def load_all_products(data_dir: str | Path | None = None) -> list[dict]:
    """3개 플랫폼 전체 로드.

    Parameters
    ----------
    data_dir : 데이터 폴더 경로. None이면 프로젝트 루트/data 사용.
    """
    if data_dir is None:
        data_dir = Path(__file__).resolve().parent.parent / "data"
    else:
        data_dir = Path(data_dir)

    products = []
    for platform in ("에이블리", "무신사", "지그재그"):
        products.extend(load_platform(data_dir, platform))
    return products


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    products = load_all_products()
    print(f"총 {len(products)}개 상품 로드")

    # 플랫폼별 카운트
    from collections import Counter
    counts = Counter(p["platform"] for p in products)
    for platform, count in counts.items():
        print(f"  {platform}: {count}")

    # 샘플 출력
    for p in products[:3]:
        print(json.dumps(p, ensure_ascii=False, indent=2))
