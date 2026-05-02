LLM은 숫자보다 맥락 있는 문장을 더 잘 처리하므로, 단순히 점수와 코드를 넘기는 게 아니라 **줄글 + 맥락**으로 전달한다.

| 구성 요소 | 역할 | 성격 |
| --- | --- | --- |
| `system_prompt` | 또바 캐릭터 설명 + 유저 S-BTI 설명 + 기초 질문 + 공통 질문 일부 | 정적 (요청마다 유저 성향만 동적으로 조합) |
| `context_sentences` | 상품 + 유저 조합에 특화된 맥락 | 동적 (매 요청마다 새로 생성) |

# system_prompt

- 또바 캐릭터 설명 + 유저 SBTI 설명 + 기초 질문 & 공통 질문 일부

- 프롬프트 생성 코드
    
    ```python
    # ==============================================
    # 또바 System Prompt Builder
    # ==============================================
    
    # --- 또바 캐릭터 설명 (정적) ---
    CHARACTER = """
    너는 또바야. 유저가 옷을 사기 직전에 찾아오는 쇼핑 의사결정 AI야.
    
    네 역할은 "이 옷, 진짜 너한테 맞는 선택이야?"를 함께 점검해주는 거야.
    무조건 말리는 것도, 무조건 밀어주는 것도 아니야.
    유저의 쇼핑 성향, 이 옷의 상품 정보, 지금 심리 상태 등 너가 가지고 있는 정보를 종합해서 유저가 스스로 납득할 수 있는 판단을 내리도록 도와줘.
    
    말투는 반말이야. 친구처럼 편하게, 근데 할 말은 해.
    - 데이터에 근거가 있으면 돌려 말하지 말고 직접적으로 짚어
    - 유저가 듣기 불편할 수 있는 지적도 피하지 마. 단, 깎아내리지는 마
    """.strip()
    
    # --- 축 단위 설명 (8개) ---
    SBTI_DESCRIPTIONS = {
        "D": "쇼핑 자체가 즐겁고 흥분된다. '지금 사고 싶다'는 충동이 강하고, 마케팅 문구와 할인에 감정적으로 반응한다.",
        "N": "'지금 나한테 필요한가?'가 먼저다. 광고나 유행에 잘 안 흔들리고, 필요하다고 판단하면 빠르게 결정한다.",
        "U": "구매 이유를 남들에게서 찾는다. 리뷰 수, 평점이 높을수록 '믿을 수 있다'는 확신이 생긴다.",
        "I": "구매 이유를 스스로 판단한다. 리뷰 수보다 소재, 핏, 품질을 직접 따져보고 결정한다.",
        "T": "'요즘 유행이야'라는 사실 자체가 관심의 시작이다. 랭킹·인기 문구에 끌리고, 많은 사람이 입는 스타일에서 소속감을 느낀다.",
        "M": "유행을 따르기보다 내 취향대로 입고 싶어한다. 대중적인 것보다 희소하고 독특한 아이템에 끌리며, 많이 입기 시작하면 흥미가 줄어든다.",
        "E": "기준 가격 대비 얼마나 이득을 봤는가가 구매 만족의 핵심이다. 할인이 없으면 같은 물건도 덜 만족스럽게 느낀다.",
        "O": "물건 자체의 품질, 활용성, 디자인 완성도로 구매를 판단한다. 할인이 없어도 '이 옷이 나한테 맞다'면 정가에 살 수 있다.",
    }
    
    # --- 긴장 관계 (2개) ---
    TENSION_DESCRIPTIONS = {
        "UM": "단, 남들과 똑같은 건 싫지만 완전히 혼자 판단하기보다는 '취향 좋은 소수'의 검증을 신뢰한다. 리뷰가 너무 많으면 오히려 흥미를 잃는다.",
        "IT": "단, 후보군은 유행 안에서 찾지만 최종 선택은 자기 기준으로 깐깐하게 검토한다.",
    }
    
    # --- 유형 한줄소개 (16개) ---
    TYPE_SUMMARIES = {
        "DUTE": "🐷 신나는 돼지 — 쇼핑이 곧 나의 엔터테인먼트",
        "DUTO": "🐒 호기심 많은 원숭이 — 유행은 따라가는 게 맞지",
        "DUME": "🦝 민첩한 미어캣 — 어디서 샀냐는 질문이 내 쇼핑의 원동력",
        "DUMO": "🦔 깐깐한 고슴도치 — 검증됐어도 내 취향 아니면 패스야",
        "DITE": "🐱 고집 센 고양이 — 유행이라니까 구경은 하는데, 결제는 내 맘이야",
        "DITO": "🦚 화려한 공작 — 내가 입으면 트렌드가 돼",
        "DIME": "🐸 엉뚱한 개구리 — 남들은 몰라보는 나만의 패션 세계관",
        "DIMO": "🦢 까다로운 백조 — 범접할 수 없는 안목, 옷장은 나의 컬렉션",
        "NUTE": "🐹 부지런한 햄스터 — 필요한 거, 검증된 퀄리티, 제일 싸게",
        "NUTO": "🐻 우직한 곰 — 검증된 스테디템, 하나를 사도 제대로",
        "NUME": "🐇 예리한 토끼 — 남들 모를 때 이미 찾아냈어",
        "NUMO": "🐢 느긋한 거북이 — 느려도 확실하게, 10년 입을 옷만 골라",
        "NITE": "🐆 직진하는 치타 — 필요한 건 망설임 없이, 오차 없는 선택",
        "NITO": "🐿️ 꼼꼼한 다람쥐 — 하나를 사도 코디까지 계산하는 철저함",
        "NIME": "🦊 영리한 여우 — 진짜 꿀매는 내가 직접 발굴해",
        "NIMO": "🦛 여유로운 카피바라 — 지름신도 비껴가는 무소유의 안목",
    }
    
    # --- 유형 상세 설명 (16개) ---
    TYPE_DETAILS = {
        "DUTE": "유행을 따르고, 리뷰로 확신을 얻고, 할인에 심장이 뛴다. 딱히 살 게 없어도 쇼핑몰을 열면 사고 싶은 게 생기고, 구매 버튼을 누르는 순간이 가장 설렌다. '다들 좋다더라'는 분위기에서 확신을 얻고, 거기에 득템 감각까지 붙으면 즐거움이 배가된다.",
        "DUTO": "유행을 흡수하는 속도가 빠르고, 타인의 검증이 구매의 든든한 근거가 된다. 무조건 싼 것보다는 퀄리티를 중시하지만, 트렌드를 놓치고 싶지 않은 마음이 늘 앞선다.",
        "DUME": "남들 반응을 슬쩍 참고하면서도, 많은 사람이 입기 시작하면 흥미가 뚝 떨어진다. 아무도 모르는 브랜드를 먼저 발굴했을 때의 쾌감이 크고, 딱히 살 게 없어도 예쁜 옷을 발견하면 손이 먼저 간다.",
        "DUMO": "타인의 안목을 참고하되 대중과는 다른 길을 간다. 리뷰 수가 많은 건 관심 없고, 아는 사람만 아는 곳의 호평을 참고한다. 최종적으로는 자기 취향과 물건 자체의 가치가 맞아야만 움직인다. 할인보다 '이건 진짜 제값한다'는 확신이 더 중요하다.",
        "DITE": "요즘 유행하는 아이템에 눈길은 가지만, 최종 결정은 어디까지나 자기 감각이다. 필요 이상으로 비싸게 사는 건 싫어서, 마음에 드는 트렌드 아이템이 보이면 타이밍과 조건도 함께 따진다. 유행 안에서 움직이되, 결론은 늘 자기 중심적이다.",
        "DITO": "유행을 따르지만 자기 심미안으로 재해석한다. 트렌드 안에서 무엇이 뜨는지는 알고 있지만, 결국 중요한 건 '다들 입으니까'가 아니라 '내 스타일에 맞으니까'다. 할인보다는 핏, 소재, 무드, 전체 스타일링의 완성도를 중시하고, 트렌드 아이템도 자기 방식으로 소화해야 만족한다.",
        "DIME": "남의 평가도 필요 없고, 대중적인 것도 딱히 끌리지 않는다. 자신만의 루트로 아무도 모르는 브랜드를 발굴하고, 내 취향에 맞으면 그걸로 충분하다. 거기에 가격까지 좋으면 혼자만 아는 보물을 발견한 듯 더 즐거워진다.",
        "DIMO": "남의 말보다 자기 안목을 더 신뢰하고, 흔한 것보다는 오래 남을 취향과 가치 있는 디테일을 모은다. 대중 브랜드는 거의 입지 않고, 소재와 핏에 대한 기준이 매우 높으며, 옷장 자체가 하나의 컬렉션이다.",
        "NUTE": "살 이유가 분명해야 움직인다. 필요하다 싶으면 리뷰와 가격 비교를 통해 가장 안전하고 합리적인 선택을 만들어낸다. 유행도 참고하지만, 결국 중요한 건 검증된 물건을 가장 합리적인 조건으로 사는 것이다.",
        "NUTO": "살 게 생기면 타인의 검증으로 품질을 체크하며, 가격보다는 물건 자체의 가치에 투자한다. 트렌드를 참고하되 오래 입을 수 있는지가 항상 최우선이다. 여러 번 사기보다 제대로 된 것 하나에 투자하는 것이 쇼핑 철학이다.",
        "NUME": "필요가 생기면 탐색을 시작하는데, 너무 대중적인 건 자연스럽게 걸러진다. 검증은 되어 있으면서도 아직 많이 알려지지 않은 것을 찾아내는 안목이 있다. 남들보다 먼저 발견한 옷에서 특별한 만족을 느낀다.",
        "NUMO": "서두르지 않지만, 한번 고른 건 오래 간다. 살 이유가 분명해야 하고, 남들이 좋다고 하는 최소한의 신뢰도는 확인한 뒤에야 자기 취향과 기준으로 다시 걸러낸다. 빠른 유행보다 오래가는 가치를 중시하고, 구매 결정이 느린 만큼 후회도 거의 없다.",
        "NITE": "필요한 것이 생기면 빠르게 목표를 정하고 가장 효율적인 경로로 움직인다. 트렌드를 참고하되, 최종 판단은 철저히 자기 감각으로 내린다. 마음에 들면 망설이기보다 가장 유리한 타이밍과 조건을 포착해 깔끔하게 끝낸다.",
        "NITO": "눈앞의 예쁜 한 벌보다, 옷장 속 전체 조합을 먼저 떠올린다. 유행하는 아이템이라도 내 옷장 속 옷들과 어울리지 않으면 아무리 예뻐도 패스한다. 활용도, 소재, 조합, 옷장 궁합까지 하나하나 따져보고, 나만의 질서 안에서 가치 있는 것만 골라낸다.",
        "NIME": "남이 깔아준 길보다, 직접 더 좋은 길을 찾아내는 타입이다. 타인의 검증 없이 자기 눈으로만 판단하며, 대중이 모르는 것을 찾아낸다. 광고나 리뷰보다 직접 탐색하는 것을 신뢰하고, 합리적인 가격까지 챙긴다.",
        "NIMO": "외부 자극에 가장 덜 흔들리는 타입이다. 네 가지가 모두 맞아야 구매한다 — 살 게 명확히 있고, 자신의 안목에 맞고, 차별화된 취향에 부합하고, 물건 자체의 가치가 있어야 한다. 충동구매와 가장 멀고, 사는 횟수는 적지만 만족도는 오래 간다.",
    }
    
    # --- 축 구분 가이드 (또바 판단용) ---
    CONFUSION_GUIDE = """
    [축 구분 가이드 — 유저 심리를 짚을 때 헷갈리지 않도록]
    
    D vs E 구분:
    - D는 쇼핑 '과정'의 감각적 자극과 흥분이다. "지금 이 순간 사고 싶다"
    - E는 구매 '결과'에서 "내가 유리한 거래를 했다"는 인지적 만족이다. "이 가격이면 안 사면 손해다"
    - 같은 할인 자극이라도 D는 "와 세일이다 신난다"이고, E는 "원래 12만원인데 5만원이면 이득이다"이다.
    
    U/I vs T/M 구분:
    - U와 I는 '최종적으로 무엇을 믿고 결정하는가'의 축이다.
      - U: "사도 괜찮은 이유"를 남들이 준다
      - I: "사도 괜찮은 이유"를 내가 판단한다
    - T와 M은 '처음에 무엇에 끌리고 어떤 방향으로 관심이 가는가'의 축이다.
      - T: "무엇을 볼지"를 유행이 정해준다
      - M: "무엇을 볼지"를 차별화 욕구가 정해준다
    """.strip()
    
    # ==============================================
    # System Prompt 조립
    # ==============================================
    
    def build_system_prompt(
        user_type: str,
        age: str,
        style_tags: list[str],
        regret_frequency: str,
        regret_reasons: list[str] | None = None,
        liked_purchases: str | None = None,
    ) -> str:
        """
        Parameters
        ----------
        user_type : 4글자 S-BTI 코드 (예: "DUTE")
        age : "10대" | "20~24" | "25~29" | "30대 이상"
        style_tags : 유저가 선택한 스타일 태그 리스트
        regret_frequency : "없어요" | "1~2번 정도" | "3번 이상"
        regret_reasons : 후회 이유 리스트 (regret_frequency가 "없어요"면 None)
        liked_purchases : 만족 구매 스크린샷의 Vision 추출 텍스트 (선택, 없으면 None)
        """
        user_axes = list(user_type)
    
        # --- 축별 특성 ---
        sbti_context = "\n".join([
            f"- {axis}형: {SBTI_DESCRIPTIONS[axis]}"
            for axis in user_axes
        ])
    
        # --- 긴장 관계 ---
        tension_lines = []
        if "U" in user_axes and "M" in user_axes:
            tension_lines.append(TENSION_DESCRIPTIONS["UM"])
        if "I" in user_axes and "T" in user_axes:
            tension_lines.append(TENSION_DESCRIPTIONS["IT"])
        tension_block = "\n".join(tension_lines)
    
        # --- 유저 프로필 ---
        profile_lines = [
            f"- 나이: {age}",
            f"- 선호 스타일: {', '.join(style_tags)}",
        ]
    
        if regret_frequency == "없어요":
            profile_lines.append("- 최근 3개월간 구매 후회 없음")
        else:
            profile_lines.append(f"- 최근 3개월간 구매 후회: {regret_frequency}")
            if regret_reasons:
                reasons_str = ", ".join(regret_reasons)
                profile_lines.append(f"- 주요 후회 이유: {reasons_str}")
    
        if liked_purchases:
            profile_lines.append(f"- 최근 만족한 구매:\n{liked_purchases}")
    
        profile_block = "\n".join(profile_lines)
    
        # --- 조립 ---
        system_prompt = f"""{CHARACTER}
    
    [유저 쇼핑 성향]
    이 유저는 {user_type}형이야. {TYPE_SUMMARIES[user_type]}
    {TYPE_DETAILS[user_type]}
    
    [축별 특성]
    {sbti_context}
    """
    
        if tension_block:
            system_prompt += f"""
    [긴장 관계]
    {tension_block}
    """
    
        system_prompt += f"""
    [유저 프로필]
    {profile_block}
    
    {CONFUSION_GUIDE}
    """
    
        return system_prompt.strip()
    
    # ==============================================
    # 실행 예시
    # ==============================================
    
    if __name__ == "__main__":
        # 예시 1: DUTE, 후회 있음, 만족 구매 없음
        print("=" * 60)
        print("예시 1: DUTE — 후회 있고, 만족 구매 데이터 없음")
        print("=" * 60)
        print(build_system_prompt(
            user_type="DUTE",
            age="20~24",
            style_tags=["편하고 캐주얼한 스타일", "힙하고 개성 있는 스타일"],
            regret_frequency="3번 이상",
            regret_reasons=["할인이나 한정 특가에 급하게 결제했어요", "비슷한 옷이 이미 있었어요"],
        ))
        print()
    
        # 예시 2: NUMO, 후회 없음, 만족 구매 있음
        print("=" * 60)
        print("예시 2: NUMO — 후회 없고, 만족 구매 데이터 있음")
        print("=" * 60)
        print(build_system_prompt(
            user_type="NUMO",
            age="25~29",
            style_tags=["깔끔하고 단정한 스타일"],
            regret_frequency="없어요",
            liked_purchases=(
                "  카테고리: 코트\n"
                "  색상: 블랙\n"
                "  핏/실루엣: 오버핏\n"
                "  스타일 키워드: 미니멀\n"
                "  촬영 유형: 모델 착용샷\n"
                "  옷 가시성: 양호"
            ),
        ))
    ```
    

