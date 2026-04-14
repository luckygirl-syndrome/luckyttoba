# 시험 0~5 구현 계획 (v2)

> 작성일: 2026-04-14
> 확정 사항: LLM = Gemini 3.1 Flash-Lite, RoBERTa 제외, 옷 묘사는 실제 추출 데이터 사용

---

## 확정된 결정사항

| 항목 | 결정 |
|------|------|
| LLM 모델 (전체) | Gemini 3.1 Flash-Lite |
| 시험 2 비교 대상 | LLM만 (RoBERTa 제외) |
| 시험 3 옷 묘사 데이터 | 시험 0에서 실제 Vision 추출한 결과 사용 |
| 시험 0 | 유저가 새 프롬프트/구조로 직접 재실험 |
| 에이블리 가격 | 추가 크롤링 예정 (exp04 전까지) |
| 지그재그 좋아요 | 없음 확정 (like_score=0 고정) |
| 찜 = 좋아요 | 동일 필드로 통합 |

---

## 🚨 발견된 불일치: style_keywords 어휘가 3곳에서 전부 다름

시험 0, 3, 4에 영향을 주는 심각한 이슈.

| 출처 | 어휘 |
|------|------|
| **exp00 Gemini 프롬프트** | 심플베이직, 락시크, 힙, 페미닌, 러블리, 모리걸, 빈티지, 스트릿, 캐주얼, 섹시글램 |
| **docs/스크린샷 추출 정보** | 캐주얼, 스트릿, 페미닌, 미니멀, 빈티지, 스포티, 포멀, Y2K, 시티보이 |
| **docs/기초 질문 (유저 태그)** | 깔끔하고 단정한, 편하고 캐주얼한, 여성스럽고 부드러운, 힙하고 개성 있는, 세련되고 포멀한, 빈티지·레트로 |

**왜 문제인가:**
style_similarity는 "유저 스타일 태그"와 "옷 추출 키워드"를 LLM이 비교해서 점수를 매김.
어휘가 다르면 LLM이 매핑을 자의적으로 해야 하고, 그러면 점수 일관성이 떨어짐.

**제안:** 시험 0에서 프롬프트를 새로 짤 때 이 어휘를 통일하거나,
style_similarity 프롬프트에서 어휘 매핑 가이드를 명시. → **유저와 합의 필요**

---

## 0. 공통 인프라 (모든 시험 전에 먼저 구축)

### 0-1. `shared/data_loader.py` — 크롤링 데이터 정규화

3개 플랫폼의 필드명, 타입, 포맷을 통일하는 로더.

**플랫폼별 파싱 로직:**

```
에이블리:
  product_name  → 그대로
  discount_rate → "10" → int 10
  review_count  → 1934 → 그대로 (이미 int)
  review_score  → 4.0 → rating (이미 float)
  product_likes → "97000" → int 97000
  platform      → 2 → "에이블리"
  original_price → None (크롤링 후 추가)
  sale_price     → None (크롤링 후 추가)
  category       → None

무신사:
  product_name   → 그대로
  discount_rate  → "10%" → int 10
  review_count   → "후기 4,826개" → int 4826
  rating         → "4.8" → float 4.8
  product_likes  → "9.2만" → int 92000  (한글 숫자 파서)
  platform       → URL로 판별 → "무신사"
  original_price → "59,900원" → int 59900
  sale_price     → "53,910원" → int 53910
  category       → top_category_parsed

지그재그:
  name           → product_name
  discount_rate  → "13%" → int 13
  review_count   → "7,588" → int 7588
  review_rating  → 4.8 → rating (이미 float)
  like_count     → None (기능 없음)
  platform       → URL로 판별 → "지그재그"
  original_price → "23,000" → int 23000
  sale_price     → "20,070" → int 20070
  category       → parsed_category
```

