import json
import threading
from pathlib import Path
from urllib import request
from urllib.error import HTTPError

from src.ai_os.api_server import create_api_server
from src.ai_os.core.orchestrator import AIOSOrchestrator


def _urlopen_json(
    url: str,
    method: str = "GET",
    payload: dict | None = None,
    headers: dict | None = None,
) -> tuple[int, dict]:
    data = None
    req_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body)


def test_api_health_and_auth(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    server = create_api_server(app, host="127.0.0.1", port=0, token="secret")
    port = server.server_port

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        s, body = _urlopen_json(f"http://127.0.0.1:{port}/health")
        assert s == 200
        assert body["ok"]

        s, body = _urlopen_json(f"http://127.0.0.1:{port}/dashboard")
        assert s == 401
        assert body["error"] == "unauthorized"

        s, body = _urlopen_json(
            f"http://127.0.0.1:{port}/dashboard",
            headers={"Authorization": "Bearer secret"},
        )
        assert s == 200
        assert "skills_count" in body
    finally:
        server.shutdown()
        server.server_close()


def test_api_code_and_benchmark(tmp_path: Path) -> None:
    app = AIOSOrchestrator(tmp_path)
    server = create_api_server(app, host="127.0.0.1", port=0, token="")
    port = server.server_port

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        s, code_body = _urlopen_json(
            f"http://127.0.0.1:{port}/code",
            method="POST",
            payload={"language": "python", "prompt": "write tests"},
        )
        assert s == 200
        assert code_body["ok"]
        assert "skill" in code_body

        s, bench_body = _urlopen_json(
            f"http://127.0.0.1:{port}/benchmark",
            method="POST",
            payload={"language": "python"},
        )
        assert s == 200
        assert bench_body["ok"]
        assert "benchmark" in bench_body

        s, train_body = _urlopen_json(
            f"http://127.0.0.1:{port}/train",
            method="POST",
            payload={"language": "python", "rounds": 2},
        )
        assert s == 200
        assert train_body["ok"]
        assert train_body["rounds"] == 2
    finally:
        server.shutdown()
        server.server_close()
