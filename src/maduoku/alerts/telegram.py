from __future__ import annotations

import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_message(token: str, chat_id: str, text: str, timeout: float = 10.0) -> None:
    if not token or not chat_id:
        raise ValueError("Telegram bot_token and chat_id are required")

    resp = requests.post(
        TELEGRAM_API.format(token=token),
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=timeout,
    )
    resp.raise_for_status()
