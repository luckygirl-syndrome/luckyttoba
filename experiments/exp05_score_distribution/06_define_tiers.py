"""시험 5 — Step 6: Match Score 구간(Tier) 정의.

style_similarity 제외 65점 범위에서 구간 설계.
3가지 구간 방식 제시: 4분위, 자연분포, 3등급.
출력: outputs/tier_definitions.json
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = Path(__file__).parent / "outputs"


def define_tiers_by_percentile(match: pd.DataFrame):
    """백분위 기반 4분위 구간."""
    scores = match["match_subtotal"]

    p25 = np.percentile(scores, 25)
    p50 = np.percentile(scores, 50)
    p75 = np.percentile(scores, 75)

    tiers = {
        "method": "percentile_4tier",
        "description": "25th, 50th, 75th percentile 기반 4구간 (균등 분할)",
        "tiers": [
            {
                "tier": 1,
                "name": "구매 위험",
                "label": "위험",
                "range": [int(scores.min()), int(p25)],
                "description": "충동구매 가능성 높음 (하위 25%)",
                "color": "#E74C3C",
                "emoji": "🔴",
                "percentile": "0~25%",
                "count": sum(scores <= p25),
            },
            {
                "tier": 2,
                "name": "구매 신중",
                "label": "신중",
                "range": [int(p25) + 1, int(p50)],
                "description": "충동구매 가능성 중간 (25~50%)",
                "color": "#F39C12",
                "emoji": "🟡",
                "percentile": "25~50%",
                "count": sum((scores > p25) & (scores <= p50)),
            },
            {
                "tier": 3,
                "name": "구매 검토",
                "label": "검토",
                "range": [int(p50) + 1, int(p75)],
                "description": "충동구매 가능성 낮음 (50~75%)",
                "color": "#3498DB",
                "emoji": "🟢",
                "percentile": "50~75%",
                "count": sum((scores > p50) & (scores <= p75)),
            },
            {
                "tier": 4,
                "name": "구매 적합",
                "label": "적합",
                "range": [int(p75) + 1, int(scores.max())],
                "description": "충동구매 가능성 매우 낮음 (상위 25%)",
                "color": "#27AE60",
                "emoji": "✅",
                "percentile": "75~100%",
                "count": sum(scores > p75),
            },
        ],
    }

    return tiers


def define_tiers_by_natural_breaks(match: pd.DataFrame):
    """자연스러운 분포 기반 (μ±σ)."""
    scores = match["match_subtotal"]
    mean = scores.mean()
    std = scores.std()

    tiers = {
        "method": "natural_breaks",
        "description": "평균과 표준편차 기반 구간 (μ±σ)",
        "tiers": [
            {
                "tier": 1,
                "name": "구매 위험",
                "label": "위험",
                "range": [int(scores.min()), int(mean - std)],
                "description": "평균 이하 (μ-σ 이하)",
                "color": "#E74C3C",
                "emoji": "🔴",
                "z_score": "-1σ 이하",
                "count": sum(scores <= mean - std),
            },
            {
                "tier": 2,
                "name": "구매 신중",
                "label": "신중",
                "range": [int(mean - std) + 1, int(mean)],
                "description": "평균 근처 (-1σ ~ 0)",
                "color": "#F39C12",
                "emoji": "🟡",
                "z_score": "-1σ ~ 0",
                "count": sum((scores > mean - std) & (scores <= mean)),
            },
            {
                "tier": 3,
                "name": "구매 검토",
                "label": "검토",
                "range": [int(mean) + 1, int(mean + std)],
                "description": "평균 이상 (0 ~ +1σ)",
                "color": "#3498DB",
                "emoji": "🟢",
                "z_score": "0 ~ +1σ",
                "count": sum((scores > mean) & (scores <= mean + std)),
            },
            {
                "tier": 4,
                "name": "구매 적합",
                "label": "적합",
                "range": [int(mean + std) + 1, int(scores.max())],
                "description": "평균 초과 (+1σ 이상)",
                "color": "#27AE60",
                "emoji": "✅",
                "z_score": "+1σ 이상",
                "count": sum(scores > mean + std),
            },
        ],
    }

    return tiers


def define_tiers_3tier(match: pd.DataFrame):
    """3등급 단순 정의."""
    scores = match["match_subtotal"]
    p33 = np.percentile(scores, 33.33)
    p66 = np.percentile(scores, 66.67)

    tiers = {
        "method": "percentile_3tier",
        "description": "3등급 단순 분할 (하/중/상)",
        "tiers": [
            {
                "tier": 1,
                "name": "위험",
                "label": "Low",
                "range": [int(scores.min()), int(p33)],
                "description": "충동구매 가능성 높음",
                "color": "#E74C3C",
                "emoji": "🔴",
                "percentile": "0~33%",
                "count": sum(scores <= p33),
            },
            {
                "tier": 2,
                "name": "중간",
                "label": "Medium",
                "range": [int(p33) + 1, int(p66)],
                "description": "중간 수준",
                "color": "#F39C12",
                "emoji": "🟡",
                "percentile": "33~67%",
                "count": sum((scores > p33) & (scores <= p66)),
            },
            {
                "tier": 3,
                "name": "적합",
                "label": "High",
                "range": [int(p66) + 1, int(scores.max())],
                "description": "충동구매 가능성 낮음",
                "color": "#27AE60",
                "emoji": "✅",
                "percentile": "67~100%",
                "count": sum(scores > p66),
            },
        ],
    }

    return tiers


def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    print("시작: Match Score 구간 정의")
    match = pd.read_parquet(DATA_DIR / "match_subtotals.parquet")
    print(f"데이터: {len(match)}명\n")

    # 3가지 구간 정의 생성
    tiers_percentile = define_tiers_by_percentile(match)
    tiers_natural = define_tiers_by_natural_breaks(match)
    tiers_3tier = define_tiers_3tier(match)

    # 전체 구간 정의
    all_tiers = {
        "version": "1.0",
        "timestamp": pd.Timestamp.now().isoformat(),
        "data_points": len(match),
        "score_range": [int(match["match_subtotal"].min()), int(match["match_subtotal"].max())],
        "distribution": {
            "mean": round(float(match["match_subtotal"].mean()), 2),
            "median": float(match["match_subtotal"].median()),
            "std": round(float(match["match_subtotal"].std()), 2),
            "unique_values": int(match["match_subtotal"].nunique()),
        },
        "recommended_tier": tiers_percentile,
        "alternatives": [
            tiers_natural,
            tiers_3tier,
        ],
    }

    # JSON 저장
    out_path = DATA_DIR / "tier_definitions.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_tiers, f, indent=2, ensure_ascii=False)

    print(f"저장: {out_path}\n")

    # 콘솔 출력
    print("=" * 70)
    print("추천 구간 정의 (4분위 백분위 기반)")
    print("=" * 70)
    for tier_info in tiers_percentile["tiers"]:
        ratio = tier_info["count"] / len(match) * 100
        print(
            f"\n{tier_info['emoji']} Tier {tier_info['tier']}: {tier_info['name']}"
        )
        print(f"   범위: {tier_info['range'][0]}~{tier_info['range'][1]}점")
        print(f"   백분위: {tier_info['percentile']}")
        print(f"   유저 수: {tier_info['count']}명 ({ratio:.1f}%)")
        print(f"   설명: {tier_info['description']}")

    print("\n" + "=" * 70)
    print("대안 1: 자연스러운 분포 기반 (μ±σ)")
    print("=" * 70)
    for tier_info in tiers_natural["tiers"]:
        ratio = tier_info["count"] / len(match) * 100
        print(
            f"\n{tier_info['emoji']} Tier {tier_info['tier']}: {tier_info['name']}"
        )
        print(f"   범위: {tier_info['range'][0]}~{tier_info['range'][1]}점")
        print(f"   Z-score: {tier_info['z_score']}")
        print(f"   유저 수: {tier_info['count']}명 ({ratio:.1f}%)")

    print("\n" + "=" * 70)
    print("대안 2: 단순 3등급 (하/중/상)")
    print("=" * 70)
    for tier_info in tiers_3tier["tiers"]:
        ratio = tier_info["count"] / len(match) * 100
        print(
            f"\n{tier_info['emoji']} Tier {tier_info['tier']}: {tier_info['name']}"
        )
        print(f"   범위: {tier_info['range'][0]}~{tier_info['range'][1]}점")
        print(f"   유저 수: {tier_info['count']}명 ({ratio:.1f}%)")


if __name__ == "__main__":
    main()