**출력 스키마:**
```python
@dataclass
class Product:
    product_name: str
    platform: str           # "에이블리" | "무신사" | "지그재그"
    discount_rate: int | None
    review_count: int
    rating: float | None
    like_count: int | None
    original_price: int | None
    sale_price: int | None
    category: str | None
    source_url: str | None
```

**한글 숫자 파서** (무신사 전용):
```
"9.2만" → 92000
"25만"  → 250000
"1.4만" → 14000
"262"   → 262
"9.2천" → 9200
```

### 0-2. `shared/marketing_detector.py` — 키워드 기반 트리거 검출

시험 5에서 48,000개 상품의 marketing score 계산에 필요.
시험 2에서 LLM 분류기와 비교할 베이스라인으로도 사용.

```python
TREND_KEYWORDS = ["인기", "랭킹", "베스트", "HOT", "hot", "트렌드",
                  "유행", "대세", "히트", "핫딜", "MD추천", "위클리"]

BUNDLE_KEYWORDS = ["1+1", "세트", "묶음", "증정", "사은품", "추가할인",
                   "2개", "3개", "+1", "덤", "같이구매"]

CONFIDENCE_KEYWORDS = ["후기", "리얼", "검증", "입증", "보장", "추천",
                       "누적판매", "재구매", "만족도", "품질보증"]
```

함수: `detect_triggers(product_name) → (trend_hype: 0|1, bundle: 0|1, confidence: 0|1)`

### 0-3. `shared/prompt_builder.py` — system_prompt + context_sentences

`docs/챗봇에게 전달할 system_prompt & context_sentences.md`에서 코드 추출.

포함:
- `build_system_prompt(user_type, age, style_tags, ...)`
- `build_context_sentences(product_name, original_price, ..., style_context, ...)`
- 헬퍼 11개: `get_review_context()`, `get_discount_context()`, `get_social_proof_context()` 등

시험 4에서 필수. 나중에 앱에서도 재사용.

---

## 1. 시험 0: Vision 추출 재실험 (`exp00_vision_extraction`)

### 변경 배경
기존은 팀원(정현)이 실험한 것. 유저가 새 프롬프트·구조로 직접 재실험.

### 구조 변경

```
exp00_vision_extraction/
├── run_extraction.py           # 기존 스크립트 (수정)
├── prompts/
│   ├── extraction_prompt_gemini.txt      # 기존 (정현 v1)
│   ├── extraction_prompt_gpt.txt         # 기존 (정현 v1)
│   ├── extraction_v2_gemini.txt          # 유저 v2 (새로 작성)
│   └── extraction_v2_gpt.txt             # (필요 시)
├── manifests/
│   └── dataset.jsonl
├── results/
│   ├── gemini_v1/              # 기존 결과
│   └── gemini_v2/              # 새 프롬프트 결과
└── README.md
```

### 코드 수정 사항

**run_extraction.py 변경:**
- `--prompt-version` 인자 추가 (v1/v2 선택)
- 결과 저장 경로에 프롬프트 버전 포함
- 모델은 Gemini 3.1 Flash-Lite 단일 (GPT-4o는 선택)

### ⚠️ 시험 0에서 해결해야 할 것들

1. **style_keywords 어휘 통일** (위 🚨 참조)
2. **좋아요 vs 브랜드 팔로워 혼동 방지** — 프롬프트에 명시적 구분 지침 추가
3. **쿠폰가 vs 기본 할인가 구분** — "첫 구매 20% 쿠폰"은 할인가가 아님을 명시
4. **100점 만점 → 5점 변환** — 기존 프롬프트에 있긴 한데, 실제로 지키는지 확인

### 산출물 → 이후 시험에 연결
- 추출된 옷 묘사 (category, color, fit, style_keywords, visibility, shot_type)
  → **시험 3**에서 style_similarity 입력으로 사용
- 추출된 숫자 (review_count, discount_rate 등)
  → **시험 1**에서 GT 대비 정확도 평가

---

