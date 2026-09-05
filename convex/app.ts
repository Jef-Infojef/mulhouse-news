import { action, internalQuery, mutation, query } from "./_generated/server";
import { internal } from "./_generated/api";
import { v } from "convex/values";
import type { Doc } from "./_generated/dataModel";

// ─────────────────────────────────────────────────────────────────────────────
// Phase 2 — fonctions applicatives remplaçant les appels Prisma de
// app/actions.ts. Appelées depuis Next.js (server actions) via ConvexHttpClient
// (lib/prisma.ts), donc sans auth Convex : la vérification admin se fait côté
// Next (lib/adminAuth), comme l'existant.
//
// Notes de portage Prisma → Convex :
//  • Les articles n'ont pas leur UUID Supabase d'origine (cuid) en champ propre
//    dans le schéma : c'est `supabaseId` (backfillé par setArticleSupabaseIds),
//    qui sert aux jointures articleGoogleTags/articleImages (ces tables
//    stockent l'UUID Supabase).
//  • La recherche Prisma `contains` (ILIKE) n'existe pas chez Convex : elle est
//    remplacée par des index de recherche full-text (search_title,
//    search_description, search_source), fusionnés en OR côté handler.
//    `content` reste volontairement exclu de la recherche (décision de
//    l'existant : ne pas permettre de reconstituer le texte intégral).
//  • Les IDs exposés au client sont les `_id` Convex (les cuids Supabase n'ont
//    pas été migrés) : getArticleContent/deleteArticle les consomment.
//  • Timestamps en epoch ms (schéma Convex) ; conversion en Date côté Next.
// ─────────────────────────────────────────────────────────────────────────────

const LIST_LIMIT = 200;
const SEARCH_TAKE_PER_INDEX = 200;

export const getLatestArticles = query({
  args: { query: v.optional(v.string()) },
  handler: async (ctx, args) => {
    const searchTerm = args.query?.trim();

    let docs: Doc<"articles">[] = [];
    if (searchTerm) {
      // Recherche FTS (token de préfixe) sur title/description/source : ON
      // fusionne les 3 index (équivalent de l'OR Prisma), déduplique par _id,
      // et re-trie par publishedAt desc. `content` jamais cherché.
      // NB : `.take(n)` renvoie directement la liste en v1.43 (pas de .collect()).
      const [byTitle, byDescription, bySource] = await Promise.all([
        ctx.db
          .query("articles")
          .withSearchIndex("search_title", (q) =>
            q.search("title", searchTerm).eq("hidden", false)
          )
          .take(SEARCH_TAKE_PER_INDEX),
        ctx.db
          .query("articles")
          .withSearchIndex("search_description", (q) =>
            q.search("description", searchTerm).eq("hidden", false)
          )
          .take(SEARCH_TAKE_PER_INDEX),
        ctx.db
          .query("articles")
          .withSearchIndex("search_source", (q) =>
            q.search("source", searchTerm).eq("hidden", false)
          )
          .take(SEARCH_TAKE_PER_INDEX),
      ]);
      const merged = new Map<string, Doc<"articles">>();
      for (const doc of [...byTitle, ...byDescription, ...bySource]) {
        if (!merged.has(doc._id)) merged.set(doc._id, doc);
      }
      docs = [...merged.values()]
        .sort((a, b) => b.publishedAt - a.publishedAt)
        .slice(0, LIST_LIMIT);
    } else {
      // Liste paginée bornée via l'index (hidden=false, publishedAt desc) :
      // pas de .collect() sur toute la table.
      docs = await ctx.db
        .query("articles")
        .withIndex("by_hidden_publishedAt", (q) => q.eq("hidden", false))
        .order("desc")
        .take(LIST_LIMIT);
    }

    // Enrichissement des tags (ex-`include: { NewsTag: true }` de Prisma).
    // newsTags ne porte pas l'UUID Supabase dans son propre champ : c'est
    // `supabaseId` qui relie articleGoogleTags.tagId → newsTags.
    const allTags = await ctx.db.query("newsTags").collect();
    const tagBySupabaseId = new Map<string, (typeof allTags)[number]>();
    for (const tag of allTags) {
      if (tag.supabaseId) tagBySupabaseId.set(tag.supabaseId, tag);
    }

    const articles = [];
    for (const doc of docs) {
      const ArticleGoogleTag: {
        NewsTag: { id: string; name: string; slug: string; color: string | null };
      }[] = [];
      if (doc.supabaseId) {
        // const local : le narrowing ne se propage pas dans les closures TS
        const articleSupabaseId = doc.supabaseId;
        const links = await ctx.db
          .query("articleGoogleTags")
          .withIndex("by_articleId", (q) => q.eq("articleId", articleSupabaseId))
          .take(50);
        for (const link of links) {
          const tag = tagBySupabaseId.get(link.tagId);
          if (tag) {
            ArticleGoogleTag.push({
              NewsTag: {
                id: tag.supabaseId!,
                name: tag.name,
                slug: tag.slug,
                color: tag.color ?? null,
              },
            });
          }
        }
      }
      articles.push({
        // Même shape que le `select` Prisma d'origine (content exclu).
        id: doc._id,
        title: doc.title,
        link: doc.link,
        imageUrl: doc.imageUrl ?? null,
        imageCaption: doc.imageCaption ?? null,
        source: doc.source ?? null,
        description: doc.description ?? null,
        publishedAt: doc.publishedAt,
        scrapedAt: doc.scrapedAt ?? null,
        createdAt: doc.createdAt ?? null,
        updatedAt: doc.updatedAt ?? null,
        localImage: doc.localImage ?? null,
        r2Url: doc.r2Url ?? null,
        author: doc.author ?? null,
        category: doc.category ?? null,
        hidden: doc.hidden,
        ArticleGoogleTag,
      });
    }

    return { articles };
  },
});

