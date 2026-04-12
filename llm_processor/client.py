from __future__ import annotations

import json
from os import getenv
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scraper.utils.logging_config import get_logger


logger = get_logger("llm_processor.client")


class LLMClientError(RuntimeError):
    pass


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def call_openai_compatible(prompt: str) -> str:
    api_key = getenv("LLM_API_KEY", "")
    base_url = getenv("LLM_BASE_URL", "")
    model = getenv("LLM_MODEL", "")

    if not api_key or not base_url or not model:
        raise LLMClientError("LLM_API_KEY, LLM_BASE_URL ve LLM_MODEL birlikte tanimli olmali.")

    endpoint = f"{_normalize_base_url(base_url)}/chat/completions"
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Sen urun teknik ozelliklerini cikaran bir analiz asistanisin. Cevabi yalnizca gecerli JSON olarak don.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise LLMClientError(f"LLM HTTP hatasi: {exc.code}") from exc
    except URLError as exc:
        raise LLMClientError(f"LLM baglanti hatasi: {exc.reason}") from exc

    try:
        return response_payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning(
            "Unexpected LLM response payload",
            extra={"extra_fields": {"response_payload": response_payload}},
        )
        raise LLMClientError("LLM cevabi beklenen formatta degil.") from exc
