# Impulse Score

> 
> 
> 
> Impulse Score는 이 옷의 마케팅·심리적 피쳐가 이 사용자에게 충동 구매를 유발할 가능성을 0~100점으로 나타낸 점수입니다.
> 
> 높을수록 "지금 이 순간 마케팅에 혹해서 사는 것"에 가깝고,
> 낮을수록 "마케팅 영향 없이 냉정하게 판단하는 것"에 가깝습니다.
> 
> 이 점수는 상품의 객관적 피쳐(할인율, 리뷰수 등)에 사용자의 심리 유형(SBTI)에 따른 multiplier를 적용해 계산됩니다. 같은 상품이라도 유형에 따라 점수가 달라집니다.
> 

### Feature

- 모든 피쳐는 0~1 사이로 정규화 후 가중합

### **`discount_rate` — 할인율**

- 변환

| discout_rate | **discount_score** | **비고** |
| --- | --- | --- |
| 0% | 0.00 | 자극 없음 |
| 1~10% | 0.15 | 약한 자극 |
| 11~20% | 0.35 | 체감 할인 시작 |
| 21~35% | 0.65 | 충동 자극 구간 |
| 36~50% | 1.00 | Peak |
| 51~60% | 0.75 | 의심 시작 |
| 61~70% | 0.45 | 브레이크 |
| 71% 이상 | 0.25 | 신뢰도 하락 |
| 정보 없음 | 0.00 |  |

- SBTI multiplier

| **축** | **타입** | **multiplier** | **근거** |
| --- | --- | --- | --- |
| D/N | D | 1.2 | 감정 기반 소비 → 할인 자극에 더 취약 |
| D/N | N | 1.2 | 필요 중심이라도 할인은 보편적 트리거 → 동일 |
| E/O | E | 1.3 | 거래 효용 민감형 → 할인 자체가 구매 동기 |
| E/O | O | 0.9 | 물건 가치 중심 → 할인보다 품질 우선 |

### **`review_count` — 리뷰 수**

- 변환
    - 단, M형의 경우 아래 수식을 따름
        
        
        | 플랫폼 | n (P75) | n2 (P90) | ≤n | n~n2 | >n2 |
        | --- | --- | --- | --- | --- | --- |
        | 무신사 (default) | 100 | 650 | 0.0 | **-0.4** | **-0.9** |
        | 에이블리 | 800 | 3,000 | 0.0 | **-0.4** | **-0.9** |
        | 지그재그 | 600 | 2,500 | 0.0 | **-0.4** | **-0.9** |

$$
review\_score = \min\left( \left( \frac{\log_{10}(review\_count + 1)}{\log_{10}(5001)} \right)^{1.5}, 1.0 \right)
$$

- 변환 예시
    
    
    | review_count | review_score | **유저 체감도** |
    | --- | --- | --- |
    | 10개 | 0.15 | "아직은 불안함 (신뢰도 낮음)" |
    | 30개 | 0.25 | "조금씩 쌓이지만 여전히 낮음" |
    | 50개 | 0.31 | "0.3점대 - 이제 막 시작" |
    | 100개 | 0.40 | "0.4점 - 유의미한 첫 지점" |
    | 200개 | 0.49 | "약 0.5점 - 검증의 시작" |
    | 500개 | 0.62 | "신뢰할 수 있는 상품" |
    | 1,000개 | 0.73 | "대세 아이템" |
    | 5,000개 | 1.00 | 사회적 증거 끝판왕 |

- SBTI multiplier

| **축** | **타입** | **multiplier** | **근거** |
| --- | --- | --- | --- |
| U/I | U | 1.3 | 사회적 증거 강하게 신뢰 |
| U/I | I | 0.7 | 타인 리뷰보다 자기 분석 우선 |
| T/M | T | 1.2 | 인기 = 유행 신호로 해석 |

### **`rating` — 리뷰 평점**

- 변환
    - 단, 리뷰가 없는 경우 0.3점

$$
rating\_score = max((rating - 3.0) / 2.0, 0.0)
$$

- SBTI multiplier

| **축** | **타입** | **multiplier** | **근거** |
| --- | --- | --- | --- |
| U/I | U | 1.2 | 집단 검증 신호로 강하게 신뢰 |
| U/I | I | 1.0 | 중립 |
| E/O | O | 1.2 | 평점 = 품질 신호 → 구매 충동에 더 영향 |
| E/O | E | 1.0 | 중립 |

