import { getLatestArticles } from './actions'
import HomeClient from '@/components/HomeClient'

// Revalidation toutes les 15 minutes pour le SEO et la fraîcheur des données
export const revalidate = 900 

export default async function Home() {
  const { articles, error } = await getLatestArticles()

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
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <HomeClient 
        initialArticles={articles || []} 
        initialCount={articles?.length || 0} 
      />
    </>
  )
}