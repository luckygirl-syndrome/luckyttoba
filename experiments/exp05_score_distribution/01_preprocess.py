"""시험 5 — Step 1: 크롤링 데이터 전처리 + 플랫폼별 200개 샘플링.

출력: outputs/products_600.parquet
"""

import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shared.data_loader import load_all_products
from shared.marketing_detector import detect_triggers

# ── 설정 로드 ─────────────────────────────────────────────
CONFIG = yaml.safe_load(
    (Path(__file__).parent / "configs" / "experiment_params.yaml").read_text(encoding="utf-8")
)
SEED = CONFIG["seed"]
SAMPLES_PER_PLATFORM = CONFIG["samples_per_platform"]

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    # 1) 전체 로드
    products = load_all_products(ROOT / "data")
    df = pd.DataFrame(products)
    print(f"전체 로드: {len(df)}개")
    print(f"  플랫폼별: {df['platform'].value_counts().to_dict()}")

    # 2) 플랫폼별 200개 샘플링 (seed 고정)
    frames = []
    for platform in ["에이블리", "무신사", "지그재그"]:
        sub = df[df["platform"] == platform]
        n = min(SAMPLES_PER_PLATFORM, len(sub))
        frames.append(sub.sample(n=n, random_state=SEED))
    sampled = pd.concat(frames, ignore_index=True)
    print(f"\n샘플링 후: {len(sampled)}개")
    print(f"  플랫폼별: {sampled['platform'].value_counts().to_dict()}")

    # 3) 이상치 처리
    sampled["rating"] = sampled["rating"].fillna(0.0)
    sampled["discount_rate"] = sampled["discount_rate"].fillna(0)
    sampled["like_count"] = sampled["like_count"].fillna(0)

    # 4) 마케팅 트리거 라벨링
    triggers = sampled["product_name"].apply(detect_triggers)
    sampled["trend_hype"] = triggers.apply(lambda t: t[0])
    sampled["bundle"] = triggers.apply(lambda t: t[1])
    sampled["confidence"] = triggers.apply(lambda t: t[2])

    # 5) product_id 부여
    sampled = sampled.reset_index(drop=True)
    sampled.insert(0, "product_id", range(len(sampled)))

    # 6) 저장
    out_path = OUTPUT_DIR / "products_600.parquet"
    sampled.to_parquet(out_path, index=False)
    print(f"\n저장: {out_path}")

    # 7) 통계 요약
    print("\n── 필드 분포 요약 ──")
    for col in ["discount_rate", "review_count", "rating", "like_count"]:
        print(f"\n{col}:")
        print(sampled[col].describe().to_string())

    print("\n── 마케팅 키워드 히트율 ──")
    for col in ["trend_hype", "bundle", "confidence"]:
        rate = sampled[col].mean() * 100
        print(f"  {col}: {sampled[col].sum()}/{len(sampled)} ({rate:.1f}%)")

    # 플랫폼별 마케팅 히트율
    print("\n── 플랫폼별 마케팅 히트율 ──")
    for platform in ["에이블리", "무신사", "지그재그"]:
        sub = sampled[sampled["platform"] == platform]
        print(f"\n  {platform} ({len(sub)}개):")
        for col in ["trend_hype", "bundle", "confidence"]:
            rate = sub[col].mean() * 100
            print(f"    {col}: {sub[col].sum()}/{len(sub)} ({rate:.1f}%)")


if __name__ == "__main__":
    main()