### **`like_count` — 찜/좋아요 수**

- 변환
    - 단, M형의 경우 아래 수식을 따름
        
        
        | 플랫폼 | n (P75) | n2 (P90) | ≤n | n~n2 | >n2 |
        | --- | --- | --- | --- | --- | --- |
        | 무신사 (default) | 4,000 | 13,000 | 0.0 | **-0.3** | **-0.6** |
        | 에이블리 | 10,000 | 30,000 | 0.0 | **-0.3** | **-0.6** |
        | 지그재그 | — | — | 0.0 | 0.0 | 0.0 |

$$
like\_score = \min\left( \left( \frac{\log_{10}(like\_count + 1)}{\log_{10}(10001)} \right)^{1.5}, 1.0 \right)
$$

- 변환 예시
    
    
    | like_count | like_score | **체감 의미** |
    | --- | --- | --- |
    | 10개 | 0.13 | "누군가는 관심을 가짐" |
    | 100개 | 0.37 | "조금씩 바이럴 타는 중" |
    | 500개 | 0.57 | "0.5점 돌파 - 인기템 진입" |
    | 1,000개 | 0.68 | "충분히 검증된 관심도" |
    | 5,000개 | 0.88 | "이미 대중적인 인기템" |
    | 10,000개+ | 1.00 | 관심도 끝판왕 |

- SBTI multiplier

| **축** | **타입** | **multiplier** | **근거** |
| --- | --- | --- | --- |
| U/I | U | 1.2 | 인기 지표로 신뢰 |
| U/I | I | 0.7 | 타인 반응 무시 |
| T/M | T | 1.2 | 인기 = 트렌드 신호 |

### **`title_marketing_score` — 마케팅 트리거 문구 강도**

- 계산식
    - 각 요소는 0 or 1 (기본) 또는 0.0~1.0 연속 스코어 (선택)
        - 판단은 LLM (Vision 추출 시 0/1과 연속 스코어 둘 다 추출)
        - 연속 스코어가 주어지면 0/1 대신 사용
    - w1, w2, w3 는 S-BTI 유형에 따라 아래 표 기준으로 결정

$$
title\_marketing\_score = w1 * trend\_hype + w2 * bundle + w3 * confidence
$$

- SBTI별 요소 가중치 변경

| **마케팅 시그널** | **기본 가중치** | **변경 가중치** |
| --- | --- | --- |
| trend_hype | 0.2 | T&U: 0.5
T: 0.4
U: 0.3
M: 0 |
| bundle | 0.2 | E: 0.4 |
| confidence | 0.3 | O: 0.4 |

- SBTI Multiplier

| **축** | 타입 | **Multiplier** | **설정 근거 (심리적 배경)** |
| --- | --- | --- | --- |
| D/N | D | 1.1 | 새로운 자극과 마케팅 문구에 뇌가 즉각적으로 흥분함 |
| D/N | N | 0.9 | 광고성 멘트보다는 목적성 구매를 지향하여 자극을 차단함 |
| T/M | M | 0.8 | 뻔한 마케팅 문구에 반감을 느끼며 매력을 낮게 평가함 |

### 계산식

