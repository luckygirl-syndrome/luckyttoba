# ==============================================
# 또바 Context Sentences Builder
# ==============================================
# context_sentences는 "이 상품 × 이 유저" 조합에 특화된 동적 맥락이다.
# system_prompt에서 이미 유저 성향을 설명했으므로,
# 여기서는 유형 언급 없이 팩트 전달만 한다.
# ==============================================

from typing import Optional, List

__all__ = ['build_context_sentences']

# --- 독립 함수 ---

def get_review_context(review_count):
    if review_count is None or review_count == 0:
        return None
    elif review_count <= 10:
        return f"리뷰 수는 {review_count}개로 구매자 의견이 적은 편입니다."
    elif review_count <= 100:
        return f"리뷰 수는 {review_count}개로 어느 정도 검증되고 있습니다."
    elif review_count <= 1000:
        return f"리뷰 수는 {review_count:,}개로 충분히 검증된 상품입니다."
    else:
        return f"리뷰 수는 {review_count:,}개로 많은 구매자의 의견을 참고할 수 있습니다."


def get_marketing_context(marketing_keywords):
    """마케팅 키워드 목록을 문장화. ai_prompt.py의 marketing_keywords 기반."""
    if not marketing_keywords:
        return ""
    return f"상품명에 '{', '.join(marketing_keywords)}' 같은 마케팅 표현이 있습니다."

# --- 연관 피쳐 묶음 함수 ---

def get_social_proof_context(review_count, rating):
    """리뷰수 + 평점 묶음 — 사회적 증거 통합"""
    parts = []

    # 리뷰수
    if review_count is not None and review_count > 0:
        parts.append(get_review_context(review_count))
    else:
        parts.append("리뷰가 없어 아직 검증이 되지 않은 상품입니다.")

    # 평점 (리뷰가 있을 때만 의미 있음)
    if rating is not None and review_count is not None and review_count > 0:
        if rating >= 4.7:
            rating_desc = "매우 높습니다"
        elif rating >= 4.3:
            rating_desc = "높은 편입니다"
        elif rating >= 3.5:
            rating_desc = "평균 수준입니다"
        else:
            rating_desc = "낮은 편입니다"
        parts.append(f"평점은 {rating}점으로 {rating_desc}.")

    return " ".join(parts)

def get_price_full_context(original_price, discounted_price, discount_rate, price_feeling):
    """가격 정보 + 유저 가격 체감 묶음"""

    # 가격 정보 파트
    if discount_rate is None or discount_rate == 0:
        price_part = f"{original_price:,}원으로 할인 없이 정가 판매 중입니다."
    elif discount_rate <= 20:
        price_part = (
            f"{original_price:,}원짜리 상품이 {discount_rate}% 할인되어 "
            f"{discounted_price:,}원에 판매 중입니다. 가벼운 할인 자극이 있습니다."
        )
    elif discount_rate <= 50:
        price_part = (
            f"{original_price:,}원짜리 상품이 {discount_rate}% 할인되어 "
            f"{discounted_price:,}원에 판매 중입니다. 충동 구매 자극이 강한 구간입니다."
        )
    elif discount_rate <= 70:
        price_part = (
            f"{original_price:,}원짜리 상품이 {discount_rate}% 할인되어 "
            f"{discounted_price:,}원에 판매 중입니다. "
            f"할인율이 높은 편으로, 원가 책정 방식을 확인해보는 게 좋을 수 있습니다."
        )
    else:
        price_part = (
            f"{original_price:,}원짜리 상품이 {discount_rate}% 할인되어 "
            f"{discounted_price:,}원에 판매 중입니다. "
            f"할인율이 매우 높아 원가가 부풀려졌을 가능성이 있습니다."
        )

    # 유저 체감 파트
    feeling_mapping = {
        "저렴한 것 같아요": "유저는 이 가격이 저렴하다고 느끼고 있습니다.",
        "이 정도면 괜찮아요": "유저는 이 가격이 적당하다고 느끼고 있습니다.",
        "좀 비싸긴 한데 못 살 정도는 아니에요": "유저는 이 가격이 다소 비싸다고 느끼고 있습니다.",
        "상품은 마음에 들지만 가격이 비싸요": "유저는 이 가격이 많이 비싸다고 느끼고 있습니다.",
    }
    feeling_part = feeling_mapping.get(price_feeling, None)

    if feeling_part:
        return f"{price_part} {feeling_part}"
    return price_part