## 2. 시험 1: Vision 추출 정확도 (`exp01_vision_accuracy`)

### 의존성
- 시험 0 완료 (추출 결과가 있어야 비교 가능)
- GT 데이터셋 (수동 라벨링)

### 파일 구조

```
exp01_vision_accuracy/
├── 01_create_gt_template.py    # GT 라벨링 템플릿 생성
├── 02_evaluate.py              # GT vs 추출 결과 비교, 지표 계산
├── 03_visualize.py             # 결과 시각화
├── gt/
│   └── gt_labels.jsonl         # 수동 라벨링 (팀원 분담)
├── configs/
│   └── eval_config.yaml        # 허용 오차 정의
└── outputs/
```

### 코드 설계

**01_create_gt_template.py**
- `manifests/dataset.jsonl`의 이미지 목록을 읽어서
- 빈 GT 템플릿 JSONL 생성 (모든 필드가 null인 껍데기)
- 팀원이 이미지를 직접 보면서 값 채움
- 이미지 경로 + 브라우저에서 원본 URL도 같이 표시 (크롤링 데이터와 대조 가능하게)

**02_evaluate.py**
- 평가 로직:

| 필드 그룹 | 필드 | 지표 | 허용 오차 |
|-----------|------|------|----------|
| 텍스트 추출 | product_name | 포함 여부 (핵심 단어) | - |
| 텍스트 추출 | original_price, discounted_price | Exact 또는 ±500원 | 500 |
| 텍스트 추출 | discount_rate | Exact 또는 ±2% | 2 |
| 텍스트 추출 | review_count | ±5% | 비율 |
| 텍스트 추출 | review_score | ±0.1 | 0.1 |
| 텍스트 추출 | wishlist_count | ±10% | 비율 |
| 추론 | category, color, fit | Exact Match | - |
| 추론 | style_keywords | Multi-label F1 | - |
| 추론 | shot_type, visibility | Exact Match | - |

- 에러 분류: `correct`, `null_miss` (있는데 null), `wrong` (잘못된 값), `null_ok` (정답도 null)
- 특수 케이스 탐지기: 좋아요↔팔로워 혼동, 쿠폰가↔할인가 혼동

**03_visualize.py**
- 필드별 정확도 막대그래프 (텍스트 추출 vs 추론 그룹 분리)
- 플랫폼별 정확도 히트맵
- 에러 유형 분포 (null_miss vs wrong)
- 프롬프트 v1 vs v2 비교 (시험 0에서 여러 버전 실험 시)

### ⚠️ 우려사항
- GT 라벨링은 사람 작업 → 템플릿만 코드로, 나머지는 팀 분담
- 현재 images/ 에 약 35개 상품. 90장 목표면 55장 추가 필요할 수 있음

---

## 3. 시험 2: 마케팅 트리거 분류 (`exp02_marketing_trigger`)

### 의존성
- `shared/data_loader.py` (상품명 로드)
- `shared/marketing_detector.py` (키워드 베이스라인)
- Gemini API 접근

### 파일 구조

```
exp02_marketing_trigger/
├── 01_create_gt_template.py    # GT 라벨링 템플릿 (200개 상품명)
├── 02_classify_keyword.py      # 키워드 매칭 (베이스라인)
├── 03_classify_llm.py          # Gemini Flash-Lite 분류
├── 04_evaluate.py              # GT 대비 평가
├── 05_visualize.py             # 키워드 vs LLM 비교 차트
├── prompts/
│   └── trigger_classify.txt    # LLM 분류 프롬프트
├── gt/
│   └── gt_labels.jsonl
├── configs/
│   └── edge_cases.yaml         # 경계 케이스 합의 기준
└── outputs/
```

### 코드 설계

**01_create_gt_template.py**
- 3개 플랫폼 크롤링 데이터에서 상품명 200개 **전략적 샘플링**:
  - 키워드 매칭 양성(마케팅 문구 있는 것) 60개
  - 키워드 매칭 음성(없는 것) 60개
  - 경계선(키워드 부분 매칭) 80개