```python
from math import log10

# ==============================================
# M형 플랫폼별 임계값 테이블
# ==============================================
# M형은 리뷰/찜이 많을수록 오히려 매력이 떨어지므로
# 임계값 초과 시 음수 점수를 부여한다.
#
# n (P75): 해당 플랫폼 상위 25% 기준
# n2 (P90): 해당 플랫폼 상위 10% 기준
# ≤n → 0.0 (중립), n~n2 → 감점, >n2 → 강한 감점

REVIEW_M_TABLE = {
    #               n      n2     ≤n    n~n2   >n2
    "무신사":     (100,   650,   0.0,  -0.4,  -0.9),
    "에이블리":   (800,   3000,  0.0,  -0.4,  -0.9),
    "지그재그":   (600,   2500,  0.0,  -0.4,  -0.9),
    "default":    (100,   650,   0.0,  -0.4,  -0.9),  # 무신사 기준
}

LIKE_M_TABLE = {
    #               n       n2      ≤n    n~n2   >n2
    "무신사":     (4000,  13000,  0.0,  -0.3,  -0.6),
    "에이블리":   (10000, 30000,  0.0,  -0.3,  -0.6),
    "지그재그":   (None,  None,   0.0,   0.0,   0.0),  # 찜 기능 없음
    "default":    (4000,  13000,  0.0,  -0.3,  -0.6),  # 무신사 기준
}

def get_m_score(count, table, platform):
    """M형 전용: 플랫폼별 임계값 기반 점수 반환"""
    row = table.get(platform, table["default"])
    n, n2, score_low, score_mid, score_high = row

    if n is None:  # 지그재그 찜처럼 해당 지표가 없는 경우
        return 0.0
    if count <= n:
        return score_low
    elif count <= n2:
        return score_mid
    else:
        return score_high

# ==============================================
# Step 1: 각 피쳐 정규화
# ==============================================

DISCOUNT_TABLE = [
    (0,   0,   0.00),
    (1,   10,  0.15),
    (11,  20,  0.35),
    (21,  35,  0.65),
    (36,  50,  1.00),
    (51,  60,  0.75),
    (61,  70,  0.45),
    (71,  100, 0.25),
]

def get_discount_score(discount_rate):
    if discount_rate is None:
        return 0.00
    for lo, hi, score in DISCOUNT_TABLE:
        if lo <= discount_rate <= hi:
            return score
    return 0.00

def compute_impulse_score(
    # 상품 데이터
    discount_rate,
    review_count,
    rating,
    like_count,
    trend_hype,      # 0 or 1
    bundle,          # 0 or 1
    confidence,      # 0 or 1

    # 유저 SBTI 플래그
    is_D, is_N,
    is_U, is_I,
    is_T, is_M,
    is_E, is_O,

    # 플랫폼 (M형 임계값 결정용)
    platform="default",
):
    # --- discount ---
    discount_score = get_discount_score(discount_rate)

    # --- review_count ---
    # M형: 플랫폼별 임계값 기반, 많을수록 음수 (대중적 = 매력 감소)
    # 비M형: 로그 스케일 (많을수록 사회적 증거 → 충동 증가)
    if is_M:
        review_score = get_m_score(review_count, REVIEW_M_TABLE, platform)
    else:
        review_score = min(log10(review_count + 1) / log10(5001), 1.0) ** 1.5

    # --- rating ---
    # 리뷰 없으면 0.3 고정 (불확실성 프리미엄)
    if review_count == 0:
        rating_score = 0.3
    else:
        rating_score = max((rating - 3.0) / 2.0, 0.0)

    # --- like_count ---
    # M형: 플랫폼별 임계값 기반, 많을수록 음수
    # 비M형: 로그 스케일
    if is_M:
        like_score = get_m_score(like_count, LIKE_M_TABLE, platform)
    else:
        like_score = min(log10(like_count + 1) / log10(10001), 1.0) ** 1.5

    # --- title_marketing_score ---
    if is_M:
        w1 = 0.0
    elif is_T and is_U:
        w1 = 0.5
    elif is_T:
        w1 = 0.4
    elif is_U:
        w1 = 0.3
    else:
        w1 = 0.2

    w2 = 0.4 if is_E else 0.2
    w3 = 0.4 if is_O else 0.3

    w_total = w1 + w2 + w3
    if w_total > 0:
        title_marketing_score = (w1 * trend_hype + w2 * bundle + w3 * confidence) / w_total
    else:
        title_marketing_score = 0.0

    # ==============================================
    # Step 2: SBTI Multiplier
    # ==============================================

    discount_m = 1.2 * (1.3 if is_E else (0.9 if is_O else 1.0))
    rating_m = (1.2 if is_U else 1.0) * (1.2 if is_O else 1.0)
    review_count_m = (1.3 if is_U else (0.7 if is_I else 1.0)) * (1.2 if is_T else 1.0)
    like_count_m = (1.2 if is_U else (0.7 if is_I else 1.0)) * (1.2 if is_T else 1.0)

    if is_M:
        title_marketing_m = 0.8
    elif is_D:
        title_marketing_m = 1.1
    elif is_N:
        title_marketing_m = 0.9
    else:
        title_marketing_m = 1.0

    # ==============================================
    # Step 3: 가중합
    # ==============================================

    raw_score = (
        0.35 * discount_score         * discount_m
      + 0.20 * rating_score           * rating_m
      + 0.15 * review_score           * review_count_m
      + 0.10 * like_score             * like_count_m
      + 0.20 * title_marketing_score  * title_marketing_m
    )

    # ==============================================
    # Step 4: 0~100 변환
    # ==============================================
    # 이론적 max: DUTE (D+U+T+E) 기준
    # discount_m         = 1.2 * 1.3        = 1.560
    # rating_m           = 1.2 * 1.0        = 1.200
    # review_count_m     = 1.3(U) * 1.2(T)  = 1.560
    # like_count_m       = 1.2(U) * 1.2(T)  = 1.440
    # title_marketing_m  = 1.1(D)           = 1.100
    #
    # max = 0.35*1.560 + 0.20*1.200 + 0.15*1.560 + 0.10*1.440 + 0.20*1.100
    #     = 0.546 + 0.240 + 0.234 + 0.144 + 0.220
    #     = 1.384

    MAX_POSSIBLE = 1.384

    # Step 4: 0~100 변환 (기본 점수 가산)
    # 모든 유저 +10점, D형 추가 +5점 (감정 기반 소비라 바닥이 너무 낮으면 변별력 저하)
    # M형은 음수 raw_score가 나올 수 있으므로 하한 0 처리
    base = 10 + (5 if is_D else 0)
    return max(0, min(100, round((raw_score / MAX_POSSIBLE) * 100) + base))

# ==============================================
# 실행 예시
# ==============================================

if __name__ == "__main__":

    # 예시 1: DUTE — 할인 50%, 리뷰 3200개, 평점 4.8, 찜 8500, 무신사
    score1 = compute_impulse_score(
        discount_rate=50, review_count=3200, rating=4.8, like_count=8500,
        trend_hype=1, bundle=0, confidence=1,
        is_D=True, is_N=False, is_U=True, is_I=False,
        is_T=True, is_M=False, is_E=True, is_O=False,
        platform="무신사",
    )
    print(f"DUTE (무신사): {score1}점")

    # 예시 2: DUMO (M형) — 같은 상품, 무신사
    # 리뷰 3200 > n2(650) → -0.9, 찜 8500 > n2(13000)? 아니므로 n~n2 → -0.3
    score2 = compute_impulse_score(
        discount_rate=50, review_count=3200, rating=4.8, like_count=8500,
        trend_hype=1, bundle=0, confidence=1,
        is_D=True, is_N=False, is_U=True, is_I=False,
        is_T=False, is_M=True, is_E=False, is_O=True,
        platform="무신사",
    )
    print(f"DUMO (무신사): {score2}점")

    # 예시 3: DUMO (M형) — 같은 상품, 에이블리
    # 리뷰 3200 > n2(3000) → -0.9, 찜 8500 ≤ n(10000) → 0.0
    score3 = compute_impulse_score(
        discount_rate=50, review_count=3200, rating=4.8, like_count=8500,
        trend_hype=1, bundle=0, confidence=1,
        is_D=True, is_N=False, is_U=True, is_I=False,
        is_T=False, is_M=True, is_E=False, is_O=True,
        platform="에이블리",
    )
    print(f"DUMO (에이블리): {score3}점")
```

