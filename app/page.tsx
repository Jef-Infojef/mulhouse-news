import { getLatestArticles } from './actions'
import HomeClient from '@/components/HomeClient'

// L'« on-demand » annonce ici n'a jamais existe pour la collecte : le seul
// revalidatePath('/') du depot est dans revalidateSite() (app/actions.ts), une
// action reservee a l'admin connecte. Les scrapers, eux, ecrivent directement
// dans l'Aiven sans rien invalider — cette page restait donc figee 24 h (le
// 17/09 elle servait encore l'etat du 16/09 16 h, sept heures de retard).
// Le TTL est le seul mecanisme qui suit la collecte : 5 minutes, le scrape
// tournant toutes les 15 minutes.
export const revalidate = 300

export default async function Home() {
  const { articles } = await getLatestArticles()

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "Mulhouse Actu - Actualités locales",
    "description": "Suivez l'actualité de Mulhouse et sa région en temps réel.",
    "url": "https://mulhouse-actu.vercel.app/",
    "mainEntity": {
      "@type": "ItemList",
      "itemListElement": (articles || []).slice(0, 20).map((article, index) => ({
        "@type": "ListItem",
        "position": index + 1,
        "item": {
          "@type": "NewsArticle",
          "headline": article.title,
          "description": article.description || "",
          "image": article.imageUrl || article.r2Url || "",
          "datePublished": article.publishedAt.toISOString(),
          "author": {
            "@type": "Organization",
            "name": article.source || "Presse locale"
          },
          "url": article.link
        }
      }))
    }
  }

  return (
    <>
      <script
        type="application/ld+json"
      >
        {JSON.stringify(jsonLd)}
      </script>
      <HomeClient 
        initialArticles={articles || []} 
        initialCount={articles?.length || 0} 
      />
    </>
  )
}