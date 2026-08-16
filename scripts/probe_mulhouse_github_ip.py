"""Teste si les IPs GitHub Actions atteignent mulhouse.fr.

Le crawl city_page depuis le runner échoue souvent (timeout / connexion
refusée) ; le sync quotidien passe donc par Vercel. Ce script dit si le
blocage est toujours là.
"""
from __future__ import annotations

import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request

TARGETS = [
    ("accueil", "https://www.mulhouse.fr/"),
    ("sitemap", "https://www.mulhouse.fr/page-sitemap.xml"),
    (
        "pdf",
        "https://www.mulhouse.fr/wp-content/uploads/2025/10/PLAN-STATIONNEMENT-CENTRE-VILLE.pdf",
    ),
    ("temoin m2a", "https://www.m2a.fr/"),
]

TIMEOUT_S = 15
UA = "Mulhouse68RAG/1.0 (+https://www.mulhouse68.fr; contact infojefweb@gmail.com)"


def public_ip() -> str:
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=8) as res:
            return res.read().decode("ascii").strip()
    except Exception as exc:
        return f"(inconnu: {exc})"


def probe(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as res:
            body = res.read(2048)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            return {
                "ok": 200 <= res.status < 400,
                "status": res.status,
                "bytes": len(body),
                "ms": elapsed_ms,
                "error": None,
            }
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        kind = type(exc).__name__
        cause = getattr(exc, "reason", None) or getattr(exc, "code", None) or exc
        return {
            "ok": False,
            "status": getattr(exc, "code", None),
            "bytes": 0,
            "ms": elapsed_ms,
            "error": f"{kind}: {cause}",
        }


def main() -> int:
    ip = public_ip()
    print(f"IP sortante du runner : {ip}")
    print(f"timeout : {TIMEOUT_S}s")
    print()

    rows = []
    for label, url in TARGETS:
        result = probe(url)
        mark = "OK " if result["ok"] else "KO "
        extra = result["error"] or f"HTTP {result['status']} {result['bytes']}o"
        print(f"{mark} {label:12} {result['ms']:5}ms  {extra}")
        print(f"         {url}")
        rows.append({"label": label, "url": url, **result})

    mulhouse = [r for r in rows if "mulhouse.fr" in r["url"]]
    blocked = not any(r["ok"] for r in mulhouse)
    temoin = next((r for r in rows if r["label"] == "temoin m2a"), None)

    print()
    if blocked:
        print("VERDICT : mulhouse.fr injoignable depuis cette IP GitHub.")
        if temoin and temoin["ok"]:
            print("         m2a.fr répond : le runner a bien un accès Internet.")
        print("         city_page doit rester sur Vercel.")
    else:
        print("VERDICT : au moins une URL mulhouse.fr répond depuis GitHub.")
        print("         le crawl city_page depuis le runner redevient envisageable.")

    summary = []
    summary.append(f"IP runner : {ip}")
    for r in rows:
        state = "OK" if r["ok"] else "KO"
        detail = r["error"] or f"HTTP {r['status']}"
        summary.append(f"{state} {r['label']} ({r['ms']}ms) {detail}")
    summary.append("BLOQUE" if blocked else "JOIGNABLE")

    env_path = __import__("os").environ.get("GITHUB_ENV")
    if env_path:
        with open(env_path, "a", encoding="utf-8") as handle:
            handle.write("MULHOUSE_IP_BODY<<IP_EOF\n")
            handle.write("\n".join(summary) + "\n")
            handle.write("IP_EOF\n")
            handle.write(f"MULHOUSE_IP_BLOCKED={'true' if blocked else 'false'}\n")

    step = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as handle:
            handle.write("\n### Test IP GitHub → mulhouse.fr\n\n")
            handle.write("\n".join(f"- {line}" for line in summary) + "\n")

    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
