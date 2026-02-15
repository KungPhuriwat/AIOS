from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .api_server import run_api_server
from .core.env_loader import load_env_file
from .core.models import TaskRequest
from .core.orchestrator import AIOSOrchestrator


HELP = """
AI OS CLI
Commands:
- code <language>: <prompt>
- ops: <prompt>
- benchmark <language>
- train <language> [rounds]
- queue benchmark <language>
- queue train <language> [rounds]
- show jobs
- show job <job_id>
- show dashboard
- show policy
- show skills
- show audit
- show audit status
- show provider
- show notify status
- test provider
- exit
""".strip()


def parse(line: str) -> TaskRequest | None:
    raw = line.strip()
    if not raw:
        return None

    if raw.startswith("code "):
        left, _, prompt = raw.partition(":")
        _, language = left.split(" ", 1)
        return TaskRequest(
            task_type="code", prompt=prompt.strip(), language=language.strip()
        )

    if raw.startswith("ops:"):
        return TaskRequest(task_type="ops", prompt=raw.split(":", 1)[1].strip())

    return TaskRequest(task_type="code", prompt=raw, language="python")


def run_single_command(
    app: AIOSOrchestrator,
    line: str,
    auto_approve_ops: bool = False,
    interactive_ops_confirm: bool = True,
) -> Any:
    cmd = line.strip()
    if not cmd:
        return None

    if cmd.startswith("benchmark "):
        language = cmd.split(" ", 1)[1].strip()
        return app.run_benchmark(language)

    if cmd.startswith("train "):
        parts = cmd.split()
        language = parts[1].strip() if len(parts) > 1 else "python"
        rounds = 3
        if len(parts) > 2:
            try:
                rounds = int(parts[2])
            except ValueError:
                rounds = 3
        return app.run_training_cycle(language=language, rounds=rounds)

    if cmd.startswith("queue benchmark "):
        language = cmd.split(" ", 2)[2].strip()
        return app.submit_benchmark_job(language)

    if cmd.startswith("queue train "):
        parts = cmd.split()
        language = parts[2].strip() if len(parts) > 2 else "python"
        rounds = 3
        if len(parts) > 3:
            try:
                rounds = int(parts[3])
            except ValueError:
                rounds = 3
        return app.submit_training_job(language=language, rounds=rounds)

    if cmd == "show jobs":
        return app.list_jobs()

    if cmd.startswith("show job "):
        job_id = cmd.split(" ", 2)[2].strip()
        return app.get_job(job_id)

    if cmd == "show dashboard":
        return app.show_dashboard()

    if cmd == "show policy":
        return app.show_policy_status()

    if cmd == "show skills":
        return app.show_skills()

    if cmd == "show audit":
        return app.show_audit()

    if cmd == "show audit status":
        return app.show_audit_status()

    if cmd == "show provider":
        return app.show_provider_status()

    if cmd == "show notify status":
        return app.show_notify_status()

    if cmd == "test provider":
        return app.test_provider()

    req = parse(cmd)
    if req is None:
        return None

    approved = auto_approve_ops
    if req.task_type == "ops" and not auto_approve_ops and interactive_ops_confirm:
        confirm = input("System command detected. Approve? [y/N]: ").strip().lower()
        approved = confirm == "y"

    return app.handle(req, approved_by_user=approved)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI OS CLI")
    parser.add_argument(
        "--run",
        action="append",
        default=[],
        help="Run a command non-interactively. Can be repeated.",
    )
    parser.add_argument(
        "--approve-ops",
        action="store_true",
        help="Auto-approve ops commands in --run mode.",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Do not print help banner.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run AI OS HTTP API server.",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="API host for --serve mode."
    )
    parser.add_argument(
        "--port", type=int, default=8787, help="API port for --serve mode."
    )
    parser.add_argument(
        "--api-token",
        default=None,
        help="Optional bearer token for API auth. Falls back to AIOS_API_TOKEN.",
    )
    return parser


def main() -> None:
    args = _build_arg_parser().parse_args()

    loaded_env = load_env_file(".env")
    app = AIOSOrchestrator(data_dir=Path("data"))

    if args.serve:
        run_api_server(app, host=args.host, port=args.port, token=args.api_token)
        return

    if args.run:
        for line in args.run:
            result = run_single_command(
                app,
                line,
                auto_approve_ops=args.approve_ops,
                interactive_ops_confirm=False,
            )
            if result is not None:
                print(result)
        return

    if not args.no_banner:
        print(HELP)
        if loaded_env:
            print(f"loaded .env keys: {len(loaded_env)}")

    while True:
        line = input("ai-os> ").strip()
        if line in {"exit", "quit"}:
            print("bye")
            return

        result = run_single_command(app, line)
        if result is None:
            continue

        if line == "show audit" and isinstance(result, list):
            for item in result:
                print(item)
        else:
            print(result)


if __name__ == "__main__":
    main()
