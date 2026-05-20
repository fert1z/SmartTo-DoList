from __future__ import annotations

import os
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def _openai_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return key


def _openai_model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL


def generate_reminder_text(
    *,
    title: str,
    description: Optional[str],
    due_iso: Optional[str],
    priority: Optional[str],
) -> str:
    """
    Сгенерировать короткий текст напоминания для Telegram.

    Важно: не падаем при ошибках внешнего AI — возвращаем дефолтную фразу.
    """
    api_key = _openai_api_key()
    if not api_key:
        return "Напоминание: пора заняться задачей. Проверьте дедлайн и приоритет."

    model = _openai_model()

    desc_part = description.strip() if description else ""
    due_part = due_iso or ""

    prompt = (
        "Ты ассистент по умным напоминаниям.\n"
        "Сгенерируй ОЧЕНЬ короткое (1-2 предложения) дружелюбное сообщение для Telegram:\n"
        "- на русском\n"
        "- без эмодзи, если не попросили\n"
        "- упомяни название задачи\n"
        "- если есть описание/дедлайн/приоритет — аккуратно используй\n"
        "- тон: деловой, но поддерживающий\n\n"
        f"Название: {title}\n"
        f"Описание: {desc_part}\n"
        f"Дедлайн: {due_part}\n"
        f"Приоритет: {priority or ''}\n\n"
        "Текст сообщения:"
    )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Ты полезный ассистент."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 120,
    }

    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=20)
        if r.status_code >= 400:
            logger.warning("OpenAI error %s: %s", r.status_code, r.text[:300])
            return "Напоминание: пора заняться задачей. Проверьте дедлайн и приоритет."

        data = r.json()
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        text = (text or "").strip()
        return text if text else "Напоминание: пора заняться задачей. Проверьте дедлайн и приоритет."
    except Exception:
        logger.exception("OpenAI request failed")
        return "Напоминание: пора заняться задачей. Проверьте дедлайн и приоритет."
