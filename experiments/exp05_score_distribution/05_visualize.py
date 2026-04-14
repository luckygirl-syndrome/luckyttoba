"""시험 5 — Step 5: 분포 시각화 전체.

Impulse Score + Match 소계 + 2차원 산점도.
출력: insights/*.png
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

CONFIG = yaml.safe_load(
    (Path(__file__).parent / "configs" / "experiment_params.yaml").read_text(encoding="utf-8")
)
DPI = CONFIG["fig_dpi"]
BINS = CONFIG["hist_bins"]

DATA_DIR = Path(__file__).parent / "outputs"
INSIGHT_DIR = Path(__file__).parent / "insights"
INSIGHT_DIR.mkdir(exist_ok=True)


def load_data():
    impulse = pd.read_parquet(DATA_DIR / "impulse_scores.parquet")
    match = pd.read_parquet(DATA_DIR / "match_subtotals.parquet")
    users = pd.read_parquet(DATA_DIR / "virtual_users.parquet")
    products = pd.read_parquet(DATA_DIR / "products_600.parquet")
    return impulse, match, users, products


# ══════════════════════════════════════════════════════════
# (a) Impulse Score 전체 히스토그램
# ══════════════════════════════════════════════════════════
def plot_impulse_histogram(impulse: pd.DataFrame):
    scores = impulse["impulse_score"]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(scores, bins=BINS, range=(0, 100), edgecolor="white", alpha=0.8, color="#4C72B0")

    mean, median, std = scores.mean(), scores.median(), scores.std()
    ax.axvline(mean, color="red", linestyle="--", label=f"평균: {mean:.1f}")
    ax.axvline(median, color="orange", linestyle="-", label=f"중앙값: {median:.1f}")

    # 분위수 라인
    for q, label in [(20, "20%"), (40, "40%"), (60, "60%"), (80, "80%")]:
        val = np.percentile(scores, q)
        ax.axvline(val, color="gray", linestyle=":", alpha=0.6)
        ax.text(val + 0.5, ax.get_ylim()[1] * 0.95, f"P{q}={val:.0f}",
                fontsize=8, color="gray", rotation=90, va="top")

    ax.set_xlabel("Impulse Score")
    ax.set_ylabel("빈도")
    ax.set_title(f"Impulse Score 분포 (N={len(scores):,}, std={std:.1f})")
    ax.legend()
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "impulse_histogram.png", dpi=DPI)
    plt.close(fig)
    print("  impulse_histogram.png")


# ══════════════════════════════════════════════════════════
# (b) 유형별 비교
# ══════════════════════════════════════════════════════════
def plot_type_comparison(impulse: pd.DataFrame):
    # DUTE vs NIMO 오버레이
    fig, ax = plt.subplots(figsize=(10, 6))
    for sbti, color in [("DUTE", "#E74C3C"), ("NIMO", "#3498DB")]:
        sub = impulse[impulse["sbti"] == sbti]["impulse_score"]
        ax.hist(sub, bins=BINS, range=(0, 100), alpha=0.5, label=f"{sbti} (n={len(sub)}, μ={sub.mean():.1f})", color=color)
    ax.set_xlabel("Impulse Score")
    ax.set_ylabel("빈도")
    ax.set_title("DUTE vs NIMO Impulse Score 비교")
    ax.legend()
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "impulse_dute_vs_nimo.png", dpi=DPI)
    plt.close(fig)
    print("  impulse_dute_vs_nimo.png")

    # D형 vs N형 비교
    impulse_dn = impulse.copy()
    impulse_dn["dn_type"] = impulse_dn["sbti"].str[0].map({"D": "D형 (도파민)", "N": "N형 (필요)"})
    fig, ax = plt.subplots(figsize=(10, 6))
    for dn, color in [("D형 (도파민)", "#E74C3C"), ("N형 (필요)", "#3498DB")]:
        sub = impulse_dn[impulse_dn["dn_type"] == dn]["impulse_score"]
        ax.hist(sub, bins=BINS, range=(0, 100), alpha=0.5, label=f"{dn} (μ={sub.mean():.1f})", color=color)
    ax.set_xlabel("Impulse Score")
    ax.set_ylabel("빈도")
    ax.set_title("D형 vs N형 Impulse Score 비교")
    ax.legend()
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "impulse_d_vs_n.png", dpi=DPI)
    plt.close(fig)
    print("  impulse_d_vs_n.png")

    # 16유형 박스플롯 (중앙값 순 정렬)
    medians = impulse.groupby("sbti")["impulse_score"].median().sort_values()
    order = medians.index.tolist()

    fig, ax = plt.subplots(figsize=(14, 6))
    sns.boxplot(data=impulse, x="sbti", y="impulse_score", hue="sbti", order=order, ax=ax, palette="RdYlBu_r", legend=False)
    ax.set_xlabel("S-BTI 유형")
    ax.set_ylabel("Impulse Score")
    ax.set_title("16유형별 Impulse Score 분포 (중앙값 순)")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "impulse_16types_boxplot.png", dpi=DPI)
    plt.close(fig)
    print("  impulse_16types_boxplot.png")


# ══════════════════════════════════════════════════════════
# (c) 피쳐별 기여도
# ══════════════════════════════════════════════════════════
def plot_feature_contribution(impulse: pd.DataFrame):
    contrib_cols = ["discount_contrib", "rating_contrib", "review_contrib", "like_contrib", "marketing_contrib"]
    labels = ["할인율", "평점", "리뷰수", "좋아요수", "마케팅"]

    # 평균 비율 파이차트
    means = [impulse[c].mean() for c in contrib_cols]
    total = sum(means)
    ratios = [m / total * 100 for m in means]

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        ratios, labels=labels, autopct="%1.1f%%", startangle=90,
        colors=sns.color_palette("Set2", len(labels)),
    )
    ax.set_title("피쳐별 평균 기여도 비율")
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "impulse_feature_pie.png", dpi=DPI)
    plt.close(fig)
    print("  impulse_feature_pie.png")

    # 피쳐 간 상관행렬 히트맵
    corr = impulse[contrib_cols].corr()
    corr.index = labels
    corr.columns = labels
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, ax=ax)
    ax.set_title("피쳐 기여도 상관행렬")
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "impulse_feature_corr.png", dpi=DPI)
    plt.close(fig)
    print("  impulse_feature_corr.png")

    # 유형별 피쳐 기여도 stacked bar
    from shared.sbti_types import ALL_TYPES
    type_means = impulse.groupby("sbti")[contrib_cols].mean().reindex(ALL_TYPES)

    fig, ax = plt.subplots(figsize=(14, 6))
    bottom = np.zeros(len(ALL_TYPES))
    colors = sns.color_palette("Set2", len(contrib_cols))
    for i, (col, label) in enumerate(zip(contrib_cols, labels)):
        vals = type_means[col].values
        ax.bar(ALL_TYPES, vals, bottom=bottom, label=label, color=colors[i])
        bottom += vals
    ax.set_xlabel("S-BTI 유형")
    ax.set_ylabel("기여도 (raw)")
    ax.set_title("유형별 피쳐 기여도 구성")
    ax.legend(loc="upper right")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "impulse_feature_stacked.png", dpi=DPI)
    plt.close(fig)
    print("  impulse_feature_stacked.png")


# ══════════════════════════════════════════════════════════
# (d) 플랫폼별 비교
# ══════════════════════════════════════════════════════════
def plot_platform_comparison(impulse: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10, 6))
    platforms = ["에이블리", "무신사", "지그재그"]
    colors = ["#E74C3C", "#3498DB", "#2ECC71"]
    for pf, color in zip(platforms, colors):
        sub = impulse[impulse["platform"] == pf]["impulse_score"]
        ax.hist(sub, bins=BINS, range=(0, 100), alpha=0.4, label=f"{pf} (μ={sub.mean():.1f})", color=color)
    ax.set_xlabel("Impulse Score")
    ax.set_ylabel("빈도")
    ax.set_title("플랫폼별 Impulse Score 분포")
    ax.legend()
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "impulse_platform.png", dpi=DPI)
    plt.close(fig)
    print("  impulse_platform.png")

    # 지그재그 like=0 영향 분리
    zigzag = impulse[impulse["platform"] == "지그재그"].copy()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(zigzag["impulse_score"], bins=BINS, range=(0, 100), alpha=0.5, label="현재 (like=0 포함)", color="#2ECC71")
    # like_contrib를 제외한 점수 시뮬레이션
    # impulse_score는 round((raw/MAX) * 100) 이므로 역산
    from shared.scoring.impulse import MAX_POSSIBLE
    zigzag_no_like = zigzag.copy()
    raw_total = (zigzag["discount_contrib"] + zigzag["rating_contrib"] +
                 zigzag["review_contrib"] + zigzag["like_contrib"] + zigzag["marketing_contrib"])
    raw_no_like = raw_total - zigzag["like_contrib"]
    zigzag_no_like_score = (raw_no_like / MAX_POSSIBLE * 100).clip(0, 100).round().astype(int)
    ax.hist(zigzag_no_like_score, bins=BINS, range=(0, 100), alpha=0.5, label="like_contrib 제외", color="#E67E22")
    ax.set_xlabel("Impulse Score")
    ax.set_ylabel("빈도")
    ax.set_title("지그재그: like_count=0의 영향")
    ax.legend()
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "impulse_zigzag_like_impact.png", dpi=DPI)
    plt.close(fig)
    print("  impulse_zigzag_like_impact.png")


# ══════════════════════════════════════════════════════════
# Match Score 소계 히스토그램
# ══════════════════════════════════════════════════════════
def plot_match_histogram(match: pd.DataFrame):
    scores = match["match_subtotal"]
    fig, ax = plt.subplots(figsize=(10, 6))
    bins = sorted(scores.unique())
    ax.hist(scores, bins=len(bins), edgecolor="white", alpha=0.8, color="#27AE60")
    for val in bins:
        count = (scores == val).sum()
        ax.text(val, count + 0.5, str(count), ha="center", fontsize=9)
    ax.set_xlabel("Match 소계 (style_similarity 제외, 0~65)")
    ax.set_ylabel("유저 수")
    ax.set_title(f"Match 3피쳐 소계 분포 (N={len(scores)}, 고유값={len(bins)}개)")
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "match_subtotal_histogram.png", dpi=DPI)
    plt.close(fig)
    print("  match_subtotal_histogram.png")


# ══════════════════════════════════════════════════════════
# Impulse × Match 2차원 산점도
# ══════════════════════════════════════════════════════════
def plot_2d_scatter(impulse: pd.DataFrame, match: pd.DataFrame):
    # impulse에 match_subtotal 조인
    merged = impulse.merge(match[["user_id", "match_subtotal"]], on="user_id")

    # D/N 2색 버전
    merged["dn"] = merged["sbti"].str[0]
    fig, ax = plt.subplots(figsize=(10, 8))

    impulse_median = merged["impulse_score"].median()
    match_median = merged["match_subtotal"].median()

    for dn, color, label in [("D", "#E74C3C", "D형"), ("N", "#3498DB", "N형")]:
        sub = merged[merged["dn"] == dn]
        ax.scatter(sub["impulse_score"], sub["match_subtotal"],
                   alpha=0.05, s=8, c=color, label=label)

    # 4분면 라인
    ax.axvline(impulse_median, color="gray", linestyle="--", alpha=0.5)
    ax.axhline(match_median, color="gray", linestyle="--", alpha=0.5)

    # 각 분면 비율
    q1 = merged[(merged["impulse_score"] >= impulse_median) & (merged["match_subtotal"] >= match_median)]
    q2 = merged[(merged["impulse_score"] < impulse_median) & (merged["match_subtotal"] >= match_median)]
    q3 = merged[(merged["impulse_score"] < impulse_median) & (merged["match_subtotal"] < match_median)]
    q4 = merged[(merged["impulse_score"] >= impulse_median) & (merged["match_subtotal"] < match_median)]
    total = len(merged)

    ax.text(85, 60, f"Q1: {len(q1)/total*100:.1f}%", fontsize=10, ha="center", fontweight="bold")
    ax.text(10, 60, f"Q2: {len(q2)/total*100:.1f}%", fontsize=10, ha="center", fontweight="bold")
    ax.text(10, 15, f"Q3: {len(q3)/total*100:.1f}%", fontsize=10, ha="center", fontweight="bold")
    ax.text(85, 15, f"Q4: {len(q4)/total*100:.1f}%", fontsize=10, ha="center", fontweight="bold")

    ax.set_xlabel("Impulse Score (0~100)")
    ax.set_ylabel("Match 소계 (0~65)")
    ax.set_title(f"Impulse × Match 2차원 분포 (N={total:,})")
    ax.legend(markerscale=5)
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "impulse_x_match_scatter.png", dpi=DPI)
    plt.close(fig)
    print("  impulse_x_match_scatter.png")


def main():
    impulse, match, users, products = load_data()
    print(f"데이터 로드: impulse={len(impulse):,}, match={len(match)}, users={len(users)}, products={len(products)}")

    print("\n시각화 생성:")
    plot_impulse_histogram(impulse)
    plot_type_comparison(impulse)
    plot_feature_contribution(impulse)
    plot_platform_comparison(impulse)
    plot_match_histogram(match)
    plot_2d_scatter(impulse, match)
    print("\n완료!")


if __name__ == "__main__":
    main()