- 출력: `gt/gt_template.jsonl` (product_name + keyword_hint + 빈 라벨)

**02_classify_keyword.py**
- `shared/marketing_detector.py` 사용
- 200개 상품명 → `(trend_hype, bundle, confidence)` 예측
- 매칭된 키워드도 함께 기록 (디버깅용)

**03_classify_llm.py**
- Gemini Flash-Lite에 상품명을 보내서 분류

프롬프트 핵심:
```
상품명에서 마케팅 시그널 3종을 판별하라.

[정의]
- trend_hype: 유행/인기/랭킹을 강조하여 "다들 사니까 나도" 심리를 자극하는 문구
- bundle: 묶음/증정/추가할인 등 "지금 사면 더 이득" 심리를 자극하는 문구
- confidence: 품질 보증/후기 검증/추천 등 "안심해도 돼" 심리를 자극하는 문구

[주의]
- 상품 자체의 속성 설명은 시그널이 아님 ("코튼 100%"는 confidence가 아님)
- 이모지나 감탄사만으로는 시그널로 판단하지 않음
- 각 시그널은 독립적 — 하나의 문구가 여러 시그널에 해당할 수 있음

반드시 JSON으로 응답:
{"trend_hype": 0 or 1, "trend_hype_phrase": "해당 문구 or null",
 "bundle": 0 or 1, "bundle_phrase": "해당 문구 or null",
 "confidence": 0 or 1, "confidence_phrase": "해당 문구 or null"}
```

- 200개를 배치 처리 (rate limit 고려)

**04_evaluate.py**
- 키워드 vs LLM, 각각 GT 대비:
  - 축별 Precision / Recall / F1
  - Confusion matrix (TP/FP/TN/FN)
  - 전체 Macro F1
- **Recall 우선** — 못 잡으면 Impulse Score 과소평가

**05_visualize.py**
- 키워드 vs LLM F1 비교 막대그래프 (축별)
- Confusion matrix 히트맵
- 오분류 샘플 top-10 출력

### ⚠️ 우려사항
- GT 라벨링 전 경계 케이스 합의 필요 → `configs/edge_cases.yaml`에 기준 문서화
- LLM 200회 호출 비용 (Flash-Lite면 매우 저렴, 거의 무시 가능)

---

## 4. 시험 3: style_similarity (`exp03_style_similarity`)

### 의존성
- **시험 0 완료** (옷 묘사 데이터 = Vision 추출 결과)
- **시험 1에서 추론 필드 정확도 확인** (추출된 style_keywords가 신뢰할 만한지)
- Gemini API 접근

### 파일 구조

```
exp03_style_similarity/
├── 01_build_test_set.py        # 스타일태그 × 옷묘사 조합 생성
├── 02_run_scoring.py           # LLM 3회 반복 호출
├── 03_analyze.py               # 분포, 일관성, 방향성, cap
├── 04_visualize.py             # 히스토그램, 박스플롯
├── configs/
│   ├── style_tags.yaml         # 테스트용 스타일 태그 5종
│   └── sanity_cases.yaml       # 자명한 케이스 20개
├── prompts/
│   └── style_similarity.txt    # docs에서 추출한 프롬프트
└── outputs/
```

### 코드 설계

**01_build_test_set.py**
- 스타일 태그 5종 (기초 질문의 선택지 기반):
  ```yaml
  - ["깔끔하고 단정한 스타일"]
  - ["편하고 캐주얼한 스타일"]
  - ["여성스럽고 부드러운 스타일"]
  - ["힙하고 개성 있는 스타일"]
  - ["깔끔하고 단정한 스타일", "편하고 캐주얼한 스타일"]
  ```
