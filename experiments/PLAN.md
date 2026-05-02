# 시험 0~5 구현 계획 (v2)

> 작성일: 2026-04-14
> 확정 사항: LLM = Gemini 3.1 Flash-Lite, RoBERTa 제외, 옷 묘사는 실제 추출 데이터 사용

---

## 확정된 결정사항

| 항목 | 결정 |
|------|------|
| LLM 모델 (전체) | Gemini 3.1 Flash-Lite |
| 시험 2 → 시험 1 흡수 | 마케팅 트리거를 Vision 추출(시험 0)에서 동시 추출, 정확도는 시험 1에서 평가. e5/별도 LLM 비교 폐기 |
| 시험 3 옷 묘사 데이터 | 시험 0에서 실제 Vision 추출한 결과 사용 |
| 시험 0 | 팜팜이가 새 프롬프트/구조로 직접 재실험 |
| 에이블리 가격 | 추가 크롤링 예정 (exp04 전까지) |
| 지그재그 좋아요 | 없음 확정 (like_score=0 고정) |
| 찜 = 좋아요 | 동일 필드로 통합 |

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

### ~~0-2. `shared/marketing_detector.py`~~ — 폐기

> **폐기 (2026-04-16):** 마케팅 트리거는 시험 0 Vision LLM이 상품 제목에서 직접 추출.
> 키워드 매칭 방식은 recall이 낮고, 확정 사항("e5/별도 LLM 비교 폐기")과 모순되므로 삭제.
> 시험 5의 marketing_contrib는 시험 0 추출 결과(product_id 조인)로 계산한다.

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
기존은 팀원(경현)이 실험한 것. 팜팜이가 새 프롬프트·구조로 직접 재실험.

### 구조 변경