export const getArticleContent = query({
  args: { id: v.id("articles") },
  handler: async (ctx, { id }) => {
    const doc = await ctx.db.get(id);
    // `content` est volumineux (HTML scrapé) : renvoyé seul, uniquement à la
    // demande (admin), comme le `select: { content: true }` d'origine.
    return { content: doc?.content ?? null };
  },
});

export const getScrapingLogs = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(1, args.limit ?? 100), 500);
    const docs = await ctx.db
      .query("scrapingLogs")
      .withIndex("by_startedAt")
      .order("desc")
      .take(limit);
    return {
      logs: docs.map((doc) => ({
        id: doc._id,
        startedAt: doc.startedAt,
        finishedAt: doc.finishedAt ?? null,
        status: doc.status,
        isConnected: doc.isConnected,
        articlesCount: doc.articlesCount,
        successCount: doc.successCount,
        errorCount: doc.errorCount,
        details: doc.details ?? null,
        errorMessage: doc.errorMessage ?? null,
      })),
    };
  },
});

export const getAppConfig = query({
  args: { key: v.string() },
  handler: async (ctx, { key }) => {
    const doc = await ctx.db
      .query("appConfig")
      .withIndex("by_key", (q) => q.eq("key", key))
      .first();
    return { value: doc?.value ?? null };
  },
});

export const setAppConfig = mutation({
  args: { key: v.string(), value: v.string() },
  handler: async (ctx, { key, value }) => {
    // Upsert par key (ex-`appConfig.upsert` Prisma).
    const existing = await ctx.db
      .query("appConfig")
      .withIndex("by_key", (q) => q.eq("key", key))
      .first();
    if (existing) {
      await ctx.db.patch(existing._id, { value, updatedAt: Date.now() });
    } else {
      await ctx.db.insert("appConfig", { key, value, updatedAt: Date.now() });
    }
    return { success: true };
  },
});

export const deleteAppConfig = mutation({
  args: { key: v.string() },
  handler: async (ctx, { key }) => {
    const existing = await ctx.db
      .query("appConfig")
      .withIndex("by_key", (q) => q.eq("key", key))
      .first();
    if (existing) await ctx.db.delete(existing._id);
    return { success: true };
  },
});

