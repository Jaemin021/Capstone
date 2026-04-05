import json
from pathlib import Path
import llm.rewrite as rewrite_module
print("rewrite file path:", rewrite_module.__file__)

from pipeline import analyze_survey
from utils.validation import validate_feature_alignment
from dictionaries.terms import TERM_DICTIONARY



SAMPLE_FILES = [
    "samples/good_survey.json",
    "samples/bad_survey.json",
    "samples/mixed_survey.json",
]

OUTPUT_DIR = Path("outputs")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_test(file_path: str, save_output: bool = True) -> dict:
    survey = load_json(file_path)
    result = analyze_survey(survey)

    print(f"\n=== {file_path} 결과 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if save_output:
        output_name = Path(file_path).stem + "_result.json"
        output_path = OUTPUT_DIR / output_name
        save_json(result, output_path)
        print(f"저장 완료: {output_path}")

    return result


if __name__ == "__main__":
    validate_feature_alignment()

    for file_path in SAMPLE_FILES:
        run_test(file_path)