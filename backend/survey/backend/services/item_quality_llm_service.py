# backend/services/item_quality_llm_service.py

import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

if not API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=API_KEY)


def extract_json_from_text(text: str):
    if not text:
        return None

    text = text.strip()

    try:
        return json.loads(text)
    except:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except:
        return None


def evaluate_item_with_llm(question_text, options):
    prompt = f"""
You are a survey item quality evaluation expert.

Evaluate the following survey item.

Question:
{question_text}

Options:
{json.dumps(options, ensure_ascii=False)}

Evaluate only wording quality, not construct consistency.

Return ONLY JSON:
{{
  "clarity": 0-10,
  "single_concept": 0-10,
  "answerability": 0-10,
  "neutrality": 0-10,
  "problem_categories": [],
  "detected_terms": [],
  "llm_comment": "",
  "suggested_rewrite": ""
}}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Return ONLY JSON"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content
        return extract_json_from_text(content)

    except Exception as e:
        print("LLM item quality evaluation failed:", e)
        return None