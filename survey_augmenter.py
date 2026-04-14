# survey_augmenter.py

from typing import Dict, Optional

from pipeline import analyze_survey


# --------------------------------------------------
# 1. 기본 서비스 옵션 정의
# --------------------------------------------------

def get_default_augmentation_options() -> Dict:
    """
    설문 보강 서비스의 기본 옵션

    각 옵션 설명:
    - run_precheck:
        사전 문항 신뢰도 평가(pipeline)를 수행할지 여부

    - show_rewrite_suggestion:
        문항 점수가 낮을 경우 LLM을 통한 수정 제안(rewrite)을 생성할지 여부

    - generate_reverse_items:
        역문항(일관성 체크용)을 생성할지 여부
        ※ 현재 MVP에서는 실제 생성은 안 하고 계획만 세움

    - insert_instruction_trap:
        지시형 함정문항(예: "3번을 선택하세요")을 삽입할지 여부
        ※ 현재 MVP에서는 실제 삽입은 안 하고 계획만 세움

    - auto_apply_augmentation:
        생성된 역문항/함정문항/수정문장을 자동으로 survey에 반영할지 여부
        False이면 "추천만" 하고 실제 survey는 그대로 유지

    - deployment_mode:
        설문 실행 환경
        예: "mobile_only", "web", "mixed"
        현재는 분석에는 직접 영향 없지만 로그 설계 시 사용 가능
    """
    return {
        "run_precheck": True,
        "show_rewrite_suggestion": True,
        "generate_reverse_items": True,
        "insert_instruction_trap": True,
        "auto_apply_augmentation": False,
        "deployment_mode": "mobile_only",
    }


# --------------------------------------------------
# 2. 함정문항/역문항 개수 결정 로직
# --------------------------------------------------

def decide_trap_plan(item_count: int) -> Dict:
    """
    문항 개수에 따라 역문항 / 지시형 함정문항 개수를 결정

    규칙:
    - 10문항 이하:
        reverse 1개

    - 11~30문항:
        reverse 1개 + instruction 1개

    - 31문항 이상:
        reverse 2개 + instruction 1개
    """
    if item_count <= 10:
        return {
            "reverse_count": 1,
            "instruction_count": 0,
        }
    elif item_count <= 30:
        return {
            "reverse_count": 1,
            "instruction_count": 1,
        }
    else:
        return {
            "reverse_count": 2,
            "instruction_count": 1,
        }


# --------------------------------------------------
# 3. 설문 보강 메인 함수 (오케스트레이터)
# --------------------------------------------------

def augment_survey(
    survey: Dict,
    options: Optional[Dict] = None
) -> Dict:
    """
    설문을 입력받아
    - 사전 평가 수행
    - 보강 옵션 적용 여부 결정
    - 함정문항/역문항 계획 생성
    - 최종 결과 반환

    ※ 현재 MVP에서는 실제 문항 삽입/생성은 하지 않고
      구조와 계획만 반환한다.
    """

    # 옵션이 없으면 기본값 사용
    if options is None:
        options = get_default_augmentation_options()

    items = survey.get("items", [])
    item_count = len(items)

    # --------------------------------------
    # 1. 사전 문항 신뢰도 평가
    # --------------------------------------
    precheck_result = None

    if options.get("run_precheck", True):
        precheck_result = analyze_survey(survey)

    # --------------------------------------
    # 2. 함정문항/역문항 계획 생성
    # --------------------------------------
    trap_plan = decide_trap_plan(item_count)

    # 옵션에 따라 실제 사용할지 여부 표시
    trap_plan["reverse_enabled"] = options.get("generate_reverse_items", False)
    trap_plan["instruction_enabled"] = options.get("insert_instruction_trap", False)

    # --------------------------------------
    # 3. 보강 기능 활성화 상태 요약
    # --------------------------------------
    augmentation_preview = {
        "rewrite_enabled": options.get("show_rewrite_suggestion", False),
        "reverse_generation_enabled": options.get("generate_reverse_items", False),
        "instruction_trap_enabled": options.get("insert_instruction_trap", False),
        "auto_apply": options.get("auto_apply_augmentation", False),
    }

    # --------------------------------------
    # 4. 최종 결과 반환
    # --------------------------------------
    result = {
        "survey_id": survey.get("survey_id"),
        "title": survey.get("title", ""),
        "item_count": item_count,

        # 원본 설문
        "original_survey": survey,

        # 사전 평가 결과
        "precheck_result": precheck_result,

        # 사용된 옵션
        "augmentation_options": options,

        # 함정문항/역문항 계획
        "trap_plan": trap_plan,

        # 현재 어떤 기능이 활성화되었는지 요약
        "augmentation_preview": augmentation_preview,

        # 실제 보강된 설문 (현재는 미구현)
        "final_augmented_survey": None,
    }

    return result