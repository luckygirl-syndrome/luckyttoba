# v1 → v2 비교

## 채움률 (값이 있는 비율)

| 필드 | v1 (37장) | v2 (102 run) | Δ | 비고 |
|------|----------:|-------------:|---:|------|
| product_name | 100% | 100% | 0 | |
| original_price | 100% | 97% | -3 | v2 100장 데이터셋이 더 다양 (가격 안 보이는 케이스 추가) |
| is_discounted | 92% | 93% | +1 | |
| discounted_price | 92% | 93% | +1 | |
| discount_rate | 92% | 92% | 0 | |
| review_count | 92% | 87% | -5 | 100장 다양성 영향 |
| review_score | 81% | 75% | -6 | 동일 |
| category | 100% | 100% | 0 | |
| color | 100% | 97% | -3 | |
| fit | 89% | 79% | -10 | 시각 추론 부담 |
| style_keywords | 100% | 100% | 0 | |
| shot_type | 100% | 100% | 0 | |
| visibility | 100% | 100% | 0 | |
| wishlist_count | **51%** | **58%** | +7 | v2가 약간 개선 |
| delivery_info | 65% | 66% | +1 | |
| brand_name | 97% | 98% | +1 | |
| **(신규) trend_hype** | — | 100% | — | |
| **(신규) bundle** | — | 100% | — | |
| **(신규) confidence** | — | 100% | — | |
| **(신규) marketing_phrases** | — | 89% | — | 11%는 빈 list |

## 핵심 변경

| 항목 | v1 | v2 |
|------|----|----|
| 필드 수 | 17 | 23 |
| visibility 정의 | 한 줄 | 면적·디자인 가림 기준 + 엣지케이스 |
| shot_type 라벨 | 모델착용샷, 흰배경단독샷 | 모델 착용샷, 흰 배경 단독샷 (띄어쓰기 추가, 후 v3에서 GT에 맞춰 다시 통일 예정) |
| 마케팅 트리거 | 없음 | trend_hype/bundle/confidence × (0/1 + score) + marketing_phrases |
| 평가 (GT 대비) | 미실시 | 99장 매칭 평가 완료 |

## v2 평가 결과 핵심

8개 필드 ≥ 90% (가격/할인/리뷰 수치 + 상품명 + brand + shot_type), 4개 필드 < 50% (마케팅 트리거 P, wishlist_count, delivery_info). 자세한 인사이트는 [v2.md §3](v2.md).

## v2 → v3 핵심

GT 엑셀 양식과 추출 결과 키를 **1:1 일치**시키면 evaluate.py의 정규화 매핑 코드 자체가 사라짐. 이번엔 매핑으로 우회했지만 다음 추출부터는 양식 일치시켜야 함. [v3_plan.md](v3_plan.md) 참고.