- 옷 묘사 20종: **시험 0의 추출 결과에서 가져옴**
  - `exp00_vision_extraction/results/`에서 20개 샘플
  - category, color, fit, style_keywords, shot_type, visibility 구성
  - 플랫폼별 골고루, 스타일 다양하게 선택
- sanity 케이스 20개: 명백히 맞는 10개 + 명백히 안 맞는 10개
- visibility 테스트: "부분 가림" 5개 + "불량" 5개 포함
- 전체: 5 × 20 + 20 + 10 = **130개 조합**

**02_run_scoring.py**
- 각 조합에 대해 Gemini Flash-Lite 호출
- temperature=0, 3회 반복
- 총 호출: 130 × 3 = **390회** (Flash-Lite면 비용 거의 없음)
- liked_purchases는 None으로 통일 (변수 통제)
- 결과 스키마:
  ```json
  {"combo_id": "s01_c15", "trial": 1, "score": 28,
   "reason": "캐주얼 태그와 캐주얼 스트릿 키워드가 잘 맞음",
   "latency_ms": 450}
  ```

**03_analyze.py**
- **분포**: 0~35 히스토그램, 구간당 비율
- **일관성**: 조합별 std, 전체 평균 std, std>3 비율, std>5 비율
- **방향성**: sanity 통과율 (맞는 조합 ≥25점, 안 맞는 조합 ≤15점)
- **cap 준수율**: visibility="부분 가림" → ≤20점, "불량" → ≤8점
- **reason 품질**: 평균 길이, 한국어 비율, 이상 응답(빈 문자열, JSON 에러) 수

### ⚠️ 우려사항
1. **style_keywords 어휘 불일치** (위 🚨 참조) — 시험 0에서 해결 후 진행
2. **시험 0 추출 품질이 낮으면** 옷 묘사 자체가 부정확 → style_similarity 테스트가 오염
   → 시험 1에서 추론 필드 정확도 먼저 확인하고, 70% 이상이면 진행
3. **liked_purchases 영향** — None으로 통제하지만, 실제 앱에서는 있을 수 있음 → v2에서 추가 테스트

---

## 5. 시험 4: 챗봇 또바 (`exp04_chatbot_ttoba`)

### 의존성
- `shared/prompt_builder.py` (system_prompt + context_sentences)
- `shared/scoring/` (점수 계산)
- Gemini API 접근
- (선택) 에이블리 가격 크롤링 완료

### 파일 구조

```
exp04_chatbot_ttoba/
├── 01_build_scenarios.py       # 시나리오 생성 + 점수/프롬프트 자동 조립
├── 02_run_conversations.py     # 또바와 대화 실행
├── 03_evaluate.py              # 자동 체크 + 수동 평가 템플릿
├── 04_compare_types.py         # DUTE vs NIMO 응답 비교
├── configs/
│   ├── scenarios.yaml          # 8~10개 시나리오 정의
│   ├── user_utterances.yaml    # 테스트 발화 3종
│   └── eval_checklist.yaml     # 평가 항목 정의
└── outputs/
```

### 코드 설계

**scenarios.yaml** — 최소 8개, 4분면 × 2유형:

| # | SBTI | 상품 특성 | Impulse | Match | 기대 방향 |
|---|------|----------|---------|-------|----------|
| 1 | DUTE | 할인50%+리뷰3000+SNS발견 | 높음 | 낮음 | 강한 브레이크 |
| 2 | DUTE | 할인50%+리뷰3000+1주고민 | 높음 | 높음 | 신중 확인 |
| 3 | NIMO | 할인50%+리뷰3000+SNS발견 | 낮음 | 낮음 | 냉정 비추 |
| 4 | NIMO | 할인0%+리뷰10+직접검색 | 낮음 | 높음 | 지지 |
| 5 | DIME | 희소 브랜드+리뷰적음 | 중간 | 중간 | M형 차별화 짚기 |
| 6 | NUTE | 할인30%+리뷰많음+쿠폰 | 중간 | 높음 | E형 할인 자극 환기 |
| 7 | DUTO | 유행+리뷰많음+오늘발견 | 높음 | 중간 | T+U형 사회적 증거 짚기 |
| 8 | NITO | 할인0%+직접검색+1주고민 | 낮음 | 높음 | 옷장 궁합 확인 |

