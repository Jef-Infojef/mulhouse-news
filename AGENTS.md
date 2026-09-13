# AGENTS.md — Mulhouse News

**Port** : 3006

## Base de données & Déploiements Convex

- **Compte Convex** : `infojefweb@gmail.com` (team : `jean-frederic-baechler`, projet : `mulhouse-news`)
- **Déploiement actif / Production** : `academic-spoonbill-914`
  - URL : `https://academic-spoonbill-914.convex.cloud`
  - Utilisé par **mulhouse-news**, **assocommercants** et alimenté en continu par les scrapers.
- **Déploiement Dev (obsolète)** : `friendly-chicken-952` — **Ne pas utiliser** (déploiement dev historique mis en pause par Convex pour inactivité). Ne rien toucher sur le dashboard, l'environnement local `.env.local` pointe désormais directement sur `academic-spoonbill-914`.

## Logs WinLauncher (dev local)

Lancé depuis WinLauncher (port 3006), le stdout est dans
`C:\dev\WinLauncher\logs\Mulhouse_News.log`.
Repli si plus récent : `C:\dev\WinLauncher\target\release\logs\Mulhouse_News.log`.
Dernière Q/R chat : depuis la fin, `[DEBUG chat] message:` puis `[DEBUG chat] answer:`.
Table complète : `C:\dev\WinLauncher\AGENTS.md`.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
