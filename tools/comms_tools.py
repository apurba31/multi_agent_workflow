from __future__ import annotations

import re

from langchain_core.tools import tool
from loguru import logger

from config.settings import settings


def _escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special)}])", r"\\\1", text)


@tool
def format_markdown(content: str, title: str = "") -> str:
    """Format raw text into clean Telegram MarkdownV2."""
    lines: list[str] = []
    if title:
        lines.append(f"*{_escape_markdown_v2(title)}*\n")
    for paragraph in content.split("\n\n"):
        lines.append(_escape_markdown_v2(paragraph.strip()))
    return "\n\n".join(lines)


@tool
def format_html(content: str, title: str = "") -> str:
    """Convert content into an HTML email body."""
    html_parts = ["<html><body>"]
    if title:
        html_parts.append(f"<h2>{title}</h2>")
    for paragraph in content.split("\n\n"):
        html_parts.append(f"<p>{paragraph.strip()}</p>")
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


@tool
def send_telegram(message: str, parse_mode: str = "MarkdownV2") -> str:
    """Send a message to the configured Telegram chat."""
    logger.info("Sending Telegram message ({} chars)", len(message))
    try:
        import httpx

        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return "Telegram not configured — missing bot token or chat ID."

        chunks = [message[i : i + 4096] for i in range(0, len(message), 4096)]
        results: list[str] = []
        for chunk in chunks:
            resp = httpx.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": chunk,
                    "parse_mode": parse_mode,
                },
                timeout=10,
            )
            data = resp.json()
            if data.get("ok"):
                msg_id = data["result"]["message_id"]
                results.append(f"Sent (message_id={msg_id})")
            else:
                results.append(f"Failed: {data.get('description', 'unknown error')}")
        return " | ".join(results)
    except Exception as exc:
        logger.error("Telegram send failed: {}", exc)
        return f"Telegram error: {exc}"


@tool
def send_email(subject: str, body: str, html: bool = False) -> str:
    """Send an email via SMTP to the configured recipient."""
    logger.info("Sending email: {}", subject)
    try:
        import asyncio
        import email.message

        import aiosmtplib

        if not settings.smtp_user or not settings.smtp_password:
            return "Email not configured — missing SMTP credentials."

        msg = email.message.EmailMessage()
        msg["From"] = settings.email_from or settings.smtp_user
        msg["To"] = settings.email_to
        msg["Subject"] = subject
        if html:
            msg.set_content("See HTML version.")
            msg.add_alternative(body, subtype="html")
        else:
            msg.set_content(body)

        async def _send():
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                start_tls=True,
            )

        asyncio.run(_send())
        return f"Email sent to {settings.email_to}"
    except Exception as exc:
        logger.error("Email send failed: {}", exc)
        return f"Email error: {exc}"


COMMS_TOOLS = [format_markdown, format_html, send_telegram, send_email]