**01_build_scenarios.py**
- yaml에서 시나리오 로드
- 각 시나리오에 대해:
  1. `compute_impulse_score()` / `compute_match_score()` 자동 계산
  2. `build_system_prompt()` 생성
  3. `build_context_sentences()` 생성
- 모든 조립 결과를 `outputs/scenarios_assembled.json`에 저장

**02_run_conversations.py**
- 시나리오별로 Gemini API에 system_prompt 설정 후 대화
- 발화 3종을 **독립적으로** 전송 (대화 맥락 누적하지 않음, 변수 통제):
  1. "이거 사도 돼?"
  2. "이거 왜 이렇게 비싸?"
  3. "비슷한 거 이미 있는데..."
- 동일 시나리오를 DUTE/NIMO 두 유형으로 실행 → 유형 간 차이 비교
- 결과: `outputs/conversations.jsonl`

**03_evaluate.py**
- **자동 체크:**
  - 반말 유지: 존댓말 패턴(`습니다`, `세요`, `께서`) 탐지
  - 응답 길이: 문장 수 카운트 (3~5 적정)
  - context 참조: context_sentences의 핵심 키워드가 응답에 포함되는지
- **수동 평가 템플릿 생성:**
  - 시나리오별 체크리스트 YAML 출력
  - 사람이 ✓/✗로 채움: 맥락 이해, 톤 적절, SBTI 반영, 방향 정확

**04_compare_types.py**
- DUTE vs NIMO 동일 시나리오 응답:
  - 단어 빈도 비교 (할인/리뷰/취향/필요/충동 등)
  - 방향성 분류 (추천/비추천/중립)
  - 응답 길이 차이

### ⚠️ 우려사항
- Gemini Flash-Lite가 또바의 톤(반말, 친근하지만 날카롭게)을 잘 따르는지 미지수
  → 첫 2개 시나리오 먼저 돌려보고 톤 확인 후 나머지 진행
- 에이블리 상품이 시나리오에 들어가면 가격 맥락이 빠짐
  → 크롤링 완료 전에는 무신사/지그재그 상품으로만 시나리오 구성

---

## 6. 시험 5: 점수 분포 & 구간 설계 (`exp05_score_distribution`)

### 의존성
- `shared/data_loader.py`
- `shared/scoring/` (이미 완성)
- `shared/marketing_detector.py`
- `shared/sbti_types.py`, `shared/survey_questions.py` (이미 완성)

### 파일 구조

```
exp05_score_distribution/
├── 01_preprocess.py            # 크롤링 데이터 전처리 + 샘플링
├── 02_generate_users.py        # 가상 유저 세트 생성
├── 03_calc_impulse.py          # Impulse Score 일괄 계산
├── 04_calc_match.py            # Match Score (3피쳐 소계)
├── 05_visualize.py             # 분포 시각화 전체
├── 06_define_tiers.py          # 구간 확정 + 이름/설명 + JSON
├── configs/
│   └── experiment_params.yaml  # seed, 샘플수 등
└── outputs/
```

### 코드 설계

**01_preprocess.py**
- `shared/data_loader.py`로 3개 플랫폼 전체 로드 & 정규화
- 플랫폼별 200개 랜덤 샘플링 (seed 고정) → 600개
- `shared/marketing_detector.py`로 trend_hype/bundle/confidence 라벨링
- 이상치 처리:
  - rating이 None → 0.0 (review_count도 0일 경우)
  - discount_rate가 None → 0
  - like_count가 None → 0 (지그재그 전체)
