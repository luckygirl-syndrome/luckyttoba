FBTI_DESCRIPTIONS = {
    "U": "판매량·랭킹·연예인 착용 등 사회적 증거에 강하게 반응. 많은 사람이 검증한 상품에 신뢰를 느낌.",
    "I": "MADE·사장픽·자체제작 등 제품 자체의 가치와 전문가 보증에 반응. 판매량·랭킹보다 품질과 희소한 가치를 중시. 대중적인 것보단 자신만의 특별한 옷을 원함.",
    "T": "유행·이번 시즌 인기·많이 입는 스타일에 반응. 집단 소속감을 통해 만족.",
    "M": "희소성·독특함에 반응. 판매량이 클수록 오히려 매력이 떨어짐. 나만의 스타일을 원함.",
    "E": "품절임박·1+1·증정 등 할인·혜택에 강하게 반응. 얼마나 이득을 봤는가가 구매 만족의 핵심.",
    "O": "할인보다 물건 자체의 품질·디자인·완성도로 판단. MADE·퀄리티 보증에 반응.",
} #유형 설명 

# ─────────────────────────────────────────────
# 1차 호출 프롬프트: 이미지 → JSON 추출 + 마케팅 키워드 + 베이스 점수
# ─────────────────────────────────────────────
EXTRACT_PROMPT = """당신은 쇼핑 스크린샷에서 상품 정보를 추출하는 전문가입니다.
출력 키와 라벨은 반드시 아래 정의 그대로 사용하세요. JSON만 응답.

## 핵심 원칙

1. **명시 vs 추론을 구분.** 추론 필드(category, color, fit, style_keywords)는 시각·문맥으로 채움. 그 외는 화면에 명시된 정보만 — 추측 금지.
2. **확실하지 않으면 보수적으로** — 단, **양호/0 쪽으로 보수적**. 즉 마케팅 트리거는 0이 default, visibility는 양호가 default.
3. **숫자는 단위 제거**. 한글 단위 변환: "9.2만"→92000, "1.4천"→1400, "5K"→5000. 0과 null 구분 (실제 0이면 0, 정보 없으면 null).
4. **쿠폰가/회원가는 모두 무시.** 일반 모든 사용자에게 적용되는 메인 할인만 인식.

## 필드

1. **product_name** (string|null): 상품명 (마케팅 괄호 포함 원문)
2. **original_price** (number|null): 원가
3. **has_discount** (0|1): 메인 할인 표시(취소선 원가+할인가, 또는 할인율 빨간 강조)가 있을 때만 1. 쿠폰가만 있으면 0.
4. **discounted_price** (number|null): 메인 할인가. 메인 할인 없으면 null.
5. **discount_rate** (number|null): 할인율(%). discounted_price와 동일 기준.
6. **review_count** (number|null): 리뷰 수. 화면에 안 보이면 null.
7. **review_score** (number|null): 평점 0~5. 화면에 명시 없으면 null. (100점 만점이면 5점 만점으로 변환)
8. **shot_type** (string|null): 다음 4개 중 정확히 하나
    - "모델착용샷": 사람이 착용
    - "단독샷": 흰/단색 배경에서 옷만 단독
    - "행거샷": 행거/마네킹에 걸린 사진
    - "기타": 디테일컷·합성·광고
9. **visibility** (string|null): 옷 자체만 평가. 배경·소품·워터마크 무시.
    - **"양호" (default)**: 전반적인 실루엣과 주요 디자인 파악 가능. 모서리 5%↓ 잘림, 자연스러운 접힘, 작은 가림 허용. **확실하지 않으면 양호.**
    - "부분가림": 디자인 포인트(넥라인·포켓·패턴)가 확실히 안 보일 때만. 면적 10~40% 가림 또는 1/4 이상 크롭.
    - "불량": 면적 40% 이상 가림, 디테일컷만, 역광/과노출.
    - 엣지: 뒷면컷=양호, 행거 자연 접힘=양호, UI 겹침=부분가림.
10. **delivery_fee** (string|null): 배송 방식·비용 (예: "무료배송", "빠른출발", "유료 3,000원")
11. **brand** (string|null): 브랜드/스토어명 (상품 카드에 명시된 것만)
12. **category** (string|null): 상품 카테고리 (예: "후드집업", "스커트"). 추론 가능.
13. **color** (string|null): 주요 색상 (추론 가능)
14. **fit** (string|null): 핏/실루엣 — 오버핏/슬림핏/루즈핏/세미오버 등. 상품명에 명시되면 우선, 없으면 시각 추론.

## 마케팅 분석
15. - **product_name에 실제로 있는 텍스트만.** 이미지의 뱃지·배너·플랫폼 UI는 product_name에 없으면 무시.
    - 추출 기준: "이 표현이 없었다면 상품이 덜 매력적으로 보였을까?" → Yes면 추출, No면 제외.
      · 추출 O: 판매량(1만장 이상 명시), 연예인/인플루언서/아이돌 실명 착용 언급, 플랫폼·전문가 보증(MADE/PICK/MD픽/사장픽 등), 희소성(REORDER/품절임박/문의폭주), 구매 욕구 직접 자극(인생핏/핏보장/미친핏 등 품질·핏 보증 표현), **사회적 승인 상황 한정(하객룩/여친룩처럼 "이 옷이면 그 자리에서 통한다"는 보증성 표현 — 단, 단순 장소·용도 태그는 제외)**
      · 추출 X: 옷 설명 일체(소재·색상·핏·실루엣·스타일·시즌·옵션·구성·컬러수·사이즈), **날짜·출고일·입고일(예: 4/1출고, 3월입고)**, 상품 코드·모델명, 이모지 단독, **상황·장소·용도 태그(휴양지룩/여행코디/캠핑룩/출근룩/데이트룩/나들이룩/피크닉룩 등 — 어디서/언제 입는지 설명하는 표현 전부)**, 일반 코디 용어(OO룩 중 판매량·연예인과 무관한 단순 스타일 제안)
    - 없으면 [].

16. **base_score** (integer, 0~100): marketing_keywords만 보고 유저 유형 무관하게 산정한 베이스 충동구매 점수.
    - **marketing_keywords가 []이면 반드시 0. 예외 없음.**
    **스코어링 기준 (키워드가 있을 때만 적용):**
    - 상황·취향 한정 키워드 단독 (하객룩, 핏보장, 미친핏 등): 10~20점
    - 판매량·랭킹 단독 / REORDER 단독: 20~30점
    - 보편 신뢰 키워드 단독 (MADE, PICK, MD픽 등): 25~35점
    - 연예인·인플루언서·아이돌 착용 단독: 35~45점
    - 판매량·랭킹 / 사람 보증 + 다른 키워드 복합: 45~60점
    - 판매량·랭킹 / 강한 키워드 3개 이상 복합: 60~75점
    - 최강 조합 (연예인 착용 + MADE + 판매량): 최대 85점
    - 키워드 과밀(5개↑)·과장 심하면 신뢰도 역전으로 낮게 조정
    - 판매량이 지나치게 크면 식상함으로 반감 고려

## 스타일 일치도
주어진 상품 이미지를 직접 분석하고, 회원의 스타일 선호도와 비교하여 일치도를 백분율로 평가합니다.

【 스타일 키워드 정의 】
심플베이직, 락시크, 힙, 페미닌, 러블리, 모리걸, 빈티지, 스트릿, 캐주얼, 섹시글램

【 회원 선택 스타일 】
{user_styles}

【 작업 순서 】
[Step 1] 이미지 분석 (직관적 평가)
- 상품 이미지에서 느껴지는 전체적인 스타일 무드를 파악
- 색상, 실루엣, 소재, 분위기를 종합적으로 고려
- 회원이 선택한 스타일과의 일치도를 직관적으로 평가

[Step 2] 회원 선택 스타일과의 매칭 분석
- 상품의 전체적인 스타일이 회원 선택 스타일과 얼마나 일치하는지 평가
- 0~100% 사이의 백분율로 표현 (소수점 1자리)
- 예시:
  * 회원이 "락시크" 1개 선택 + 상품이 클래식하고 세련된 라이더 재킷 → 70% 일치
  * 회원이 "힙|스트릿|캐주얼" 3개 선택 + 상품이 카고팬츠 → 85% 일치
  * 회원이 "페미닌|러블리" 선택 + 상품이 캐주얼 스트릿 팬츠 → 10% 일치 (거의 안 맞음)

[Step 3] 근거 작성
- 간단하고 명확한 1~2줄 설명

17. **style_match_percentage**: 0~100 사이의 소수점 1자리 백분율 % (예: 85.0)
18. **style_match_score**: 0~35 사이의 실수 또는 정수 / percentage를 보고 score 도출 (예: 29.8)
19. **style_match_reasoning**: 1~2줄 설명 (예: 가죽 재킷의 세련된 무드와 데님의 캐주얼함, 레오파드 패턴의 힙한 감각이 회원 선택 스타일과 85% 일치합니다.)

## 최종 JSON 출력 형식 (키 순서 고정, JSON만, 마크다운 코드블록 없이)

{{
  "product_name": null,
  "original_price": null,
  "has_discount": 0,
  "discounted_price": null,
  "discount_rate": null,
  "review_count": null,
  "review_score": null,
  "shot_type": null,
  "visibility": null,
  "delivery_fee": null,
  "brand": null,
  "category": null,
  "color": null,
  "fit": null,
  "marketing_keywords": [],
  "base_score": 0,
  "style_match_percentage": 0,
  "style_match_score": 0,
  "style_match_reasoning": null
}}"""