### 점수 구간별 해석

# Match Score

> 
> 
> 
> Match Score는 이 옷이 사용자의 취향·상황·가치 기준에
> 얼마나 잘 맞는지를 0~100점으로 나타낸 점수입니다. 높을수록 "사고 나서도 잘 입고 후회하지 않을 구매"에 가깝습니다.
> 유형별 가중치 없이 피쳐 그대로 합산합니다. (취향은 개인마다 너무 달라 유형별 일반화가 오히려 오차를 키우기 때문)
> 

### Feature & 계산식

| feature | 만점 | 데이터 출처 |
| --- | --- | --- |
| `style_similarity` | 35점 | 기초 질문(스타일) × 옷 이미지 묘사 텍스트 |
| `price_reasonable` | 25점 | 설문 응답 (가격 체감) |
| `interest_persistence` | 20점 | 설문 응답 (관심 지속 기간) |
| `discovery_stability` | 20점 | 설문 응답 (발견 경로) |

### `style_similarity` **—** 스타일 일치도

- 데이터 출처
    
    
    - 주로 어떤 스타일을 입나요? **(다중 선택 가능)**
        - `깔끔하고 단정한 스타일`
        - `편하고 캐주얼한 스타일`
        - `여성스럽고 부드러운 스타일`
        - `힙하고 개성 있는 스타일`
        - `세련되고 포멀한 스타일`
        - `빈티지·레트로 스타일`
        - `기타 (직접 입력)`
    
    - 옷 이미지 묘사 텍스트
        - 카테고리
            - 예시: 미니스커트, 팬츠, 후드티, 자켓, 원피스
        - 색상
            - 예시: 블랙, 오프화이트, 버터옐로우, 올리브그린, 버건디, 멀티컬러
        - 핏/실루엣
            - 예시: 오버핏, 루즈핏, 슬림핏, 크롭, 박시, 플레어, 언밸런스 헴라인
        - 스타일 키워드 (최대 3개)
            - 허용값: 심플베이직, 락시크, 힙, 페미닌, 러블리, 모리걸, 빈티지, 스트릿, 캐주얼, 섹시글램
        - 촬영 유형
            - 다음 4개 중에서 고르도록
                - 모델착용샷 | 단독샷 | 행거샷 | 기타
        - 옷 가시성
            - 다음 3개 중에서 고르도록
                - 양호 | 부분 가림 | 불량
