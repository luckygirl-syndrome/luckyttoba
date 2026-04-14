# Vision Extraction Benchmark

쇼핑 스크린샷에서 상품 정보를 추출하는 Vision 모델 벤치마크 프로젝트입니다.
Gemini와 GPT-4o의 추출 퀄리티를 동일한 조건에서 비교합니다.

## 프로젝트 구조

```
vision-test/
├── images/                          # 테스트 이미지
│   └── {product_id}/
│       ├── 01.png
│       └── 02.png
├── manifests/
│   └── dataset.jsonl               # 이미지 목록
├── prompts/
│   ├── extraction_prompt_gemini.txt
│   └── extraction_prompt_gpt.txt
├── results/                         # 추출 결과
│   ├── gemini/
│   └── gpt/
├── run_extraction.py                # 메인 실행 스크립트
├── requirements.txt                 # Python 의존성
└── .env.example                     # API 키 설정 예제
```

## 설치

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. API 키 설정

`.env.example`을 `.env`로 복사하고 API 키를 입력하세요:

```bash
cp .env.example .env
```

그리고 `.env` 파일을 열어서 각 API 키를 입력하세요:
- **Gemini**: https://aistudio.google.com/app/apikeys에서 생성
- **OpenAI**: https://platform.openai.com/api-keys에서 생성

### 3. 이미지 준비

`images/` 디렉토리에 상품별 폴더를 만들고 이미지를 넣으세요:

```
images/
├── musinsa_pants_001/
│   ├── 01.png
│   └── 02.png (선택사항)
└── zigzag_skirt_001/
    └── 01.png
```

### 4. Dataset 파일 작성

`manifests/dataset.jsonl`에 처리할 이미지 목록을 입력하세요:

```jsonl
{"id": "musinsa_pants_001", "images": ["images/musinsa_pants_001/01.png", "images/musinsa_pants_001/02.png"]}
{"id": "zigzag_skirt_001", "images": ["images/zigzag_skirt_001/01.png"]}
```

## 실행

### 모든 모델로 추출
```bash
python run_extraction.py
```

### 특정 모델만 사용
```bash
python run_extraction.py --models gpt
```

### 특정 데이터만 처리 (인덱스 기반, 0부터 시작)
```bash
python run_extraction.py --indices 0 2 3
```

## 결과

결과는 `results/{모델명}/{product_id}_{run_number}.jsonl` 형식으로 저장됩니다.

### 결과 파일 예시
```jsonl
{"run": 1, "model": "gemini", "image_id": "musinsa_pants_001", "timestamp": "2026-04-12T15:30:00Z", "result": {"product_name": "오버핏 코튼 후드집업", ...}}
```

- **run**: 실행 번호 (같은 이미지를 여러 번 실행할 때 증가)
- **model**: 사용된 모델명
- **image_id**: 상품 ID
- **timestamp**: 실행 시간 (UTC)
- **result**: 추출된 상품 정보

## 필드 설명

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| product_name | string | 상품명 | "오버핏 코튼 후드집업" |
| original_price | number | 원가 | 39000 |
| is_discounted | boolean | 할인 여부 | true |
| discounted_price | number | 할인가 | 27300 |
| discount_rate | number | 할인율 (%) | 30 |
| review_count | number | 리뷰 수 | 1284 |
| review_score | number | 평점 (0-5) | 4.8 |
| category | string | 카테고리 | "후드티" |
| color | string | 색상 | "오프화이트" |
| fit | string | 핏 | "오버핏" |
| style_keywords | array | 스타일 키워드 | ["캐주얼", "스트릿"] |
| shot_type | string | 사진 유형 | "모델착용샷" / "흰배경단독샷" / "행거샷" / "기타" |
| visibility | string | 가시성 | "양호" / "부분가림" / "불량" |
| wishlist_count | number | 찜 수 | 3200 |
| delivery_info | string | 배송 정보 | "내일 도착" |
| brand_name | string | 브랜드명 | "무신사 스탠다드" |

## 주의사항

- 이미지가 없으면 실행되지 않습니다. 먼저 이미지를 `images/` 디렉토리에 추가하세요.
- 프롬프트를 변경한 후 재실행하면 run 번호가 자동으로 증가합니다.
- 0과 null을 구분해야 합니다 (null = 정보 없음, 0 = 실제 값이 0).

## API 가격

각 모델별 Vision API 가격은 다를 수 있으니 공식 문서를 참고하세요:
- [Google Gemini Pricing](https://ai.google.dev/pricing)
- [OpenAI Vision Pricing](https://openai.com/pricing/gpt-4-and-gpt-4-turbo)

## 트러블슈팅

### API 키 오류
- `.env` 파일이 존재하는지 확인
- API 키가 올바르게 입력되었는지 확인
- API 사용량 제한에 도달했는지 확인

### 이미지 로드 오류
- 이미지 파일 경로가 `dataset.jsonl`과 일치하는지 확인
- 이미지 파일이 실제로 존재하는지 확인
- 지원되는 형식: PNG, JPG, GIF, WebP

### JSON 파싱 오류
- 모델 응답이 유효한 JSON 형식인지 확인
- 일부 모델이 JSON을 마크다운 코드 블록으로 감싸는 경우 자동 처리됩니다

## 라이선스

이 프로젝트는 교육 및 벤치마킹 목적으로 만들어졌습니다.
