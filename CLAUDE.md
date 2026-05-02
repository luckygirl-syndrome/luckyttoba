# LuckyTtoba — 실험 프로젝트

쇼핑 충동구매 방지 챗봇 "또바"의 핵심 로직을 검증하는 실험 모음.

## 디렉토리

```
data/           크롤링 원본 JSON (무신사·에이블리·지그재그) — 시험 간 공유
shared/         공유 모듈 (S-BTI, 점수 계산, 데이터 로더, 프롬프트 빌더)
images/         테스트 이미지 (Vision 추출용)
docs/           설계 문서 8개 (S-BTI, 점수 공식, 파이프라인 등)
experiments/    시험별 독립 폴더 + PLAN.md(구현 설계) + TODO.md(작업 추적)
```

## 시험 목록

| 번호 | 폴더 | 내용 |
|------|------|------|
| 00 | exp00_vision_extraction | Vision LLM 상품정보 추출 |
| 01 | exp01_vision_accuracy | 추출 정확도 + 마케팅 트리거 (GT 대비) |
| ~~02~~ | ~~exp02_marketing_trigger~~ | ~~시험 1에 흡수 (2026-04-15)~~ |
| 03 | exp03_style_similarity | style_similarity 검증 |
| 04 | exp04_chatbot_ttoba | 또바 대화 품질 |
| 05 | exp05_score_distribution | Impulse/Match Score 분포 & 구간 설계 |

> 진행 상태는 `experiments/TODO.md` 단일 소스로 관리

## 확정 사항

- **LLM**: Gemini 3.1 Flash-Lite (전체 시험 공통)
- **API**: Gemini만 (.env에 GEMINI_API_KEY 설정됨)
- **style_keywords 어휘**: 추출 프롬프트 기준 10종 (심플베이직, 락시크, 힙, 페미닌, 러블리, 모리걸, 빈티지, 스트릿, 캐주얼, 섹시글램)
- **찜 = 좋아요**: 동일 필드로 통합
- **시험 2 → 시험 1 흡수**: 마케팅 트리거는 시험 0 Vision 추출에서 동시 식별, 시험 1에서 100장 GT로 정확도 평가. e5/별도 LLM 비교 폐기
- **시험 3**: 옷 묘사는 시험 0 Vision 추출 실제 데이터 사용

## shared/ 모듈

| 모듈 | 설명 |
|------|------|
| `sbti_types.py` | 16유형 정의, `parse_sbti_flags()` |
| `scoring/impulse.py` | `compute_impulse_score()` |
| `scoring/match.py` | `compute_match_score()`, `_without_style()` |
| `survey_questions.py` | 공통질문 점수 매핑, `get_all_survey_combinations()` |
| `data_loader.py` | 3개 플랫폼 정규화 (한글 숫자 파서 포함) |
| ~~`marketing_detector.py`~~ | ~~키워드 기반 트리거 검출~~ — 폐기, 시험 0 Vision LLM으로 대체 |
| `prompt_builder.py` | system_prompt + context_sentences 빌더 |

## 데이터 주의사항

- **에이블리**: 가격(original_price, sale_price) 없음 → 추가 크롤링 예정
- **지그재그**: 좋아요 기능 없음 → like_count=None 고정
- **무신사**: 한글 혼합 문자열("9.2만", "후기 4,826개") → 파서 필요
- 필드명 플랫폼별 상이 → data_loader.py에서 통일

## 참조

- 전체 구현 설계: `experiments/PLAN.md`
- 작업 추적: `experiments/TODO.md`
- 코딩 규칙: `.claude/rules/coding.md`
- 데이터 규격: `.claude/rules/data-schema.md`