- 점수 계산
    
    ```jsx
    [유저 스타일 태그]
    {user_style_tags}
    
    [유저가 만족한 최근 구매]
    {liked_purchases}   # 아래 상품 분석 결과와 동일한 포맷
    
    [상품 분석 결과]
    - 카테고리: {category}
    - 색상: {color}
    - 핏/실루엣: {fit}
    - 스타일 키워드: {style_keywords}
    - 촬영 유형: {shot_type}
    - 옷 가시성: {visibility}
    
    아래 기준에 따라 유저 스타일과 상품의 일치도를 0~35점으로 평가하라.
    
    평가 기준:
    - 유저 스타일 태그를 이 사람의 스타일 방향성으로 해석한다
    - 만족한 구매 데이터가 있으면 취향 신호로 보조 참고한다 (선택 입력이며 표본이 작을 수 있으므로 태그를 대체하지 않는다)
    - 만족한 구매 데이터가 "데이터 없음"이면 태그만으로 평가한다
    - 스타일 키워드를 중심으로 비교하되, 카테고리·핏·색상은 보조 참고용으로만 활용한다
    - 스타일 간 유사도는 패션 업계의 일반적인 상식을 기준으로 판단하며, 완전 일치부터 계열 유사, 부분 관련, 무관까지 연속적인 스펙트럼으로 평가한다
    
    반드시 JSON으로만 응답: {"score": <int>, "reason": "<한 줄 이유>"}
    ```
    

### `price_reasonable` **—** 가격 적합도

- 데이터 출처 & 점수 계산
    
    
    - 이 가격, 적당한 것 같아요?
        - `저렴한 것 같아요`
            - price_reasonable: 25점
        - `이 정도면 괜찮아요`
            - price_reasonable: 18점
        - `좀 비싸긴 한데 못 살 정도는 아니에요`
            - price_reasonable: 10점
        - `상품은 마음에 들지만 가격이 비싸요`
            - price_reasonable: 3점

### `interest_persistence` **—** 관심 지속도

- 데이터 출처 & 점수 계산
    
    
    - 이 옷, 언제부터 눈에 들어왔어요?
        - `오늘 처음 봤어요`
            - interest_persistence: 4점
        - `2~3일 됐어요`
            - interest_persistence: 10점
        - `1주일 정도 됐어요`
            - interest_persistence: 20점
        - `2주 이상 고민했어요`
            - interest_persistence: 16점

### `discovery_stability` **—** 관심 경로

- 데이터 출처 & 점수 계산
    
    
    - 이 옷, 어떻게 하다가 발견했어요?
        - `쇼핑 앱에서 카테고리 검색 후 찾아보다 발견했어요`
            - discovery_stability: 20점
        - `유튜버/인플루언서가 입은 것을 봤어요`
            - discovery_stability: 6점
        - `쇼핑 앱에서 랭킹이나 유저 추천을 둘러보다 발견했어요`
            - discovery_stability: 10점
        - `인스타/틱톡/X 같은 SNS 보다가 발견했어요`
            - discovery_stability: 6점
        - `브랜드 계정에 신상이 추가된 걸 봤어요`
            - discovery_stability: 12점
- 계산식
    
    ```python
    match_score = style_similarity + price_reasonable
    + interest_persistence + discovery_stability
    ```
    

### 점수 구간별 해석