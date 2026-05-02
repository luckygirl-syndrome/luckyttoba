"""시험 5 — Step 5: Match Score 3피쳐 분포 시각화.

style_similarity 제외 65점 범위에서 피쳐 분포 분석.
출력: insights/*.png
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

DPI = 150
BINS = 20

DATA_DIR = Path(__file__).parent / "outputs"
INSIGHT_DIR = Path(__file__).parent / "insights"
INSIGHT_DIR.mkdir(exist_ok=True)


def load_data():
    """Match Score 데이터 로드."""
    match = pd.read_parquet(DATA_DIR / "match_subtotals.parquet")
    return match


# ══════════════════════════════════════════════════════════
# 1. 전체 Match Score 분포
# ══════════════════════════════════════════════════════════
def plot_match_distribution(match: pd.DataFrame):
    """전체 점수 분포 + 통계."""
    scores = match["match_subtotal"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # 히스토그램
    ax1.hist(scores, bins=BINS, edgecolor="black", alpha=0.7, color="#27AE60")
    mean_val = scores.mean()
    median_val = scores.median()
    ax1.axvline(mean_val, color="red", linestyle="--", linewidth=2, label=f"평균: {mean_val:.1f}")
    ax1.axvline(median_val, color="orange", linestyle="-", linewidth=2, label=f"중앙값: {median_val:.1f}")

    ax1.set_xlabel("Match Score (0~65)", fontsize=11)
    ax1.set_ylabel("유저 수", fontsize=11)
    ax1.set_title(f"Match Score 분포 (N={len(scores)})", fontsize=12, fontweight="bold")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    # 박스플롯
    bp = ax2.boxplot([scores], labels=["Match"], patch_artist=True)
    bp["boxes"][0].set_facecolor("#27AE60")
    ax2.set_ylabel("Match Score", fontsize=11)
    ax2.set_title("박스플롯", fontsize=12, fontweight="bold")
    ax2.grid(axis="y", alpha=0.3)

    # 통계 텍스트
    stats_text = f"""
    평균: {mean_val:.2f}
    중앙값: {median_val:.2f}
    표준편차: {scores.std():.2f}
    최소값: {scores.min():.0f}
    최대값: {scores.max():.0f}
    고유값: {scores.nunique()}개
    """
    ax2.text(1.3, scores.max() * 0.5, stats_text, fontsize=10,
             bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "01_match_distribution.png", dpi=DPI)
    plt.close(fig)
    print("  01_match_distribution.png")


# ══════════════════════════════════════════════════════════
# 2. 피쳐별 분포 (3개 feature)
# ══════════════════════════════════════════════════════════
def plot_feature_distributions(match: pd.DataFrame):
    """가격, 관심지속도, 발견경로별 분포."""
    features = [
        ("price_reasonable", "Price Reasonable\n(가격 적합도)", "#E74C3C", 0, 26),
        ("interest_persistence", "Interest Persistence\n(관심 지속도)", "#3498DB", 0, 21),
        ("discovery_stability", "Discovery Stability\n(발견 경로 안정도)", "#F39C12", 0, 21),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for ax, (col, label, color, y_min, y_max) in zip(axes, features):
        data = match[col]
        unique_vals = sorted(data.unique())
        counts = [sum(data == v) for v in unique_vals]

        ax.bar(range(len(unique_vals)), counts, color=color, alpha=0.7, edgecolor="black")

        # 각 막대에 값과 개수 표시
        for i, (val, count) in enumerate(zip(unique_vals, counts)):
            ax.text(i, count + 0.3, f"{count}\n({val}점)", ha="center", fontsize=9)

        ax.set_xticks(range(len(unique_vals)))
        ax.set_xticklabels([f"{v}점" for v in unique_vals])
        ax.set_ylabel("유저 수", fontsize=10)
        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.set_ylim(0, max(counts) * 1.2)
        ax.grid(axis="y", alpha=0.3)

        # 통계
        stats = f"μ={data.mean():.1f}\nσ={data.std():.1f}"
        ax.text(0.95, 0.95, stats, transform=ax.transAxes, fontsize=9,
                verticalalignment="top", horizontalalignment="right",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "02_feature_distributions.png", dpi=DPI)
    plt.close(fig)
    print("  02_feature_distributions.png")


# ══════════════════════════════════════════════════════════
# 3. 피쳐 간 상관성
# ══════════════════════════════════════════════════════════
def plot_feature_correlations(match: pd.DataFrame):
    """3피쳐 간 산점도 + 상관계수."""
    features = ["price_reasonable", "interest_persistence", "discovery_stability"]
    labels = ["Price", "Interest", "Discovery"]

    fig, axes = plt.subplots(3, 3, figsize=(12, 12))

    for i in range(3):
        for j in range(3):
            ax = axes[i, j]

            if i == j:
                # 대각선: 히스토그램
                ax.hist(match[features[i]], bins=10, color="skyblue", alpha=0.7, edgecolor="black")
                ax.set_ylabel("Freq", fontsize=9)
            else:
                # 오프-대각선: 산점도
                ax.scatter(match[features[j]], match[features[i]], alpha=0.5, s=30, color="steelblue")

                # 상관계수
                corr = match[features[i]].corr(match[features[j]])
                ax.text(0.05, 0.95, f"r={corr:.2f}", transform=ax.transAxes, fontsize=9,
                       verticalalignment="top", bbox=dict(boxstyle="round", facecolor="yellow", alpha=0.7))

            if i == 2:
                ax.set_xlabel(labels[j], fontsize=10)
            if j == 0:
                ax.set_ylabel(labels[i], fontsize=10)

    fig.suptitle("피쳐 간 상관성 분석", fontsize=13, fontweight="bold", y=0.995)
    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "03_feature_correlations.png", dpi=DPI)
    plt.close(fig)
    print("  03_feature_correlations.png")


# ══════════════════════════════════════════════════════════
# 4. 누적 분포 (CDF)
# ══════════════════════════════════════════════════════════
def plot_cumulative_distribution(match: pd.DataFrame):
    """누적 분포 함수 + 백분위."""
    scores = sorted(match["match_subtotal"])
    cumulative = np.arange(1, len(scores) + 1) / len(scores) * 100

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(scores, cumulative, linewidth=2.5, color="#27AE60", label="누적분포")
    ax.fill_between(scores, 0, cumulative, alpha=0.3, color="#27AE60")

    # 주요 백분위 표시
    percentiles = [25, 50, 75]
    colors_pct = ["#3498DB", "#E74C3C", "#F39C12"]
    for pct, color in zip(percentiles, colors_pct):
        val = np.percentile(match["match_subtotal"], pct)
        ax.axvline(val, color=color, linestyle="--", alpha=0.7)
        ax.axhline(pct, color=color, linestyle="--", alpha=0.7)
        ax.plot(val, pct, "o", color=color, markersize=8)
        ax.text(val + 1.5, pct + 2, f"P{pct}={val:.0f}", fontsize=9, color=color)

    ax.set_xlabel("Match Score", fontsize=11)
    ax.set_ylabel("누적 백분위 (%)", fontsize=11)
    ax.set_title("Match Score 누적 분포함수 (CDF)", fontsize=12, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "04_cumulative_distribution.png", dpi=DPI)
    plt.close(fig)
    print("  04_cumulative_distribution.png")


# ══════════════════════════════════════════════════════════
# 5. 피쳐별 영향력 분석
# ══════════════════════════════════════════════════════════
def plot_feature_impact(match: pd.DataFrame):
    """각 피쳐가 전체 점수에 미치는 영향도."""
    features = ["price_reasonable", "interest_persistence", "discovery_stability"]
    labels = ["Price\n(0~25)", "Interest\n(0~20)", "Discovery\n(0~20)"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 1. 피쳐별 분산 (영향력)
    ax = axes[0]
    stds = [match[col].std() for col in features]

    bars = ax.bar(labels, stds, color=["#E74C3C", "#3498DB", "#F39C12"], alpha=0.7, edgecolor="black", linewidth=2)
    for bar, std in zip(bars, stds):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{std:.2f}', ha='center', va='bottom', fontsize=10, fontweight="bold")

    ax.set_ylabel("표준편차 (σ)", fontsize=11)
    ax.set_title("피쳐별 편차 (점수 변동성)", fontsize=12, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)

    # 2. 피쳐별 기여도 비율
    ax = axes[1]
    ranges = [25, 20, 20]  # 각 피쳐의 만점
    contributions = [stds[i] / ranges[i] * 100 for i in range(3)]

    colors = ["#E74C3C", "#3498DB", "#F39C12"]
    wedges, texts, autotexts = ax.pie(
        contributions, labels=labels, autopct="%1.1f%%",
        colors=colors, explode=[0.05] * 3
    )
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontweight("bold")
        autotext.set_fontsize(11)

    ax.set_title("피쳐별 기여도 비율\n(범위 대비 표준편차)", fontsize=12, fontweight="bold")

    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "05_feature_impact.png", dpi=DPI)
    plt.close(fig)
    print("  05_feature_impact.png")


# ══════════════════════════════════════════════════════════
# 6. 점수 조합 매트릭스 (Heatmap)
# ══════════════════════════════════════════════════════════
def plot_combination_heatmap(match: pd.DataFrame):
    """각 피처 조합별 유저 수."""
    features = ["price_reasonable", "interest_persistence", "discovery_stability"]

    # 모든 조합의 유저 수
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    for idx, (feat1, feat2) in enumerate([(0, 1), (0, 2), (1, 2)]):
        ax = axes[idx]

        pivot = pd.crosstab(
            match[features[feat1]],
            match[features[feat2]],
            margins=False
        )

        sns.heatmap(pivot, annot=True, fmt="d", cmap="YlOrRd",
                   ax=ax, cbar_kws={"label": "유저 수"}, linewidths=0.5)

        ax.set_xlabel(f"{features[feat2]}", fontsize=10)
        ax.set_ylabel(f"{features[feat1]}", fontsize=10)
        ax.set_title(f"{features[feat1]} × {features[feat2]}", fontsize=11, fontweight="bold")

    fig.tight_layout()
    fig.savefig(INSIGHT_DIR / "06_combination_heatmap.png", dpi=DPI)
    plt.close(fig)
    print("  06_combination_heatmap.png")


def main():
    print("시작: Match Score 분포 분석")
    match = load_data()
    print(f"데이터 로드: {len(match)}명\n")
    print("차트 생성:")

    plot_match_distribution(match)
    plot_feature_distributions(match)
    plot_feature_correlations(match)
    plot_cumulative_distribution(match)
    plot_feature_impact(match)
    plot_combination_heatmap(match)

    print(f"\n모든 시각화 저장 완료: {INSIGHT_DIR}")

    # 요약 통계
    print("\n" + "="*60)
    print("Match Score 분포 요약")
    print("="*60)
    print(match["match_subtotal"].describe())
    print(f"\n고유 점수 값: {sorted(match['match_subtotal'].unique())}")


if __name__ == "__main__":
    main()
