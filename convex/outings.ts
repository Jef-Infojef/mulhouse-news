import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// ─────────────────────────────────────────────────────────────────────────────
// Sorties / agenda — fonctions Convex des collections outings/outingCategories/
// outingTags (port Supabase → Convex, 12/08/2026).
//
// Consommées par :
//  • le scraper Python `scripts/scrape_outings.py` via `convex_client.py`
//    (endpoints /api/query + /api/mutation) — UPSERT, en double écriture avec
//    Supabase (assocommercants.fr lit encore Supabase) ;
//  • le pont RAG MulhouseGPT `lib/convex-news.ts` — lectures getRecentOutings /
//    getOutingCategories.
//
// Conventions (identiques aux autres collections) :
//  • `supabaseId` = UUID Supabase d'origine (id de la ligne Outing /
//    OutingCategory). Pour OutingTag, pas d'id Prisma (PK composite) → UUID v5
//    déterministe calculé sur (outingId, categoryId), stable entre les runs.
//  • Les clés de relation (associationId, outingId, categoryId) restent en
//    v.string() (jamais de v.id() Convex).
//  • Dates Prisma → epoch ms (v.number()).
//  • Convex refuse `null` sur les champs v.optional(...) : le client Python/TS
//    omet les champs None/undefined avant l'appel.
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// Mutations
// ─────────────────────────────────────────────────────────────────────────────

export const upsertOuting = mutation({
  args: {
    row: v.object({
      supabaseId: v.string(), // UUID Supabase (id de la ligne Outing)
      associationId: v.string(),
      title: v.string(),
      description: v.optional(v.string()),
      imageUrl: v.optional(v.string()),
      date: v.number(), // epoch ms
      endDate: v.optional(v.number()),
      location: v.optional(v.string()),
      price: v.optional(v.string()),
      link: v.optional(v.string()),
      hidden: v.optional(v.boolean()),
      createdAt: v.optional(v.number()),
      updatedAt: v.optional(v.number()),
    }),
  },
  handler: async (ctx, { row }) => {
    const existing = await ctx.db
      .query("outings")
      .withIndex("by_supabaseId", (q) => q.eq("supabaseId", row.supabaseId))
      .first();

    if (existing) {
      // Patch partiel : seuls les champs fournis sont mis à jour (les champs
      // optionnels absents/None sont omis par le client — pas d'effacement).
      const patch: Record<string, unknown> = {};
      const keys = [
        "title",
        "description",
        "imageUrl",
        "date",
        "endDate",
        "location",
        "price",
        "link",
        "hidden",
      ] as const;
      for (const key of keys) {
        if (row[key] !== undefined) patch[key] = row[key];
      }
      patch["updatedAt"] = row.updatedAt ?? Date.now();
      await ctx.db.patch(existing._id, patch);
      return { created: false, id: existing._id, supabaseId: existing.supabaseId };
    }

    const id = await ctx.db.insert("outings", {
      supabaseId: row.supabaseId,
      associationId: row.associationId,
      title: row.title,
      description: row.description,
      imageUrl: row.imageUrl,
      date: row.date,
      endDate: row.endDate,
      location: row.location,
      price: row.price,
      link: row.link,
      hidden: row.hidden ?? false,
      createdAt: row.createdAt ?? Date.now(),
      updatedAt: row.updatedAt ?? Date.now(),
    });
    return { created: true, id, supabaseId: row.supabaseId };
  },
});

export const upsertOutingCategory = mutation({
  args: {
    row: v.object({
      supabaseId: v.string(), // UUID Supabase (id de la ligne OutingCategory)
      associationId: v.string(),
      name: v.string(),
      slug: v.string(),
      color: v.optional(v.string()),
      createdAt: v.optional(v.number()),
      updatedAt: v.optional(v.number()),
    }),
  },
  handler: async (ctx, { row }) => {
    const existing = await ctx.db
      .query("outingCategories")
      .withIndex("by_supabaseId", (q) => q.eq("supabaseId", row.supabaseId))
      .first();

    if (existing) {
      const patch: Record<string, unknown> = {};
      const keys = ["name", "slug", "color"] as const;
      for (const key of keys) {
        if (row[key] !== undefined) patch[key] = row[key];
      }
      patch["updatedAt"] = row.updatedAt ?? Date.now();
      await ctx.db.patch(existing._id, patch);
      return { created: false, id: existing._id, supabaseId: existing.supabaseId };
    }

    const id = await ctx.db.insert("outingCategories", {
      supabaseId: row.supabaseId,
      associationId: row.associationId,
      name: row.name,
      slug: row.slug,
      color: row.color,
      createdAt: row.createdAt ?? Date.now(),
      updatedAt: row.updatedAt ?? Date.now(),
    });
    return { created: true, id, supabaseId: row.supabaseId };
  },
});

