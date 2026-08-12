# Plan de migration Supabase → Convex

> Statut : **DÉCISIONS VALIDÉES** (12/08/2026) — Phase 0 en cours.
> Objectif : sortir du quota egress Supabase (5.5 GB/cycle) et simplifier l'ops.
> Alternative conservatrice : fixes d'egress déjà déployés (commit `d6a6fc1`) + Supabase Pro ($25/mois, 250 GB).

## 0. Décisions validées (12/08/2026)

| # | Point dur | Décision |
|---|---|---|
| 1 | GO/NO-GO | **GO — migration Convex** |
| 2 | Exécution des scrapers | **Hybride** : GitHub Actions exécute le réseau, Convex stocke (mutations via endpoints HTTP) |
| 3 | MulhouseGPT | **Adapter directement** : lectures SQL remplacées par le client Convex (pas de bridge temporaire) |
| 4 | Scripts one-shot | **A — archiver** dans `scripts/legacy/` + doc SQL de substitution |

## 1. État des lieux (inventaire réalisé le 12/08/2026)

### Supabase (projet `wmvjpdedrfyttixdkzpi`), tables Prisma
| Table | Rôle | Volume estimé | Priorité migration |
|---|---|---|---|
| `Article` | Articles presse scrapés (contenu complet) | gros (10k+ lignes, contenu HTML) | 1 |
| `ArticleImage` | Images de galerie par article | moyen (lien B2) | 1 |
| `NewsArticle` | Articles du site mulhouse68.fr | moyen | 1 |
| `AppConfig` | Cookies EBRA, cooldowns de retry, rate-limit login | petit | 1 |
| `ScrapingLog` | Logs d'exécution des scrapers | moyen (croît vite) | 2 |
| `ArticleGoogleTag`, `NewsTag`, `NewsArticleTag` | Tags/JDS | petit | 2 |
| `WeatherHistory` | Historique météo | petit | 3 |