- 결과: `outputs/products_600.parquet`
- 통계 요약 출력: 플랫폼별 필드 분포, 마케팅 키워드 히트율

**02_generate_users.py**
- 16개 S-BTI 유형 × 공통질문 응답 조합
- 조합 생성:
  - price_reasonable: 4가지
  - interest_persistence: 4가지
  - discovery_stability: 5가지
  - contact_reason: 3가지 (점수에는 안 쓰이지만 프로필용)
- 모순 필터:
  - "오늘 처음 봤어요" + "오래 고민했는데 결정이 안 나서요" → 제거
  - "2주 이상 고민했어요" + "그냥 이 옷 어떤가 궁금해서요" → 제거
- 유형당 5개 조합 선택 (다양성 최대화) → 16 × 5 = **80명**
- 결과: `outputs/virtual_users.parquet`

**03_calc_impulse.py**
- `products_600` × `virtual_users_80` = **48,000 쌍**
- 각 쌍에 대해 `compute_impulse_score()` 호출
- 피쳐 기여도 분해 저장:
  ```
  discount_contrib = 0.35 * discount_score * discount_m
  rating_contrib   = 0.20 * rating_score * rating_m
  review_contrib   = 0.15 * review_score * review_count_m
  like_contrib     = 0.10 * like_score * like_count_m
  marketing_contrib = 0.20 * title_marketing_score * title_marketing_m
  ```
- 결과: `outputs/impulse_scores.parquet`
  - columns: product_id, user_id, sbti, platform, impulse_score,
    discount_contrib, rating_contrib, review_contrib, like_contrib, marketing_contrib

**04_calc_match.py**
- style_similarity 제외, 3피쳐 소계 (0~65)
- 사실상 유저별 고정값 → 80명의 소계 분포
- 결과: `outputs/match_subtotals.parquet`
- 80가지 조합의 소계 히스토그램

**05_visualize.py** — 핵심. 모든 시각화를 여기서.

```python
# === 5-2: Impulse Score ===

# (a) 전체 히스토그램 (48,000개)
#     - bin=20, 0~100 범위
#     - 평균, 중앙값, std 표시
#     - 분위수 라인(20/40/60/80) 표시

# (b) 유형별 비교
#     - DUTE vs NIMO 오버레이 히스토그램
#     - D형 전체 vs N형 전체 비교
#     - 16유형 박스플롯 (y축: score, x축: 유형, 정렬: 중앙값 순)

# (c) 피쳐별 기여도
#     - 5개 피쳐 기여도의 평균 비율 파이차트
#     - 피쳐 간 상관행렬 히트맵
#     - 유형별 피쳐 기여도 stacked bar

# (d) 플랫폼별 비교
#     - 에이블리 vs 무신사 vs 지그재그 히스토그램 오버레이
#     - 지그재그 like=0 영향 분리: 지그재그에서 like_contrib 제외한 점수 vs 포함한 점수

# === 5-3: Match Score ===

# (a) 3피쳐 소계 히스토그램 (80가지 조합)
#     - 13~65 범위
#     - 몰림 구간 확인

# (c) Impulse × Match 2차원 산점도
#     - x축: Impulse Score (0~100), y축: Match 소계 (0~65)
#     - 색상: SBTI 유형 (16색) 또는 D/N 2색
#     - 4분면 라인 표시 (중앙값 기준)
#     - 각 분면 점 개수 비율 표시
```

**06_define_tiers.py**
- Impulse Score:
  - 48,000개의 20/40/60/80 백분위 계산
  - 가장 가까운 5의 배수로 반올림
  - 5구간 이름/설명 매핑
- Match Score (3피쳐 소계 기준):
  - 65점 만점 → 비율로 0~100 환산 후 구간 적용? 또는 65점 기준 구간?
  - → **0~100 환산 없이 65점 만점 그대로**, style_similarity 합산 후 최종 구간 재확정
- 2차원 조합 해석 4분면 JSON 출력
- 결과: `outputs/tier_definitions.json`

