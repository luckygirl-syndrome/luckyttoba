# exp07_all_output_json 실험 결과

## 실험 개요
LLM Vision을 이용하여 상품 이미지를 분석하고, 추출된 정보를 기반으로 사용자 맞춤형 context sentences를 생성하는 2단계 파이프라인.

## 실행 완료 (2026-05-16)

### 단계별 실행 현황

#### Step 1: Vision LLM 프롬프트 실행
- **입력**: `test_cases.csv` (60개 케이스)
- **처리**: 각 케이스별로 해당 image_id에 해당하는 폴더에서 모든 이미지(1~N장)을 로드
- **이미지 포맷**: PNG, JPG, JPEG 지원
- **API**: Gemini 3.1 Flash-Lite
- **출력**: `output_results_v1.csv`

**추출된 정보**:
- product_name (상품명)
- original_price, has_discount, discounted_price, discount_rate (가격 정보)
- review_count, review_score (리뷰/평점)
- shot_type, visibility (이미지 특성)
- delivery_fee, brand, category, color, fit (상품 정보)
- marketing_keywords, base_score (마케팅 신호)
- style_match_percentage, style_match_score, style_match_reasoning (스타일 일치도)

#### Step 2: Context Sentences 생성
- **입력**: `output_results_v1.csv` (Step 1 결과)
- **처리**: 각 케이스별로 `build_context_sentences()` 실행
- **모듈**: 리뷰/평점, 가격, 마케팅 신호, 관심도, 발견 경로, 구매점수 등을 통합
- **출력**: 
  - `context_sentences_results.json` (구조화된 JSON)
  - `context_sentences_results.csv` (CSV 포맷)

**생성된 정보**:
- product_info: 상품명, 가격, 특성, 배송, 브랜드 정보
- score_context: 다음 요소들의 문맥화 문장
  - 스타일 일치도 설명
  - 관심도 + 발견 경로
  - 가격 정보 + 사용자 가격 체감
  - 리뷰수 + 평점 (사회적 증거)
  - 마케팅 키워드
  - 구매 연락 이유
  - 충동 점수 + 일치도 점수

## 결과 파일 위치
```
experiments/exp07_all_output_json/outputs/
├── output_results_v1.csv              (43K) - Vision 추출 결과
├── context_sentences_results.json     (79K) - Context Sentences (JSON)
└── context_sentences_results.csv      (65K) - Context Sentences (CSV)
```

## 데이터 통계
- **총 케이스**: 60개
- **포함된 상품**: 10개
- **사용자 그룹**: 6명
- **스타일 선택 다양도**: 1개~10개 스타일 조합

## 테스트된 상품
1. etc_outer_001 (ZARA 가죽재킷) - 6 케이스
2. ably_pants_001 (카고팬츠) - 6 케이스
3. musinsa_pants_001 (체크팬츠) - 6 케이스
4. musinsa_onepiece_001 (드레스) - 6 케이스
5. ably_top_002 (블라우스) - 6 케이스
6. musinsa_bag_004 (마이크로백) - 6 케이스
7. musinsa_onepiece_002 (드레스) - 6 케이스
8. zigzag_outer_004 (가디건) - 6 케이스
9. ably_skirt_0003 (미니스커트) - 6 케이스
10. ably_top_007 (셔츠세트) - 6 케이스

## 주요 기능 검증
✓ 모든 이미지 형식(PNG, JPG, JPEG) 지원
✓ 복수 이미지(1~N장) 동시 처리
✓ 랜덤 이미지명 파싱
✓ Gemini API 호출 성공
✓ JSON 응답 파싱 및 추출
✓ 마케팅 신호 분류
✓ 스타일 일치도 계산
✓ Context sentences 문맥화 생성
✓ 점수 계산 (Impulse + Match Score)

## 실행 명령어
```bash
cd experiments/exp07_all_output_json
python run_exp07.py
```

## 환경 요구사항
- Python 3.7+
- dotenv (`.env`에서 `GEMINI_API_KEY` 로드)
- requests
- pathlib

## 다음 단계 (필요시)
- 결과 검증 (정확도 평가)
- 마케팅 신호 재분류 검토
- Context sentences 품질 개선
- 점수 알고리즘 튜닝