# context_sentences

- 상품 + 유저 조합에 특화된 맥락
- context_sentences는 두 종류의 데이터로 나뉨
    
    
    | 종류 | 설명 | 예시 |
    | --- | --- | --- |
    | **상품 기본 정보** | 점수 계산과 무관하게 LLM이 알아야 하는 상품 정보 | 상품명, 가격, 이미지 묘사, 배송 |
    | **점수 기반 맥락** | impulse score / match score를 구성하는 요소들 | 할인율, 리뷰수, 가격 체감, 발견 경로 |

- 프롬프트 생성 코드
    
    ```python
    # ==============================================
    # 또바 Context Sentences Builder
    # ==============================================
    # context_sentences는 "이 상품 × 이 유저" 조합에 특화된 동적 맥락이다.
    # system_prompt에서 이미 유저 성향을 설명했으므로,
    # 여기서는 유형 언급 없이 팩트 전달만 한다.
    # ==============================================
    
    # --- 독립 함수 ---
    
    def get_review_context(review_count):
        if review_count is None or review_count == 0:
            return "리뷰가 없어 아직 검증이 되지 않은 상품입니다."
        elif review_count <= 10:
            return f"리뷰가 {review_count}개로 거의 없어 검증이 부족한 상품입니다."
        elif review_count <= 100:
            return f"리뷰가 {review_count}개로 적은 편으로, 소수만 구매한 상품입니다."
        elif review_count <= 1000:
            return f"리뷰가 {review_count}개로 어느 정도 검증된 상품입니다."
        else:
            return f"리뷰가 {review_count:,}개로 많아 이미 대중적으로 알려진 상품입니다."
    
    def get_rating_context(rating):
        if rating is None:
            return "평점 정보가 없습니다."
        elif rating < 3.5:
            return f"평점이 {rating}점으로 낮은 편입니다. 리뷰 내용을 직접 확인해보세요."
        elif rating < 4.3:
            return f"평점이 {rating}점으로 평균 수준입니다."
        elif rating < 4.7:
            return f"평점이 {rating}점으로 높은 편입니다."
        else:
            return f"평점이 {rating}점으로 매우 높습니다."
    
    def get_like_context(like_count):
        if like_count is None or like_count == 0:
            return None  # 찜 데이터 없으면 문장 자체를 생성하지 않음
        elif like_count <= 50:
            return f"찜 수는 {like_count}개로 관심도가 낮은 편입니다."
        elif like_count <= 500:
            return f"찜 수는 {like_count}개로 어느 정도 관심을 받고 있습니다."
        elif like_count <= 3000:
            return f"찜 수는 {like_count:,}개로 관심도가 높은 편입니다."
        else:
            return f"찜 수는 {like_count:,}개로 관심도가 매우 높습니다."
    
    def get_marketing_context(trend_hype, bundle, confidence):
        """마케팅 트리거 문구 감지 결과를 문장화"""
        parts = []
    
        if trend_hype:
            parts.append(f"'{'·'.join(trend_hype)}' 같은 트렌드 강조 문구")
        if bundle:
            parts.append(f"'{'·'.join(bundle)}' 같은 혜택 문구")
        if confidence:
            parts.append(f"'{'·'.join(confidence)}' 같은 신뢰성을 주는 문구")
    
        if not parts:
            return ""  # 마케팅 시그널 없으면 빈값 → 최종 조합에서 자동 제외
    
        return f"상품명에 {', '.join(parts)}가 있습니다."
    
    def get_discount_context(discount_rate):
        if discount_rate is None or discount_rate == 0:
            return "할인 없이 정가로 판매 중입니다."
        elif discount_rate <= 10:
            return f"{discount_rate}% 할인 중으로, 거의 정가에 가깝습니다."
        elif discount_rate <= 20:
            return f"{discount_rate}% 할인 중으로, 가벼운 할인 자극이 있습니다."
        elif discount_rate <= 50:
            return f"{discount_rate}% 할인 중으로, 충동 구매 자극이 강한 구간입니다."
        elif discount_rate <= 70:
            return f"{discount_rate}% 할인율이 높은 편입니다. 옷의 품질 신뢰성이 떨어지기 시작하는 구간입니다."
        else:
            return f"{discount_rate}% 할인율이 매우 큽니다. 원가가 부풀려졌을 가능성이 높습니다."
    
    def get_interest_context(interest):
        mapping = {
            "오늘 처음 봤어요": "오늘 처음 발견한 상품입니다.",
            "2~3일 됐어요": "2~3일 전부터 눈에 들어온 상품입니다.",
            "1주일 정도 됐어요": "약 1주일 전부터 관심을 가져온 상품입니다.",
            "2주 이상 고민했어요": "2주 이상 오래 고민해온 상품입니다.",
        }
        return mapping.get(interest, "관심 지속 기간 정보가 없습니다.")
    
    def get_discovery_context(discovery):
        mapping = {
            "쇼핑 앱에서 카테고리 검색 후 찾아보다 발견했어요": "직접 검색해서 찾아낸 상품입니다.",
            "유튜버/인플루언서가 입은 것을 봤어요": "인플루언서를 통해 접한 상품입니다.",
            "쇼핑 앱에서 랭킹이나 유저 추천을 둘러보다 발견했어요": "쇼핑 앱 추천을 통해 발견한 상품입니다.",
            "인스타/틱톡/X 같은 SNS 보다가 발견했어요": "SNS를 보다가 수동적으로 노출된 상품입니다.",
            "브랜드 계정에 신상이 추가된 걸 봤어요": "팔로우 중인 브랜드의 신상 업데이트로 알게 된 상품입니다.",
        }
        return mapping.get(discovery, "발견 경로 정보가 없습니다.")
    
    # --- 연관 피쳐 묶음 함수 ---
    
    def get_social_proof_context(review_count, rating, like_count=None):
        """리뷰수 + 평점 + 찜 수 묶음 — 사회적 증거 통합"""
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
    
        # 찜 수 (선택 데이터, 있을 때만 추가)
        like_part = get_like_context(like_count)
        if like_part:
            parts.append(like_part)
    
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
        discounted_price: int | None,
        discount_rate: int | None,
        product_description: str,       # "블랙 미니스커트, 언밸런스 헴라인, 루즈핏, ..."
        shipping_info: str | None = None,
        brand_name: str | None = None,
    
        # 사회적 증거 (Vision 추출)
        review_count: int | None = None,
        rating: float | None = None,
        like_count: int | None = None,
    
        # 마케팅 시그널 (Vision 추출에서 분류)
        trend_hype: list[str] | None = None,
        bundle: list[str] | None = None,
        confidence: list[str] | None = None,
    
        # 공통 질문 응답
        interest: str | None = None,        # "오늘 처음 봤어요" 등
        discovery: str | None = None,       # "SNS 보다가 발견했어요" 등
        price_feeling: str | None = None,   # "이 정도면 괜찮아요" 등
        contact_reason: str | None = None,  # "오래 고민했는데 결정이 안 나서요" 등
    
        # style_similarity LLM 결과
        # → Match Score 파이프라인에서 LLM이 style_similarity를 평가할 때
        #   {"score": 28, "reason": "..."} 형태로 반환하는데,
        #   그 중 reason 문자열을 여기에 넣는다.
        #   룰베이스가 아니라 LLM이 생성한 문장이므로 별도 함수 없이 그대로 사용.
        style_context: str | None = None,
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
            get_social_proof_context(review_count, rating, like_count),
            get_marketing_context(trend_hype, bundle, confidence),
            get_contact_reason_context(contact_reason) if contact_reason else None,
        ] if x]
    
        return {
            "product_info": product_info,
            "score_context": score_context,
        }
    
    # ==============================================
    # 실행 예시
    # ==============================================
    
    if __name__ == "__main__":
        import json
    
        result = build_context_sentences(
            product_name="[랭킹1위] 비대칭 언밸런스 블랙 미니스커트 (사장픽)",
            original_price=49000,
            discounted_price=24500,
            discount_rate=50,
            product_description="블랙 미니스커트, 언밸런스 헴라인, 루즈핏, 스트릿/Y2K 스타일, 모델 착용샷, 가시성 양호",
            shipping_info="무료배송",
            brand_name="OOO",
            review_count=3200,
            rating=4.8,
            like_count=8500,
            trend_hype=["랭킹1위"],
            bundle=None,
            confidence=["사장픽"],
            interest="2~3일 됐어요",
            discovery="인스타/틱톡/X 같은 SNS 보다가 발견했어요",
            price_feeling="좀 비싸긴 한데 못 살 정도는 아니에요",
            contact_reason="오래 고민했는데 결정이 안 나서요",
            style_context="유저가 선호하는 힙하고 개성 있는 스타일과 이 옷의 스트릿/Y2K 키워드가 잘 맞습니다.",
        )
    
        print(json.dumps(result, ensure_ascii=False, indent=2))
    ```