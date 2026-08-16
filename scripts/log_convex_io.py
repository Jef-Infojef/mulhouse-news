"""Snapshot Convex usage (Database I/O) avant/après un job GitHub Actions.

Lit le JSON produit par `npx convex deployment usage --json`.
Sans mesure « avant », n'affiche que le cumul jour/mois.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BEFORE_PATH = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "convex-usage-before.json"


def fetch_usage() -> dict:
    env = os.environ.copy()
    result = subprocess.run(
        ["npx", "convex", "deployment", "usage", "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout or "convex usage failed\n")
        raise SystemExit(result.returncode)
    return json.loads(result.stdout)


def metric(blob: dict, name: str, window: str) -> float:
    return float(blob["metrics"][name]["usage"][window])


def fmt_gb(value: float) -> str:
    if abs(value) < 0.0005:
        return "0 Mo"
    mb = value * 1024
    if mb < 1:
        return f"{mb * 1024:.0f} Ko"
    if mb < 900:
        return f"{mb:.1f} Mo"
    return f"{value:.3f} Go"


def write_summary(lines: list[str]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n### Convex Database I/O\n\n")
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "after"
    if mode == "before":
        usage = fetch_usage()
        BEFORE_PATH.write_text(json.dumps(usage), encoding="utf-8")
        day = metric(usage, "databaseIoGb", "current_day")
        month = metric(usage, "databaseIoGb", "current_month")
        print(f"[convex-io] avant  jour={fmt_gb(day)}  mois={fmt_gb(month)}")
        return 0

    after = fetch_usage()
    day = metric(after, "databaseIoGb", "current_day")
    month = metric(after, "databaseIoGb", "current_month")
    calls_day = metric(after, "functionCalls", "current_day")
    calls_month = metric(after, "functionCalls", "current_month")

    delta_io = None
    delta_calls = None
    if BEFORE_PATH.exists():
        before = json.loads(BEFORE_PATH.read_text(encoding="utf-8"))
        delta_io = day - metric(before, "databaseIoGb", "current_day")
        delta_calls = calls_day - metric(before, "functionCalls", "current_day")

    lines = [
        f"ce run : {fmt_gb(delta_io) if delta_io is not None else '(pas de snapshot avant)'}",
        f"jour   : {fmt_gb(day)}",
        f"mois   : {fmt_gb(month)}",
        f"appels : +{int(delta_calls) if delta_calls is not None else '?'} (jour {int(calls_day)}, mois {int(calls_month)})",
    ]
    print("[convex-io] " + "  |  ".join(lines))
    write_summary([f"- {line}" for line in lines])

    try:
        import convex_client

        if convex_client.use_convex():
            now = datetime.now(timezone.utc)
            convex_client.insert_scraping_log(
                started_at=now,
                finished_at=now,
                status="CONVEX_IO",
                details={
                    "databaseIoGbDelta": delta_io,
                    "databaseIoGbDay": day,
                    "databaseIoGbMonth": month,
                    "functionCallsDelta": delta_calls,
                    "functionCallsDay": calls_day,
                    "githubRun": os.environ.get("GITHUB_RUN_ID"),
                },
            )
    except Exception as exc:
        print(f"[convex-io] log Convex ignoré: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