// Rate-limit du login admin. L'existant stockait le compteur dans AppConfig
// (JSON {c, t} + purge opportuniste des compteurs expirés) : la logique est
// portée telle quelle en mutation Convex. Retourne le compteur incrémenté ;
// l'appelant Next compare au seuil. `max` est conservé pour la symétrie avec
// l'existant (le seuil est en réalité comparé côté serveur Next).
export const incRateLimit = mutation({
  args: {
    key: v.string(),
    prefix: v.string(),
    max: v.number(),
    windowMs: v.number(),
  },
  // `max` (seuil) est accepté pour la symétrie avec le contrat d'appel historique
  // (`incRateLimit(key, max, windowMs)`) ; la comparaison `count > max` reste faite
  // côté serveur Next (actions.ts), comme dans l'existant.
  handler: async (ctx, args) => {
    const { key, prefix, windowMs } = args;
    const now = Date.now();
    const existing = await ctx.db
      .query("appConfig")
      .withIndex("by_key", (q) => q.eq("key", key))
      .first();

    let count = 0;
    let windowStart = now;
    if (existing) {
      let parsed: { c?: number; t?: number } | null = null;
      try {
        parsed = JSON.parse(existing.value) as { c?: number; t?: number };
      } catch {
        parsed = null;
      }
      if (parsed && typeof parsed.t === "number" && now - parsed.t <= windowMs) {
        count = typeof parsed.c === "number" ? parsed.c : 0;
        windowStart = parsed.t;
      }
    }
    count++;
    const value = JSON.stringify({ c: count, t: windowStart });
    if (existing) {
      await ctx.db.patch(existing._id, { value, updatedAt: now });
    } else {
      await ctx.db.insert("appConfig", { key, value, updatedAt: now });
    }

    // Purge opportuniste (2 %) des compteurs expirés (ex-`deleteMany` Prisma).
    // appConfig reste une petite table : le scan filtré par préfixe suffit.
    if (Math.random() < 0.02) {
      const candidates = await ctx.db
        .query("appConfig")
        .filter((q) =>
          q.and(
            q.gte(q.field("key"), prefix),
            q.lt(q.field("key"), prefix + "\uffff")
          )
        )
        .take(100);
      for (const doc of candidates) {
        const updatedAt = typeof doc.updatedAt === "number" ? doc.updatedAt : 0;
        if (now - updatedAt > windowMs) await ctx.db.delete(doc._id);
      }
    }
    return count;
  },
});

export const deleteArticle = mutation({
  args: { id: v.id("articles") },
  handler: async (ctx, { id }) => {
    const doc = await ctx.db.get(id);
    if (!doc) return { success: true, error: null };
    // Cascade manuelle : Prisma supprimait ArticleGoogleTag et ArticleImage
    // (onDelete: Cascade) ; Convex ne cascade pas, on le reproduit ici.
    if (doc.supabaseId) {
      const articleSupabaseId = doc.supabaseId;
      const tags = await ctx.db
        .query("articleGoogleTags")
        .withIndex("by_articleId", (q) => q.eq("articleId", articleSupabaseId))
        .take(100);
      for (const tag of tags) await ctx.db.delete(tag._id);
      const images = await ctx.db
        .query("articleImages")
        .withIndex("by_articleId", (q) => q.eq("articleId", articleSupabaseId))
        .take(100);
      for (const image of images) await ctx.db.delete(image._id);
    }
    await ctx.db.delete(id);
    return { success: true, error: null };
  },
});