```
exp00_vision_extraction/
├── run_extraction.py           # 기존 스크립트 (수정)
├── prompts/
│   ├── extraction_v1_gemini.txt          # 기존 (경현 v1)
│   └── extraction_v2_gemini.txt          # 팜팜이 v2 (새로 작성)
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
- 프롬프트 파일명: `extraction_v{N}_gemini.txt` (버전별 별도 파일, v1 덮어쓰기 금지)
- 모델은 Gemini 3.1 Flash-Lite 단일

### shot_type 정의

| 유형 | 설명 |
|------|------|
| 모델착용샷 | 모델이 옷을 입고 촬영 |
| 단독샷 | 옷만 놓고 촬영 (배경 무관) |
| 행거샷 | 옷걸이에 걸어서 촬영 |
| 기타 | 위 3가지에 해당하지 않는 경우 |

### visibility 정의

"구매 결정에 필요한 상품 정보를 얼마나 볼 수 있는가" 기준. 배경·소품·워터마크는 무시, 옷 자체만 평가.
착용샷은 타겟 상품 부위 기준 판정 (상의 타겟이면 하의 잘림은 감점 없음).

| 등급 | 기준 | 스타일 판단 |
|------|------|------------|
| 양호 | 핵심 실루엣+디자인 온전. 모서리 5%이하 잘림, 포즈 접힘, 비핵심 워터마크 허용 | 가능 |
| 부분가림 | 면적 10~40% 가림, 디자인 포인트 가림, 크롭 1/4 이상 잘림 | 제한적 |
| 불량 | 면적 40% 초과 가림, 디테일컷만, 역광/과노출, 여러 상품 겹침 | 불가 |

> 상세 판정 기준 + 엣지케이스는 `prompts/extraction_v2_gemini.txt` 참조

### 배송 정보

배송 정보(무료배송, 당일발송, 빠른출발, 직진배송 등)는 Vision 추출 대상에 **포함**.
이미지에서 배송 관련 문구가 보이면 `delivery_info` 필드로 추출.

### ⚠️ 시험 0에서 해결해야 할 것들

1. ~~**style_keywords 어휘 통일**~~ → ✅ 확정: 추출 프롬프트 기준 10종
2. **좋아요 vs 브랜드 팔로워 혼동 방지** — 프롬프트에 명시적 구분 지침 추가
3. **쿠폰가 vs 기본 할인가 구분** — "첫 구매 20% 쿠폰"은 할인가가 아님을 명시
4. **100점 만점 → 5점 변환** — 기존 프롬프트에 있긴 한데, 실제로 지키는지 확인
5. **마케팅 트리거 동시 추출** — 이미지에서 읽은 상품 제목 텍스트에서 마케팅 트리거(trend_hype, bundle, confidence)도 같이 식별 (경현 제안)
6. **복수 이미지 처리** — 상품에 여러 사진이 있으면 **제일 앞 한 장만** 옷 스타일 판단 (category, color, fit, style_keywords). 텍스트 정보(가격, 리뷰수 등)는 모든 이미지에서 추출

### 산출물 → 이후 시험에 연결
- 추출된 옷 묘사 (category, color, fit, style_keywords, visibility, shot_type)
  → **시험 3**에서 style_similarity 입력으로 사용
- 추출된 숫자 (review_count, discount_rate 등)
  → **시험 1**에서 GT 대비 정확도 평가
- 추출된 마케팅 트리거 (trend_hype, bundle, confidence)
  → **시험 1**에서 GT 대비 정확도 평가 (기존 시험 2를 흡수)

---

## 2. 시험 1: Vision 추출 정확도 + 마케팅 트리거 (`exp01_vision_accuracy`)

> **변경 (2026-04-15):** 기존 시험 2(마케팅 트리거 분류)를 시험 1에 흡수.
> 시험 0 프롬프트 v2에서 마케팅 트리거도 동시 추출하므로, 같은 100장 스크린샷의 GT로 정확도를 함께 평가한다.
> e5 임베딩 비교·별도 텍스트 200개 실험은 폐기.

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
| 텍스트 추출 | has_discount | Exact Match (0/1) | - |
| 텍스트 추출 | discount_rate | Exact 또는 ±2% | 2 |
| 텍스트 추출 | review_count | ±5% | 비율 |
| 텍스트 추출 | review_score | ±0.1 | 0.1 |
| 텍스트 추출 | wishlist_count | ±10% | 비율 |
| 추론 | category, color, fit | 수동 판단 (모델 결과를 사람이 직접 맞는지 평가) | - |
| 추론 | style_keywords | Multi-label F1 | 최대 3개 태깅 |
| 추론 | shot_type | Exact Match (모델착용샷/단독샷/행거샷/기타) | - |
| 추론 | visibility | Exact Match (양호/부분가림/불량) | - |
| 마케팅 트리거 | trend_hype, bundle, confidence | 0/1: 축별 P/R/F1. 0~1 스코어: GT 없이 정성 평가 | LLM 추출 (프롬프트에서 0/1 + 0~1 둘 다 출력) |
| 선택 | delivery_info | 존재 여부 + 내용 일치 (정성 평가) | - |
| 선택 | brand | Exact Match | - |

> **category, color, fit**은 표기 변형이 너무 다양하여(후드집업 vs 집업, black vs 블랙, 스탠다드핏 vs 레귤러핏 등) 자동 exact match 대신 **모델이 뽑은 결과를 사람이 직접 보고 맞는지 판단**하는 방식으로 평가한다. GT를 일괄 생성하지 않음.

> **마케팅 트리거**는 시험 0 프롬프트에서 LLM이 상품 제목 텍스트 기반으로 trend_hype/bundle/confidence를 추출.
> - **0/1 바이너리**: 해당 마케팅 문구 존재 여부. GT와 비교하여 축별 Precision/Recall/F1 측정.
> - **0~1 연속 스코어**: LLM이 자극 강도를 판단 (키워드 개수·강렬함 종합). GT 없이 나온 결과를 보고 정성 평가.
> - **marketing_phrases**: 매칭된 원문 문구 추출.
> - **Recall 우선** — 시그널을 못 잡으면 Impulse Score 과소평가.

- 에러 분류: `correct`, `null_miss` (있는데 null), `wrong` (잘못된 값), `null_ok` (정답도 null)
- 특수 케이스 탐지기: 좋아요↔팔로워 혼동, 쿠폰가↔할인가 혼동

**03_visualize.py**
- 필드별 정확도 막대그래프 (텍스트 추출 vs 추론 vs 마케팅 트리거 그룹 분리)
- 플랫폼별 정확도 히트맵
- 에러 유형 분포 (null_miss vs wrong)
- 마케팅 트리거 축별 Confusion matrix
- 프롬프트 v1 vs v2 비교 (시험 0에서 여러 버전 실험 시)

### GT 라벨링 전략

GT는 전부 사람이 직접 만든다 — 프롬프트 튜닝의 정답 기준으로 사용.

| 필드 그룹 | 필드 | 담당 | 방식 |
|-----------|------|------|------|
| 텍스트 추출 | product_name, original_price, has_discount, discounted_price, discount_rate, review_count, review_score, wishlist_count | 경현+팜팜이 (50장씩) | 이미지 보고 직접 라벨링 |
| 메타 | shot_type, visibility | 경현+팜팜이 (숫자와 함께) | 이미지 보고 직접 라벨링. shot_type은 4종(모델착용샷/단독샷/행거샷/기타) |
| 스타일 | style_keywords | 낭연+정현 (50장씩) | 이미지 보고 직접 라벨링, **최대 3개** |
| 스타일 (수동) | category, color, fit | 낭연+정현 | 모델 결과를 보고 맞는지 판단 (GT 일괄 생성 안 함) |
| 마케팅 트리거 | trend_hype, bundle, confidence | 낭연+정현 (50장씩) | 상품 제목 보고 0/1 라벨링 (GT). 0~1 스코어는 LLM 추출, GT 없이 정성 평가 |
| 선택 | delivery_info, brand | 경현+팜팜이 (숫자와 함께) | 이미지에 보이면 입력, 안 보이면 비워두기 |

- **100장** = 플랫폼별 균등 배분 (현재 37장 → 인당 21장씩 추가 수집)
- 프롬프트를 바꿔가면서 GT와 비교 → 정확도 개선 반복
- 애매한 케이스는 표시해두고 회의에서 합의

### ⚠️ 우려사항
- 현재 images/ 에 약 37개 상품. 100장 목표면 인당 21장 추가 필요

---

## ~~3. 시험 2: 마케팅 트리거 분류~~ → 시험 1에 흡수

> **폐기 (2026-04-15):** 시험 0 프롬프트 v2에서 마케팅 트리거를 Vision 추출과 동시에 식별하므로,
> 별도 텍스트 200개 실험(e5 임베딩, LLM 분류)은 불필요. 마케팅 트리거 정확도 평가는 시험 1에서 같은 100장 GT로 수행.
> `exp02_marketing_trigger/` 폴더는 기존 노트북 참조용으로만 보존.

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
├── 03_analyze.py               # 분포, 일관성, 방향성
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
- 전체: 5 × 20 + 20 = **120개 조합**

**02_run_scoring.py**
- 각 조합에 대해 Gemini Flash-Lite 호출
- temperature=0, 3회 반복
- 총 호출: 120 × 3 = **360회** (Flash-Lite면 비용 거의 없음)
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
- **reason 품질**: 평균 길이, 한국어 비율, 이상 응답(빈 문자열, JSON 에러) 수

### ⚠️ 우려사항
1. ~~**style_keywords 어휘 불일치**~~ → ✅ 확정 (추출 프롬프트 기준 10종). 시험 0 프롬프트 v2에서 사용
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

### prompt_builder 실험 조건

system_prompt에 어떤 정보를 넣느냐에 따라 또바 응답이 달라짐.
다음 조합을 비교 실험:

| 조건 | 포함 내용 |
|------|----------|
| 축 설명 (개요) | 8개 축의 한 줄 요약 |
| 축 설명 (상세) | 8개 축의 상세 설명 |
| 유형 설명 (개요) | 16유형의 한 줄 요약 |
| 유형 설명 (상세) | 16유형의 상세 설명 |
| 축 + 긴장관계 | 축 설명 + IT, UM 같은 긴장관계 쌍 설명 |

→ 긴장관계까지 보여줄 수 있는 **유형 하나**(예: IT 또는 UM)를 정해서 평가.
전체 조합 실험은 비용 문제로 1개 유형에 집중.

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
| 9 | DUTE | 할인30%+리뷰많음+2주고민+안사기로결정 | 낮음 | 중간 | "안 살 건데 궁금" — 구매 의사 없는 유저에 또바가 어떻게 반응하는지 |

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
- 시험 0 Vision 추출 결과 (마케팅 트리거 라벨)
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
- 시험 0 Vision 추출 결과에서 trend_hype/bundle/confidence 라벨 조인 (product_id 기준)
- 이상치 처리:
  - rating이 None → 0.0 (review_count도 0일 경우)
  - discount_rate가 None → 0
  - like_count가 None → 0 (지그재그 전체)
- 결과: `outputs/products_600.parquet`
- 통계 요약 출력: 플랫폼별 필드 분포, 마케팅 트리거 히트율

**02_generate_users.py**
- 16개 S-BTI 유형 × 공통질문 응답 조합
- 조합 생성:
  - price_reasonable: 4가지
  - interest_persistence: 4가지
  - discovery_stability: 5가지
  - contact_reason: 3가지 (점수에는 안 쓰이지만 프로필용)
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

1. **마케팅 트리거 의존성: 시험 0 선행 필요**
   - 시험 5의 marketing_contrib 계산에 시험 0 Vision LLM 추출 결과가 필요
   - 시험 0 완료 전에는 marketing_contrib 없이 나머지 피쳐만으로 분포 확인 가능 (부분 실행)

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

## 7. 2차 비교 실험

> 1차 작업(시험 0·1·5 + 챗봇 시나리오) 완료 후 진행.
> 각 실험은 독립적으로 병렬 수행 가능.

### 7-1. context_sentences 룰베이스 vs LLM 비교

현재 `shared/prompt_builder.py`의 `build_context_sentences()`는 룰베이스(템플릿 기반)로 문장을 생성한다.
LLM이 상품 정보를 보고 직접 context 문장을 생성하는 방식과 비교하여 어느 쪽이 또바 응답 품질에 더 효과적인지 검증.

**의존성:** 시험 4 기본 시나리오 완료 (룰베이스 baseline 확보 후)

**비교 방법:**
- 동일 시나리오에 대해 룰베이스 context vs LLM 생성 context로 또바 응답 비교
- 평가: 맥락 반영 정도, 자연스러움, 정보 누락 여부, 할루시네이션

### 7-2. SBTI 설명 수준 비교

system_prompt에 SBTI 정보를 얼마나 상세하게 넣느냐에 따른 또바 응답 차이 비교.
시험 4의 prompt_builder 실험 조건을 독립 실험으로 분리.

**의존성:** 시험 4 기본 시나리오 완료 + 긴장관계 평가용 유형 1개 확정

**비교 조건:**

| 조건 | 포함 내용 |
|------|----------|
| 축 설명 (개요) | 8개 축의 한 줄 요약 |
| 축 설명 (상세) | 8개 축의 상세 설명 |
| 유형 설명 (개요) | 16유형의 한 줄 요약 |
| 유형 설명 (상세) | 16유형의 상세 설명 |
| 축 + 긴장관계 | 축 설명 + IT, UM 같은 긴장관계 쌍 설명 |

→ 긴장관계까지 평가할 **유형 1개**(IT 또는 UM)를 확정하고, 해당 유형에 집중 비교.

### 7-3. title marketing keyword 스코어링 룰베이스 vs LLM 비교

상품 제목에서 마케팅 키워드를 식별하고 자극 강도를 스코어링하는 두 가지 방식 비교.

- **룰베이스:** 키워드 목록 매칭 + 가중치 합산
- **LLM:** 시험 0 프롬프트에서 Vision LLM이 직접 판단 (현재 방식)

**의존성:** 시험 0 + 시험 1 완료 (LLM 방식 정확도 확인 후)

**비교 방법:**
- 동일 100장에 대해 룰베이스 vs LLM 추출 결과를 GT와 비교
- 지표: 축별 P/R/F1, 스코어 상관계수
- LLM이 충분히 정확하면 룰베이스 불필요, 아니면 혼합 방식 검토

---

## 8. 실행 순서 & 타임라인

```
[Phase 0] 공통 인프라 ──────────────────────────────────────
  ├─ shared/data_loader.py          ← 코드로 즉시
  └─ shared/prompt_builder.py       ← docs에서 추출, 코드로 즉시

