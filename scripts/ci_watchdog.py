"""Filet anti-silence : cron mort, I/O Convex trop haut.

Sortie 0 = tout va. Sortie 1 = au moins une alerte (le job GitHub passe rouge).
N'envoie pas Telegram lui-même : le step appelant le fait.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import log_convex_io as io

MAX_SCRAPE_AGE_MIN = 90
MAX_KNOWLEDGE_AGE_H = 36
# 4 Go faisait sonner tout le 16/08 : le jour restait à 5,45 Go (fuite
# .take(500) déjà stoppée, ~2 Mo/scrape depuis). Plafond disable = 8 Go/j.
IO_DAY_WARN_GB = 6.0
IO_MONTH_WARN_GB = 64.0  # 80 % du plafond disable 80 Go


def gh_json(args: list[str]):
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gh failed")
    return json.loads(result.stdout) if result.stdout.strip() else None


def _parse_gh_time(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def last_success_age_min(workflow: str) -> float | None:
    """Minutes depuis la *fin* du dernier run vert de ce workflow.

    Ne pas prendre `gh run list --status success --limit 1` puis `createdAt` :
    l'ordre n'est pas garanti (mesuré 2026-09-10, run 34529407063 : 826 h alors
    que le scrape était vert 1 h plus tôt). On relit une page de runs et on
    garde le success au `updated_at` le plus récent (= fin du job).
    """
    repo = os.environ.get("GITHUB_REPOSITORY") or "Jef-Infojef/mulhouse-news"
    # Fenêtre récente : même si l'API rend les runs du plus ancien au plus
    # récent, max(updated_at) dans ces 3 jours est le vrai dernier vert.
    since = (datetime.now(timezone.utc) - timedelta(days=3)).date().isoformat()
    payload = gh_json(
        [
            "api",
            f"repos/{repo}/actions/workflows/{workflow}/runs?per_page=100&created=>={since}",
        ]
    )
    runs = (payload or {}).get("workflow_runs") or []
    successes = [
        run
        for run in runs
        if run.get("conclusion") == "success" and run.get("status") == "completed"
    ]
    if not successes:
        return None
    latest = max(
        successes,
        key=lambda run: _parse_gh_time(run.get("updated_at") or run.get("created_at")),
    )
    finished = _parse_gh_time(latest.get("updated_at") or latest["created_at"])
    age = (datetime.now(timezone.utc) - finished).total_seconds() / 60
    print(
        f"[watchdog] {workflow} dernier vert il y a {age:.0f} min "
        f"({finished.isoformat()}) {latest.get('html_url') or latest.get('id')}"
    )
    return age


def main() -> int:
    alerts: list[str] = []

    scrape_age = last_success_age_min("scrape-news.yml")
    if scrape_age is None:
        alerts.append("Scrape Mulhouse News : aucun run vert connu")
    elif scrape_age > MAX_SCRAPE_AGE_MIN:
        alerts.append(f"Scrape Mulhouse News : dernier succès il y a {scrape_age / 60:.1f} h (seuil {MAX_SCRAPE_AGE_MIN} min)")

    kn_age = last_success_age_min("m68-knowledge-sync.yml")
    if kn_age is None:
        alerts.append("M68 Knowledge Sync : aucun run vert connu (YAML invalide / cron arrêté ?)")
    elif kn_age > MAX_KNOWLEDGE_AGE_H * 60:
        alerts.append(f"M68 Knowledge Sync : dernier succès il y a {kn_age / 60:.1f} h (seuil {MAX_KNOWLEDGE_AGE_H} h)")

    try:
        usage = io.fetch_usage()
        day = io.metric(usage, "databaseIoGb", "current_day")
        month = io.metric(usage, "databaseIoGb", "current_month")
        print(f"[watchdog] Convex I/O  jour={io.fmt_gb(day)}  mois={io.fmt_gb(month)}")
        if day >= IO_DAY_WARN_GB:
            alerts.append(f"Convex Database I/O jour = {io.fmt_gb(day)} (seuil {IO_DAY_WARN_GB:.0f} Go)")
        if month >= IO_MONTH_WARN_GB:
            alerts.append(f"Convex Database I/O mois = {io.fmt_gb(month)} (seuil {IO_MONTH_WARN_GB:.0f} Go / plafond 80)")
    except Exception as exc:
        alerts.append(f"Impossible de lire l'I/O Convex : {exc}")

    if not alerts:
        print("[watchdog] OK")
        return 0

    print("[watchdog] ALERTES :")
    for line in alerts:
        print(f"  - {line}")
    summary = os.environ.get("GITHUB_ENV")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("WATCHDOG_BODY<<WD_EOF\n")
            handle.write("\n".join(f"· {a}" for a in alerts) + "\n")
            handle.write("WD_EOF\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