### ⚠️ 우려사항 (이전 + 추가)

1. **마케팅 키워드 recall이 낮을 수 있음**
   - 키워드 매칭은 "인기상품"은 잡지만 "🔥완판임박"은 못 잡음
   - → 분포 해석에 "marketing_contrib가 과소추정됐을 수 있음" 주석
   - → 시험 2 이후 LLM 라벨로 재계산 가능하게 설계 (product_id로 조인)

2. **에이블리 가격 없음 → context_sentences 불가**
   - 시험 5에서는 context_sentences 안 씀 → 문제 없음
   - 시험 4에서 에이블리 상품 쓰려면 크롤링 필요

3. **Match 소계가 13~65에 편중**
   - 분석 결과로 어디에 몰리는지 확인 → style_similarity(0~35)가 변별력 책임 큰지 판단
   - 이게 시험 3의 중요도를 결정함

4. **M형 음수 처리**
   - review_score, like_score가 음수(-0.4, -0.9)까지 갈 수 있음
   - raw_score가 음수 → `max(0, ...)` 처리 → 0점
   - M형의 0점이 얼마나 많은지 확인 필요 (너무 많으면 M형 변별력 없음)

---

## 7. 실행 순서 & 타임라인

```
[Phase 0] 공통 인프라 ──────────────────────────────────────
  ├─ shared/data_loader.py          ← 코드로 즉시
  ├─ shared/marketing_detector.py   ← 코드로 즉시
  └─ shared/prompt_builder.py       ← docs에서 추출, 코드로 즉시

[Phase 1] 즉시 시작 가능 ──────────────────────────────────
  ├─ 시험 5: 점수 분포            ← 데이터+코드 모두 있음, 바로 가능
  └─ 시험 0: Vision 추출 재실험    ← 유저가 프롬프트 작성 후 직접 실행

[Phase 2] Phase 1 결과 필요 ────────────────────────────────
  ├─ 시험 1: Vision 정확도         ← 시험 0 결과 + GT 라벨링 (병렬 가능)
  └─ 시험 2: 마케팅 트리거         ← GT 라벨링 (시험 1과 병렬 가능)

[Phase 3] Phase 2 결과 필요 ────────────────────────────────
  └─ 시험 3: style_similarity     ← 시험 0 추출 데이터 + 시험 1 정확도 확인

[Phase 4] 전체 통합 ────────────────────────────────────────
  └─ 시험 4: 챗봇 또바             ← 모든 컴포넌트 검증 후

[별도] 에이블리 가격 크롤링         ← Phase 4 전까지 완료
```

**코드 작성 순서 (내가 짤 것):**
1. `shared/data_loader.py` + `shared/marketing_detector.py` + `shared/prompt_builder.py`
2. `exp05` 전체 (01~06)
3. `exp00` 구조 개선 (프롬프트 버전 관리, `--prompt-version` 인자)
4. `exp01` 전체 (01~03)
5. `exp02` 전체 (01~05)
6. `exp03` 전체 (01~04)
7. `exp04` 전체 (01~04)

---

## 8. 열린 질문 (유저 확인 필요)

| # | 질문 | 영향 | 긴급도 |
|---|------|------|--------|
| 1 | **style_keywords 어휘 통일** — 3곳(추출 프롬프트, docs, 기초질문)이 다른데 어떻게 맞출지 | 시험 0, 3, 4 | 🔴 높음 |
| 2 | **에이블리 크롤링 범위** — original_price + sale_price만 추가? category도? | 데이터 완전성 | 🟡 중간 |
| 3 | **이미지 추가 수집** — 현재 35개, 90장 목표면 추가 필요 | 시험 1 | 🟡 중간 |
| 4 | **시험 0 프롬프트 방향** — 기존 v1 대비 뭘 바꾸고 싶은지 | 시험 0 | 🟢 나중 |
