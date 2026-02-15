from __future__ import annotations

from pathlib import Path

from .core.env_loader import load_env_file
from .core.models import TaskRequest
from .core.orchestrator import AIOSOrchestrator


HELP = """
AI OS CLI
รูปแบบ:
- code <language>: <prompt>
- ops: <prompt>
- benchmark <language>
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


def main() -> None:
    loaded_env = load_env_file(".env")
    app = AIOSOrchestrator(data_dir=Path("data"))
    print(HELP)
    if loaded_env:
        print(f"loaded .env keys: {len(loaded_env)}")

    while True:
        line = input("ai-os> ").strip()
        if line in {"exit", "quit"}:
            print("bye")
            return

        if line.startswith("benchmark "):
            language = line.split(" ", 1)[1].strip()
            print(app.run_benchmark(language))
            continue

        if line == "show dashboard":
            print(app.show_dashboard())
            continue

        if line == "show policy":
            print(app.show_policy_status())
            continue

        if line == "show skills":
            print(app.show_skills())
            continue

        if line == "show audit":
            for item in app.show_audit():
                print(item)
            continue

        if line == "show audit status":
            print(app.show_audit_status())
            continue

        if line == "show provider":
            print(app.show_provider_status())
            continue

        if line == "show notify status":
            print(app.show_notify_status())
            continue

        if line == "test provider":
            print(app.test_provider())
            continue

        req = parse(line)
        if req is None:
            continue

        approved = False
        if req.task_type == "ops":
            confirm = input("System command detected. Approve? [y/N]: ").strip().lower()
            approved = confirm == "y"

        print(app.handle(req, approved_by_user=approved))


if __name__ == "__main__":
    main()