export const upsertOutingTag = mutation({
  args: {
    row: v.object({
      supabaseId: v.string(), // UUID v5 déterministe (outingId:categoryId)
      outingId: v.string(), // supabaseId de l'Outing
      categoryId: v.string(), // supabaseId de l'OutingCategory
    }),
  },
  handler: async (ctx, { row }) => {
    // Dédup par (outingId, categoryId) — PK composite Prisma de OutingTag.
    const existing = await ctx.db
      .query("outingTags")
      .withIndex("by_outingId", (q) => q.eq("outingId", row.outingId))
      .filter((q) => q.eq(q.field("categoryId"), row.categoryId))
      .first();

    if (existing) {
      // Même couple mais supabaseId différent (re-génération) : on patche pour
      // garder la cohérence avec l'id synthétique attendu.
      if (existing.supabaseId !== row.supabaseId) {
        await ctx.db.patch(existing._id, { supabaseId: row.supabaseId });
      }
      return { created: false, id: existing._id, supabaseId: existing.supabaseId };
    }

    const id = await ctx.db.insert("outingTags", {
      supabaseId: row.supabaseId,
      outingId: row.outingId,
      categoryId: row.categoryId,
    });
    return { created: true, id, supabaseId: row.supabaseId };
  },
});

/** Suppression d'une sortie par supabaseId (+ ses tags, cascade manuelle). */
export const deleteOutingBySupabaseId = mutation({
  args: { supabaseId: v.string() },
  handler: async (ctx, { supabaseId }) => {
    const doc = await ctx.db
      .query("outings")
      .withIndex("by_supabaseId", (q) => q.eq("supabaseId", supabaseId))
      .first();
    if (!doc) return { success: true, deleted: false };
    const tags = await ctx.db
      .query("outingTags")
      .withIndex("by_outingId", (q) => q.eq("outingId", supabaseId))
      .take(100);
    for (const tag of tags) await ctx.db.delete(tag._id);
    await ctx.db.delete(doc._id);
    return { success: true, deleted: true };
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Queries
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Sorties à venir (hidden=false, date dans [maintenant, maintenant+90j]),
 * triées par date asc, LIMIT ~3000 — équivalent de la query SQL `indexOutings`
 * de MulhouseGPT. `id` = supabaseId (sourceId RAG stable). Catégories jointes
 * en JS via outingTags + outingCategories (index par couple, pas de v.id()).
 */
export const getRecentOutings = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const now = Date.now();
    const end = now + 90 * 24 * 3600_000;
    const limit = Math.min(Math.max(1, args.limit ?? 3000), 3000);

    const outings = await ctx.db
      .query("outings")
      .withIndex("by_hidden_date", (q) =>
        q.eq("hidden", false).gte("date", now).lte("date", end)
      )
      .order("asc")
      .take(limit);

    // Jointure en JS : toutes les catégories (petit volume) puis regroupement
    // des tags par outingId. `outingTags.collect()` reste sous la limite de
    // lecture (5,5k docs ~<1 Mo) — à réviser si le volume explose.
    const categories = await ctx.db.query("outingCategories").collect();
    const categoryName = new Map(categories.map((c) => [c.supabaseId, c.name]));
    const tags = await ctx.db.query("outingTags").collect();
    const namesByOuting = new Map<string, string[]>();
    for (const tag of tags) {
      const name = categoryName.get(tag.categoryId);
      if (!name) continue;
      const list = namesByOuting.get(tag.outingId) ?? [];
      list.push(name);
      namesByOuting.set(tag.outingId, list);
    }

    return {
      outings: outings.map((o) => ({
        id: o.supabaseId,
        supabaseId: o.supabaseId,
        title: o.title,
        description: o.description ?? null,
        date: o.date,
        endDate: o.endDate ?? null,
        location: o.location ?? null,
        price: o.price ?? null,
        link: o.link ?? null,
        categories: (namesByOuting.get(o.supabaseId) ?? []).map((name) => ({ name })),
      })),
    };
  },
});

/** Toutes les catégories de sorties (supabaseId, name, slug, color). */
export const getOutingCategories = query({
  args: {},
  handler: async (ctx) => {
    const docs = await ctx.db.query("outingCategories").collect();
    return docs.map((doc) => ({
      supabaseId: doc.supabaseId,
      name: doc.name,
      slug: doc.slug,
      color: doc.color ?? null,
    }));
  },
});
