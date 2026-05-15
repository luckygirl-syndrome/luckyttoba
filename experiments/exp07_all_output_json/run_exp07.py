#!/usr/bin/env python3
"""
exp07 실험 전체 워크플로우 실행
1. ai_prompt.py: test_cases.csv 기반으로 Vision LLM 프롬프트 실행 (모든 이미지 사용)
2. context_sentences_builder.py: 추출 결과를 바탕으로 context_sentences 생성
"""

import sys
from pathlib import Path

# Script directory
script_dir = Path(__file__).resolve().parent

# Step 1: Run ai_prompt.py
print("=" * 60)
print("[Step 1/2] Vision LLM 프롬프트 실행 (test_cases.csv 처리)")
print("=" * 60)

from ai_prompt import AllInputVisionProcessor

test_cases_csv = script_dir / 'test_cases.csv'
output_dir = script_dir / 'outputs'

if not test_cases_csv.exists():
    print(f"[ERROR] test_cases.csv를 찾을 수 없습니다: {test_cases_csv}")
    sys.exit(1)

processor = AllInputVisionProcessor()
results = processor.process_test_cases(str(test_cases_csv), str(output_dir))

if not results:
    print("[ERROR] Vision 추출 실패")
    sys.exit(1)

print(f"\n[OK] Step 1 완료: {len(results)}개 케이스 처리")

# Step 2: Run context_sentences_builder.py
print("\n" + "=" * 60)
print("[Step 2/2] Context Sentences 생성")
print("=" * 60)

from context_sentences_builder import process_all_results_csv

csv_path = output_dir / 'output_results_v1.csv'
if not csv_path.exists():
    print(f"[ERROR] 출력 CSV를 찾을 수 없습니다: {csv_path}")
    sys.exit(1)

context_results = process_all_results_csv(str(csv_path), str(output_dir))

print(f"\n[OK] Step 2 완료: {len(context_results)}개 케이스 처리")

print("\n" + "=" * 60)
print("[OK] 전체 워크플로우 완료!")
print("=" * 60)
print(f"결과 위치: {output_dir}/")
print(f"  - output_results_v1.csv (Vision 추출 결과)")
print(f"  - context_sentences_results.json (Context Sentences)")
print(f"  - context_sentences_results.csv (Context Sentences - CSV 포맷)")