# ─────────────────────────────────────────────
# 2차 호출 프롬프트: 키워드 + 베이스 점수 → 유저별 보정 점수
# ─────────────────────────────────────────────
SCORING_PROMPT_TEMPLATE = """당신은 쇼핑 마케팅 심리 전문가입니다.
아래 마케팅 키워드와 베이스 충동구매 점수만 보고, 유저의 F-BTI 유형에 맞춰 보정한 최종 personalized_score를 산출하세요.
**마케팅 키워드 목록에 있는 표현만 점수 보정에 사용할 것. 키워드 외 다른 정보(상품명·소재·색상·구성 등)는 절대 참고하지 말 것.**
JSON만 응답. 마크다운 코드블록 없이.

## 입력
- 마케팅 키워드: {marketing_keywords}
- 베이스 점수: {base_score}

## 보정 원칙
- 베이스 점수를 출발점으로, 유저 유형에 따라 키워드별 반응을 고려해 가감.
- **보정 폭 제한 (반드시 준수):**
  · 베이스 점수가 0이면 → 모든 유저 0점. 보정 불가.
  · 최대 상승폭: base_score × 0.3 (예: 베이스 15 → 최대 +4, 즉 19점 상한 / 베이스 30 → 최대 +9, 즉 39점 상한)
  · 최대 하락폭: base_score × 0.4 (예: 베이스 15 → 최대 -6, 즉 9점 하한 / 베이스 30 → 최대 -12, 즉 18점 하한)
  · 보정이 미미한 유형(키워드와 무관)은 base_score 그대로 반환.
- 키워드와 유형 간 궁합이 좋으면 상승 보정, 역효과면 하락 보정.
- 각 키워드가 해당 유형에게 왜 긍정/부정인지 맥락을 반드시 고려할 것.
  예: "문의 폭주"는 M형(차별화 지향)에게 거부감 → 하락 보정.
  예: 대규모 판매량은 M형에게 매력 감소 → 하락 보정, U형·T형에게는 신뢰 상승 → 상승 보정.
  예: MADE·MD픽은 I형·O형에게 강한 신뢰 → 상승 보정, E형에게는 중립.
  예: 핏보장·인생핏 같은 핏 보증은 어느 유형에게나 약한 긍정이나, 특정 유형 강점 키워드가 아님 → 소폭 상승 또는 중립.
- 0~100 범위 유지.

## 유저 F-BTI 유형
{user_fbti}

## 출력 형식 (JSON만)
{"personalized_score": 0}
"""

