from __future__ import annotations

import requests

from backend.app.core.settings import Settings


class AiSummaryService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_summary(self, raw_text: str) -> str | None:
        if not raw_text.strip():
            return None

        prompt = f"""
Ты анализируешь документацию по закупке.

Ответь строго на русском языке.
Сделай:
1. Краткую выжимку закупки.
2. Ключевые требования к поставщику.
3. Основные риски.
4. Что проверить перед участием.
5. Короткий вывод.

Текст документа:
{raw_text[:12000]}
"""

        payload = {
            "model": self.settings.ollama_model,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты помощник по анализу тендерной документации. Всегда отвечай только на русском языке.",
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }

        try:
            response = requests.post(
                self.settings.ollama_url,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
        except Exception:
            return None

        data = response.json()
        return data.get("message", {}).get("content")
