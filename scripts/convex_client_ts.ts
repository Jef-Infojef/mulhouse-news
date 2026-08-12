// Client HTTP Convex pour les scripts TS d'images (Phase 4).
//
// Équivalent TS de `scripts/convex_client.py` : remplace les accès Prisma des
// scripts `download_images.ts` / `sync_to_b2.ts` par des appels aux fonctions
// Convex du cloud (`convex/images.ts`), exécutés côté GitHub Actions.
//
// Configuration (env) :
//   CONVEX_DEPLOY_KEY      - deploy key `dev:<deployment>|<token>` (auth HTTP)
//   NEXT_PUBLIC_CONVEX_URL - URL du déploiement, ex https://friendly-chicken-952.convex.cloud
//
// Endpoints HTTP Convex v1.43 :
//   - queries   → POST {url}/api/query
//   - mutations → POST {url}/api/mutation
//   avec en-tête `Authorization: Convex <deploy_key>` et corps
//   `{"path": "<module>:<fonction>", "format": "json", "args": {...}}`.
// Convex refuse `null` sur un champ v.optional(v.string()) : les champs
// optionnels null/undefined sont omis avant l'envoi (même règle que le client
// Python, champ par champ via _STRIP_NONE_KEYS).
//
// dotenv est chargé ici (scripts run via `node -r tsx/cjs` ou `npx tsx`) ;
// en GitHub Actions, les env du workflow écrasent les valeurs des fichiers .env
// (dotenv ne surcharge pas une variable déjà définie).

import * as dotenv from "dotenv";

dotenv.config();
dotenv.config({ path: ".env.local" });

export function getConvexUrl(): string | null {
  return process.env.NEXT_PUBLIC_CONVEX_URL || null;
}

export function getDeployKey(): string | null {
  return process.env.CONVEX_DEPLOY_KEY || null;
}

/** True si la bascule Convex est activée (clef deploy + URL définies). */
export function useConvex(): boolean {
  return Boolean(getDeployKey() && getConvexUrl());
}

export class ConvexError extends Error {}

function requireConfig(): { url: string; key: string } {
  const url = getConvexUrl();
  const key = getDeployKey();
  if (!url || !key) {
    throw new ConvexError(
      "Backend Convex non configuré : définir CONVEX_DEPLOY_KEY " +
        "et NEXT_PUBLIC_CONVEX_URL (ou lancer avec USE_CONVEX=1)."
    );
  }
  return { url, key };
}

// Champs optionnels des fonctions Convex : Convex refuse `null` sur un champ
// v.optional(v.string()) — il faut l'OMETTRE.
const STRIP_NONE_KEYS = new Set([
  "title",
  "imageUrl",
  "imageCaption",
  "source",
  "description",
  "publishedAt",
  "scrapedAt",
  "createdAt",
  "updatedAt",
  "content",
  "localImage",
  "r2Url",
  "hidden",
  "supabaseId",
  "caption",
  "position",
  "finishedAt",
  "errorMessage",
  "details",
]);

function stripNone(args: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(args)) {
    if (value === undefined) continue;
    if (value === null && STRIP_NONE_KEYS.has(key)) continue;
    out[key] = value;
  }
  return out;
}

