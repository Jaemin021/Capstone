# 캡스톤 실험계획서 (응답 신뢰도 + 문항 구성/CITC 근사)

작성일: 2026-04-29
저장 경로: docs/archive/experiment-plan.md

## 1. 프로젝트 목표
- 문항 단위에서 CITC에 근사하는 구성 점수를 예측한다.
- 응답 단위에서 신뢰도 점수(0~100)를 산출한다.
- 소규모 데이터 환경(캡스톤)에서도 재현 가능한 실험/라벨링/평가 체계를 만든다.

## 2. 현재 구현 상태 핵심 요약
- 프론트/백엔드 설문 생성, 수정, 목록, 응답, 결과 통계 흐름 동작.
- 문항 품질 평가는 규칙감점 제거 후 LLM 보수 프롬프트 기반으로 변경.
- 응답 신뢰도 계산에서 `offline_ratio`, `connection_lost` 감점 제거.
- 대신 통계(Cronbach/CITC) 표본 제외 기준으로 네트워크 품질 사용.
- 집단 대비 이상치(time_curve_deviation)는 자기 자신 제외 + 네트워크 제외 응답 제외로 계산.

## 3. 실험 설계 의사결정
### 3.1 데이터 수집 전략
- 설문은 분리 수집하지 않고 통합 수집한다.
- 도메인 최소 3개 설문을 운영한다.
- 도메인별로 아래 3개 응답군을 모두 수집한다.
  - 자연응답군
  - 성실지시군
  - 비성실지시군

### 3.2 비성실 지시군 패턴
- 최소 3패턴으로 분리한다.
  - 과속형
  - 직선형(동일 보기 반복)
  - 무작위형
- 목적: 실제 비성실 행동 다양성을 반영하고 단일 패턴 과적합을 피함.

### 3.3 저품질 문항 삽입 원칙 (CITC 근사용)
- 문항 이질감이 크지 않게 삽입한다.
- 저품질 유도 문항 비율은 초기 10~20%로 제한한다.
- 유도 유형은 다양화한다.
  - 모호 표현
  - 이중질문
  - construct 이탈
  - 과도한 일반화 표현

## 4. 라벨링 전략
### 4.1 문항 구성/CITC 근사 라벨
- 통계 기반 실제 CITC를 정답 라벨로 사용.
- 응답 수가 부족한 경우 라벨 신뢰도를 낮춘다(학습 가중치 반영).

### 4.2 응답 신뢰도 라벨
- 고신뢰 라벨
  - 성실지시군: 성실(1), weight=1.0
  - 비성실지시군: 비성실(0), weight=1.0
- 자연응답군은 약라벨
  - 성실 후보: weight 0.5~0.8
  - 불확실: weight 0.1~0.3 또는 학습 제외
- 마지막 자기보고 성실도 문항은 보조 신호로만 사용.

## 5. 현재 Feature 체계 (응답 단위)
### 5.1 원본 feature 묶음
- `log_features`
- `content_features`
- `relation_features`
- `population_features`
- `compact_features`
- `reliability` (score/status/reasons)

### 5.2 신뢰도 점수 계산에 직접 쓰는 핵심 항목
- too_fast_item_ratio
- trap_fail_ratio
- reverse_consistency_score
- answer_changed_ratio
- revisit_item_ratio
- time_curve_deviation

### 5.3 감점에서 제외된 항목
- offline_ratio
- connection_lost

### 5.4 통계 표본 제외 규칙
- `offline_ratio >= OFFLINE_EXCLUSION_RATIO_THRESHOLD` (기본 0.15)
- `EXCLUDE_IF_CONNECTION_LOST=1`일 때 connection_lost 응답 제외
- 제외 여부/사유는 compact_features에 기록
  - exclude_from_statistics
  - exclude_reasons
  - offline_exclusion_ratio_threshold

## 6. 집단 대비 이상치(time_curve_deviation) 계산 방식
1. 문항별 시간 비율 벡터 생성
   - 각 문항 시간 / 총 응답 시간
2. 비교 집단 구성
   - 같은 설문의 완료 응답 중 자기 자신 제외
   - 네트워크 제외 규칙에 해당하는 응답 제외
3. 집단 평균/표준편차 계산
4. 현재 응답과 항목별 z 편차 계산
   - abs(current_i - mean_i) / std_i
5. 항목별 z 편차 평균을 deviation으로 사용

## 7. 모델링 전략
### 7.1 CITC 근사 모델
- 목표: item-level CITC 회귀(또는 순위)
- 입력: 문항 품질/구성 관련 feature + 설문 컨텍스트
- 1차 모델: 트리계열(XGBoost/LightGBM)
- 평가지표: MAE, RMSE, Spearman

### 7.2 응답 신뢰도 모델
- 목표: response-level 0~100 점수
- 입력: 행동/시간/함정/역문항/집단편차 feature
- 1차 모델: 트리계열
- 출력 점수는 calibration 후 사용
- 평가지표: AUC, PR-AUC, F1, calibration error
- 실용 지표: 저신뢰 필터링 전후 Cronbach alpha/CITC 개선

## 8. 로그 feature 축소 사용 권장 (소규모 데이터용)
- 1차 핵심 입력 후보
  - too_fast_item_ratio
  - avg_item_time_ms
  - mean_time_to_first_answer_ms
  - mean_change_count
  - revisit_item_ratio
  - answer_changed_ratio
  - trap_fail_ratio
  - reverse_consistency_score
  - time_curve_deviation
  - population_sample_count
  - item_count
- 권장 전처리
  - count/time: log1p
  - ratio: 원값 유지
  - 극단치 clip
  - 결측 플래그 분리

## 9. 검증 전략
- random split만 사용하지 않는다.
- 도메인 홀드아웃 검증을 병행한다.
  - 예: 도메인 2개 학습, 1개 테스트
- 목적: 도메인 일반화 성능 확인

## 10. 운영 체크리스트
1. 도메인 3개 설문 문항 확정
2. 비성실 지시문 3패턴 확정
3. 저품질 유도 문항 비율(10~20%) 확정
4. 제외 임계치(`OFFLINE_EXCLUSION_RATIO_THRESHOLD`) 확정
5. 1차 수집 후 라벨 품질 점검
6. CITC 근사 모델 v1 학습
7. 신뢰도 모델 v1 학습
8. 도메인 홀드아웃 평가
9. 개선사항 반영 후 v2 실험

## 11. 향후 확장 아이디어
- 현재 통계 요약 feature + 시퀀스 인코더(LSTM/GRU) 임베딩 결합
- 데이터가 더 쌓이면 규칙 비중을 줄이고 모델 출력 비중 확대
- 불확실 샘플 처리 전략(가중치/제외)을 실험별로 비교

## 12. 주의사항
- 자연응답군을 전부 성실 확정 라벨로 두지 않는다.
- 지시군만으로 학습하면 실제 분포와 괴리 가능성이 있으므로 자연응답군을 반드시 포함한다.
- 비성실 지시를 단일 패턴으로만 만들면 일반화가 급격히 떨어질 수 있다.