def get_interest_discovery_context(interest, discovery):
    """관심 지속도 + 발견 경로 묶음 — 관심의 맥락 통합"""
    discovery_mapping = {
        "쇼핑 앱에서 카테고리 검색 후 찾아보다 발견했어요": "직접 검색해서 찾아낸",
        "유튜버/인플루언서가 입은 것을 봤어요": "인플루언서를 통해 접한",
        "쇼핑 앱에서 랭킹이나 유저 추천을 둘러보다 발견했어요": "쇼핑 앱 추천으로 발견한",
        "인스타/틱톡/X 같은 SNS 보다가 발견했어요": "SNS를 보다가 수동적으로 노출된",
        "브랜드 계정에 신상이 추가된 걸 봤어요": "팔로우 중인 브랜드 신상으로 알게 된",
    }
    interest_mapping = {
        "오늘 처음 봤어요": "오늘 처음 본 상태입니다.",
        "2~3일 됐어요": "2~3일 전부터 눈여겨보고 있는 상태입니다.",
        "1주일 정도 됐어요": "약 1주일 전부터 관심을 두고 있는 상태입니다.",
        "2주 이상 고민했어요": "2주 이상 오래 고민하고 있는 상태입니다.",
    }

    discovery_str = discovery_mapping.get(discovery, "발견한")
    interest_str = interest_mapping.get(interest, "관심을 두고 있는 상태입니다.")

    return f"{discovery_str} 상품으로, {interest_str}"

# --- 연락 이유 (상품별로 매번 달라지므로 context_sentences에 포함) ---

def get_contact_reason_context(contact_reason):
    """공통 질문 중 '저한테 어떤 이유로 연락했어요?' 응답"""
    mapping = {
        "이미 마음은 정했는데 마지막으로 한 번만 봐줘요": "유저는 이미 마음을 거의 정한 상태로, 마지막 확인을 원하고 있습니다.",
        "그냥 이 옷 어떤가 궁금해서요": "유저는 가벼운 궁금증으로 찾아왔고, 아직 구매 의향이 뚜렷하지 않습니다.",
        "오래 고민했는데 결정이 안 나서요": "유저는 오래 고민했지만 결정을 못 내리고 있어, 판단 근거 정리를 필요로 합니다.",
    }
    return mapping.get(contact_reason, "연락 이유 정보가 없습니다.")

# ==============================================
# Context Sentences 조립
# ==============================================

def build_context_sentences(
    # 상품 기본 정보 (Vision 추출)
    product_name: str,
    original_price: int,
    discounted_price: Optional[int],
    discount_rate: Optional[int],
    product_description: str,       # "블랙 미니스커트, 언밸런스 헴라인, 루즈핏, ..."
    shipping_info: Optional[str] = None,
    brand_name: Optional[str] = None,

    # 사회적 증거 (Vision 추출)
    review_count: Optional[int] = None,
    rating: Optional[float] = None,

    # 마케팅 시그널 (Vision 추출에서 분류)
    marketing_keywords: Optional[List[str]] = None,

    # 공통 질문 응답
    interest: Optional[str] = None,        # "오늘 처음 봤어요" 등
    discovery: Optional[str] = None,       # "SNS 보다가 발견했어요" 등
    price_feeling: Optional[str] = None,   # "이 정도면 괜찮아요" 등
    contact_reason: Optional[str] = None,  # "오래 고민했는데 결정이 안 나서요" 등

    # style_similarity LLM 결과
    style_context: Optional[str] = None,

    # 점수 정보
    impulse_score: Optional[int] = None,   # 충동구매 점수 (0~100)
    match_score: Optional[int] = None,     # 매칭 점수 (0~100)

    # 사용자 정보
    user_type: Optional[str] = None,
    user_age: Optional[str] = None,
    user_style_tags: Optional[List[str]] = None,
    user_regret_frequency: Optional[str] = None,
    user_regret_reason: Optional[List[str]] = None,
) -> dict:

    # --- product_info ---
    product_info = [
        f"상품명: {product_name}",
    ]

    # 가격 한줄 요약
    if discount_rate and discount_rate > 0:
        product_info.append(
            f"가격: {original_price:,}원 → {discounted_price:,}원 ({discount_rate}% 할인)"
        )
    else:
        product_info.append(f"가격: {original_price:,}원 (정가)")

    product_info.append(f"상품 특성: {product_description}")

    # 촬영 유형 및 옷 가시성
    product_info.append("촬영 유형: 모델착용샷")
    product_info.append("옷 가시성: 양호")

    # 배송 / 브랜드 (있을 경우만)
    extras = []
    if shipping_info:
        extras.append(f"배송: {shipping_info}")
    if brand_name:
        extras.append(f"브랜드: {brand_name}")
    if extras:
        product_info.append(" / ".join(extras))

    # --- score_context ---
    score_context = [x for x in [
        style_context,
        get_interest_discovery_context(interest, discovery) if interest and discovery else None,
        get_price_full_context(original_price, discounted_price, discount_rate, price_feeling),
        get_social_proof_context(review_count, rating),
        get_marketing_context(marketing_keywords),
        get_contact_reason_context(contact_reason) if contact_reason else None,
        f"이 상품이 유저에게 주는 충동 점수는 {impulse_score}점이고 유저의 취향과 일치하는 점수는 {match_score}점입니다." if impulse_score is not None and match_score is not None else None,
    ] if x]

    # --- user_info ---
    user_info = {}
    if user_type:
        user_info["type"] = user_type
    if user_age:
        user_info["age"] = user_age
    if user_style_tags:
        user_info["style_tags"] = user_style_tags
    if user_regret_frequency:
        user_info["regret_frequency"] = user_regret_frequency
    if user_regret_reason:
        user_info["regret_reason"] = user_regret_reason

    return {
        "product_info": product_info,
        "score_context": score_context,
        "user_info": user_info,
    }

