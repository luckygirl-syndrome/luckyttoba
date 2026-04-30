"""평가 결과 시각화.

Inputs:
  outputs/eval_results.parquet
  outputs/summary.json

Outputs (outputs/):
  field_accuracy.png       — 필드별 정확도 (그룹별 색상)
  platform_field_heatmap.png — 플랫폼 × 필드 정확도 히트맵
  error_stacked.png        — 필드별 에러 유형 stacked bar
  marketing_confusion.png  — 마케팅 3축 confusion matrix
"""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import confusion_matrix


BASE = Path(__file__).resolve().parent
DEFAULT_OUT = BASE / "outputs"

# 한글 폰트 (윈도우 기준 — macOS면 AppleGothic, Linux는 NanumGothic 자동 폴백)
import matplotlib.font_manager as fm

for cand in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"]:
    if any(cand in f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False

# 그룹 색상 (CLAUDE 톤)
FIELD_GROUPS = {
    "텍스트추출": ["product_name", "original_price", "has_discount", "discounted_price",
              "discount_rate", "review_count", "review_score", "wishlist_count"],
    "메타": ["shot_type", "visibility"],
    "스타일": ["style_keywords"],
    "마케팅": ["trend_hype", "bundle", "confidence"],
    "선택필드": ["delivery_info", "brand"],
}
GROUP_COLORS = {
    "텍스트추출": "#ED7D31",
    "메타": "#A5A5A5",
    "스타일": "#70AD47",
    "마케팅": "#FFC000",
    "선택필드": "#9DC3E6",
}


def field_to_group(field):
    for g, fs in FIELD_GROUPS.items():
        if field in fs:
            return g
    return "기타"


def plot_field_accuracy(summary: dict, out_path: Path):
    rows = []
    for field, m in summary["per_field"].items():
        acc = m.get("accuracy_excl_null_ok")
        if acc is None:
            continue
        rows.append({"field": field, "accuracy": acc, "group": field_to_group(field)})
    df = pd.DataFrame(rows).sort_values(["group", "accuracy"])

    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.bar(df["field"], df["accuracy"],
                  color=[GROUP_COLORS.get(g, "#888") for g in df["group"]])
    for b, acc in zip(bars, df["accuracy"]):
        ax.text(b.get_x() + b.get_width() / 2, acc + 0.01,
                f"{acc:.0%}", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("정확도 (null_ok 제외)")
    ax.set_title("필드별 추출 정확도")
    ax.axhline(0.8, ls="--", color="red", alpha=0.4, label="목표 80%")
    ax.legend(loc="lower right")
    plt.xticks(rotation=35, ha="right")

    # 그룹 범례
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in GROUP_COLORS.values()]
    ax.legend(handles + [plt.Line2D([0], [0], ls="--", color="red")],
              list(GROUP_COLORS.keys()) + ["목표 80%"],
              loc="upper left", bbox_to_anchor=(1, 1))
    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_platform_heatmap(df: pd.DataFrame, out_path: Path):
    pivot = (df.assign(is_correct=(df["status"] == "correct").astype(int),
                       evaluatable=(df["status"] != "null_ok").astype(int))
             .groupby(["platform", "field"])
             .agg(correct=("is_correct", "sum"), n=("evaluatable", "sum"))
             .reset_index())
    pivot["accuracy"] = pivot.apply(
        lambda r: r["correct"] / r["n"] if r["n"] else np.nan, axis=1
    )
    mat = pivot.pivot(index="platform", columns="field", values="accuracy")

    fig, ax = plt.subplots(figsize=(13, max(3, 0.5 * len(mat))))
    sns.heatmap(mat, annot=True, fmt=".0%", cmap="RdYlGn", vmin=0, vmax=1,
                cbar_kws={"label": "정확도"}, ax=ax)
    ax.set_title("플랫폼 × 필드 정확도 히트맵")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_error_stacked(df: pd.DataFrame, out_path: Path):
    counts = (df.groupby(["field", "status"]).size()
              .unstack(fill_value=0)
              .reindex(columns=["correct", "null_ok", "null_miss", "wrong"], fill_value=0))
    # 그룹 순서로 정렬
    field_order = []
    for g, fs in FIELD_GROUPS.items():
        for f in fs:
            if f in counts.index:
                field_order.append(f)
    counts = counts.reindex(field_order)
    pct = counts.div(counts.sum(axis=1), axis=0)

    fig, ax = plt.subplots(figsize=(11, 6))
    palette = {"correct": "#4CAF50", "null_ok": "#90CAF9",
               "null_miss": "#FFB74D", "wrong": "#E57373"}
    bottom = np.zeros(len(pct))
    for status in ["correct", "null_ok", "null_miss", "wrong"]:
        ax.bar(pct.index, pct[status], bottom=bottom,
               color=palette[status], label=status)
        bottom += pct[status].values
    ax.set_ylim(0, 1)
    ax.set_ylabel("비율")
    ax.set_title("필드별 에러 유형 분포")
    ax.legend(loc="lower right", bbox_to_anchor=(1.18, 0))
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_marketing_confusion(gts, preds, out_path: Path):
    axes = ["trend_hype", "bundle", "confidence"]
    fig, axarr = plt.subplots(1, 3, figsize=(13, 4))
    pred_lookup = {p_id: p for p_id, p in preds.items()}
    for ax, axis_name in zip(axarr, axes):
        y_t, y_p = [], []
        for gt in gts:
            if gt["image_id"] not in pred_lookup:
                continue
            gv, pv = gt.get(axis_name), pred_lookup[gt["image_id"]].get(axis_name)
            if gv is None or pv is None:
                continue
            y_t.append(int(gv))
            y_p.append(int(pv))
        if not y_t:
            ax.set_title(f"{axis_name}\n(데이터 없음)")
            ax.axis("off")
            continue
        cm = confusion_matrix(y_t, y_p, labels=[0, 1])
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                    xticklabels=["pred 0", "pred 1"],
                    yticklabels=["gt 0", "gt 1"], ax=ax, cbar=False)
        ax.set_title(f"{axis_name} (n={len(y_t)})")
    plt.suptitle("마케팅 트리거 3축 Confusion Matrix")
    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def load_jsonl(p: Path):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def load_predictions(pred_dir: Path):
    by_id = {}
    for p in sorted(pred_dir.glob("*.jsonl")):
        for row in load_jsonl(p):
            img_id = row["image_id"]
            run = row.get("run", 1)
            existing = by_id.get(img_id)
            if existing is None or run > existing[0]:
                by_id[img_id] = (run, row.get("result") or {})
    return {k: v[1] for k, v in by_id.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--gt", default=str(BASE / "gt" / "gt_labels.jsonl"))
    ap.add_argument("--pred-dir",
                    default=str(BASE.parent / "exp00_vision_extraction" / "results" / "gemini_v2"))
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(out_dir / "eval_results.parquet")
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))

    plot_field_accuracy(summary, out_dir / "field_accuracy.png")
    plot_error_stacked(df, out_dir / "error_stacked.png")
    plot_platform_heatmap(df, out_dir / "platform_field_heatmap.png")

    gts = load_jsonl(Path(args.gt))
    preds = load_predictions(Path(args.pred_dir))
    plot_marketing_confusion(gts, preds, out_dir / "marketing_confusion.png")

    print(f"[OK] 시각화 4종 저장 → {out_dir}")


if __name__ == "__main__":
    main()