async function call(
  path: string,
  args: Record<string, unknown>,
  mutation: boolean
): Promise<unknown> {
  const { url, key } = requireConfig();
  const endpoint = `${url}/api/${mutation ? "mutation" : "query"}`;
  const payload = { path, format: "json", args: stripNone(args) };

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90000);
  let resp: Response;
  try {
    resp = await fetch(endpoint, {
      method: "POST",
      signal: controller.signal,
      headers: {
        Authorization: `Convex ${key}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new ConvexError(`Erreur HTTP Convex (${path}): ${msg}`);
  } finally {
    clearTimeout(timeout);
  }

  if (!resp.ok) {
    const text = await resp.text();
    throw new ConvexError(`Convex HTTP ${resp.status} (${path}): ${text.slice(0, 500)}`);
  }
  const data = (await resp.json()) as {
    status: string;
    value?: unknown;
    errorMessage?: string;
  };
  if (data.status !== "success") {
    throw new ConvexError(
      `Convex UDF en erreur (${path}): ${data.errorMessage ?? JSON.stringify(data)}`
    );
  }
  return data.value;
}

export async function callQuery<T>(path: string, args: Record<string, unknown> = {}): Promise<T> {
  return (await call(path, args, false)) as T;
}

export async function callMutation<T>(path: string, args: Record<string, unknown> = {}): Promise<T> {
  return (await call(path, args, true)) as T;
}

// ─────────────────────────────────────────────────────────────────────────────
// Types renvoyés par convex/images.ts
// ─────────────────────────────────────────────────────────────────────────────

export interface ArticleImageRow {
  id: string; // _id Convex
  supabaseId: string | null;
  imageUrl: string;
  link: string;
  localImage: string | null;
  r2Url: string | null;
}

export interface GalleryImageRow {
  id: string; // _id Convex
  url: string;
  localImage: string | null;
  r2Url: string | null;
  supabaseId: string | null;
  articleLink: string;
}

export interface UploadArticleRow {
  id: string; // _id Convex
  supabaseId: string | null;
  localImage: string;
  r2Url: string | null;
}

export interface UploadGalleryRow {
  id: string; // _id Convex
  url: string;
  localImage: string;
  r2Url: string | null;
}

interface Paged<T> {
  isDone: boolean;
  cursor: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Queries — téléchargement
// ─────────────────────────────────────────────────────────────────────────────

/** Articles récents (48h) dont l'image principale est à télécharger. */
export async function getImagesToDownload(
  limit = 200,
  hours = 48
): Promise<ArticleImageRow[]> {
  // startMs stable pendant toute la boucle : voir convex/images.ts (cursor).
  const startMs = Date.now() - hours * 3600_000;
  const rows: ArticleImageRow[] = [];
  let cursor: string | null = null;
  do {
    const res = await callQuery<Paged<ArticleImageRow> & { articles: ArticleImageRow[] }>(
      "images:getImagesToDownload",
      { limit, startMs, cursor }
    );
    rows.push(...res.articles);
    if (res.isDone) break;
    cursor = res.cursor;
  } while (cursor);
  return rows;
}

/** Images de galerie (articleImages) à télécharger (articles parents récents 48h). */
export async function getArticleImagesToDownload(
  limit = 500,
  hours = 48
): Promise<GalleryImageRow[]> {
  const res = await callQuery<{ images: GalleryImageRow[] }>(
    "images:getArticleImagesToDownload",
    { limit, hours }
  );
  return res.images;
}

// ─────────────────────────────────────────────────────────────────────────────
// Queries — upload B2
// ─────────────────────────────────────────────────────────────────────────────

/** Articles avec localImage mais sans r2Url (à uploader sur B2). */
export async function getImagesToUpload(limit = 500): Promise<UploadArticleRow[]> {
  const res = await callQuery<{ articles: UploadArticleRow[] }>("images:getImagesToUpload", {
    limit,
  });
  return res.articles;
}

/** Images de galerie avec localImage mais sans r2Url (à uploader sur B2). */
export async function getArticleImagesToUpload(limit = 500): Promise<UploadGalleryRow[]> {
  const res = await callQuery<{ images: UploadGalleryRow[] }>("images:getArticleImagesToUpload", {
    limit,
  });
  return res.images;
}

// ─────────────────────────────────────────────────────────────────────────────
// Mutations (patch par `_id` Convex)
// ─────────────────────────────────────────────────────────────────────────────

export function updateArticleLocalImage(id: string, localImage: string): Promise<unknown> {
  return callMutation("images:updateArticleLocalImage", { id, localImage });
}

export function updateArticleR2Url(id: string, r2Url: string): Promise<unknown> {
  return callMutation("images:updateArticleR2Url", { id, r2Url });
}

export function updateArticleImageLocalImage(id: string, localImage: string): Promise<unknown> {
  return callMutation("images:updateArticleImageLocalImage", { id, localImage });
}

export function updateArticleImageR2Url(id: string, r2Url: string): Promise<unknown> {
  return callMutation("images:updateArticleImageR2Url", { id, r2Url });
}
