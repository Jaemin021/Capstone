설문 문항 품질 평가 시스템 (Survey Evaluation System)
1. 개요

이 시스템은 설문 문항의 품질을 자동으로 평가하는 백엔드 시스템이다.

기존의 단순 규칙 기반 방식의 한계를 보완하기 위해
사전 기반 규칙 탐지 + LLM 기반 보조 및 평가를 결합한
Hybrid 평가 구조로 설계되었다.

2. 시스템 구조 (핵심)

본 시스템은 3단계 구조로 동작한다.

🔹 1단계: Rule-based 탐지 (Exact Matcher)
TERM_DICTIONARY 기반으로 문제 표현을 탐지
문자열 포함 방식 (exact match)
매우 보수적이고 재현 가능한 baseline

출력:

rule_analysis
feature_counts
🔹 2단계: LLM 기반 보조 탐지 (Rule-Assist)
사전(dictionary)을 기반으로
형태 변화 및 표면형 변형을 LLM이 보조 탐지

특징:

사전 외 개념 생성 금지
의미 확장 금지 (strict constraint)
exact matcher가 놓친 표현만 보완

출력:

assist_rule_analysis
🔹 3단계: Rule 병합 및 점수 계산
exact + assist 결과 병합
(feature, dictionary_term) 기준으로 중복 제거
feature count 재계산
penalty 기반 rule score 계산
🔹 4단계: LLM 품질 평가 (Evaluation LLM)
문항 전체를 보고 품질 점수 산출
rule 결과는 참고 정보로 사용
각 카테고리별 점수 + 이유 생성
🔹 5단계: 최종 점수 결합
Final Score = Rule Score + LLM Score (가중 결합)
rule: 구조적 문제 반영
llm: 자연스러움/맥락 보정
3. 전체 흐름
문항 입력
 ↓
Exact Rule 분석
 ↓
LLM Rule-Assist (보조 탐지)
 ↓
Rule 병합 + Feature Count 재계산
 ↓
Rule Score 계산
 ↓
LLM Evaluation (품질 평가)
 ↓
Score 결합
 ↓
최종 점수 + 추천 생성
4. 입력 형식 (Survey JSON)
{
  "survey_id": "S1",
  "title": "설문 제목",
  "items": [
    {
      "item_id": "Q1",
      "question": "문항 내용",
      "option_type": "single_choice",
      "options": ["보기1", "보기2"]
    }
  ]
}
5. 출력 형식
{
  "survey_id": "S1",
  "title": "설문 제목",
  "item_count": 1,
  "summary": {
    "avg_overall_pre_score": 9.3,
    "avg_overall_pre_score_100": 93.0
  },
  "items": [
    {
      "item_id": "Q1",
      "final_scores": {
        "clarity": 9.2,
        "single_concept": 9.5,
        "answerability": 9.0
      },
      "overall_pre_score_100": 93.0
    }
  ]
}
6. 점수 구조
기본 개념
초기 점수: 10점 (→ 100점 환산)
rule 기반 감점
LLM 기반 보정
계산 방식
Rule Score = penalty 기반 감점
LLM Score = 문항 품질 평가
Final Score = weighted sum
7. 평가 기준
항목	설명
clarity	문장이 모호한가
single_concept	여러 개념이 섞였는가
neutrality	유도/편향 표현이 있는가
answerability	현실적으로 답하기 어려운가
8. 핵심 특징
✔ Hybrid 구조
Rule 기반 + LLM 결합
단순 규칙 한계를 보완
✔ Dictionary-constrained LLM
LLM이 자유롭게 판단하지 않음
사전 기반으로만 탐지
오염 최소화
✔ 중복 문제 해결
(feature, dictionary_term) 기준 병합
동일 문제 중복 감지 방지
✔ 추적 가능성 (Explainability)

각 탐지 결과에 포함:

{
  "feature": "...",
  "dictionary_term": "...",
  "match": "...",
  "source": "exact | assist"
}

👉 exact vs LLM 보조 구분 가능

✔ GOOD / BAD 문항 구분 가능
좋은 문항 → 높은 점수 유지
나쁜 문항 → 명확한 감점
9. 실행 방법
python main.py

샘플 데이터:

samples/good_survey.json
samples/bad_survey.json
samples/mixed_survey.json
10. 현재 상태
완료된 기능

✔ Rule 기반 탐지
✔ LLM 보조 탐지 (형태 변형 대응)
✔ 중복 제거 로직
✔ LLM 평가
✔ 점수 결합
✔ 추천 문장 생성
✔ JSON 기반 테스트

11. 시스템 한계 (현재)
일부 표현은 상황에 따라 과도하게 감점될 수 있음
rule score에 LLM 보조 탐지가 포함됨 (완전 분리 구조 아님)
12. 향후 계획
exact / assist 분리 평가 구조 실험
응답 데이터 기반 신뢰도 평가 추가
사전(term) 확장 및 튜닝
성능 정량 평가 (precision / recall)