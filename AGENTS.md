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
