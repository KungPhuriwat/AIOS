from __future__ import annotations

import json
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from urllib import request

from .retry import retry_call


@dataclass
class NotificationFanoutResult:
    local_log: str
    sent: list[str]
    failed: list[str]


class Notifier:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.attempts = int(os.getenv("AIOS_RETRY_ATTEMPTS", "3"))

    def notify(self, message: str) -> NotificationFanoutResult:
        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        line = f"[{ts}] {message}"
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

        sent: list[str] = []
        failed: list[str] = []

        for channel, sender in (
            ("discord", self._send_discord),
            ("line", self._send_line),
            ("email", self._send_email),
        ):
            try:
                did_send = retry_call(
                    lambda: sender(line),
                    attempts=self.attempts,
                    base_delay=0.7,
                )
                if did_send:
                    sent.append(channel)
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{channel}: {exc}")

        return NotificationFanoutResult(local_log=line, sent=sent, failed=failed)

    def status(self) -> dict[str, bool]:
        return {
            "discord": bool(os.getenv("AIOS_DISCORD_WEBHOOK", "").strip()),
            "line": bool(
                os.getenv("AIOS_LINE_CHANNEL_ACCESS_TOKEN", "").strip()
                and os.getenv("AIOS_LINE_TO", "").strip()
            ),
            "email": bool(
                os.getenv("AIOS_EMAIL_SMTP_HOST", "").strip()
                and os.getenv("AIOS_EMAIL_USERNAME", "").strip()
                and os.getenv("AIOS_EMAIL_PASSWORD", "").strip()
                and os.getenv("AIOS_EMAIL_TO", "").strip()
            ),
        }

    def _send_discord(self, message: str) -> bool:
        webhook = os.getenv("AIOS_DISCORD_WEBHOOK", "").strip()
        if not webhook:
            return False

        payload = {"content": message}
        req = request.Request(
            webhook,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        _post_json(req, timeout=15)
        return True

    def _send_line(self, message: str) -> bool:
        token = os.getenv("AIOS_LINE_CHANNEL_ACCESS_TOKEN", "").strip()
        to_user = os.getenv("AIOS_LINE_TO", "").strip()
        if not token or not to_user:
            return False

        payload = {
            "to": to_user,
            "messages": [{"type": "text", "text": message[:1000]}],
        }
        req = request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        _post_json(req, timeout=15)
        return True

    def _send_email(self, message: str) -> bool:
        smtp_host = os.getenv("AIOS_EMAIL_SMTP_HOST", "").strip()
        smtp_port = int(os.getenv("AIOS_EMAIL_SMTP_PORT", "587"))
        smtp_user = os.getenv("AIOS_EMAIL_USERNAME", "").strip()
        smtp_password = os.getenv("AIOS_EMAIL_PASSWORD", "").strip()
        to_addr = os.getenv("AIOS_EMAIL_TO", "").strip()
        if not (smtp_host and smtp_user and smtp_password and to_addr):
            return False

        msg = EmailMessage()
        msg["Subject"] = "AI OS Notification"
        msg["From"] = smtp_user
        msg["To"] = to_addr
        msg.set_content(message)

        def send_once() -> bool:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            return True

        return retry_call(send_once, attempts=self.attempts, base_delay=0.7)


def _post_json(req: request.Request, timeout: int) -> dict:
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}
