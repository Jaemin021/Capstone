import json
import os
import socket
import time
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


def _get_int_env(name: str, default: int, min_value: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(min_value, value)


def _get_float_env(name: str, default: float, min_value: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(min_value, value)


def _is_retryable_http_status(status_code: int) -> bool:
    return status_code in {408, 409, 429} or 500 <= status_code <= 599


def _is_retryable_network_error(reason: object) -> bool:
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return True

    text = str(reason).lower()
    retryable_signatures = (
        "timed out",
        "timeout",
        "temporary failure",
        "temporarily unavailable",
        "connection reset",
        "connection aborted",
        "network is unreachable",
        "name or service not known",
        "server disconnected",
        "remote end closed connection",
    )
    return any(sig in text for sig in retryable_signatures)


def _retry_delay_seconds(attempt_index: int, base_delay: float, max_delay: float) -> float:
    # attempt_index starts at 1
    delay = base_delay * (2 ** max(0, attempt_index - 1))
    return min(max_delay, delay)


def _post_json(path: str, payload: dict[str, Any], timeout_sec: int | None = None) -> dict[str, Any]:
    timeout = timeout_sec or _get_int_env("OPENAI_REQUEST_TIMEOUT_SEC", 90, 1)
    max_attempts = _get_int_env("OPENAI_RETRY_MAX_ATTEMPTS", 3, 1)
    base_delay_sec = _get_float_env("OPENAI_RETRY_BASE_DELAY_SEC", 1.0, 0.0)
    max_delay_sec = _get_float_env("OPENAI_RETRY_MAX_DELAY_SEC", 8.0, 0.0)

    url = f"{_get_api_base()}{path}"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
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
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")

            data = json.loads(raw)
            if not isinstance(data, dict):
                raise OpenAIRequestError("OpenAI response format is invalid.")
            return data

        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            last_error = OpenAIRequestError(f"OpenAI HTTP {error.code}: {detail[:600]}")
            retryable = _is_retryable_http_status(error.code)
        except urllib.error.URLError as error:
            last_error = OpenAIRequestError(f"OpenAI request failed: {error.reason}")
            retryable = _is_retryable_network_error(error.reason)
        except json.JSONDecodeError as error:
            # Transient upstream proxy issues can return invalid JSON.
            last_error = OpenAIRequestError(f"OpenAI response JSON decode failed: {str(error)}")
            retryable = True
        except Exception as error:
            last_error = OpenAIRequestError(f"OpenAI unexpected request failure: {repr(error)}")
            retryable = False

        if not retryable or attempt >= max_attempts:
            break

        delay = _retry_delay_seconds(
            attempt_index=attempt,
            base_delay=base_delay_sec,
            max_delay=max_delay_sec,
        )
        if delay > 0:
            time.sleep(delay)

    if last_error is not None:
        raise last_error
    raise OpenAIRequestError("OpenAI request failed for an unknown reason.")


def _extract_text_content(content: object) -> str | None:
    if isinstance(content, str):
        return content

    # Some providers may return block-style content arrays.
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
                continue
            if not isinstance(block, dict):
                continue
            text_value = block.get("text")
            if isinstance(text_value, str):
                parts.append(text_value)
                continue
            # compatibility with alternative block shapes
            if isinstance(text_value, dict):
                nested = text_value.get("value")
                if isinstance(nested, str):
                    parts.append(nested)
        merged = "\n".join(x for x in parts if x)
        return merged if merged else None

    return None


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

    content = _extract_text_content(message.get("content"))
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
