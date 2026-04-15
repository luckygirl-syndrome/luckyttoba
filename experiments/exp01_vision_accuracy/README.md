# 시험 1: Vision 추출 정확도 + 마케팅 트리거

> 기존 시험 2(마케팅 트리거 분류)를 흡수 (2026-04-15)

## 목적

Vision LLM이 쇼핑 스크린샷에서 뽑은 숫자가 Impulse/Match Score의 입력값.
틀리면 점수 전체가 틀림. 필드별 정확도를 정량 측정한다.
마케팅 트리거(trend_hype, bundle, confidence)도 시험 0에서 동시 추출하므로 여기서 함께 평가.

## 추출 대상 필드

product_name, original_price, discounted_price, discount_rate,
review_count, review_score, category, color, fit, style_keywords,
shot_type, visibility, wishlist_count, delivery_info, brand_name,
**trend_hype, bundle, confidence** (마케팅 트리거 3축, 0/1 이진)

## GT 데이터셋

- 플랫폼별(무신사/에이블리/지그재그) 균등, **총 100장**
- 케이스 다양성: 할인 유/무, 리뷰 다/없, 가시성 불량, 브랜드좋아요+상품좋아요 동시 노출
- GT 라벨링 담당:
  - 숫자 필드 + 메타: 경현+팜팜이 (50장씩)
  - 스타일 필드: 낭연+정현 (50장씩)
  - 마케팅 트리거: 낭연+정현 (50장씩)

## 측정 지표

### 텍스트 추출 필드 (product_name, price, review_count, rating 등)
- Exact Match 또는 ±허용 오차 내 정확도
- price: "사용자 맞춤 할인가 vs 일반 할인가" 혼동 집중 체크

### 추론 필드 (category, color, fit, style_keywords, shot_type, visibility)
- GT 일치율
- style_keywords: multi-label F1

### 마케팅 트리거 (trend_hype, bundle, confidence)
- 축별 Precision / Recall / F1
- **Recall 우선** — 시그널을 못 잡으면 Impulse Score 과소평가
- Confusion matrix

### 에러 유형 분류
- 미추출(null) vs 잘못된 값 구분 (잘못된 값이 더 위험)

## 특히 주의할 케이스

- 좋아요 수 vs 브랜드 팔로워 수 혼동
- 쿠폰 적용가 vs 기본 할인가 혼동
- 리뷰 점수 100점 만점 플랫폼 → 5점 변환 정확도
- 여러 색상 옵션이 있는 상품에서 어떤 색상을 뽑는가
