# Database Schema and Tag Structure Summary

## Overview
This is a Next.js news aggregation application ("Mulhouse Actu") that scrapes articles from multiple French news sources. Currently, **there is NO Tag model or tag-related functionality implemented**.

---

## Article Model Fields (Prisma Schema)

The `Article` model in `prisma/schema.prisma` contains the following fields:

| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| `id` | String | @id, @default(cuid()) | Unique identifier |
| `title` | String | Required | Article headline |
| `link` | String | @unique | Original article URL (unique constraint) |
| `imageUrl` | String? | Optional | Original image URL from source |
| `source` | String? | Optional | News source name (e.g., "L'Alsace", "DNA") |
| `description` | String? | Optional | Summary/description of article |
| `publishedAt` | DateTime | Required | Publication date from source |
| `scrapedAt` | DateTime | @default(now()) | When article was scraped |
| `createdAt` | DateTime | @default(now()) | Database creation timestamp |
| `updatedAt` | DateTime | @updatedAt | Last update timestamp |
| `content` | String? | Optional | Full article content (text body) |
| `localImage` | String? | Optional | Local file path for image |
| `r2Url` | String? | Optional | Cloudflare R2 storage URL for image |

**Indexes:**
- `@@index([publishedAt])` - For efficient date-based queries
- `@@index([source])` - For filtering by news source

---

## Tag Model

**Status:** NOT IMPLEMENTED

There is currently no `Tag` model in the schema. No tag-related fields exist in the Article model, and no tag relationship or association table is defined.

---

## Other Models in Schema

1. **ScrapingLog** - Tracks scraping operations
   - Records: startedAt, finishedAt, status, articlesCount, successCount, errorCount, details, errorMessage

2. **AppConfig** - Application configuration key-value store
   - Fields: key, value, updatedAt

3. **WeatherHistory** - Weather data (appears unused in current views)
   - Fields: location, day, month, year, tempMax, tempMin, weatherCode

---

## Query Operations in `app/actions.ts`

### `getLatestArticles(query?: string)`
**Purpose:** Fetch articles with optional search filtering

**Database Query:**
```typescript
const articles = await prisma.article.findMany({
  where: whereClause,
  take: 200,
  orderBy: { publishedAt: 'desc' }
})
```

**Search Fields (when query provided):**
- `title` (case-insensitive contains)
- `content` (case-insensitive contains)
- `description` (case-insensitive contains)
- `source` (case-insensitive contains)

**Returned Fields:** All Article fields (no explicit select, so all fields returned)

**Deduplication:** 
- Filters duplicates by: title (trimmed, lowercase), imageUrl, and EBRA image UUID
- Returns up to 200 unique articles

---

## Article Fields Used in Components

### ArticleCard Component (components/ArticleCard.tsx)
All Article fields are accessible in the component interface:
- Display: `title`, `imageUrl`, `source`, `description`, `publishedAt`
- Links: `link`
- Fallback images: `r2Url`, `localImage`
- Metadata: `id`, `scrapedAt`, `createdAt`, `updatedAt`, `content`

### HomeClient Component (components/HomeClient.tsx)
Fetches articles via `getLatestArticles()` and displays with:
- Search/filter functionality across all text fields
- Pagination (24 articles per page)
- Admin deletion capability
- No tag filtering or display

---

## Data Flow Summary

```
Database (Article table)
    ↓
getLatestArticles(query?) [app/actions.ts]
    ↓ (filters, deduplicates)
    ↓
HomeClient [components/HomeClient.tsx]
    ↓ (displays 24 at a time)
    ↓
ArticleCard [components/ArticleCard.tsx]
```

---

## Key Observations

1. **No Tag Support:** The entire system operates without tags or categories
2. **Source-Based Organization:** Articles are organized primarily by `source` field
3. **Search is Text-Based:** Filtering works via full-text search on title, content, description, and source
4. **Simple Relationships:** No complex relational data; Articles are standalone entities
5. **Image Handling:** Uses a fallback strategy (original imageUrl → R2 → local → favicon)
6. **Deduplication Logic:** Handles duplicates at query time, not schema level

---

## Recommendations for Adding Tags

If tags need to be implemented, consider:

1. **Create a Tag model** with fields: id, name, slug, description
2. **Create ArticleTag junction table** for many-to-many relationship
3. **Add indexes** on Tag name/slug for efficient queries
4. **Update queries** to include tag relations
5. **Add tag filtering** to getLatestArticles() function
6. **Update UI components** to display tags on ArticleCard