// Dernier article L'Alsace (source ILIKE '%Alsace%' + link contains 'lalsace.fr',
// trié par publishedAt desc — approximation : scan borné des 500 plus récents,
// puis filtre en JS, même sensibilité). Query INTERNE : consommée uniquement par
// l'action testEbraConnection (les actions n'ont pas accès direct à ctx.db).
// Masquer/Afficher un article (équivalent de `article.update({ hidden })` Prisma
// côté Supabase). Consommé en HTTP par le pont assocommercants
// (PATCH /api/google-news/[id] quand useConvexNews()).
export const setArticleHidden = mutation({
  args: { id: v.id("articles"), hidden: v.boolean() },
  handler: async (ctx, { id, hidden }) => {
    const doc = await ctx.db.get(id);
    if (!doc) return { success: false, error: "Article introuvable" };
    await ctx.db.patch(id, { hidden });
    return { success: true, error: null };
  },
});

export const getLastAlsaceArticle = internalQuery({
  args: {},
  handler: async (ctx) => {
    const candidates = await ctx.db
      .query("articles")
      .withIndex("by_publishedAt")
      .order("desc")
      .take(500);
    return (
      candidates.find(
        (article) =>
          (article.source ?? "").toLowerCase().includes("alsace") &&
          (article.link ?? "").includes("lalsace.fr")
      ) ?? null
    );
  },
});

