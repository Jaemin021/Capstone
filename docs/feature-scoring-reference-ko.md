# Feature/점수 산식 정리 (코드 기준)

이 문서는 현재 백엔드 코드 기준으로 **응답 feature 종류**, **각 feature 의미**, **점수 계산식(가중합/패널티)** 을 정리한 문서입니다.

기준 코드:
- `backend/survey/backend/services/feature_service.py`
- `backend/survey/backend/services/population_feature_service.py`
- `backend/survey/backend/services/item_quality_score_service.py`
- `backend/survey/backend/services/item_construct_embedding_service.py`
- `backend/survey/backend/services/item_construct_llm_service.py`
- `backend/survey/backend/services/survey_statistical_evaluation_service.py`
- `backend/survey/backend/routers/survey_evaluations.py`

## 1) 응답 신뢰도 feature 그룹

응답 1건이 제출되면 백엔드에서 아래 순서로 계산됩니다.

1. `log_features`
2. `content_features`
3. `relation_features`
4. `population_features`
5. 위 4개를 합쳐 `compact_features`
6. `compact_features`로 `reliability_score`, `reliability_status` 산출

### 1-1. Log Features (행동/시간 로그)

| 키 | 의미 |
|---|---|
| `total_time_ms` | 전체 응답 소요 시간(ms) |
| `item_count` | 문항 수(로그 기반) |
| `avg_item_time_ms` | 문항당 평균 응답 시간(ms) |
| `too_fast_threshold_ms` | 너무 빠른 응답 판정 임계값(ms), 현재 1500 |
| `too_fast_item_ratio` | 임계값보다 빠른 문항 비율 |
| `avg_touch_per_item` | 문항당 평균 터치 횟수 |
| `offline_ratio` | 전체 시간 대비 오프라인 시간 비율 |
| `connection_lost` | 연결 끊김 감지 여부(0/1) |
| `mean_time_to_first_answer_ms` | 문항 진입 후 첫 선택까지 평균 시간 |
| `min_time_to_first_answer_ms` | 첫 선택까지 최소 시간 |
| `max_time_to_first_answer_ms` | 첫 선택까지 최대 시간 |
| `mean_time_after_last_answer_ms` | 마지막 선택 후 이탈까지 평균 시간 |
| `max_time_after_last_answer_ms` | 마지막 선택 후 이탈까지 최대 시간 |
| `mean_initial_visit_time_ms` | 최초 방문 체류 시간 평균 |
| `mean_revisit_time_ms` | 재방문 체류 시간 평균 |
| `max_revisit_time_ms` | 재방문 체류 시간 최대 |
| `total_change_count` | 전체 답 변경 횟수 합 |
| `mean_change_count` | 문항당 평균 답 변경 횟수 |
| `total_visit_count` | 전체 방문 횟수 합 |
| `mean_visit_count` | 문항당 평균 방문 횟수 |
| `total_back_visit_count` | 뒤로가기/재방문 횟수 합 |
| `mean_back_visit_count` | 문항당 평균 뒤로가기/재방문 횟수 |
| `revisited_item_count` | 재방문된 문항 개수 |
| `revisit_item_ratio` | 재방문 문항 비율 |
| `answer_changed_count` | 답이 바뀐 문항 개수 |
| `answer_changed_ratio` | 답이 바뀐 문항 비율 |
| `changed_after_revisit_count` | 재방문 후 답 변경된 문항 개수 |
| `changed_after_revisit_ratio` | 재방문 후 답 변경 비율 |

### 1-2. Content Features (함정문항 기반)

| 키 | 의미 |
|---|---|
| `trap_total_count` | 함정문항 수 |
| `trap_fail_count` | 함정문항 오답/미응답 수 |
| `trap_fail_ratio` | 함정문항 실패 비율 (`trap_fail_count / trap_total_count`) |

### 1-3. Relation Features (역문항 일관성)

역문항에 대해 원문항 답과의 반대 대응을 검사합니다.

- 기대 역문항 선택값: `expected_reverse_order = 6 - source_answer`
- 문항별 오차: `diff = abs(reverse_answer - expected_reverse_order)`

| 키 | 의미 |
|---|---|
| `reverse_pair_count` | 계산 가능한 역문항 쌍 개수 |
| `reverse_total_diff` | 역문항 오차 합 |
| `reverse_avg_diff` | 역문항 평균 오차 (`reverse_total_diff / reverse_pair_count`) |
| `reverse_consistency_score` | 역문항 일관성 점수 (`1 - reverse_avg_diff/4`) |

### 1-4. Population Features (집단 대비 시간곡선)

응답자의 문항별 시간 비율 벡터를 집단 평균과 비교합니다.

- 문항 시간 비율 벡터: `item_time_ms / total_time_ms`
- 기준 집단: 같은 설문의 다른 완료 응답 중, 제외 규칙에 걸리지 않은 응답들
- 최소 표본: `3`개 미만이면 편차 계산 안 함(`None`)

