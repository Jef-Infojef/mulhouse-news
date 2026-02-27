'use client'

import { useState, useEffect, useMemo } from 'react'
import { getLatestArticles } from '@/app/actions'
import { ArticleCard } from '@/components/ArticleCard'
import { Logo } from '@/components/Logo'
import { SplashScreen } from '@/components/SplashScreen'
import { AlertTriangle, Search, Loader2, Moon, Sun, Calendar, Clock, Cloud, CloudRain, CloudSnow } from 'lucide-react'
import { useTheme } from 'next-themes'

interface NewsTag {
  id: string
  name: string
  slug: string
  color: string | null
}

interface Article {
  id: string
  title: string
  link: string
  imageUrl: string | null
  localImage: string | null
  r2Url: string | null
  source: string | null
  description: string | null
  content: string | null
  publishedAt: Date
  scrapedAt: Date
  createdAt: Date
  updatedAt: Date
  ArticleGoogleTag: { NewsTag: NewsTag }[]
}

interface HomeClientProps {
  initialArticles: Article[]
  initialCount: number
}

export default function HomeClient({ initialArticles, initialCount }: HomeClientProps) {
  const [allArticles, setAllArticles] = useState<Article[]>(initialArticles)
  const [displayedArticles, setDisplayedArticles] = useState<Article[]>(initialArticles.slice(0, 24))
  const [filteredCount, setFilteredCount] = useState(initialCount)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [activeSearch, setActiveQuery] = useState('')
  const [displayCount, setDisplayCount] = useState(24)
  const [mounted, setMounted] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())
  const [weather, setWeather] = useState<{ temp: number; code: number } | null>(null)
  const { resolvedTheme, setTheme } = useTheme()
  const [showSplash, setShowSplash] = useState(true)
  const [isAdmin, setIsAdmin] = useState(false)
  const [activeTag, setActiveTag] = useState<string | null>(null)

  const pageSize = 24

  useEffect(() => {
    setMounted(true)
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)

    // Check Admin status
    const auth = document.cookie.split('; ').find(row => row.startsWith('admin_auth='))?.split('=')[1]
    if (auth === 'true') {
      setIsAdmin(true)
    }

    const fetchWeather = async () => {
      try {
        const res = await fetch('https://api.open-meteo.com/v1/forecast?latitude=47.7508&longitude=7.3359&current_weather=true')
        const data = await res.json()
        if (data.current_weather) {
          setWeather({
            temp: data.current_weather.temperature,
            code: data.current_weather.weathercode
          })
        }
      } catch (e) { console.error("Erreur météo", e) }
    }
    fetchWeather()
    
    return () => clearInterval(timer)
  }, [])

  const loadArticles = async (query: string) => {
    setLoading(true)
    try {
      const { articles, error: fetchError } = await getLatestArticles(query)

      if (fetchError) {
        setError(fetchError)
        return
      }

      setAllArticles(articles)
      setFilteredCount(articles.length)
      setDisplayedArticles(articles.slice(0, displayCount))
      setError(null)
    } catch (err: any) {
      setError(err.message || 'Une erreur est survenue')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      setActiveQuery(search)
      loadArticles(search)
    }
  }

  const clearSearch = () => {
    setSearch('')
    setActiveQuery('')
    loadArticles('')
  }


  const loadMore = () => {
    setDisplayCount((prev) => prev + pageSize)
  }

  const handleArticleDeleted = (id: string) => {
    setAllArticles(prev => prev.filter(a => a.id !== id))
    setFilteredCount(prev => prev - 1)
  }

  // Collect all unique tags from all articles
  const allTags = useMemo(() => {
    const tagMap = new Map<string, NewsTag>()
    allArticles.forEach(article => {
      article.ArticleGoogleTag?.forEach(({ NewsTag: tag }) => {
        if (!tagMap.has(tag.id)) tagMap.set(tag.id, tag)
      })
    })
    return Array.from(tagMap.values()).sort((a, b) => a.name.localeCompare(b.name))
  }, [allArticles])

  // Filter displayed articles by active tag
  const tagFilteredArticles = useMemo(() => {
    if (!activeTag) return allArticles
    return allArticles.filter(article =>
      article.ArticleGoogleTag?.some(({ NewsTag: tag }) => tag.id === activeTag)
    )
  }, [allArticles, activeTag])

  useEffect(() => {
    setFilteredCount(tagFilteredArticles.length)
    setDisplayedArticles(tagFilteredArticles.slice(0, displayCount))
  }, [tagFilteredArticles, displayCount])

  function getWeatherIcon(code: number) {
    if (code === 0) return <Sun size={14} className="text-yellow-500 shrink-0" />
    if (code >= 1 && code <= 3) return <Cloud size={14} className="text-blue-400 shrink-0" />
    if (code >= 45 && code <= 48) return <Cloud size={14} className="text-gray-400 shrink-0" />
    if (code >= 51 && code <= 67) return <CloudRain size={14} className="text-blue-500 shrink-0" />
    if (code >= 71 && code <= 77) return <CloudSnow size={14} className="text-blue-200 shrink-0" />
    if (code >= 80 && code <= 82) return <CloudRain size={14} className="text-blue-600 shrink-0" />
    if (code >= 85 && code <= 86) return <CloudSnow size={14} className="text-blue-300 shrink-0" />
    return <Sun size={14} className="text-yellow-500 shrink-0" />
  }

  return (
    <>
      {showSplash && <SplashScreen onFinish={() => setShowSplash(false)} />}
      <main className="min-h-screen transition-colors">
        {/* Top Bar Info */}
        <div className="w-full bg-gray-100/50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-800 py-2">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center gap-2 text-[10px] sm:text-sm font-medium text-gray-600 dark:text-gray-400">
            <div className="flex items-center gap-1.5 capitalize">
              <Calendar size={14} className="text-blue-600 shrink-0" />
              <span className="whitespace-nowrap">
                {mounted ? currentTime.toLocaleDateString('fr-FR', { 
                  weekday: 'long', 
                  day: 'numeric', 
                  month: 'long', 
                  year: 'numeric',
                  timeZone: 'Europe/Paris'
                }) : '...'}
              </span>
            </div>
            <div className="flex items-center gap-3 sm:gap-4">
              <div className="flex items-center gap-1.5 sm:border-l border-gray-300 dark:border-gray-700 sm:pl-4">
                <Clock size={14} className="text-blue-600 shrink-0" />
                <span>{mounted ? currentTime.toLocaleTimeString('fr-FR', { 
                  hour: '2-digit', 
                  minute: '2-digit',
                  timeZone: 'Europe/Paris'
                }) : '...'}</span>
              </div>

              {weather && (
                <div className="flex items-center gap-1.5 border-l border-gray-300 dark:border-gray-700 pl-3 sm:pl-4">
                  {getWeatherIcon(weather.code)}
                  <span className="font-bold text-gray-900 dark:text-white">{weather.temp}°C</span>
                </div>
              )}

              {mounted && (
                <button
                  onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
                  className="flex items-center justify-center p-1.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm"
                  aria-label="Toggle dark mode"
                >
                  {resolvedTheme === 'dark' ? <Sun size={14} className="text-yellow-500" /> : <Moon size={14} className="text-blue-600" />}
                </button>
              )}
            </div>
          </div>
        </div>

        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
            <div className="flex items-start justify-between gap-6 lg:gap-8">
              <div className="flex items-center gap-3 sm:gap-6 flex-1 min-w-0">
                <div className="inline-flex items-center justify-center p-1 bg-slate-900 rounded-2xl shadow-xl shadow-red-900/10 border border-slate-800 shrink-0">
                  <Logo className="h-24 w-24 sm:h-32 sm:w-32 text-red-600" />
                </div>
                <div className="min-w-0">
                  <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-foreground tracking-tight truncate">
                    Mulhouse Actu
                  </h1>
                  <p className="text-sm sm:text-lg text-gray-600 dark:text-gray-400 mb-3">
                    Toute l'actu de Mulhouse en temps réel
                  </p>
                  {allTags.length > 0 && (
                    <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
                      <button
                        onClick={() => { setActiveTag(null); setDisplayCount(24) }}
                        className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${
                          activeTag === null
                            ? 'bg-blue-600 text-white border-blue-600 shadow'
                            : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-blue-400 hover:text-blue-600'
                        }`}
                      >
                        Tous
                      </button>
                      {allTags.map(tag => (
                        <button
                          key={tag.id}
                          onClick={() => { setActiveTag(tag.id); setDisplayCount(24) }}
                          className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${
                            activeTag === tag.id ? 'shadow' : 'hover:border-opacity-80'
                          }`}
                          style={
                            activeTag === tag.id
                              ? { backgroundColor: tag.color || '#3b82f6', color: '#fff', borderColor: tag.color || '#3b82f6' }
                              : tag.color
                                ? { backgroundColor: tag.color + '22', color: tag.color, borderColor: tag.color + '55' }
                                : undefined
                          }
                        >
                          #{tag.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className="hidden lg:flex shrink-0">
                <div className="w-80 h-64 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-700 flex items-center justify-center">
                  <div className="text-center px-4">
                    <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">Espace Publicitaire</p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">300x250px</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </header>


        <div className="max-w-7xl mx-auto py-6 sm:py-8 px-4 sm:px-6 lg:px-8">
          <div className="mb-8">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={search}
                placeholder="Rechercher une actualité..."
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all shadow-sm"
              />
            </div>
          </div>

          {activeSearch && !loading && (
            <div className="mb-8 flex items-center justify-between bg-blue-50/50 dark:bg-blue-900/10 p-4 rounded-xl border border-blue-100 dark:border-blue-900/30">
              <p className="text-blue-800 dark:text-blue-300 font-medium">
                {filteredCount > 0 
                  ? `${filteredCount} article${filteredCount > 1 ? 's' : ''} trouvé${filteredCount > 1 ? 's' : ''} pour "${activeSearch}"`
                  : `Aucun article trouvé pour "${activeSearch}"`
                }
              </p>
              <button onClick={clearSearch} className="text-blue-600 dark:text-blue-400 text-sm font-bold hover:underline">
                Effacer la recherche
              </button>
            </div>
          )}

          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 mb-8 rounded-r">
              <div className="flex">
                <AlertTriangle className="h-5 w-5 text-red-400" />
                <div className="ml-3">
                  <p className="text-sm text-red-700 dark:text-red-400">Erreur : {error}</p>
                </div>
              </div>
            </div>
          )}

          {loading ? (
            <div className="text-center py-20">
              <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400 text-lg">Chargement des articles...</p>
            </div>
          ) : displayedArticles.length === 0 ? (
            <div className="text-center py-20 bg-gray-50 dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800">
              <p className="text-gray-500 dark:text-gray-400 text-lg">Aucun article trouvé.</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                {displayedArticles.map((article) => (
                  <ArticleCard 
                    key={article.id} 
                    article={article} 
                    isAdmin={isAdmin}
                    onDelete={handleArticleDeleted}
                  />
                ))}
              </div>

              {displayCount < filteredCount && (
                <div className="text-center py-8">
                  <button
                    onClick={loadMore}
                    className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
                  >
                    Charger plus d'articles
                  </button>
                </div>
              )}
            </>
          )}

          <footer className="mt-16 text-center text-gray-400 dark:text-gray-600 text-sm pb-8 border-t border-gray-200 dark:border-gray-800 pt-8">
            <p>© {new Date().getFullYear()} Mulhouse Actu • Agrégateur automatique</p>
          </footer>
        </div>
      </main>
    </>
  )
}
