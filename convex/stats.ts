import { query } from "./_generated/server";
import { v } from "convex/values";

// Comptage paginé côté client : chaque page est une exécution de query séparée,
// ce qui évite la limite d'opérations système d'une query unique sur les grosses
// tables (articles ~27k docs avec contenu HTML). Le client boucle sur le cursor.
export const countTablePage = query({
  args: {
    table: v.union(
      v.literal("articles"),
      v.literal("articleImages"),
      v.literal("scrapingLogs"),
      v.literal("appConfig"),
      v.literal("weatherHistory"),
      v.literal("articleGoogleTags"),
      v.literal("newsArticles"),
      v.literal("newsArticleTags"),
      v.literal("newsTags")
    ),
    cursor: v.union(v.null(), v.string()),
  },
  handler: async (ctx, { table, cursor }) => {
    const res = await ctx.db.query(table).paginate({ cursor, numItems: 500 });
    return { count: res.page.length, isDone: res.isDone, continueCursor: res.continueCursor };
  },
});