| 키 | 의미 |
|---|---|
| `time_curve_deviation` | 집단 평균 대비 시간곡선 편차(평균 절대 z-score) |
| `population_sample_count` | 비교에 사용된 집단 표본 수 |

편차 계산식:
- `z_i = abs(current_i - mean_i) / std_i`
- `time_curve_deviation = average(z_i)`
- 표준편차 하한: `EPS = 0.03` (너무 작은 분모 방지)

## 2) Compact Features (저장/다운로드용 통합 피처)

`compact_features`에는 아래가 포함됩니다.

- 핵심 log 피처 일부
- `trap_fail_ratio`
- `reverse_avg_diff`, `reverse_consistency_score`
- `time_curve_deviation`, `population_sample_count`
- `item_count`
- 파생값:
  - `reliability_score`
  - `reliability_status`
  - `exclude_from_statistics`
  - `exclude_reasons`
  - `offline_exclusion_ratio_threshold`

## 3) 응답 신뢰도 점수 산식 (reliability_score)

초기점수 100점에서 패널티를 빼는 구조입니다.

```text
score = 100
score -= min(35, too_fast_item_ratio * 35)
score -= min(30, trap_fail_ratio * 30)
score -= min(20, max(0, 1 - reverse_consistency_score) * 20)   # reverse_consistency_score가 있을 때만
score -= min(10, answer_changed_ratio * 10)
score -= min(8,  revisit_item_ratio * 8)
score -= min(12, time_curve_deviation * 3)                      # time_curve_deviation이 있을 때만
final_score = round(clamp(score, 0, 100), 1)
```

상태 판정:
- `good`: 75 이상
- `warning`: 55 이상 75 미만
- `bad`: 55 미만

## 4) 통계 분석 제외 규칙 (exclude_from_statistics)

아래 중 하나라도 참이면 통계 계산에서 제외됩니다.

1. `offline_ratio >= OFFLINE_EXCLUSION_RATIO_THRESHOLD` (기본 0.15)
2. `connection_lost == true` 이고 `EXCLUDE_IF_CONNECTION_LOST == true` (기본 true)

이 제외 규칙은:
- Cronbach alpha/CITC 계산용 응답 행렬 구성
- population feature 기준집단 구성
에서 공통으로 사용됩니다.

## 5) 문항 품질평가 점수 (quality_score, 0~10)

입력 하위점수:
- `clarity`
- `single_concept`
- `answerability`
- `neutrality`
- (옵션) `overall_quality_score`

기본 가중합:
```text
weighted_subscore =
  clarity * 0.35 +
  single_concept * 0.25 +
  answerability * 0.25 +
  neutrality * 0.15
```

`overall_quality_score`가 있으면 보수적으로 블렌딩:
```text
score = weighted_subscore * 0.8 + overall_quality_score * 0.2
```

최종:
- 0~10 클램프 후 소수점 3자리 반올림
- 품질 상태 판정 기준(조회 시): `good >= 8`, `warning >= 6`, 그 외 `bad`
- `suggested_rewrite` 노출은 **score < 6.0일 때만**

## 6) 구성개념(Construct) 평가 점수

### 6-1. Embedding Score (0~10)

`construct_similarity`, `mean_item_similarity`로 계산:

```text
embedding_score = (construct_similarity * 0.6 + mean_item_similarity * 0.4) * 10
```

### 6-2. LLM Construct Score (0~10)

```text
llm_score =
  construct_fit * 0.45 +
  semantic_consistency * 0.35 -
  redundancy_risk * 0.10 -
  off_construct_risk * 0.25
```

최종 0~10 클램프, 소수점 3자리.

### 6-3. Combined Score (조회 응답용)

`/survey-evaluations/{survey_id}/construct` 조회 시:

```text
combined_score = embedding_score * 0.4 + llm_score * 0.6
```

상태 판정:
- `good >= 8`
- `warning >= 6`
- `bad < 6`

## 7) 통계 품질 지표 (Survey-level)

### 7-1. Cronbach alpha

표준식:

```text
alpha = (k / (k - 1)) * (1 - (sum(item_variances) / total_variance))
```

- `k`: 문항 수
- 최소 응답 2개, 최소 문항 2개 필요
- 상태 판정: `good >= 0.7`, `warning >= 0.6`, 그 외 `bad`

### 7-2. CITC

문항별 `item_score`와 `(총점 - 해당 문항점수)` 간 상관계수.

상태 판정:
- `good >= 0.4`
- `warning >= 0.2`
- `bad < 0.2`

### 7-3. Alpha if item deleted

각 문항을 하나씩 제거한 행렬로 alpha 재계산.

## 8) 실무 해석 요약

- 응답 신뢰도(`reliability_score`)는 **패널티 누적형**이라, 특정 위험(예: 함정문항 실패, 너무 빠른 응답)이 있으면 즉시 점수가 내려갑니다.
- 집단 대비 편차(`time_curve_deviation`)는 표본이 충분할 때만 반영됩니다.
- 오프라인/연결끊김 기준으로 제외된 응답은 통계치(Cronbach/CITC)와 집단기반 feature 계산에서 빠집니다.

