from typing import Dict, List, Optional
from dictionaries.terms import TERM_DICTIONARY


def build_rule_assist_prompt(
    question: str,
    categories: List[str] | None = None,
    exact_rule_analysis: Optional[Dict] = None,
) -> List[Dict[str, str]]:
    """
    단어 사전을 기반으로 LLM에게 rule-like 탐지를 수행하게 하는 프롬프트 생성.
    목표는 '의미 확장'이 아니라 사전에 있는 표현의 표면형 변형 보조 탐지이다.
    """

    if categories is None:
        target_dict = TERM_DICTIONARY
        target_categories = list(TERM_DICTIONARY.keys())
    else:
        target_dict = {
            cat: TERM_DICTIONARY.get(cat, {})
            for cat in categories
        }
        target_categories = categories

    output_example = {
        category: [
            {
                "feature": "...",
                "dictionary_term": "...",
                "match": "..."
            }
        ]
        for category in target_categories
    }

    exact_rule_analysis = exact_rule_analysis or {}

    system_prompt = """
You are a strict rule-based detector assistant.

Your job is to detect whether a sentence contains expressions that match a predefined feature dictionary.

STRICT RULES:
1. You MUST only use the provided dictionary.
2. Do NOT create new features.
3. Do NOT infer new categories.
4. Only detect expressions that are:
   - exact matches, OR
   - clear surface-form variations of the same dictionary expression
     (e.g., particles, endings, tense, spacing, minor inflection)
5. Do NOT detect broad paraphrases or loosely similar meanings.
6. If the connection to a dictionary expression is uncertain, DO NOT detect it.
7. Precision is more important than recall.
8. Do NOT evaluate quality.
9. Do NOT assign scores.
10. Only return detected matches.
11. Use the exact category names provided in the dictionary.
12. Use the exact feature names provided in the dictionary.
13. Use an exact dictionary term from the provided feature list as dictionary_term.
14. Do NOT return expressions that were already detected by exact matching.

Output format:
Return a JSON object where each top-level key is a category name.
Each category value must be a list of objects like:
{"feature": "...", "dictionary_term": "...", "match": "..."}

If no matches exist for a category, return an empty list for that category.
"""

    user_prompt = f"""
[Question]
{question}

[Feature Dictionary]
{target_dict}

[Allowed Categories]
{target_categories}

[Already Detected by Exact Rule]
{exact_rule_analysis}

[Task]
Detect matching expressions in the question using ONLY the given dictionary.

Important:
- Match Korean expressions only when they are clear surface-form variations of dictionary expressions.
- For each detected item, return:
  1. feature
  2. dictionary_term = the exact dictionary expression that serves as the canonical basis
  3. match = the actual matched phrase from the question
- Extract the actual matched phrase from the question.
- Do NOT return anything already detected by exact matching.
- Do NOT match based on broad semantic similarity.
- If uncertain, return nothing for that case.
- Do NOT hallucinate.
- Do NOT add explanations.
- Return all categories, even if empty.

[Example Output Shape]
{output_example}
"""

    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_prompt.strip()},
    ]