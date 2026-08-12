# Scripts one-shot archivés (legacy)

Ces scripts **ne sont plus exécutés par les workflows GitHub Actions** : ils ont
été déplacés ici lors de la **Phase 3** de la migration Convex pour ne pas
polluer `scripts/` (accès direct Supabase via psycopg2/SQL).

## Pourquoi sont-ils archivés ?

Ils sont **one-shot** (rescue/repair/backfill/diagnose/report/…) : exécutés une
fois à la main pour corriger des données, jamais référencés par `.github/workflows/`.
Ils écrivent encore dans **Supabase** (`DATABASE_URL`), pas dans Convex. La liste
de référence des scripts actifs (whitelist) vit dans `scripts/` :
`scrape_and_seed.py`, `scrape_mplusinfo.py`, `scrape_periscope_seed.py`,
`scrape_mag_m2a.py`, `scrape_content_full.py`, `scrape_outings.py`,
`scrape_utils.py`, `convex_client.py`, `rag_sync_articles.py`,
`log_github_failure.py`, `check_ebra_cookie.py`, `migrate_supabase_to_convex.ts`,
`migrate_check.ts`, `download_images.ts`, `sync_to_b2.ts`,
`backfill_image_captions.py`, `backfill_image_captions_other.py`.

## Comment les utiliser encore (contre Supabase)

- Ils lisent/écrivent Supabase avec **`DATABASE_URL`** (`psycopg2`), comme avant
  la Phase 3. Définir la variable d'environnement comme dans les workflows :
  ```bash
  export DATABASE_URL="postgresql://..."
  python scripts/legacy/rescue_figaro.py
  ```
- Certains scripts historiques lisent `NEWS_DATABASE_URL` (ex. `rescue_*.py`,
  `diagnose_*.py`, `report_completeness.py`) : définir cette variable à la place
  de `DATABASE_URL` si c'est leur cas.
- `scrape_periscope.py` importe `scrape_utils` (resté dans `scripts/`) : ajouter
  le dossier parent au `PYTHONPATH` :
  ```bash
  PYTHONPATH=scripts python scripts/legacy/scrape_periscope.py
  ```
- Aucun de ces scripts n'utilise `convex_client` : ils ne déclenchent **jamais**
  de bascule Convex, même si `CONVEX_DEPLOY_KEY` est définie.

## Portage Convex

Ces scripts ne seront **pas** portés vers Convex : ils sont ponctuels et
historiques. Leur équivalent « base de vérité » est désormais :
- données : Convex cloud (`https://friendly-chicken-952.convex.cloud`)
- helpers d'accès : `scripts/convex_client.py`
- alternative de lecture : exports Supabase (projet `wmvjpdedrfyttixdkzpi`)
  ou SQL via le dashboard Supabase / `scripts/migrate_check.ts`.

Pour reprendre un de ces scripts à l'avenir, le porter en mode dual
(`USE_CONVEX`/`CONVEX_DEPLOY_KEY` → `convex_client`) comme les scripts actifs.