### Code qui touche la base
- **Next.js** : `lib/prisma.ts` (client), `app/actions.ts` (~10 fonctions Prisma : article, appConfig, scrapingLog), route `app/mplus-mag/download/[filename]/route.ts`. C'est la **partie la plus simple** (~10 fonctions à réécrire).
- **~40 scripts Python** avec SQL brut `psycopg2` : `scrape_*.py` (actifs en prod), `rescue_*.py` / `repair_*.py` / `backfill_*.py` (one-shot), `rag_sync_articles.py`, `log_github_failure.py`, `check_ebra_cookie.py`, `sync_article_images` etc. → **le plus gros du chantier** (Convex n'a pas de SQL).
- **17 workflows GitHub Actions** (cron : scrape `*/5`, publish `*/15`, airport `h * * * *`, knowledge daily, backups `pg_dump` hebdo+quotidien, keep-alive, alertes Telegram).
- **MulhouseGPT (autre repo)** : lit `NEWS_DATABASE_URL` (Supabase, user `mulhousegpt_readonly`) pour ses syncs RAG. À migrer ou à maintenir en pont lecture seule.
- **Images** : servies depuis **B2 Backblaze** (pas Supabase Storage) — le pont images n'est **pas** affecté par la migration DB.

### Contraintes détectées
- Pas de SQL chez Convex : chaque script doit réécrire ses requêtes en queries/mutations.
- Cookies de session paywall EBRA (`AppConfig`) : mécanique de cooldown récente (fix A) à porter telle quelle.
- Recherche plein-texte (index FTS français sur `KnowledgeChunk`) : côté Convex c'est Aiven (RAG), pas touché. La recherche site (getLatestArticles) utilise des filtres simples → index Convex suffisent.
- Concurrence : scrapers qui écrivent en même temps → mutations Convex sérialisées, plus sûr qu'aujourd'hui.

## 2. Architecture cible

```
Vercel (Next.js, lectures/écritures admin)         GitHub Actions (scrapers)
        │  queries/mutations via ConvexProvider           │  HTTP actions/endpoints
        ▼                                                ▼
┌───────────────────────────────  CONVEX  ───────────────────────────────┐
│  Backend : schema TS + queries/mutations/actions + cron natif          │
│  - collections : Article, ArticleImage, NewsArticle, AppConfig,        │
│    ScrapingLog, NewsTag, ArticleGoogleTag, WeatherHistory              │
│  - cron Convex : remplace les schedules GitHub (scrape, publish, etc.) │
│  - (option) file storage Convex pour les images si B2 doit être quitté │
└───────────────────────────────────────────────────────────────────────┘
        │ reads (HTTP)                                    │ SQL (inchangé)
        ▼                                                 ▼
   MulhouseGPT (pont lecture seule)                  Aiven PostgreSQL (RAG)
   B2 Backblaze (images, inchangé)                   B2 (backups)
```

- Les **scrapers Python** gardent leur logique de scraping (BeautifulSoup, curl_cffi, cookies) mais remplacent `psycopg2` par des appels HTTPS aux **endpoints Convex** (mutations `addArticle`, `upsertArticleImages`, `setCooldown`…).
- Les **crons GitHub** deviennent des **crons Convex** (actions `scrapeNews`, `publishScheduled`…) — GitHub Actions ne garde que backups B2 + alertes Telegram (ou tout passe en Convex, à arbitrer).

## 3. Phases

### Phase 0 — Décision & spike (1–2 semaines) ✅ FAITE (12/08/2026)
- [x] POC : projet Convex `convex init` sur le repo, schéma minimal (`articles`, `appConfig`, `articleImages`)
- [x] Export/import de test : **100 articles Supabase → Convex validé** (compteurs OK, idempotence vérifiée au 2e passage)
- [x] Backend local `convex dev` en arrière-plan (port 3210, watch actif) ; démarrage sans prompt via pipe `"Y" | npx convex dev` (script : `C:\Users\HP\AppData\Local\Temp\opencode\start-convex-dev.ps1`)
- [ ] Valider les limites **Starter (gratuit)** : 1M calls/mois, 0.5 GB DB, 1 GB bandwidth, 20 GB-h action compute, 1 GB egress
  - Volume cible estimé : app → qq 10k calls/jour OK ; **scrapers */5 = 8 640 runs/mois** → doivent appeler des mutations, pas des pages (calls comptés par mutation)
  - Egress : si les lectures site restent sur Vercel→Convex ~0.5–1 GB/mois, c'est limite → prévoir **Pro $25/dev/mois** (25M calls, 50 GB DB, 50 GB egress, 250 GB-h)
- [ ] GO/NO-GO final sur le plan tarifaire (déjà GO sur la migration)

### Phase 1 — Fondations Convex (2–3 semaines) ✅ FAITE (12/08/2026)
- [x] Schéma TS complet des 9 collections (voir `convex/schema.ts` — note : refs en `v.string()` avec UUID Supabase d'origine, timestamps optionnels pour tolérer les docs du spike)
- [x] Migration complète des données : `scripts/migrate_supabase_to_convex.ts` (lots dynamiques, idempotent) — **27 102 articles, 28 066 ArticleImage, 11 530 ScrapingLog, 2 197 ArticleGoogleTag, 5 NewsTag, 2 AppConfig** — compteurs Supabase = Convex à ±0 (WeatherHistory inexistante en prod, NewsArticle vide)
- [x] Script de vérification : `scripts/migrate_check.ts` (comparaison par table, pagination)
- [x] CI : `.github/workflows/deploy-convex.yml` (push main + dispatch ; secret `CONVEX_DEPLOY_KEY` créé via `npx convex deployment token create github-actions --deployment friendly-chicken-952` et enregistré dans GitHub) — **testé : `npx convex deploy` via la deploy key → Deployed OK**
- [x] Déploiement cloud créé : projet `mulhouse-news` (équipe jean-frederic-baechler), dev deployment `friendly-chicken-952` (`https://friendly-chicken-952.convex.cloud`), URL dans `.env.local`
- [x] Backfill `supabaseId` (UUID Supabase d'origine) sur `articles` + `newsTags` — nécessaire pour les jointures articleGoogleTags/articleImages ; inclus dans le script de migration

### Phase 2 — Application Next.js (2–3 semaines) ✅ FAITE (12/08/2026)
- [x] `lib/prisma.ts` converti en client `ConvexHttpClient` (le nom de fichier est conservé pour ne pas casser les imports ; Prisma reste dans le build jusqu'à la Phase 3 pour les scripts GitHub Actions)
- [x] `app/actions.ts` réécrit : toutes les fonctions passent par Convex (getLatestArticles, getArticleContent, getScrapingLogs, getAppConfig, updateAppConfig, testEbraConnection, deleteArticle, rate-limit login) — signatures exportées inchangées
- [x] Fonctions Convex créées : `convex/app.ts` (queries/mutations/action, recherche FTS title/description/source, cascade manuelle deleteArticle, action réseau testEbraConnection, backfill supabaseId) + `convex/stats.ts`, `convex/migrations.ts`
- [x] Schéma enrichi : champ `supabaseId`, searchIndex FTS (title/description/source, `content` exclu volontairement), index par relation
- [x] Route `mplus-mag/download/[filename]` : inchangée (lit le FS local/B2, hors périmètre DB)
- [x] Validation : `tsc --noEmit` OK, lint OK sur les fichiers Phase 2 (les 165 problèmes eslint sont préexistants sur d'autres fichiers), push cloud OK (`convex dev --once` → Convex functions ready), smoke test des 6 fonctions OK (200 articles, recherche, logs, AppConfig CRUD)
- [x] Variables Vercel : `NEXT_PUBLIC_CONVEX_URL` ajoutée sur **Production, Preview, Development** (via `vercel env add` + API REST pour Preview) — projet Vercel `mulhouse-actu` (id `prj_MDJheflx5Jxxk9T5U8k1T6FiVNKw`)
- [ ] À tester en ligne : rendu admin/production après redéploiement Vercel
- [ ] Retirer Prisma & `DATABASE_URL` du build Vercel — **reporté Phase 3** (les scripts GitHub Actions utilisent encore Prisma via `scripts/*.ts`)

### Phase 3 — Scrapers & syncs Python (3–4 semaines, le gros morceau)
- [x] Créer le module Python `convex_client.py` (POST sur les endpoints mutations, retry, auth token)
- [x] Port des **scrapers actifs** (ceux des workflows) :
  `scrape_and_seed.py`, `scrape_mplusinfo.py`, `scrape_periscope_seed.py`, `scrape_mag_m2a.py`, `scrape_content_full.py` (incl. cooldowns AppConfig → mutation `setAppConfig`), `scrape_outings.py`, `scrape_news.py`, `publish-scheduled.ts` (via assocommercants)
- [x] `rag_sync_articles.py` : lit Convex (queries) + écrit Aiven (SQL inchangé)
- [x] `log_github_failure.py` / `check_ebra_cookie.py` : port en mutations
- [x] Scripts one-shot (`rescue_*`, `repair_*`, `backfill_*`, 30+) : **ne pas porter** — archivage dans `scripts/legacy/` (127 fichiers) ; documenter l'alternative (SQL via Convex dashboard/Supabase export)
- [ ] Compatibilité MulhouseGPT : pont `NEWS_DATABASE_URL` → soit MulhouseGPT lit l'API Convex (client TS), soit on maintient un sync BDD → Supabase lecteur temporaire

### Phase 3 — avancement (12/08/2026)

**Fichiers créés / modifiés :**
- `convex/scrapers.ts` — **nouveau** : fonctions Convex consommées par les scrapers Python (HTTP `/api/query` + `/api/mutation`, auth `Authorization: Convex <deploy key>`)
- `scripts/convex_client.py` — **nouveau** : client Python typé des helpers (upsert_article, get_article_links, get_articles_short_content, app_config, insert_scraping_log, get_recent_articles_with_content, delete_article_by_link…)
- `scripts/legacy/` — **nouveau** : 127 scripts one-shot archivés (`rescue_*`, `repair_*`, `backfill_*`, `diagnose_*`, `decode_*`, `fix_*`, `report_*`, `stats_*`, `monthly_balance_*`, `view_*`, scrapers historiques…) + `README.md` expliquant leur usage Supabase
- Portés en **dual-mode** (`USE_CONVEX=1`/`CONVEX_DEPLOY_KEY` → Convex, sinon psycopg2) : `scrape_and_seed.py`, `scrape_mplusinfo.py`, `scrape_periscope_seed.py`, `scrape_mag_m2a.py`, `scrape_content_full.py`, `rag_sync_articles.py`, `log_github_failure.py`, `check_ebra_cookie.py`
- `convex/_generated/` — régénéré (module `scrapers`)

**Fonctions Convex créées (chemins publics, `convex/scrapers.ts`) :**
- Mutations : `scrapers:upsertArticle` (dédup `link`, patch partiel + `supabaseId`), `scrapers:upsertArticleImages` (dédup `(articleId, url)`), `scrapers:upsertArticleGoogleTags`, `scrapers:insertScrapingLog`, `scrapers:deleteArticleByLink` (cascade images/tags)
- Queries : `scrapers:getArticleByLink`, `scrapers:getArticleLinks` (paginée, filtre `source`), `scrapers:getArticlesShortContent` (hidden=false, content court/null, X heures), `scrapers:getArticleByTitleRecent`, `scrapers:getArticleByImage`, `scrapers:getArticlesMissingCaptions`, `scrapers:getNewsTags`, `scrapers:getRecentArticlesWithContent` (RAG)
- Réutilisées depuis `convex/app.ts` (déjà en place) : `app:getAppConfig`, `app:setAppConfig`, `app:deleteAppConfig`
- **NB API** : l'endpoint `/api/execute` du plan n'existe pas en Convex v1.43 — les appels passent par `/api/query` (queries) et `/api/mutation` (mutations), corps `{"path", "format":"json", "args"}`. Convex rejette `null` sur `v.optional(v.string())` → les helpers Python omettent les champs `None`.

**Scripts non portés et pourquoi :**
- `scrape_outings.py` (+ `outing_scrape_utils.py`) : tables `Outing`/`OutingCategory`/`OutingTag`/`ScrapeLog` **absentes du schéma Convex** (non migrées en Phase 1) → reste 100 % Supabase, à porter dans une phase ultérieure si les tables sorties sont migrées
- `scrape_news.py` : n'existe pas dans le repo (whitelist mentionnée mais fichier absent)
- Scripts TS `download_images.ts` / `sync_to_b2.ts` : **hors périmètre Phase 3 bis** — continuent de tourner sur Prisma/Supabase (appelés par `scrape_content_full.py`, inchangés)
- Scripts one-shot archivés dans `scripts/legacy/` : restent utilisables contre Supabase (voir `scripts/legacy/README.md`)
- Workflows m68-* : référence des scripts `.ts` d'un autre repo (MulhouseGPT), non concernés

**Dual-mode `USE_CONVEX`** — exemple de bloc (même pattern dans chaque script porté) :
```python
import convex_client
USE_CONVEX = convex_client.use_convex()   # True si CONVEX_DEPLOY_KEY + URL définies
...
if USE_CONVEX:
    convex_client.upsert_article({...})
else:
    cur.execute('INSERT INTO "Article" (...) VALUES (...)')
```

**Reste à faire (Phase 3 bis / Phase 4) :**
- Phase 3 bis : porter `download_images.ts` / `sync_to_b2.ts` (Prisma → Convex) pour retirer `DATABASE_URL` du build
- Phase 4 : ajouter les secrets GHA `CONVEX_DEPLOY_KEY` + `NEXT_PUBLIC_CONVEX_URL` et `USE_CONVEX=1` aux workflows `scrape-news.yml`, `scrape-outings.yml`, `check-ebra-cookie.yml` ; décider du sort de `scrape_outings.py` (tables sorties)

### Phase 4 — Crons & workflows (1–2 semaines)
- [ ] Crons Convex : `scrapeNews (toutes 15 min)`, `publishScheduled`, `airportSync`, `knowledgeSync`, `scrapeOutings`, `revalidateTags` — remplacent les `schedule:` des workflows
- [ ] `backup-database.yml` (pg_dump hebdo) → snapshot Convex (`npx convex export` ou API snapshots) → B2 ; `backup-incremental.yml` → export des documents du jour
- [ ] Keep-alive / alertes Telegram : inchangés ou absorbés

### Phase 5 — Cutover (1–2 jours)
- [ ] **Double écriture 1 semaine** : scrapers écrivent Supabase + Convex ; site lit Convex ; comparaison de compteurs quotidienne
- [ ] Bascule des lectures (déploiement Vercel pointant Convex) ; rollback = ancien build Prisma/Supabase
- [ ] Vérification : recherche, galeries, admin, logs scraping, revalidate
- [ ] Fin de vie Supabase : downgrade Free (les données restent exportables)

### Phase 6 — Validation & ops (1 semaine, en continu)
- [ ] Dashboard Convex : calls/bandwidth/action compute la 1re semaine ; seuils d'alerte
- [ ] Nettoyage : suppression des secrets `DATABASE_URL`, workflows obsolètes, doc
- [ ] Bilan coût réel vs prévision

## 4. Risques & mitigations

| Risque | Impact | Mitigation |
|---|---|---|
| Réécriture des ~40 scripts Python | Effort majeur, régressions | Prioriser les 10 scripts actifs ; archiver le reste ; tests de compteurs |
| MulhouseGPT (repo tiers) lit Supabase en SQL | Rupture RAG | Pont lecture via API Convex ou sync temporaire |
| Queries sans index chez Convex | Bandwidth DB facturé par doc scannée | Index systématiques (publishedAt, hidden, source) + `database: "patch"` vs lecture complète |
| Payloads `content` volumineux | Egress | Ne jamais lire `content` en query de liste (projections) |
| Volume starter (1 GB egress/mois) | Dépassement | Plan Pro $25/mois validé en Phase 0 |
| Crons Convex avec fetch long (scrape) | Timeouts (default 10 min, max 80 en action) | Actions avec timeout max, ou garder exécution sur GitHub Actions → mutations Convex (hybride) |
| Images B2 | Aucun impact | Hors périmètre ; option Convex file storage si B2 à abandonner |

## 5. Estimation

| Phase | Effort solo | Effort 2 devs |
|---|---|---|
| 0. Spike/décision | 1–2 sem | 1 sem |
| 1. Fondations + data | 2–3 sem | 1.5 sem |
| 2. App Next.js | 2–3 sem | 1.5 sem |
| 3. Scrapers Python | 3–4 sem | 2 sem |
| 4. Crons/workflows | 1–2 sem | 1 sem |
| 5. Cutover | 1 sem | 0.5 sem |
| **Total** | **~10–14 sem** | **~6–8 sem** |

## 6. Points durs à trancher (avant Phase 1)

1. **GO/NO-GO Convex vs Supabase Pro** — ✅ **GO** (12/08/2026) — le quota egress était déjà largement résorbé par `d6a6fc1` ; Convex se justifie par l'ops unifiée (DB + crons + logs).
2. **Qui exécute les scrapers ?** — ✅ **Hybride** : GitHub Actions exécute le réseau, Convex stocke ; migration vers les crons Convex natifs à réévaluer après validation du fonctionnement.
3. **MulhouseGPT** — ✅ **Adapter directement** (client Convex), suppression de la dépendance `NEWS_DATABASE_URL`.
4. **Sort des 30+ scripts one-shot** — ✅ **Archivage** `scripts/legacy/` avec doc SQL de substitution.

## 7. Définition de fait (acceptance)
- [ ] Le site lit 100 % Convex, Prisma/Supabase retirés du build
- [ ] Les scrapers actifs écrivent dans Convex (plus aucun `psycopg2` dans les workflows)
- [ ] Crons Convex en place, workflows de scraping supprimés
- [ ] Backups Convex → B2 fonctionnels et testés (restore)
- [ ] RAG opérationnel (MulhouseGPT) sans dépendre de Supabase
- [ ] Coût mensuel documenté et sous budget fixé
