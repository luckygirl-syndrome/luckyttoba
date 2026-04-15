# LuckyTtoba

쇼핑 충동구매 방지 챗봇 **"또바"**의 핵심 로직을 검증하는 실험 프로젝트.

## 팀원

| 이름 | 역할 |
|------|------|
| 팜팜이 | 실험 설계, 코드 구현 |
| 경현 | Vision 추출 v1, 실험 검증 |
| 낭연 | GT 라벨링 (스타일 필드) |
| 정현 | GT 라벨링 (스타일 필드) |

## 시험 목록

| 번호 | 폴더 | 내용 |
|------|------|------|
| 00 | `experiments/exp00_vision_extraction` | Vision LLM 상품정보 추출 |
| 01 | `experiments/exp01_vision_accuracy` | 추출 정확도 + 마케팅 트리거 (GT 대비) |
| ~~02~~ | ~~`experiments/exp02_marketing_trigger`~~ | ~~마케팅 트리거 분류~~ → 시험 1에 흡수 |
| 03 | `experiments/exp03_style_similarity` | style_similarity 검증 |
| 04 | `experiments/exp04_chatbot_ttoba` | 또바 대화 품질 |
| 05 | `experiments/exp05_score_distribution` | Impulse/Match Score 분포 & 구간 설계 |

## 디렉토리 구조

```
data/           크롤링 원본 JSON (무신사, 에이블리, 지그재그)
shared/         공유 모듈 (S-BTI, 점수 계산, 데이터 로더, 프롬프트 빌더)
images/         테스트 이미지 (Vision 추출용)
docs/           설계 문서
experiments/    시험별 독립 폴더 + PLAN.md + TODO.md
```

## 시작하기

```bash
pip install -r requirements.txt
cp .env.example .env   # GEMINI_API_KEY 설정
```

## 참고 문서

- 구현 설계: [`experiments/PLAN.md`](experiments/PLAN.md)
- 작업 추적: [`experiments/TODO.md`](experiments/TODO.md)
