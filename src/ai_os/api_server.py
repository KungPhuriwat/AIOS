from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .core.models import TaskRequest
from .core.orchestrator import AIOSOrchestrator


def run_api_server(
    app: AIOSOrchestrator, host: str, port: int, token: str | None = None
) -> None:
    server = create_api_server(app, host, port, token)
    print(f"AI OS API listening on http://{host}:{port}")
    server.serve_forever()


def create_api_server(
    app: AIOSOrchestrator,
    host: str = "127.0.0.1",
    port: int = 8787,
    token: str | None = None,
) -> ThreadingHTTPServer:
    token = token if token is not None else os.getenv("AIOS_API_TOKEN", "").strip()
    handler = _make_handler(app, token)
    return ThreadingHTTPServer((host, port), handler)


def _make_handler(app: AIOSOrchestrator, token: str):
    class AIOSAPIHandler(BaseHTTPRequestHandler):
        _app = app
        _token = token

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._json({"ok": True, "service": "aios-api"})
                return

            if not self._authorized():
                self._json(
                    {"ok": False, "error": "unauthorized"},
                    status=HTTPStatus.UNAUTHORIZED,
                )
                return

            routes = {
                "/dashboard": self._app.show_dashboard,
                "/policy": self._app.show_policy_status,
                "/skills": self._app.show_skills,
                "/provider": self._app.show_provider_status,
                "/notify": self._app.show_notify_status,
                "/audit/status": self._app.show_audit_status,
            }
            handler = routes.get(self.path)
            if handler is None:
                self._json(
                    {"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND
                )
                return
            self._json(handler())

        def do_POST(self) -> None:  # noqa: N802
            if not self._authorized():
                self._json(
                    {"ok": False, "error": "unauthorized"},
                    status=HTTPStatus.UNAUTHORIZED,
                )
                return

            payload = self._read_json()
            if payload is None:
                self._json(
                    {"ok": False, "error": "invalid_json"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            if self.path == "/code":
                prompt = str(payload.get("prompt", "")).strip()
                language = str(payload.get("language", "python")).strip()
                out = self._app.handle(
                    TaskRequest(task_type="code", prompt=prompt, language=language)
                )
                self._json(out)
                return

            if self.path == "/ops":
                prompt = str(payload.get("prompt", "")).strip()
                approved = bool(payload.get("approved_by_user", False))
                out = self._app.handle(
                    TaskRequest(task_type="ops", prompt=prompt),
                    approved_by_user=approved,
                )
                self._json(out)
                return

            if self.path == "/benchmark":
                language = str(payload.get("language", "python")).strip()
                out = self._app.run_benchmark(language)
                self._json(out)
                return

            if self.path == "/train":
                language = str(payload.get("language", "python")).strip()
                rounds = int(payload.get("rounds", 3))
                out = self._app.run_training_cycle(language=language, rounds=rounds)
                self._json(out)
                return

            if self.path == "/provider/test":
                self._json(self._app.test_provider())
                return

            self._json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, _format: str, *args: Any) -> None:
            return

        def _authorized(self) -> bool:
            if not self._token:
                return True
            header = self.headers.get("Authorization", "")
            expected = f"Bearer {self._token}"
            return header == expected

        def _read_json(self) -> dict[str, Any] | None:
            length_raw = self.headers.get("Content-Length", "0")
            try:
                length = int(length_raw)
            except ValueError:
                return None

            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return None

        def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return AIOSAPIHandler