// Action réseau : test de la session Premium EBRA (lalsace.fr). Reproduit à
// l'identique la logique de l'ancien app/actions.ts (nettoyage cookie,
// fetch home, détection de marqueurs, fetch d'un article récent L'Alsace).
export const testEbraConnection = action({
  args: { session: v.string(), poool: v.optional(v.string()) },
  handler: async (ctx, args) => {
    const sessionValue = args.session;
    const pooolValue = args.poool;
    try {
      const cleanSession = String(sessionValue).trim();
      const cleanPoool = pooolValue
        ? String(pooolValue).trim()
        : "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7";

      let finalSession = cleanSession;
      if (cleanSession.includes("2=")) {
        finalSession = cleanSession.substring(cleanSession.indexOf("2="));
        if (finalSession.includes(";")) finalSession = finalSession.split(";")[0];
      }
      finalSession = finalSession.replace(/['"]/g, "").trim();

      let finalPoool = cleanPoool;
      if (cleanPoool.includes("_poool=")) {
        finalPoool = cleanPoool.split("_poool=")[1].split(";")[0];
      }
      // Formats DevTools type '_poool :"79f0c712-..."' : on extrait l'UUID directement
      const uuidMatch = finalPoool.match(
        /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/
      );
      if (uuidMatch) finalPoool = uuidMatch[0];
      finalPoool = finalPoool.replace(/['"]/g, "").trim();

      const finalCookie = `.XCONNECT_SESSION=${finalSession}; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=${finalPoool}`;

      console.log(`[TEST EBRA] Cookie final: ${finalCookie.substring(0, 80)}...`);

      const homeResponse = await fetch("https://www.lalsace.fr/", {
        headers: {
          Cookie: finalCookie,
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          Accept:
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/apng,*/*;q=0.8",
          "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
          "Cache-Control": "no-store",
        },
      });

      const html = await homeResponse.text();

      // Debug dans les logs serveur
      console.log(`[TEST EBRA] Status: ${homeResponse.status}`);
      console.log(`[TEST EBRA] Taille HTML: ${html.length}`);

      const checks = {
        "Se déconnecter": html.includes("Se déconnecter"),
        "Mon compte": html.includes("Mon compte"),
        "Mon profil": html.includes("Mon profil"),
        subscriber: html.includes("subscriber"),
        Abonné: html.includes("Abonné"),
        premium: html.includes("premium"),
        "pro-item": html.includes("pro-item"),
        AccountCircle: html.includes("AccountCircle"),
        connected: html.includes("connected"),
        "logged-in": html.includes("logged-in"),
        auth: html.includes("auth"),
        XCONNECT: html.includes("XCONNECT"),
        JSESSIONID: html.includes("JSESSIONID"),
        "user-menu": html.includes("user-menu"),
        "mon-espace": html.includes("mon-espace"),
        "espace-client": html.includes("espace-client"),
      };
      console.log("[TEST EBRA] Résultats détection:", checks);

      // Détection plus large
      const isConnected = Object.values(checks).some((value) => value === true);

      // Si tous les tests échouent mais qu'on a un gros HTML (comme vu dans les logs ~840ko),
      // on considère que la session est probablement active car le paywall réduit drastiquement la taille.
      if (!isConnected && html.length > 300000) {
        console.log(
          `[TEST EBRA] Aucune clé explicite trouvée mais HTML volumineux (${html.length}), passage au test d'article.`
        );
        // On continue pour voir si l'article est complet
      } else if (!isConnected) {
        if (html.includes("Ray ID:") || html.includes("cloudflare")) {
          return {
            success: false,
            message:
              "Bloqué par Cloudflare (le serveur ne peut pas simuler le navigateur)",
          };
        }
        return {
          success: false,
          message:
            "Session non reconnue sur la home. Vérifiez la valeur du cookie.",
        };
      }

      if (!isConnected) {
        if (html.includes("Ray ID:") || html.includes("cloudflare")) {
          return {
            success: false,
            message:
              "Bloqué par Cloudflare (le serveur ne peut pas simuler le navigateur)",
          };
        }
        return {
          success: false,
          message:
            "Session non reconnue. Vérifiez que vous avez bien copié la valeur de ebra_session.",
        };
      }

      // Test sur un article pour confirmer l'accès
      // (ex-`findFirst` Prisma, remplacé par la query interne getLastAlsaceArticle).
      const lastPremium = await ctx.runQuery(internal.app.getLastAlsaceArticle, {});

      if (lastPremium) {
        const artResponse = await fetch(lastPremium.link, {
          headers: {
            Cookie: finalCookie,
            "User-Agent":
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          },
        });
        const artHtml = await artResponse.text();
        const hasContent =
          artHtml.includes("textComponent") ||
          artHtml.includes("article__body") ||
          artHtml.length > 60000;

        if (hasContent) {
          return {
            success: true,
            message: "Succès ! Vous êtes bien connecté en Premium.",
          };
        } else {
          return {
            success: true,
            message:
              "Connecté, mais le contenu de l'article semble quand même limité.",
          };
        }
      }

      return { success: true, message: "Connecté avec succès !" };
    } catch (error: unknown) {
      console.error("[TEST EBRA] Erreur:", error);
      const message =
        error instanceof Error
          ? error.message
          : typeof error === "string"
            ? error
            : String(error);
      return { success: false, message: "Erreur technique : " + message };
    }
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Backfill Phase 2 : stocke l'UUID Supabase d'origine (cuid Prisma) sur les
// documents migrés en Phase 1. Sans lui, les jointures articleGoogleTags /
// articleImages (qui référencent cet UUID) ne peuvent pas être résolues.
// Idempotent : matche par clé naturelle (link / associationId+slug).
// ─────────────────────────────────────────────────────────────────────────────

export const setArticleSupabaseIds = mutation({
  args: {
    rows: v.array(
      v.object({ link: v.string(), supabaseId: v.string() })
    ),
  },
  handler: async (ctx, { rows }) => {
    let updated = 0;
    for (const row of rows) {
      const doc = await ctx.db
        .query("articles")
        .withIndex("by_link", (q) => q.eq("link", row.link))
        .first();
      if (doc && doc.supabaseId !== row.supabaseId) {
        await ctx.db.patch(doc._id, { supabaseId: row.supabaseId });
        updated++;
      }
    }
    return { updated };
  },
});

export const setNewsTagSupabaseIds = mutation({
  args: {
    rows: v.array(
      v.object({
        associationId: v.string(),
        slug: v.string(),
        supabaseId: v.string(),
      })
    ),
  },
  handler: async (ctx, { rows }) => {
    let updated = 0;
    for (const row of rows) {
      const doc = await ctx.db
        .query("newsTags")
        .withIndex("by_associationId_slug", (q) =>
          q.eq("associationId", row.associationId).eq("slug", row.slug)
        )
        .first();
      if (doc && doc.supabaseId !== row.supabaseId) {
        await ctx.db.patch(doc._id, { supabaseId: row.supabaseId });
        updated++;
      }
    }
    return { updated };
  },
});