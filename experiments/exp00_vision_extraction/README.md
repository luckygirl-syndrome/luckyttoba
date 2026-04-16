# Vision Extraction Test

쇼핑 스크린샷 이미지에서 Vision LLM이 상품 정보를 정확하게 추출하는지 평가하는 실험입니다.

## 개요

- **목표**: Vision 모델의 상품 정보 추출 성능 테스트
- **모델**: Gemini 3.1 Flash-Lite
- **테스트 데이터**: 쇼핑몰 스크린샷 이미지
- **추출 대상**: 상품명, 가격, 할인율, 리뷰, 색상, 핏, 배송 정보, 마케팅 트리거 등

## 설치

```bash
pip install -r requirements.txt
```

## API 설정

`.env.example`을 참고해서 `.env` 파일을 만들고 API 키를 입력하세요:

```bash
cp .env.example .env
```

필요한 API 키:
- **Gemini**: https://aistudio.google.com/app/apikeys

## 사용법

### 1. 이미지 준비

`images/` 디렉토리에 상품별 폴더를 만들어 이미지를 추가:

```
images/
├── product_001/
│   ├── 01.png
│   └── 02.png (선택)
└── product_002/
    └── 01.png
```

### 2. 데이터셋 작성

`manifests/dataset.jsonl`에 테스트할 이미지 목록을 작성:

```jsonl
{"id": "product_001", "images": ["images/product_001/01.png", "images/product_001/02.png"]}
{"id": "product_002", "images": ["images/product_002/01.png"]}
```

### 3. 추출 실행

기본 실행 (v1 프롬프트):
```bash
python run_extraction.py
```

v2 프롬프트로 실행:
```bash
python run_extraction.py --prompt-version v2
```

특정 데이터만 처리 (인덱스 기반):
```bash
python run_extraction.py --indices 0 2 3
```

## 결과 확인

결과는 `results/{모델명}/{product_id}_{run_number}.jsonl`로 저장됩니다.

예시:
```jsonl
{"run": 1, "model": "gemini", "image_id": "product_001", "timestamp": "2026-04-14T10:30:00Z", "result": {"product_name": "오버핏 후드티", "original_price": 39000, ...}}
```

## 추출 필드

| 필드 | 설명 | 예시 |
|------|------|------|
| product_name | 상품명 | "오버핏 코튼 후드집업" |
| original_price | 원가 | 39000 |
| is_discounted | 할인 여부 | true |
| discounted_price | 할인가 | 27300 |
| discount_rate | 할인율 (%) | 30 |
| review_count | 리뷰 수 | 1284 |
| review_score | 평점 (0-5) | 4.8 |
| category | 카테고리 | "후드티" |
| color | 색상 | "오프화이트" |
| fit | 핏 | "오버핏" |
| style_keywords | 스타일 | ["캐주얼", "스트릿"] |
| shot_type | 사진 유형 | "모델착용샷", "단독샷", "행거샷", "기타" |
| visibility | 상품 가시성 | "양호", "부분가림", "불량" |
| wishlist_count | 찜 수 | 3200 |
| delivery_info | 배송 정보 | "빠른출발", "직진배송" |
| brand_name | 브랜드명 | "무신사 스탠다드" |