# ==============================================
# CSV 처리 및 결과 저장
# ==============================================

def process_all_results_csv(csv_path, output_dir):
    """all_results.csv를 읽고 각 행에 대해 build_context_sentences()를 실행"""
    import csv
    import json
    import sys
    from pathlib import Path

    # shared 모듈 임포트
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from shared.scoring.impulse import compute_impulse_score
    from shared.scoring.match import compute_match_score
    from shared.survey_questions import PRICE_REASONABLE, INTEREST_PERSISTENCE, DISCOVERY_STABILITY

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 사용자별 후회 정보 매핑
    regret_mapping = {
        "u_001": {"frequency": "없어요", "reasons": []},
        "u_002": {"frequency": "1~2번 정도", "reasons": ["비슷한 옷이 이미 있었어요", "핏이 예상과 달랐어요"]},
        "u_003": {"frequency": "3번 이상", "reasons": ["사진이랑 실물이 너무 달랐어요", "소재나 퀄리티가 기대 이하였어요"]},
        "u_004": {"frequency": "1~2번 정도", "reasons": ["할인이나 한정 특가에 급하게 결제했어요"]},
        "u_005": {"frequency": "없어요", "reasons": []},
        "u_006": {"frequency": "1~2번 정도", "reasons": ["막상 입을 일이 없었어요", "코디할 다른 옷이 없어서 결국 못 입었어요"]},
    }

    results = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            try:
                # CSV 데이터 파싱
                original_price = int(float(row.get('original_price', 0) or 0))
                discounted_price = row.get('discounted_price')
                discounted_price = int(float(discounted_price)) if discounted_price and discounted_price.strip() else None

                discount_rate = row.get('discount_rate')
                discount_rate = int(float(discount_rate)) if discount_rate and discount_rate.strip() else None

                review_count = row.get('review_count')
                review_count = int(float(review_count)) if review_count and review_count.strip() else None

                rating = row.get('review_score')
                rating = float(rating) if rating and rating.strip() else None

                # product_description: color + fit + category
                color = row.get('color', '')
                fit = row.get('fit', '')
                category = row.get('category', '')
                parts = [p for p in [color, fit, category] if p]
                product_description = ", ".join(parts) if parts else "상품 정보"

                # marketing_keywords 파싱 (JSON 형식의 리스트)
                marketing_str = row.get('marketing_keywords', '[]')
                try:
                    marketing_keywords = json.loads(marketing_str)
                except:
                    marketing_keywords = []

                # 점수 정보
                base_score = row.get('base_score')
                base_score = int(float(base_score)) if base_score and str(base_score).strip() else 0

                style_match_score_raw = row.get('style_match_score')
                style_match_score_raw = float(style_match_score_raw) if style_match_score_raw and str(style_match_score_raw).strip() else 0
                
                # Survey 응답 읽기
                price_feeling = row.get('price_feeling')
                interest = row.get('interest')
                discovery = row.get('discovery')
                user_id = row.get('user_id')
                user_type = row.get('user_type')
                age = row.get('age')

                # user_selected_styles를 리스트로 파싱
                user_selected_styles_str = row.get('user_selected_styles', '')
                user_style_tags = [s.strip() for s in user_selected_styles_str.split('|')] if user_selected_styles_str else []

                # 후회 정보 가져오기
                regret_info = regret_mapping.get(user_id, {"frequency": "없어요", "reasons": []})

                # Survey 응답에 따라 점수 계산
                price_reasonable = PRICE_REASONABLE.get(price_feeling, 0) if price_feeling else 0
                interest_persistence = INTEREST_PERSISTENCE.get(interest, 0) if interest else 0
                discovery_stability = DISCOVERY_STABILITY.get(discovery, 0) if discovery else 0

                # Impulse Score 계산
                try:
                    impulse_score = compute_impulse_score(
                        discount_rate=discount_rate or 0,
                        review_count=review_count or 0,
                        rating=rating or 3.0,
                        personalized_score=base_score,
                        is_D=False, is_N=False,
                        is_U=False, is_I=False,
                        is_T=False, is_M=False,
                        is_E=False, is_O=False,
                        platform="default",
                    )
                except Exception as e:
                    print(f"  Impulse Score 계산 실패 (Row {i}): {e}")
                    impulse_score = None

                # Match Score 계산
                try:
                    match_score = compute_match_score(
                        style_match_score=style_match_score_raw,
                        price_reasonable=price_reasonable,
                        interest_persistence=interest_persistence,
                        discovery_stability=discovery_stability,
                    )
                except Exception as e:
                    print(f"  Match Score 계산 실패 (Row {i}): {e}")
                    match_score = None

                # build_context_sentences 실행
                result = build_context_sentences(
                    product_name=row.get('product_name_extracted', ''),
                    original_price=original_price,
                    discounted_price=discounted_price,
                    discount_rate=discount_rate,
                    product_description=product_description,
                    shipping_info=row.get('delivery_fee'),
                    brand_name=row.get('brand'),
                    review_count=review_count,
                    rating=rating,
                    marketing_keywords=marketing_keywords,
                    interest=interest,
                    discovery=discovery,
                    price_feeling=price_feeling,
                    contact_reason=row.get('contact_reason'),
                    style_context=row.get('style_match_reasoning'),
                    impulse_score=impulse_score,
                    match_score=match_score,
                    user_type=user_type,
                    user_age=age,
                    user_style_tags=user_style_tags,
                    user_regret_frequency=regret_info["frequency"],
                    user_regret_reason=regret_info["reasons"],
                )

                # 결과에 case_id 추가
                result['case_id'] = row.get('case_id')
                result['user_id'] = row.get('user_id')
                result['style_match_score'] = row.get('style_match_score')

                results.append(result)

            except Exception as e:
                print(f"Row {i} 처리 중 오류: {e}")
                continue

    # 결과를 JSON과 CSV로 저장
    json_output_path = Path(output_dir) / 'context_sentences_results.json'
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # CSV로도 저장
    csv_output_path = Path(output_dir) / 'context_sentences_results.csv'
    if results:
        import csv as csv_module
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['case_id', 'user_id', 'style_match_score', 'product_info', 'score_context', 'user_info']
            writer = csv_module.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow({
                    'case_id': result['case_id'],
                    'user_id': result['user_id'],
                    'style_match_score': result['style_match_score'],
                    'product_info': ' | '.join(result['product_info']),
                    'score_context': ' | '.join(result['score_context']),
                    'user_info': json.dumps(result['user_info'], ensure_ascii=False),
                })

    print(f"[OK] 처리 완료: {len(results)}개 행")
    print(f"  - JSON 저장: {json_output_path}")
    print(f"  - CSV 저장: {csv_output_path}")

    return results


# ==============================================
# 실행
# ==============================================

if __name__ == "__main__":
    from pathlib import Path

    # all_results_v1.csv 경로 (절대 경로)
    script_dir = Path(__file__).resolve().parent
    csv_path = script_dir / 'outputs' / 'output_results_v1.csv'

    # 출력 디렉토리
    output_dir = script_dir / 'outputs'

    print(f"CSV 경로: {csv_path}")
    print(f"출력 디렉토리: {output_dir}")

    if not csv_path.exists():
        print(f"[ERROR] CSV 파일을 찾을 수 없습니다: {csv_path}")
    else:
        process_all_results_csv(str(csv_path), str(output_dir))