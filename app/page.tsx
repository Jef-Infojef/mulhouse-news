'use client'

import { useState, useEffect, useRef } from 'react'
import { getLatestArticles } from './actions'
import { ArticleCard } from '@/components/ArticleCard'
import { Newspaper, AlertTriangle, Search, Loader2, Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'

interface Article {
  id: string
  title: string
  link: string
  imageUrl: string | null
  source: string | null
  description: string | null
  publishedAt: Date
}

export default function Home() {
  const [allArticles, setAllArticles] = useState<Article[]>([])
  const [displayedArticles, setDisplayedArticles] = useState<Article[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [displayCount, setDisplayCount] = useState(20)
  const { theme, setTheme } = useTheme()
  const observerTarget = useRef<HTMLDivElement>(null)

  const pageSize = 20

  // Load all articles once
  useEffect(() => {
    const loadArticles = async () => {
      try {
        const { articles, error: fetchError } = await getLatestArticles()

        if (fetchError) {
          setError(fetchError)
          return
        }

        setAllArticles(articles)
        setError(null)
      } catch (err: any) {
        setError(err.message || 'Une erreur est survenue')
      } finally {
        setLoading(false)
      }
    }

    loadArticles()
  }, [])

  // Filter and slice articles based on search and displayCount
  useEffect(() => {
    let filtered = allArticles

    if (search) {
      const query = search.toLowerCase()
      filtered = allArticles.filter(
        (article) =>
          article.title.toLowerCase().includes(query) ||
          article.description?.toLowerCase().includes(query) ||
          article.source?.toLowerCase().includes(query)
      )
    }

    setDisplayedArticles(filtered.slice(0, displayCount))
  }, [allArticles, search, displayCount])

  // Infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && displayCount < displayedArticles.length) {
          setDisplayCount((prev) => prev + pageSize)
        }
      },
      { threshold: 0.1 }
    )

    if (observerTarget.current) {
      observer.observe(observerTarget.current)
    }

    return () => {
      if (observerTarget.current) {
        observer.unobserve(observerTarget.current)
      }
    }
  }, [displayCount, displayedArticles.length])

  return (
    <main className="min-h-screen bg-white dark:bg-gray-950 transition-colors">
      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="mb-10">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="inline-flex items-center justify-center p-3 bg-blue-600 rounded-full shadow-lg shadow-blue-200 dark:shadow-blue-900/50">
                <Newspaper className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white tracking-tight sm:text-5xl">
                  Mulhouse News.
                </h1>
                <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl">
                  L'actualité locale en temps réel
                </p>
              </div>
            </div>
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-lg bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100 hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors"
              aria-label="Toggle dark mode"
            >
              {theme === 'dark' ? <Sun size={24} /> : <Moon size={24} />}
            </button>
          </div>

          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-2">
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              Mise à jour automatique toutes les 15 minutes
            </div>
          </div>
        </header>

        {/* Search Bar */}
        <div className="mb-8">
          <div className="relative">
            <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher des articles..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
            />
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 mb-8 rounded-r">
            <div className="flex">
              <div className="flex-shrink-0">
                <AlertTriangle className="h-5 w-5 text-red-400" aria-hidden="true" />
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700 dark:text-red-400">
                  Erreur de connexion : {error}
                </p>
                <p className="text-xs text-red-500 dark:text-red-400 mt-1">
                  Vérifiez la variable DATABASE_URL dans Vercel.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="text-center py-20">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400 text-lg">Chargement des articles...</p>
          </div>
        ) : displayedArticles.length === 0 ? (
          <div className="text-center py-20 bg-gray-50 dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800">
            <p className="text-gray-500 dark:text-gray-400 text-lg">Aucun article trouvé.</p>
            {search && <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">Essayez une autre recherche</p>}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {displayedArticles.map((article) => (
                <ArticleCard key={article.id} article={article} />
              ))}
            </div>

            {/* Infinite Scroll Indicator */}
            {displayCount < allArticles.filter((a) => {
              if (!search) return true
              const query = search.toLowerCase()
              return a.title.toLowerCase().includes(query) ||
                a.description?.toLowerCase().includes(query) ||
                a.source?.toLowerCase().includes(query)
            }).length && (
              <div ref={observerTarget} className="text-center py-8">
                <div className="flex items-center justify-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                  <span className="text-gray-500 dark:text-gray-400">Chargement de plus d'articles...</span>
                </div>
              </div>
            )}

            {displayCount >= allArticles.filter((a) => {
              if (!search) return true
              const query = search.toLowerCase()
              return a.title.toLowerCase().includes(query) ||
                a.description?.toLowerCase().includes(query) ||
                a.source?.toLowerCase().includes(query)
            }).length && displayedArticles.length > 0 && (
              <div className="text-center py-8">
                <p className="text-gray-400 dark:text-gray-500">Fin des articles</p>
              </div>
            )}
          </>
        )}

        {/* Footer */}
        <footer className="mt-16 text-center text-gray-400 dark:text-gray-600 text-sm pb-8 border-t border-gray-200 dark:border-gray-800 pt-8">
          <p>© {new Date().getFullYear()} Mulhouse News • Agrégateur automatique</p>
        </footer>
      </div>
    </main>
  )
}
