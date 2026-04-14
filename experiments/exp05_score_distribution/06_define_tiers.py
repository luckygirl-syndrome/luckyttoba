"""시험 5 — Step 6: 구간 확정 + 이름/설명 + JSON 출력.

Impulse Score: 백분위 → 5배수 반올림 → 5구간
Match 소계: 65점 만점 그대로 (style_similarity 합산 후 최종 재확정)
2차원 4분면 해석 포함.
출력: insights/tier_definitions.json
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = Path(__file__).parent / "outputs"
INSIGHT_DIR = Path(__file__).parent / "insights"
INSIGHT_DIR.mkdir(exist_ok=True)


def round_to_5(val):
    """가장 가까운 5의 배수로 반올림."""
    return int(round(val / 5) * 5)


IMPULSE_TIER_NAMES = {
    1: {"name": "매우 낮음", "description": "충동 요소가 거의 없는 상품-유저 조합"},
    2: {"name": "낮음", "description": "충동 자극이 약한 수준"},
    3: {"name": "보통", "description": "평균적인 충동 자극 수준"},
    4: {"name": "높음", "description": "충동 자극이 강한 수준, 주의 필요"},
    5: {"name": "매우 높음", "description": "충동구매 위험이 높은 조합, 경고 권장"},
}

QUADRANT_DESCRIPTIONS = {
    "Q1_high_impulse_high_match": {
        "label": "충동 높음 + 취향 맞음",
        "description": "충동 요소가 강하지만 실제 취향에도 맞는 상품. 구매 자체는 나쁘지 않으나 충동적 결정은 경계.",
        "recommendation": "잠깐 멈추고 정말 필요한지 생각해보세요",
    },
    "Q2_low_impulse_high_match": {
        "label": "충동 낮음 + 취향 맞음",
        "description": "충동 자극 없이 취향에 맞는 건강한 구매 후보.",
        "recommendation": "좋은 선택이에요!",
    },
    "Q3_low_impulse_low_match": {
        "label": "충동 낮음 + 취향 안맞음",
        "description": "충동도 없고 취향도 안 맞음. 자연스럽게 넘어갈 상품.",
        "recommendation": "다른 상품을 둘러보는 건 어때요?",
    },
    "Q4_high_impulse_low_match": {
        "label": "충동 높음 + 취향 안맞음",
        "description": "충동에 의해 끌리지만 실제 취향과는 안 맞는 위험한 조합.",
        "recommendation": "충동구매 위험! 한번 더 생각해보세요",
    },
}


def define_impulse_tiers(impulse: pd.DataFrame):
    scores = impulse["impulse_score"]

    # 백분위 계산
    percentiles = {}
    for q in [20, 40, 60, 80]:
        raw = np.percentile(scores, q)
        rounded = round_to_5(raw)
        percentiles[f"P{q}"] = {"raw": float(raw), "rounded": rounded}

    # 구간 경계
    boundaries = [
        percentiles["P20"]["rounded"],
        percentiles["P40"]["rounded"],
        percentiles["P60"]["rounded"],
        percentiles["P80"]["rounded"],
    ]

    tiers = []
    ranges = [
        (0, boundaries[0]),
        (boundaries[0] + 1, boundaries[1]),
        (boundaries[1] + 1, boundaries[2]),
        (boundaries[2] + 1, boundaries[3]),
        (boundaries[3] + 1, 100),
    ]
    for i, (lo, hi) in enumerate(ranges, 1):
        tier_info = IMPULSE_TIER_NAMES[i]
        count = len(scores[(scores >= lo) & (scores <= hi)])
        tiers.append({
            "tier": i,
            "name": tier_info["name"],
            "description": tier_info["description"],
            "range": [lo, hi],
            "count": int(count),
            "ratio": round(count / len(scores) * 100, 1),
        })

    return {
        "score_type": "impulse",
        "total": int(len(scores)),
        "stats": {
            "mean": round(float(scores.mean()), 1),
            "median": round(float(scores.median()), 1),
            "std": round(float(scores.std()), 1),
            "min": int(scores.min()),
            "max": int(scores.max()),
        },
        "percentiles": percentiles,
        "tiers": tiers,
    }


def define_match_info(match: pd.DataFrame):
    scores = match["match_subtotal"]
    return {
        "score_type": "match_subtotal",
        "note": "style_similarity 제외, 65점 만점. 시험 3 후 최종 구간 재확정.",
        "total": int(len(scores)),
        "stats": {
            "mean": round(float(scores.mean()), 1),
            "median": round(float(scores.median()), 1),
            "std": round(float(scores.std()), 1),
            "min": int(scores.min()),
            "max": int(scores.max()),
        },
        "unique_values": sorted([int(v) for v in scores.unique()]),
    }


def define_quadrants(impulse: pd.DataFrame, match: pd.DataFrame):
    merged = impulse.merge(match[["user_id", "match_subtotal"]], on="user_id")
    imp_med = merged["impulse_score"].median()
    mat_med = merged["match_subtotal"].median()

    total = len(merged)
    q_stats = {}
    for key, imp_cond, mat_cond in [
        ("Q1_high_impulse_high_match", ">=", ">="),
        ("Q2_low_impulse_high_match", "<", ">="),
        ("Q3_low_impulse_low_match", "<", "<"),
        ("Q4_high_impulse_low_match", ">=", "<"),
    ]:
        if imp_cond == ">=":
            imp_mask = merged["impulse_score"] >= imp_med
        else:
            imp_mask = merged["impulse_score"] < imp_med
        if mat_cond == ">=":
            mat_mask = merged["match_subtotal"] >= mat_med
        else:
            mat_mask = merged["match_subtotal"] < mat_med

        count = int((imp_mask & mat_mask).sum())
        q_stats[key] = {
            **QUADRANT_DESCRIPTIONS[key],
            "count": count,
            "ratio": round(count / total * 100, 1),
        }

    return {
        "impulse_median": round(float(imp_med), 1),
        "match_median": round(float(mat_med), 1),
        "quadrants": q_stats,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    impulse = pd.read_parquet(DATA_DIR / "impulse_scores.parquet")
    match = pd.read_parquet(DATA_DIR / "match_subtotals.parquet")

    impulse_tiers = define_impulse_tiers(impulse)
    match_info = define_match_info(match)
    quadrant_info = define_quadrants(impulse, match)

    result = {
        "impulse_score": impulse_tiers,
        "match_score": match_info,
        "quadrant_analysis": quadrant_info,
    }

    out_path = INSIGHT_DIR / "tier_definitions.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"저장: {out_path}")

    # 요약 출력
    print("\n═══ Impulse Score 구간 ═══")
    for tier in impulse_tiers["tiers"]:
        print(f"  Tier {tier['tier']} [{tier['range'][0]}~{tier['range'][1]}] "
              f"{tier['name']}: {tier['count']:,}개 ({tier['ratio']}%)")

    print(f"\n═══ Match 소계 (참고) ═══")
    print(f"  범위: {match_info['stats']['min']}~{match_info['stats']['max']}")
    print(f"  고유값: {match_info['unique_values']}")

    print(f"\n═══ 4분면 분석 ═══")
    print(f"  기준: Impulse median={quadrant_info['impulse_median']}, "
          f"Match median={quadrant_info['match_median']}")
    for key, info in quadrant_info["quadrants"].items():
        print(f"  {info['label']}: {info['count']:,}개 ({info['ratio']}%)")


if __name__ == "__main__":
    main()
