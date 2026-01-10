import { getLatestArticles } from './actions'
import { ArticleCard } from '@/components/ArticleCard'
import { Newspaper, RefreshCw } from 'lucide-react'

// Force le rendu dynamique pour avoir toujours les dernières news
export const dynamic = 'force-dynamic'
export const revalidate = 60 // Revalidation toutes les minutes au max

export default async function Home() {
  const articles = await getLatestArticles(100)

  return (
    <main className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-10 text-center">
          <div className="inline-flex items-center justify-center p-3 bg-blue-600 rounded-full mb-4 shadow-lg shadow-blue-200">
            <Newspaper className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight sm:text-5xl mb-2">
            Mulhouse News
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            L'actualité locale en temps réel, agrégée depuis toutes les sources locales.
          </p>
          <div className="mt-4 text-sm text-gray-500 flex items-center justify-center gap-2">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
            Mise à jour automatique toutes les 15 minutes
          </div>
        </header>

        {articles.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-2xl shadow-sm">
            <p className="text-gray-500 text-lg">Aucun article trouvé pour le moment.</p>
            <p className="text-sm text-gray-400 mt-2">Le scraper est peut-être en train de tourner ?</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        )}
        
        <footer className="mt-16 text-center text-gray-400 text-sm pb-8">
          <p>© {new Date().getFullYear()} Mulhouse News • Agrégateur automatique</p>
        </footer>
      </div>
    </main>
  )
}