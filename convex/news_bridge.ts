import { query } from "./_generated/server";
import { v } from "convex/values";
import type { Id } from "./_generated/dataModel";

// ─────────────────────────────────────────────────────────────────────────────
// Pont RAG MulhouseGPT (12/08/2026) — queries Convex consommées par le moteur
// RAG de MulhouseGPT (repo B) via le client HTTP `lib/convex-news.ts`
// (endpoints /api/query, auth `Authorization: Convex <deploy key>`).
//
// Ce module remplace les lectures SQL Supabase (`NEWS_DATABASE_URL`) pour les
// tables désormais écrites côté Convex (articles presse + newsArticles) :
//  • `Article`       → Convex `articles` (scrapers actifs depuis la Phase 4)
//  • `NewsArticle`   → Convex `newsArticles` (table VIDE, jamais migrée)
//  • Cinema / Outing → restent sur Supabase (pas encore dans le schéma Convex)
//
// Conventions identiques à `convex/scrapers.ts` :
//  • `id` exposé = `supabaseId` (UUID Supabase d'origine) quand présent, sinon
//    `_id` Convex — c'est le `sourceId` stable attendu par les formatters RAG.
//  • Timestamps en epoch ms (schéma Convex) ; la conversion en Date est faite
//    côté MulhouseGPT AVANT d'appeler les formatters RAG.
//  • Pas de .collect() sur les grosses tables : scans bornés .take()/paginate().
//    `content` n'est renvoyé que par les queries dédiées (jamais les listes
//    d'ids) — le RAG en a besoin pour indexer.
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// Query 1 — article complet par `supabaseId` (UUID Supabase d'origine).
// Équivalent de `SELECT ... FROM "Article" WHERE id = $1` pour `indexPressArticleById`.
// `content` est renvoyé : nécessaire au RAG.
// ─────────────────────────────────────────────────────────────────────────────
export const getArticleById = query({
  args: { id: v.string() },
  handler: async (ctx, { id }) => {
    const doc = await ctx.db
      .query("articles")
      .withIndex("by_supabaseId", (q) => q.eq("supabaseId", id))
      .first();
    if (!doc) return null;
    const row: {
      id: string;
      supabaseId: string | null;
      title: string;
      description: string | null;
      content: string | null;
      source: string | null;
      link: string;
      publishedAt: number;
      updatedAt: number | null;
      imageUrl: string | null;
      r2Url: string | null;
      imageCaption?: string;
      hidden: boolean;
    } = {
      id: doc.supabaseId ?? doc._id,
      supabaseId: doc.supabaseId ?? null,
      title: doc.title,
      description: doc.description ?? null,
      content: doc.content ?? null,
      source: doc.source ?? null,
      link: doc.link,
      publishedAt: doc.publishedAt,
      updatedAt: doc.updatedAt ?? null,
      imageUrl: doc.imageUrl ?? null,
      r2Url: doc.r2Url ?? null,
      hidden: doc.hidden,
    };
    if (doc.imageCaption) row.imageCaption = doc.imageCaption;
    return row;
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Query 2 — articles presse récents pour `indexRecentPressArticles(limit)`.
// Approx. de `WHERE hidden=false ORDER BY "updatedAt" DESC LIMIT n` : scan
// borné par l'index by_hidden_publishedAt (desc) puis filtre JS sur updatedAt.
// `content` renvoyé (RAG).
// ─────────────────────────────────────────────────────────────────────────────
export const getRecentPressArticles = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(1, args.limit ?? 200), 1000);
    const candidates = await ctx.db
      .query("articles")
      .withIndex("by_hidden_publishedAt", (q) => q.eq("hidden", false))
      .order("desc")
      .take(Math.max(limit * 8, 500));
    const rows = candidates
      .filter((doc) => typeof doc.updatedAt === "number")
      .sort((a, b) => (b.updatedAt as number) - (a.updatedAt as number));
    const articles = [];
    for (const doc of rows) {
      articles.push({
        id: doc.supabaseId ?? doc._id,
        title: doc.title,
        description: doc.description ?? null,
        content: doc.content ?? null,
        source: doc.source ?? null,
        link: doc.link,
        publishedAt: doc.publishedAt,
        updatedAt: doc.updatedAt ?? null,
        imageUrl: doc.imageUrl ?? null,
        r2Url: doc.r2Url ?? null,
        author: doc.author ?? null,
        category: doc.category ?? null,
      });
      if (articles.length >= limit) break;
    }
    return { articles };
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Query 3 — actualités internes récentes pour `indexRecentNewsArticles(limit)`.
// Approx. de `WHERE hidden=false AND "statusWorkflow"='PUBLISHED'
// ORDER BY "updatedAt" DESC LIMIT n` : scan borné par l'index by_hidden puis
// filtre JS. Table actuellement VIDE (NewsArticle jamais migrée) — la query
// renverra [] tant que la table n'est pas alimentée côté Convex.
// ─────────────────────────────────────────────────────────────────────────────
export const getRecentNewsArticles = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(1, args.limit ?? 40), 1000);
    const candidates = await ctx.db
      .query("newsArticles")
      .withIndex("by_hidden", (q) => q.eq("hidden", false))
      .take(Math.max(limit * 8, 200));
    const rows = candidates
      .filter(
        (doc) =>
          doc.statusWorkflow === "PUBLISHED" && typeof doc.updatedAt === "number"
      )
      .sort((a, b) => (b.updatedAt as number) - (a.updatedAt as number));
    const articles = rows.slice(0, limit).map((doc) => ({
      id: doc._id,
      title: doc.title,
      slug: doc.slug,
      excerpt: doc.excerpt ?? null,
      content: doc.content,
      publishedAt: doc.publishedAt ?? null,
      updatedAt: doc.updatedAt ?? null,
      featuredImage: doc.featuredImage ?? null,
    }));
    return { articles };
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Query 4 — actualité interne par id (`_id` Convex) pour `indexNewsArticleById`.
// ─────────────────────────────────────────────────────────────────────────────
export const getNewsArticleById = query({
  args: { id: v.string() },
  handler: async (ctx, { id }) => {
    const doc = await ctx.db.get(id as Id<"newsArticles">);
    if (!doc || doc.hidden !== false || doc.statusWorkflow !== "PUBLISHED") return null;
    return {
      id: doc._id,
      title: doc.title,
      slug: doc.slug,
      excerpt: doc.excerpt ?? null,
      content: doc.content,
      publishedAt: doc.publishedAt ?? null,
      updatedAt: doc.updatedAt ?? null,
      featuredImage: doc.featuredImage ?? null,
    };
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Query 5 — enrichissement des citations : images de galerie (articleImages)
// par `articleId` (UUID Supabase d'origine). Prendre la meilleure image
// disponible : `bestUrl = r2Url ?? localImage ?? url`.
// ─────────────────────────────────────────────────────────────────────────────
export const getArticleImagesByArticleIds = query({
  args: { ids: v.array(v.string()) },
  handler: async (ctx, { ids }) => {
    const images: Array<{
      articleId: string;
      url: string;
      caption?: string;
      localImage: string | null;
      r2Url: string | null;
      bestUrl: string;
    }> = [];
    for (const articleId of ids) {
      const rows = await ctx.db
        .query("articleImages")
        .withIndex("by_articleId", (q) => q.eq("articleId", articleId))
        .take(50);
      if (rows.length > 0) {
        for (const row of rows) {
          const resolvedUrl =
            row.url ||
            (row.r2Url && !row.r2Url.includes("backblazeb2.com") ? row.r2Url : "") ||
            row.localImage ||
            "";
          if (resolvedUrl) {
            const image: {
              articleId: string;
              url: string;
              caption?: string;
              localImage: string | null;
              r2Url: string | null;
              bestUrl: string;
            } = {
              articleId,
              url: row.url,
              localImage: row.localImage ?? null,
              r2Url: row.r2Url ?? null,
              bestUrl: resolvedUrl,
            };
            if (row.caption) image.caption = row.caption;
            images.push(image);
          }
        }
      } else {
        const article = await ctx.db
          .query("articles")
          .withIndex("by_supabaseId", (q) => q.eq("supabaseId", articleId))
          .first();
        if (article && (article.imageUrl || article.r2Url)) {
          const resolvedUrl =
            article.imageUrl ||
            (article.r2Url && !article.r2Url.includes("backblazeb2.com") ? article.r2Url : "") ||
            "";
          if (resolvedUrl) {
            const image: {
              articleId: string;
              url: string;
              caption?: string;
              localImage: string | null;
              r2Url: string | null;
              bestUrl: string;
            } = {
              articleId,
              url: article.imageUrl || article.r2Url || "",
              localImage: null,
              r2Url: article.r2Url ?? null,
              bestUrl: resolvedUrl,
            };
            if (article.imageCaption) image.caption = article.imageCaption;
            images.push(image);
          }
        }
      }
    }
    return { images };
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Query 6 — enrichissement des citations news_article.
// NewsArticle n'a PAS de collection d'images dédiée dans le schéma Convex
// (featuredImage vit sur la ligne elle-même) et la table est VIDE (jamais
// migrée) : l'enrichissement renvoie donc [] tant que rien n'est alimenté.
// Lecture via `ctx.db.get` par _id Convex (retourne null hors table).
// ─────────────────────────────────────────────────────────────────────────────
export const getNewsArticleImagesByIds = query({
  args: { ids: v.array(v.string()) },
  handler: async (ctx, { ids }) => {
    const images: Array<{ articleId: string; url: string; caption?: string }> = [];
    for (const id of ids) {
      // db.get lève une erreur sur un id malformé (et non retourne null) :
      // les ids du RAG peuvent être des _id Convex OU des UUID étrangers à la
      // table — on saute ce qui ne se décode pas.
      let doc: Awaited<ReturnType<typeof ctx.db.get>> | null = null;
      try {
        doc = await ctx.db.get(id as Id<"newsArticles">);
      } catch {
        continue;
      }
      if (doc && doc.featuredImage) {
        images.push({ articleId: id, url: doc.featuredImage });
      }
    }
    return { images };
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Query 7 — pagination de TOUS les articles (id=supabaseId) pour la purge /
// l'archive complète. Ne renvoie QUE les ids (léger, égrès maîtrisé).
// ─────────────────────────────────────────────────────────────────────────────
export const getAllArticleIds = query({
  args: {
    cursor: v.optional(v.union(v.null(), v.string())),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, { cursor, limit }) => {
    const numItems = Math.min(Math.max(1, limit ?? 500), 1000);
    const res = await ctx.db
      .query("articles")
      .withIndex("by_publishedAt")
      .paginate({ cursor: cursor ?? null, numItems });
    return {
      ids: res.page.map((doc) => doc.supabaseId ?? doc._id),
      cursor: res.continueCursor,
      isDone: res.isDone,
    };
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Query 8 — page d'articles complets (CONTENT inclus) pour `indexArticles()`
// (archive complète paginée). Un seul appel HTTP par page, contrairement à un
// getArticleById par article (~27k appels sur l'archive). Equivalent du
// SELECT paginé SQL (hidden=false) ; `content` renvoyé (RAG).
// ─────────────────────────────────────────────────────────────────────────────
export const getArticlesPage = query({
  args: {
    cursor: v.optional(v.union(v.null(), v.string())),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, { cursor, limit }) => {
    const numItems = Math.min(Math.max(1, limit ?? 200), 500);
    const res = await ctx.db
      .query("articles")
      .withIndex("by_hidden_publishedAt", (q) => q.eq("hidden", false))
      .order("desc")
      .paginate({ cursor: cursor ?? null, numItems });
    return {
      articles: res.page.map((doc) => ({
        id: doc.supabaseId ?? doc._id,
        title: doc.title,
        description: doc.description ?? null,
        content: doc.content ?? null,
        source: doc.source ?? null,
        link: doc.link,
        publishedAt: doc.publishedAt,
        updatedAt: doc.updatedAt ?? null,
        imageUrl: doc.imageUrl ?? null,
        r2Url: doc.r2Url ?? null,
        author: doc.author ?? null,
        category: doc.category ?? null,
      })),
      cursor: res.continueCursor,
      isDone: res.isDone,
    };
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Query 9 — pagination de TOUTES les actualités internes publiées (contenu
// inclus) pour `indexNewsArticles()` (source complète, table petite).
// ─────────────────────────────────────────────────────────────────────────────
export const getAllNewsArticles = query({
  args: {
    cursor: v.optional(v.union(v.null(), v.string())),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, { cursor, limit }) => {
    const numItems = Math.min(Math.max(1, limit ?? 200), 500);
    const res = await ctx.db
      .query("newsArticles")
      .withIndex("by_publishedAt")
      .paginate({ cursor: cursor ?? null, numItems });
    const articles = res.page
      .filter((doc) => doc.hidden === false && doc.statusWorkflow === "PUBLISHED")
      .map((doc) => ({
        id: doc._id,
        title: doc.title,
        slug: doc.slug,
        excerpt: doc.excerpt ?? null,
        content: doc.content,
        publishedAt: doc.publishedAt ?? null,
        updatedAt: doc.updatedAt ?? null,
        featuredImage: doc.featuredImage ?? null,
      }));
    return { articles, cursor: res.continueCursor, isDone: res.isDone };
  },
});