# ─────────────────────────────────────────────
# 실행 코드
# ─────────────────────────────────────────────

import json
import os
import base64
import csv
from pathlib import Path
from typing import Dict, Any, List
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


class AllInputVisionProcessor:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.project_root = self.base_dir.parent.parent
        self.images_dir = self.project_root / "images"
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in .env")

    def get_image_media_type(self, image_path: str) -> str:
        """이미지 파일 확장자에 따른 MIME type 반환"""
        ext = Path(image_path).suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        return media_types.get(ext, "image/jpeg")

    def load_image_as_base64(self, image_path: Path) -> str:
        """이미지를 base64로 인코딩"""
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        with open(image_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")

    def get_all_images_for_image_id(self, image_id: str) -> List[Path]:
        """image_id에 해당하는 폴더의 모든 이미지 파일 반환 (알파벳순 정렬)"""
        image_folder = self.images_dir / image_id
        if not image_folder.exists():
            raise FileNotFoundError(f"Image folder not found: {image_folder}")

        image_files = []
        for ext in ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp"]:
            image_files.extend(image_folder.glob(ext))

        return sorted(image_files)

    def extract_with_gemini(self, image_id: str, user_styles: str) -> Dict[str, Any]:
        """Gemini API를 사용해 모든 이미지를 분석"""
        try:
            # image_id에 해당하는 모든 이미지 로드
            image_paths = self.get_all_images_for_image_id(image_id)
            if not image_paths:
                raise FileNotFoundError(f"No images found for {image_id}")

            # user_styles를 프롬프트에 반영
            prompt = EXTRACT_PROMPT.format(user_styles=user_styles)

            # 프롬프트 + 모든 이미지를 parts에 추가
            parts = [{"text": prompt}]
            for image_path in image_paths:
                image_base64 = self.load_image_as_base64(image_path)
                media_type = self.get_image_media_type(str(image_path))
                parts.append({
                    "inline_data": {
                        "mime_type": media_type,
                        "data": image_base64
                    }
                })

            # Gemini API 호출
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {
                        "parts": parts
                    }
                ]
            }

            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()

            result_data = response.json()
            response_text = result_data["candidates"][0]["content"]["parts"][0]["text"].strip()

            # 디버그: 첫 번째 요청에 대해서만 응답 저장
            if image_id == "etc_outer_001":
                debug_file = Path(__file__).parent / "debug_response.txt"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(response_text)
                print(f"\n[DEBUG] Response saved to {debug_file}")

            # JSON 마크다운 코드블록 제거
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # JSON 객체 추출 (첫 { 부터 마지막 } 까지)
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                response_text = response_text[start_idx:end_idx+1]

            result = json.loads(response_text)
            return result

        except Exception as e:
            print(f"[ERROR] Gemini extraction failed for {image_id}: {e}")
            return None

    def process_test_cases(self, csv_path: str, output_dir: str):
        """test_cases.csv를 읽고 각 case를 처리"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = []
        errors = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 2):  # 헤더 제외
                case_id = row.get('case_id')
                image_id = row.get('image_id')
                user_selected_styles = row.get('user_selected_styles', '')

                print(f"[*] Processing {case_id} ({image_id})...", end=" ", flush=True)

                try:
                    # Gemini API로 이미지 분석
                    result = self.extract_with_gemini(image_id, user_selected_styles)

                    if result:
                        # test_cases.csv의 정보 + 추출 결과 병합
                        merged_result = dict(row)
                        merged_result.update({
                            'product_name_extracted': result.get('product_name'),
                            'original_price': result.get('original_price'),
                            'has_discount': result.get('has_discount'),
                            'discounted_price': result.get('discounted_price'),
                            'discount_rate': result.get('discount_rate'),
                            'review_count': result.get('review_count'),
                            'review_score': result.get('review_score'),
                            'shot_type': result.get('shot_type'),
                            'visibility': result.get('visibility'),
                            'delivery_fee': result.get('delivery_fee'),
                            'brand': result.get('brand'),
                            'category': result.get('category'),
                            'color': result.get('color'),
                            'fit': result.get('fit'),
                            'marketing_keywords': json.dumps(result.get('marketing_keywords', [])),
                            'base_score': result.get('base_score'),
                            'style_match_percentage': result.get('style_match_percentage'),
                            'style_match_score': result.get('style_match_score'),
                            'style_match_reasoning': result.get('style_match_reasoning'),
                        })
                        results.append(merged_result)
                        print("[OK]")
                    else:
                        errors.append((case_id, "Gemini extraction failed"))
                        print("[FAIL]")

                except Exception as e:
                    errors.append((case_id, str(e)))
                    print(f"[FAIL] ({str(e)})")

        # 결과를 CSV로 저장
        if results:
            output_csv_path = output_path / 'output_results_v1.csv'
            fieldnames = list(results[0].keys())

            with open(output_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)

            print(f"\n[OK] 처리 완료: {len(results)}개 case")
            print(f"  - CSV 저장: {output_csv_path}")

        if errors:
            print(f"\n[ERROR] {len(errors)}개 case 실패:")
            for case_id, error in errors:
                print(f"  - {case_id}: {error}")

        return results


def main():
    script_dir = Path(__file__).resolve().parent
    test_cases_csv = script_dir / 'test_cases.csv'
    output_dir = script_dir / 'outputs'

    if not test_cases_csv.exists():
        print(f"[ERROR] test_cases.csv를 찾을 수 없습니다: {test_cases_csv}")
        return

    processor = AllInputVisionProcessor()
    processor.process_test_cases(str(test_cases_csv), str(output_dir))


if __name__ == "__main__":
    main()