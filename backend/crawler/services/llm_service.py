from __future__ import annotations

import os
import re
import time
from typing import Any

import requests

OLLAMA_API_URL = os.getenv(
    "OLLAMA_API_URL",
    "http://127.0.0.1:11434/api/chat",
).strip()

OLLAMA_MODEL = "qwen2.5:7b-instruct"
PERSIAN_MODEL = "aya:8b"


if not OLLAMA_MODEL:
    OLLAMA_MODEL = "qwen2.5:7b-instruct"


DEFAULT_TIMEOUT = 600
DEFAULT_NUM_PREDICT = 3000  
DEFAULT_NUM_CTX = 16384       
DEFAULT_KEEP_ALIVE = "10m"



def clean_ollama_response(content: str) -> str:
    if not content:
        return ""

    content = str(content).strip()

    content = re.sub(
        r"<think>.*?</think>",
        "",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    content = re.sub(
        r"<think>.*$",
        "",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    content = re.sub(
        r"\n{3,}",
        "\n\n",
        content,
    )

    return content.strip()



def chat_with_ollama(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    timeout: int = DEFAULT_TIMEOUT,
    num_predict: int = DEFAULT_NUM_PREDICT,
    num_ctx: int = DEFAULT_NUM_CTX,
     model: str | None = None,
) -> str | None:
    
    actual_model = model or OLLAMA_MODEL
    system_prompt = str(system_prompt or "").strip()
    user_prompt = str(user_prompt or "").strip()

    if not system_prompt:
        print("[Ollama] System prompt is empty.")
        return None

    if not user_prompt:
        print("[Ollama] User prompt is empty.")
        return None

    try:
        temperature = float(temperature)
    except (TypeError, ValueError):
        temperature = 0.1

    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT

    try:
        num_predict = int(num_predict)
    except (TypeError, ValueError):
        num_predict = DEFAULT_NUM_PREDICT

    try:
        num_ctx = int(num_ctx)
    except (TypeError, ValueError):
        num_ctx = DEFAULT_NUM_CTX

    timeout = max(1, timeout)
    num_predict = max(1, num_predict)
    num_ctx = max(512, num_ctx)

    payload: dict[str, Any] = {
        "model": actual_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "keep_alive": DEFAULT_KEEP_ALIVE,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        },
    }

    total_characters = len(system_prompt) + len(user_prompt)
    start_time = time.perf_counter()

    print(f"[Ollama] Sending request model={actual_model}, characters={total_characters}, num_predict={num_predict}, num_ctx={num_ctx}")

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=timeout,
        )

        elapsed = time.perf_counter() - start_time
        print(f"[Ollama] HTTP status={response.status_code}, elapsed={elapsed:.1f}s")

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as error:
            print(f"[Ollama] Invalid JSON response: {error}")
            print("[Ollama] Raw response:", response.text[:500])
            return None

        if not isinstance(data, dict):
            print("[Ollama] Unexpected response type:", type(data).__name__)
            return None

        message = data.get("message")
        if not isinstance(message, dict):
            print("[Ollama] Response does not contain a valid message object.")
            print("[Ollama] Response keys:", list(data.keys()))
            return None

        content = message.get("content", "")
        if not isinstance(content, str):
            print("[Ollama] Response content is not a string.")
            return None

        content = clean_ollama_response(content)

        if not content:
            thinking = message.get("thinking", "")
            print("[Ollama] Empty response content.")
            if isinstance(thinking, str) and thinking.strip():
                print(f"[Ollama] Model returned thinking but no final answer. thinking_characters={len(thinking)}")
            print("[Ollama] Full message keys:", list(message.keys()))
            return None

        total_elapsed = time.perf_counter() - start_time
        print(f"[Ollama] Completed successfully in {total_elapsed:.1f}s, response_characters={len(content)}")
        return content

    except requests.exceptions.ConnectionError as error:
        elapsed = time.perf_counter() - start_time
        print(f"[Ollama] Connection error after {elapsed:.1f}s: {error}")
        print("[Ollama] Make sure the Ollama application is running.")
        return None

    except requests.exceptions.Timeout:
        elapsed = time.perf_counter() - start_time
        print(f"[Ollama] Request timed out after {elapsed:.1f}s.")
        return None

    except requests.exceptions.HTTPError as error:
        elapsed = time.perf_counter() - start_time
        status_code = error.response.status_code if error.response is not None else "unknown"
        response_text = error.response.text[:500] if error.response is not None else ""
        print(f"[Ollama] HTTP error after {elapsed:.1f}s, status={status_code}: {error}")
        if response_text:
            print("[Ollama] Response body:", response_text)
        return None

    except requests.RequestException as error:
        elapsed = time.perf_counter() - start_time
        print(f"[Ollama] Request error after {elapsed:.1f}s: {error}")
        return None

    except Exception as error:
        elapsed = time.perf_counter() - start_time
        print(f"[Ollama] Unexpected error after {elapsed:.1f}s: {type(error).__name__}: {error}")
        return None