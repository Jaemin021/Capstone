import json
import os
import urllib.error
import urllib.request
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class OpenAIRequestError(RuntimeError):
    pass


def _get_api_base() -> str:
    return os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")


def _get_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIRequestError("OPENAI_API_KEY is not configured.")
    return api_key


def _post_json(path: str, payload: dict[str, Any], timeout_sec: int = 90) -> dict[str, Any]:
    url = f"{_get_api_base()}{path}"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {_get_api_key()}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise OpenAIRequestError(f"OpenAI HTTP {error.code}: {detail[:600]}") from error
    except urllib.error.URLError as error:
        raise OpenAIRequestError(f"OpenAI request failed: {error.reason}") from error

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise OpenAIRequestError(f"OpenAI response JSON decode failed: {raw[:300]}") from error

    if not isinstance(data, dict):
        raise OpenAIRequestError("OpenAI response format is invalid.")

    return data


def create_chat_completion(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
) -> str:
    response = _post_json(
        "/chat/completions",
        {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        },
    )

    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        raise OpenAIRequestError(f"OpenAI choices missing: {response}")

    first = choices[0]
    if not isinstance(first, dict):
        raise OpenAIRequestError(f"OpenAI first choice invalid: {first}")

    message = first.get("message")
    if not isinstance(message, dict):
        raise OpenAIRequestError(f"OpenAI message missing: {first}")

    content = message.get("content")
    if not isinstance(content, str):
        raise OpenAIRequestError(f"OpenAI content missing: {message}")

    return content


def create_embedding(*, model: str, text: str) -> list[float]:
    response = _post_json(
        "/embeddings",
        {
            "model": model,
            "input": text,
        },
    )

    data = response.get("data")
    if not isinstance(data, list) or len(data) == 0:
        raise OpenAIRequestError(f"OpenAI embedding data missing: {response}")

    first = data[0]
    if not isinstance(first, dict):
        raise OpenAIRequestError(f"OpenAI embedding row invalid: {first}")

    embedding = first.get("embedding")
    if not isinstance(embedding, list):
        raise OpenAIRequestError(f"OpenAI embedding vector missing: {first}")

    return [float(value) for value in embedding]