[Phase 1] 즉시 시작 가능 ──────────────────────────────────
  ├─ 시험 5: 점수 분포            ← 데이터+코드 모두 있음, 바로 가능
  └─ 시험 0: Vision 추출 재실험    ← 팜팜이가 프롬프트 작성 후 직접 실행

[Phase 2] Phase 1 결과 필요 ────────────────────────────────
  └─ 시험 1: Vision 정확도 + 마케팅 트리거  ← 시험 0 결과 + GT 100장 라벨링

[Phase 3] Phase 2 결과 필요 ────────────────────────────────
  └─ 시험 3: style_similarity     ← 시험 0 추출 데이터 + 시험 1 정확도 확인

[Phase 4] 전체 통합 ────────────────────────────────────────
  └─ 시험 4: 챗봇 또바             ← 모든 컴포넌트 검증 후

[Phase 5] 2차 비교 실험 (병렬 가능) ────────────────────────
  ├─ 7-1: context_sentences 룰베이스 vs LLM    ← 시험 4 완료 후
  ├─ 7-2: SBTI 설명 수준 비교                   ← 시험 4 완료 후
  └─ 7-3: marketing keyword 스코어링 비교       ← 시험 0+1 완료 후

[별도] 에이블리 가격 크롤링         ← Phase 4 전까지 완료
```

**코드 작성 순서 (내가 짤 것):**
1. `shared/data_loader.py` + `shared/prompt_builder.py`
2. `exp05` 전체 (01~06)
3. `exp00` 구조 개선 (프롬프트 버전 관리, `--prompt-version` 인자)
4. `exp01` 전체 (01~03) — 마케팅 트리거 평가 포함 (기존 exp02 흡수)
5. `exp03` 전체 (01~04)
6. `exp04` 전체 (01~04)

---

## 9. 열린 질문 (팀 확인 필요)

| # | 질문 | 영향 | 긴급도 |
|---|------|------|--------|
| ~~1~~ | ~~**style_keywords 어휘 통일**~~ → ✅ 추출 프롬프트 기준 10종으로 확정 | ~~시험 0, 3, 4~~ | ✅ 해결 |
| 2 | **에이블리 크롤링 범위** — original_price + sale_price만 추가? category도? | 데이터 완전성 | 🟡 중간 |
| 3 | **이미지 추가 수집** — 현재 37개, 100장 목표 (인당 21장 추가) | 시험 1 | 🟡 중간 |
| ~~4~~ | ~~**시험 0 프롬프트 방향**~~ → ✅ v2 작성 완료: shot_type 변경(단독샷), visibility 판정 기준 추가 | ~~시험 0~~ | ✅ 해결 |
