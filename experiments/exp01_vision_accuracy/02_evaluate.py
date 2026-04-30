"""GT vs Vision 추출 결과 평가.

Inputs:
  gt/gt_labels.jsonl
  ../exp00_vision_extraction/results/gemini_v2/*.jsonl

Outputs:
  outputs/eval_results.parquet  (이미지별·필드별 결과 longform)
  outputs/summary.json          (필드별 정확도, 마케팅 P/R/F1, 플래그 카운트 등)

에러 분류:
  correct   : 둘 다 값 있고 비교 통과
  null_ok   : GT=null, 추출=null
  null_miss : GT는 값 있는데 추출=null (놓침)
  wrong     : 비교 실패

특수 플래그:
  follower_confusion  : wishlist_count 차이가 5배 이상
  coupon_confusion    : 추출 discounted_price < GT × 0.85

Usage:
  python 02_evaluate.py
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from sklearn.metrics import precision_recall_fscore_support


BASE = Path(__file__).resolve().parent
DEFAULT_GT = BASE / "gt" / "gt_labels.jsonl"
DEFAULT_PRED_DIR = BASE.parent / "exp00_vision_extraction" / "results" / "gemini_v2"
DEFAULT_OUT = BASE / "outputs"

# 추출 → GT 키 매핑 (이름이 다른 경우)
PRED_TO_GT_KEY = {
    "is_discounted": "has_discount",
    "brand_name": "brand",
}

# 비교 필드별 결과 행을 만든다.
# (없으면 GT에 추가 안된 — 별도 출력)
EXTRACTED_ONLY_FIELDS = ["category", "color", "fit"]
MARKETING_AXES = ["trend_hype", "bundle", "confidence"]


def load_jsonl(path: Path):
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_predictions(pred_dir: Path):
    """{image_id: result_dict} — 같은 image_id에 여러 run이 있으면 가장 큰 run을 사용."""
    by_id = {}
    for p in sorted(pred_dir.glob("*.jsonl")):
        rows = load_jsonl(p)
        for row in rows:
            img_id = row["image_id"]
            run = row.get("run", 1)
            existing = by_id.get(img_id)
            if existing is None or run > existing[0]:
                by_id[img_id] = (run, row.get("result") or {})
    return {k: v[1] for k, v in by_id.items()}


# ---------------------------------------------------------------------------
# 비교 함수: returns (status, detail) where status in {correct, null_ok, null_miss, wrong}
# ---------------------------------------------------------------------------

def _is_null(v):
    return v is None or (isinstance(v, str) and not v.strip())


def cmp_exact(gt, pred):
    if _is_null(gt) and _is_null(pred):
        return "null_ok", None
    if _is_null(pred):
        return "null_miss", None
    if _is_null(gt):
        return "wrong", "gt_null_pred_value"
    return ("correct" if gt == pred else "wrong"), None


def cmp_int_tol(gt, pred, abs_tol):
    if _is_null(gt) and _is_null(pred):
        return "null_ok", None
    if _is_null(pred):
        return "null_miss", None
    if _is_null(gt):
        return "wrong", "gt_null_pred_value"
    try:
        diff = abs(int(gt) - int(pred))
    except (TypeError, ValueError):
        return "wrong", f"non_numeric pred={pred}"
    return ("correct" if diff <= abs_tol else "wrong"), f"diff={diff}"


def cmp_float_tol(gt, pred, abs_tol):
    if _is_null(gt) and _is_null(pred):
        return "null_ok", None
    if _is_null(pred):
        return "null_miss", None
    if _is_null(gt):
        return "wrong", "gt_null_pred_value"
    try:
        diff = abs(float(gt) - float(pred))
    except (TypeError, ValueError):
        return "wrong", f"non_numeric pred={pred}"
    return ("correct" if diff <= abs_tol else "wrong"), f"diff={diff:.3f}"


def cmp_relative(gt, pred, rel_tol):
    """abs(diff)/gt <= rel_tol — gt=0이면 pred도 0이어야 correct."""
    if _is_null(gt) and _is_null(pred):
        return "null_ok", None
    if _is_null(pred):
        return "null_miss", None
    if _is_null(gt):
        return "wrong", "gt_null_pred_value"
    try:
        gt_v, pred_v = float(gt), float(pred)
    except (TypeError, ValueError):
        return "wrong", f"non_numeric pred={pred}"
    if gt_v == 0:
        return ("correct" if pred_v == 0 else "wrong"), f"gt=0 pred={pred_v}"
    rel = abs(gt_v - pred_v) / abs(gt_v)
    return ("correct" if rel <= rel_tol else "wrong"), f"rel={rel:.3f}"


_TOKEN_RE = re.compile(r"[^0-9a-zA-Z가-힣]+")


def _tokenize_name(s: str):
    s = re.sub(r"\[[^\]]*\]", " ", s)  # [태그] 제거
    s = re.sub(r"\([^)]*\)", " ", s)
    return [t for t in _TOKEN_RE.split(s) if t]


def cmp_product_name(gt, pred):
    if _is_null(gt) and _is_null(pred):
        return "null_ok", None
    if _is_null(pred):
        return "null_miss", None
    if _is_null(gt):
        return "wrong", "gt_null_pred_value"
    gt_tok = set(_tokenize_name(str(gt)))
    pred_tok = set(_tokenize_name(str(pred)))
    if not gt_tok:
        return ("correct" if not pred_tok else "wrong"), None
    overlap = len(gt_tok & pred_tok) / len(gt_tok)
    return ("correct" if overlap >= 0.7 else "wrong"), f"overlap={overlap:.2f}"


def cmp_set(gt_list, pred_list):
    """style_keywords F1 (sample-level F1; aggregate later)."""
    gt = set(gt_list or [])
    pred = set(pred_list or [])
    if not gt and not pred:
        return "null_ok", {"f1": 1.0, "p": 1.0, "r": 1.0}
    if gt and not pred:
        return "null_miss", {"f1": 0.0, "p": 0.0, "r": 0.0}
    tp = len(gt & pred)
    p = tp / len(pred) if pred else 0.0
    r = tp / len(gt) if gt else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    status = "correct" if f1 >= 0.5 else ("wrong" if gt else "null_ok")
    return status, {"f1": f1, "p": p, "r": r}


def cmp_string_contains(gt, pred):
    """delivery_info, brand: 존재여부 일치 + 부분 문자열 일치."""
    if _is_null(gt) and _is_null(pred):
        return "null_ok", None
    if _is_null(pred):
        return "null_miss", None
    if _is_null(gt):
        return "wrong", "gt_null_pred_value"
    g, p = str(gt).strip(), str(pred).strip()
    return ("correct" if (g in p or p in g) else "wrong"), None


# ---------------------------------------------------------------------------
# 필드 비교 정의
# ---------------------------------------------------------------------------

def compare_record(gt: dict, pred: dict):
    """한 이미지에 대한 (image_id, field, status, detail) 행 리스트."""
    rows = []
    img_id = gt["image_id"]

    def _get_pred(key):
        # 추출 결과는 다른 이름일 수 있다 (is_discounted/has_discount 등)
        if key in pred:
            return pred[key]
        for pred_key, gt_key in PRED_TO_GT_KEY.items():
            if gt_key == key and pred_key in pred:
                v = pred[pred_key]
                # is_discounted bool → 0/1
                if pred_key == "is_discounted":
                    if v is True:
                        return 1
                    if v is False:
                        return 0
                return v
        return None

    def add(field, status, detail=None, **extra):
        rows.append({
            "image_id": img_id,
            "platform": gt.get("platform"),
            "field": field,
            "status": status,
            "detail": detail,
            **extra,
        })

    # 1) product_name
    add("product_name", *cmp_product_name(gt.get("product_name"), _get_pred("product_name")))

    # 2) 가격류
    add("original_price", *cmp_int_tol(gt.get("original_price"), _get_pred("original_price"), 500))
    add("discounted_price", *cmp_int_tol(gt.get("discounted_price"), _get_pred("discounted_price"), 500))

    # 3) has_discount (exact 0/1)
    add("has_discount", *cmp_exact(gt.get("has_discount"), _get_pred("has_discount")))

    # 4) discount_rate (abs ≤ 2)
    add("discount_rate", *cmp_int_tol(gt.get("discount_rate"), _get_pred("discount_rate"), 2))

    # 5) review_count (rel ≤ 0.05)
    add("review_count", *cmp_relative(gt.get("review_count"), _get_pred("review_count"), 0.05))

    # 6) review_score (abs ≤ 0.1)
    add("review_score", *cmp_float_tol(gt.get("review_score"), _get_pred("review_score"), 0.1))

    # 7) wishlist_count (rel ≤ 0.10)
    add("wishlist_count", *cmp_relative(gt.get("wishlist_count"), _get_pred("wishlist_count"), 0.10))

    # 8) shot_type, visibility (exact)
    add("shot_type", *cmp_exact(gt.get("shot_type"), _get_pred("shot_type")))
    add("visibility", *cmp_exact(gt.get("visibility"), _get_pred("visibility")))

    # 9) style_keywords (multi-label F1)
    sk_status, sk_detail = cmp_set(gt.get("style_keywords"), _get_pred("style_keywords"))
    rows.append({
        "image_id": img_id, "platform": gt.get("platform"),
        "field": "style_keywords", "status": sk_status,
        "detail": json.dumps(sk_detail, ensure_ascii=False) if sk_detail else None,
        **{f"sk_{k}": v for k, v in (sk_detail or {}).items()},
    })

    # 10) marketing axes (per-axis exact 0/1)
    for axis in MARKETING_AXES:
        add(axis, *cmp_exact(gt.get(axis), _get_pred(axis)))

    # 11) delivery_info, brand (포함)
    add("delivery_info", *cmp_string_contains(gt.get("delivery_info"), _get_pred("delivery_info")))
    add("brand", *cmp_string_contains(gt.get("brand"), _get_pred("brand")))

    # 12) 특수 플래그
    flags = []
    gt_w = gt.get("wishlist_count")
    pr_w = _get_pred("wishlist_count")
    if gt_w not in (None, 0) and pr_w not in (None, 0):
        try:
            ratio = max(float(pr_w) / float(gt_w), float(gt_w) / float(pr_w))
            if ratio >= 5.0:
                flags.append({"type": "follower_confusion", "gt": gt_w, "pred": pr_w, "ratio": ratio})
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    gt_dp = gt.get("discounted_price")
    pr_dp = _get_pred("discounted_price")
    if gt_dp and pr_dp:
        try:
            if float(pr_dp) < float(gt_dp) * 0.85:
                flags.append({"type": "coupon_confusion", "gt": gt_dp, "pred": pr_dp})
        except (TypeError, ValueError):
            pass

    return rows, flags


def aggregate_summary(df: pd.DataFrame, gts, preds):
    """필드별 정확도 + 마케팅 P/R/F1."""
    summary = {"per_field": {}, "marketing_metrics": {}, "n_images": int(df["image_id"].nunique())}

    # 필드별 status 카운트
    for field, sub in df.groupby("field"):
        cnt = sub["status"].value_counts().to_dict()
        total = len(sub)
        evaluatable = total - cnt.get("null_ok", 0)  # null_ok는 분모에서 빼는 게 정직 (양쪽 다 null이면 평가 의미 없음)
        correct = cnt.get("correct", 0)
        accuracy = correct / evaluatable if evaluatable else None
        summary["per_field"][field] = {
            "total": total,
            "correct": correct,
            "wrong": cnt.get("wrong", 0),
            "null_miss": cnt.get("null_miss", 0),
            "null_ok": cnt.get("null_ok", 0),
            "accuracy_excl_null_ok": accuracy,
        }

    # style_keywords sample-mean F1
    sk = df[df["field"] == "style_keywords"]
    if not sk.empty and "sk_f1" in sk.columns:
        evaluatable = sk[sk["status"] != "null_ok"]
        if not evaluatable.empty:
            summary["per_field"]["style_keywords"]["mean_f1"] = float(evaluatable["sk_f1"].mean())
            summary["per_field"]["style_keywords"]["mean_p"] = float(evaluatable["sk_p"].mean())
            summary["per_field"]["style_keywords"]["mean_r"] = float(evaluatable["sk_r"].mean())

    # 마케팅 트리거 sklearn P/R/F1 (binary)
    pred_lookup = {p_id: p for p_id, p in preds.items()}
    for axis in MARKETING_AXES:
        y_true, y_pred = [], []
        for gt in gts:
            img_id = gt["image_id"]
            if img_id not in pred_lookup:
                continue
            gv = gt.get(axis)
            pv = pred_lookup[img_id].get(axis)
            if gv is None or pv is None:
                continue
            y_true.append(int(gv))
            y_pred.append(int(pv))
        if y_true:
            p, r, f1, _ = precision_recall_fscore_support(
                y_true, y_pred, average="binary", zero_division=0, pos_label=1
            )
            summary["marketing_metrics"][axis] = {
                "n": len(y_true),
                "precision": float(p),
                "recall": float(r),
                "f1": float(f1),
            }

    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", default=str(DEFAULT_GT))
    ap.add_argument("--pred-dir", default=str(DEFAULT_PRED_DIR))
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    gt_path = Path(args.gt)
    pred_dir = Path(args.pred_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not gt_path.exists():
        sys.exit(f"GT JSONL이 없습니다: {gt_path}\n먼저 02_load_gt.py 를 실행하세요.")
    if not pred_dir.exists():
        sys.exit(f"추출 결과 폴더가 없습니다: {pred_dir}")

    gts = load_jsonl(gt_path)
    preds = load_predictions(pred_dir)

    # 매칭
    matched = [g for g in gts if g["image_id"] in preds]
    missing = [g["image_id"] for g in gts if g["image_id"] not in preds]
    print(f"GT: {len(gts)}개, 추출: {len(preds)}개, 매칭: {len(matched)}개")
    if missing:
        print(f"  매칭 안된 GT 이미지({len(missing)}개): {missing[:10]}{'...' if len(missing)>10 else ''}")

    # 비교
    all_rows = []
    all_flags = []
    extracted_only_records = []
    for gt in matched:
        pred = preds[gt["image_id"]]
        rows, flags = compare_record(gt, pred)
        all_rows.extend(rows)
        for fl in flags:
            fl["image_id"] = gt["image_id"]
            all_flags.append(fl)
        # 추출 only 필드 (category/color/fit)
        extracted_only_records.append({
            "image_id": gt["image_id"],
            "platform": gt.get("platform"),
            **{k: pred.get(k) for k in EXTRACTED_ONLY_FIELDS},
        })

    df = pd.DataFrame(all_rows)
    parquet_path = out_dir / "eval_results.parquet"
    df.to_parquet(parquet_path, index=False)
    print(f"[OK] {parquet_path}")

    extracted_only_df = pd.DataFrame(extracted_only_records)
    extracted_only_path = out_dir / "extracted_only_fields.parquet"
    extracted_only_df.to_parquet(extracted_only_path, index=False)
    print(f"[OK] {extracted_only_path}")

    # 요약
    summary = aggregate_summary(df, matched, preds)
    summary["flags"] = {
        "follower_confusion": [f for f in all_flags if f["type"] == "follower_confusion"],
        "coupon_confusion": [f for f in all_flags if f["type"] == "coupon_confusion"],
        "missing_pred_image_ids": missing,
    }
    summary_path = out_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[OK] {summary_path}")

    # 콘솔 요약
    print("\n=== 필드별 정확도 (null_ok 제외) ===")
    for field, m in sorted(summary["per_field"].items(), key=lambda kv: (kv[1].get("accuracy_excl_null_ok") or -1)):
        acc = m["accuracy_excl_null_ok"]
        acc_s = f"{acc:.1%}" if acc is not None else "N/A"
        print(f"  {field:22s} {acc_s:>6s}  correct={m['correct']:>3d}  wrong={m['wrong']:>3d}  null_miss={m['null_miss']:>3d}  null_ok={m['null_ok']:>3d}")
    if summary["marketing_metrics"]:
        print("\n=== 마케팅 트리거 P/R/F1 ===")
        for axis, m in summary["marketing_metrics"].items():
            print(f"  {axis:14s} P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f} (n={m['n']})")
    if any(summary["flags"].values()):
        print("\n=== 플래그 ===")
        for k, vs in summary["flags"].items():
            if isinstance(vs, list) and vs and k != "missing_pred_image_ids":
                print(f"  {k}: {len(vs)}건")


if __name__ == "__main__":
    main()
