import json
from response_pipeline import analyze_response_reliability

def run_case(survey_path: str, response_path: str) -> None:
    with open(survey_path, "r", encoding="utf-8") as f:
        survey = json.load(f)

    with open(response_path, "r", encoding="utf-8") as f:
        response = json.load(f)

    result = analyze_response_reliability(survey, response)

    print("=" * 80)
    print(f"response_id: {result['response_id']}")
    print(f"participant_id: {result['participant_id']}")
    print(f"overall_response_score: {result['overall_response_score']}")
    print(f"overall_response_score_100: {result['overall_response_score_100']}")
    print(f"issue_count: {result['issue_count']}")
    print(f"has_issue: {result['has_issue']}")
    print("flags:", result["flags"])
    print("\nfeature_counts:")
    print(json.dumps(result["feature_counts"], ensure_ascii=False, indent=2))
    print("\nrule_scores:")
    print(json.dumps(result["rule_scores"], ensure_ascii=False, indent=2))
    print("\nfull_result:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    run_case("sample_survey_response_eval.json", "sample_response_good.json")
    run_case("sample_survey_response_eval.json", "sample_response_bad.json")
