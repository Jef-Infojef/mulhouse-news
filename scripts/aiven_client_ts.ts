/**
 * Accès aux tables Article / ArticleImage de l'Aiven, pour le miroir d'images.
 *
 * Pendant du `aiven_client.py` côté Node. Les deux scripts d'images
 * (download_images.ts, sync_to_b2.ts) lisaient leur liste de travail dans
 * Convex et y réécrivaient `localImage` / `r2Url` ; le déploiement coupé pour
 * quota le 11/09/2026, ils échouaient sur leur première requête et plus aucune
 * image n'était téléchargée ni poussée sur B2.
 *
 * L'Aiven porte les mêmes colonnes et fait autorité pour l'actualité depuis le
 * 13/09/2026. Contrairement au client Python, celui-ci écrit aussi : il n'y a
 * pas de journal pour les images, et un miroir qu'on ne peut pas marquer comme
 * fait serait refait à chaque run.
 */
import { Client } from "pg";

let client: Client | null = null;

export function url(): string | null {
  return (process.env.RAG_DATABASE_URL || "").trim() || null;
}

export function disponible(): boolean {
  return Boolean(url());
}

/** Connexion paresseuse, partagée par tout le run. */
async function co(): Promise<Client> {
  if (client) return client;
  // Aiven impose TLS et refuse la connexion en clair (FATAL 28000). psycopg2
  // negocie SSL tout seul, pas node-pg : sans ce bloc, les scripts d’images
  // echouent a l’authentification la ou leur pendant Python passe.
  //
  // La chaine de certification n’est verifiee que si un CA est fourni
  // (PGSSLROOTCERT ou RAG_DATABASE_CA, chemin d’un fichier .pem) ; sans lui on
  // chiffre sans authentifier le serveur. Poser l’un des deux dans les secrets
  // du workflow reste souhaitable.
  const cheminCa = process.env.PGSSLROOTCERT || process.env.RAG_DATABASE_CA || "";
  const ssl = cheminCa
    ? { ca: require("fs").readFileSync(cheminCa, "utf8"), rejectUnauthorized: true }
    : { rejectUnauthorized: false };
  const c = new Client({ connectionString: url() as string, ssl });
  await c.connect();
  client = c;
  return c;
}

/** À appeler en fin de script : sans cela le process Node ne rend pas la main. */
export async function fermer(): Promise<void> {
  if (client) {
    await client.end();
    client = null;
  }
}

export interface LigneArticle {
  id: string;
  supabaseId: string | null;
  imageUrl: string;
  link: string;
  localImage: string | null;
  r2Url: string | null;
}

export interface LigneGalerie {
  id: string;
  url: string;
  localImage: string | null;
  r2Url: string | null;
  supabaseId: string | null;
  articleLink: string;
}

/** Articles récents dont l'image principale n'est pas encore descendue. */
export async function imagesATelecharger(limit = 200, hours = 48): Promise<LigneArticle[]> {
  const c = await co();
  const r = await c.query(
    `SELECT id, id AS "supabaseId", "imageUrl", link, "localImage", "r2Url"
       FROM "Article"
      WHERE "imageUrl" IS NOT NULL AND "imageUrl" <> ''
        AND "localImage" IS NULL
        AND "publishedAt" > NOW() - ($2 || ' hours')::interval
      ORDER BY "publishedAt" DESC
      LIMIT $1`,
    [limit, String(hours)]
  );
  return r.rows;
}

/** Images de galerie des articles récents, pas encore descendues. */
export async function galerieATelecharger(limit = 500, hours = 48): Promise<LigneGalerie[]> {
  const c = await co();
  const r = await c.query(
    `SELECT i.id, i.url, i."localImage", i."r2Url",
            i."articleId" AS "supabaseId", a.link AS "articleLink"
       FROM "ArticleImage" i
       JOIN "Article" a ON a.id = i."articleId"
      WHERE i.url IS NOT NULL AND i.url <> ''
        AND i."localImage" IS NULL
        AND a."publishedAt" > NOW() - ($2 || ' hours')::interval
      ORDER BY a."publishedAt" DESC
      LIMIT $1`,
    [limit, String(hours)]
  );
  return r.rows;
}

/** Articles descendus localement mais pas encore poussés sur B2. */
export async function imagesAUploader(limit = 500): Promise<LigneArticle[]> {
  const c = await co();
  const r = await c.query(
    `SELECT id, id AS "supabaseId", "imageUrl", link, "localImage", "r2Url"
       FROM "Article"
      WHERE "localImage" IS NOT NULL AND "localImage" <> ''
        AND "r2Url" IS NULL
      ORDER BY "publishedAt" DESC
      LIMIT $1`,
    [limit]
  );
  return r.rows;
}

/** Images de galerie descendues mais pas encore poussées sur B2. */
export async function galerieAUploader(limit = 500): Promise<LigneGalerie[]> {
  const c = await co();
  const r = await c.query(
    `SELECT i.id, i.url, i."localImage", i."r2Url",
            i."articleId" AS "supabaseId", a.link AS "articleLink"
       FROM "ArticleImage" i
       JOIN "Article" a ON a.id = i."articleId"
      WHERE i."localImage" IS NOT NULL AND i."localImage" <> ''
        AND i."r2Url" IS NULL
      LIMIT $1`,
    [limit]
  );
  return r.rows;
}

/**
 * Articles marques comme descendus mais dont le miroir B2 manque.
 *
 * Sequelle de la coupure Convex et des runs plus anciens : `localImage` porte
 * un nom de fichier dont le fichier lui-meme a disparu avec le runner. Comme
 * `localImage` est renseigne, le telechargement normal les ignore, et comme le
 * fichier est absent, l’upload B2 les ignore aussi : ils ne sortent de cet
 * angle mort que si on les cherche explicitement. Sans borne de date, donc.
 */
export async function imagesOrphelines(limit = 500): Promise<LigneArticle[]> {
  const c = await co();
  const r = await c.query(
    `SELECT id, id AS "supabaseId", "imageUrl", link, "localImage", "r2Url"
       FROM "Article"
      WHERE "localImage" IS NOT NULL AND "r2Url" IS NULL
        AND "imageUrl" IS NOT NULL AND "imageUrl" <> ''
      ORDER BY "publishedAt" DESC
      LIMIT $1`,
    [limit]
  );
  return r.rows;
}

async function poser(table: string, colonne: string, id: string, valeur: string) {
  const c = await co();
  await c.query(
    `UPDATE "${table}" SET "${colonne}" = $1 WHERE id = $2`,
    [valeur, id]
  );
}

export const poserArticleLocalImage = (id: string, v: string) => poser("Article", "localImage", id, v);
export const poserArticleR2Url = (id: string, v: string) => poser("Article", "r2Url", id, v);
export const poserGalerieLocalImage = (id: string, v: string) => poser("ArticleImage", "localImage", id, v);
export const poserGalerieR2Url = (id: string, v: string) => poser("ArticleImage", "r2Url", id, v);
