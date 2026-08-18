-- ============================================================================
-- Sécurité : RLS + verrouillage des tables du schéma public
-- Contexte  : alerte Supabase du 17/08/2026 « Table publicly accessible »
--             projet wmvjpdedrfyttixdkzpi
--
-- Constat vérifié le 18/08/2026 (inspection SQL, base `postgres`) :
--   - aucune table nommée `rls_disabled_in_public` ne subsiste ;
--   - la seule table du schéma `public` avec RLS désactivée est `ArticleImage` ;
--   - les rôles `anon`/`authenticated` ont TOUS les privilèges (SELECT/INSERT/
--     UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER) sur les 16 tables du schéma.
--   - 0 politique RLS définie : une fois RLS activée, ces rôles n'ont accès à
--     aucune ligne (accès aux données = 0 ligne, DML silencieusement filtré).
--
-- L'application n'utilise PAS la Data API / PostgREST : tous les accès passent
-- par des connexions directes (`postgres`, `service_role`, `mulhousegpt_readonly`,
-- pooler), qui contournent RLS et ne sont PAS affectées par ce script.
--
-- Exécution :
--   Tableau de bord Supabase → SQL Editor  (connexion `postgres`)
--   OU : psql "$DATABASE_URL" -f supabase/migrations/20260818_enable_rls_and_lockdown_public.sql
--
-- Le script est idempotent et réversible (REVOKE rejouable, ALTER TABLE sans
-- IF NOT EXISTS sur l'état rowsecurity n'existe pas → bloc DO ciblé).
-- ============================================================================

BEGIN;

-- ─── 1. Activer RLS sur toutes les tables applicatives du schéma public ───
--    Idempotent : ignore les tables déjà activées ; couvre aussi toute table
--    créée entre l'alerte et maintenant.
DO $$
DECLARE
  t record;
BEGIN
  FOR t IN
    SELECT n.nspname, c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind = 'r'
      AND c.relname NOT LIKE 'pg_%'
      AND NOT c.relrowsecurity
    ORDER BY c.relname
  LOOP
    EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY', t.nspname, t.relname);
    RAISE NOTICE 'RLS activée sur : %', t.nspname || '.' || t.relname;
  END LOOP;
END $$;

-- ─── 2. Révoquer les privilèges des rôles API (Data API / PostgREST) ───
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM anon, authenticated;

-- ─── 3. Prévenir les futures expositions (privilèges par défaut) ───
--    Sans cela, tout objet créé plus tard (ex. `prisma db push`) redeviendrait
--    accessible aux rôles API via les ACL par défaut de Supabase.
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES    FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, authenticated;

COMMIT;

-- ─── Vérification (à relancer après exécution) ───────────────────────────────
-- -- 1) Plus aucun tableau public sans RLS :
-- SELECT schemaname, tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public' AND rowsecurity = false;
--
-- -- 2) Plus aucun privilège pour anon/authenticated sur le schéma public :
-- SELECT grantee, table_name
-- FROM information_schema.role_table_grants
-- WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated');