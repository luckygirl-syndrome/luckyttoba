# 시험 0 분석 — 프롬프트 × 결과 × 인사이트

각 프롬프트 버전마다 한 문서. **프롬프트 의도 → 추출 숫자 → 인사이트 → 다음 버전 권장 변경**의 4단 구조.

## 파일

| 문서 | 내용 |
|------|------|
| [v1.md](v1.md) | 초기 프롬프트 (37장 추출, GT 평가 없음) |
| [v2.md](v2.md) | 마케팅 트리거 3축 + visibility 판정 기준 추가 (100장, GT 99 매칭) |
| [v3_plan.md](v3_plan.md) | v2 인사이트로부터 도출한 v3 프롬프트 변경 권장사항 (미실행) |
| [COMPARISON.md](COMPARISON.md) | v1 → v2 변경점 + 채움률 비교 |

## 평가 산출물 위치

- 평가 longform: `experiments/exp01_vision_accuracy/outputs/eval_results.parquet`
- 요약 JSON: `experiments/exp01_vision_accuracy/outputs/summary.json`
- 시각화 4종 PNG: `experiments/exp01_vision_accuracy/outputs/{field_accuracy, error_stacked, platform_field_heatmap, marketing_confusion}.png`
- 점수 엑셀: `experiments/exp01_vision_accuracy/outputs/score_summary.xlsx`

## 한 줄 결론 (v2)

99장 매칭에서 **8개 핵심 텍스트 필드 ≥90%** (가격/할인/리뷰/상품명/shot_type/brand). 단 **마케팅 트리거 P=0.14~0.23** (recall은 1.0 — 과탐지), **wishlist_count 35%** (브랜드 팔로워와 혼동 27건). 다음 버전(v3) 우선과제: 팔로워-찜 분리, 마케팅 트리거 기준 강화, GT 엑셀 양식과 키 1:1 일치.
