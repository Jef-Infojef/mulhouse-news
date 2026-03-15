'use client'

import { useReducer, useEffect, useMemo, useCallback, useId } from 'react'
import { getLatestArticles } from '@/app/actions'
import { ArticleCard } from '@/components/ArticleCard'
import { Logo } from '@/components/Logo'
import { SplashScreen } from '@/components/SplashScreen'
import { AlertTriangle, Search, Loader2, Moon, Sun, Calendar, Clock, Cloud, CloudRain, CloudSnow, Vote } from 'lucide-react'
import { useTheme } from 'next-themes'
import Link from 'next/link'

// --- Types ---

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

type State = {
  allArticles: Article[]
  error: string | null
  loading: boolean
  search: string
  activeSearch: string
  displayCount: number
  mounted: boolean
  currentTime: Date
  weather: { temp: number; code: number } | null
  showSplash: boolean
  isAdmin: boolean
  activeTag: string | null
}

type Action =
  | { type: 'SET_ARTICLES'; payload: Article[] }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_SEARCH'; payload: string }
  | { type: 'SET_ACTIVE_SEARCH'; payload: string }
  | { type: 'LOAD_MORE' }
  | { type: 'SET_MOUNTED' }
  | { type: 'SET_TIME'; payload: Date }
  | { type: 'SET_WEATHER'; payload: { temp: number; code: number } | null }
  | { type: 'HIDE_SPLASH' }
  | { type: 'SET_ADMIN'; payload: boolean }
  | { type: 'SET_TAG'; payload: string | null }
  | { type: 'DELETE_ARTICLE'; payload: string }

const PAGE_SIZE = 24

// --- Components ---

function TopInfoBar({ 
  mounted, 
  currentTime, 
  weather, 
  onToggleTheme, 
  resolvedTheme 
}: { 
  mounted: boolean, 
  currentTime: Date, 
  weather: any, 
  onToggleTheme: () => void,
  resolvedTheme: string | undefined
}) {
  function getWeatherIcon(code: number) {
    if (code === 0) return <Sun size={14} className="text-yellow-500 shrink-0" aria-hidden="true" />
    if (code >= 1 && code <= 3) return <Cloud size={14} className="text-blue-400 shrink-0" aria-hidden="true" />
    if (code >= 45 && code <= 48) return <Cloud size={14} className="text-gray-400 shrink-0" aria-hidden="true" />
    if (code >= 51 && code <= 67) return <CloudRain size={14} className="text-blue-500 shrink-0" aria-hidden="true" />
    if (code >= 71 && code <= 77) return <CloudSnow size={14} className="text-blue-200 shrink-0" aria-hidden="true" />
    if (code >= 80 && code <= 82) return <CloudRain size={14} className="text-blue-600 shrink-0" aria-hidden="true" />
    if (code >= 85 && code <= 86) return <CloudSnow size={14} className="text-blue-300 shrink-0" aria-hidden="true" />
    return <Sun size={14} className="text-yellow-500 shrink-0" aria-hidden="true" />
  }

  return (
    <div className="w-full bg-gray-100/50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-800 py-2">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center gap-2 text-[10px] sm:text-sm font-medium text-gray-600 dark:text-gray-400">
        <div className="flex items-center gap-1.5 capitalize">
          <Calendar size={14} className="text-blue-600 shrink-0" aria-hidden="true" />
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
            <Clock size={14} className="text-blue-600 shrink-0" aria-hidden="true" />
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
            <div className="flex items-center gap-2">
              <Link
                href="/municipales-2026"
                className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-600 hover:bg-blue-700 text-white transition-colors shadow-sm text-[10px] sm:text-xs font-bold"
              >
                <Vote size={12} />
                <span>Municipales 2026</span>
              </Link>
              
              <button
                onClick={onToggleTheme}
                className="flex items-center justify-center p-1.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm"
                aria-label={resolvedTheme === 'dark' ? "Passer au mode clair" : "Passer au mode sombre"}
              >
                {resolvedTheme === 'dark' ? <Sun size={14} className="text-yellow-500" /> : <Moon size={14} className="text-blue-600" />}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function PageHeader({ 
  allTags, 
  activeTag, 
  onTagSelect 
}: { 
  allTags: NewsTag[], 
  activeTag: string | null, 
  onTagSelect: (id: string | null) => void 
}) {
  return (
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
                <nav className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1" aria-label="Filtrer par catégories">
                  <button
                    onClick={() => onTagSelect(null)}
                    className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${
                      activeTag === null
                        ? 'bg-blue-600 text-white border-blue-600 shadow'
                        : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-blue-400 hover:text-blue-600'
                    }`}
                    aria-pressed={activeTag === null}
                  >
                    Tous
                  </button>
                  {allTags.map(tag => (
                    <button
                      key={tag.id}
                      onClick={() => onTagSelect(tag.id)}
                      className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${
                        activeTag === tag.id ? 'shadow' : 'hover:border-opacity-80'
                      }`}
                      aria-pressed={activeTag === tag.id}
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
                </nav>
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
  )
}

// --- Main Page ---

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_ARTICLES': return { ...state, allArticles: action.payload }
    case 'SET_ERROR': return { ...state, error: action.payload }
    case 'SET_LOADING': return { ...state, loading: action.payload }
    case 'SET_SEARCH': return { ...state, search: action.payload }
    case 'SET_ACTIVE_SEARCH': return { ...state, activeSearch: action.payload, displayCount: PAGE_SIZE }
    case 'LOAD_MORE': return { ...state, displayCount: state.displayCount + PAGE_SIZE }
    case 'SET_MOUNTED': return { ...state, mounted: true }
    case 'SET_TIME': return { ...state, currentTime: action.payload }
    case 'SET_WEATHER': return { ...state, weather: action.payload }
    case 'HIDE_SPLASH': return { ...state, showSplash: false }
    case 'SET_ADMIN': return { ...state, isAdmin: action.payload }
    case 'SET_TAG': return { ...state, activeTag: action.payload, displayCount: PAGE_SIZE }
    case 'DELETE_ARTICLE': return { ...state, allArticles: state.allArticles.filter(a => a.id !== action.payload) }
    default: return state
  }
}

export default function HomeClient({ initialArticles }: { initialArticles: Article[], initialCount: number }) {
  const [state, dispatch] = useReducer(reducer, {
    allArticles: initialArticles,
    error: null,
    loading: false,
    search: '',
    activeSearch: '',
    displayCount: PAGE_SIZE,
    mounted: false,
    currentTime: new Date(),
    weather: null,
    showSplash: true,
    isAdmin: false,
    activeTag: null,
  })

  const { resolvedTheme, setTheme } = useTheme()
  const searchInputId = useId()

  const loadArticles = useCallback(async (query: string) => {
    dispatch({ type: 'SET_LOADING', payload: true })
    let result
    try {
      result = await getLatestArticles(query)
    } catch (err: any) {
      dispatch({ type: 'SET_ERROR', payload: err.message || 'Une erreur est survenue' })
      dispatch({ type: 'SET_LOADING', payload: false })
      return
    }

    const { articles, error: fetchError } = result
    if (fetchError) {
      dispatch({ type: 'SET_ERROR', payload: fetchError })
    } else {
      dispatch({ type: 'SET_ARTICLES', payload: articles || [] })
      dispatch({ type: 'SET_ERROR', payload: null })
    }
    dispatch({ type: 'SET_LOADING', payload: false })
  }, [])

  const fetchWeather = useCallback(async () => {
    try {
      const res = await fetch('https://api.open-meteo.com/v1/forecast?latitude=47.7508&longitude=7.3359&current_weather=true')
      if (res.ok) {
        const data = await res.json()
        if (data.current_weather) {
          dispatch({ type: 'SET_WEATHER', payload: {
            temp: data.current_weather.temperature,
            code: data.current_weather.weathercode
          }})
        }
      }
    } catch (e) {
      console.error("Erreur météo", e)
    }
  }, [])

  useEffect(() => {
    const auth = document.cookie.split('; ').find(row => row.startsWith('admin_auth='))?.split('=')[1]
    dispatch({ type: 'SET_MOUNTED' })
    if (auth === 'true') dispatch({ type: 'SET_ADMIN', payload: true })

    const timer = setInterval(() => dispatch({ type: 'SET_TIME', payload: new Date() }), 1000)
    fetchWeather()
    const weatherTimer = setInterval(fetchWeather, 30 * 60 * 1000)

    return () => {
      clearInterval(timer)
      clearInterval(weatherTimer)
    }
  }, [fetchWeather])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      dispatch({ type: 'SET_ACTIVE_SEARCH', payload: state.search })
      loadArticles(state.search)
    }
  }

  const allTags = useMemo(() => {
    const tagMap = new Map<string, NewsTag>()
    state.allArticles.forEach(article => {
      article.ArticleGoogleTag?.forEach(({ NewsTag: tag }) => {
        if (!tagMap.has(tag.id)) tagMap.set(tag.id, tag)
      })
    })
    return Array.from(tagMap.values()).sort((a, b) => a.name.localeCompare(b.name))
  }, [state.allArticles])

  const tagFilteredArticles = useMemo(() => {
    if (!state.activeTag) return state.allArticles
    return state.allArticles.filter(article =>
      article.ArticleGoogleTag?.some(({ NewsTag: tag }) => tag.id === state.activeTag)
    )
  }, [state.allArticles, state.activeTag])

  const displayedArticles = useMemo(() => tagFilteredArticles.slice(0, state.displayCount), [tagFilteredArticles, state.displayCount])
  const filteredCount = tagFilteredArticles.length

  return (
    <>
      {state.showSplash && <SplashScreen onFinish={() => dispatch({ type: 'HIDE_SPLASH' })} />}
      <main className="min-h-screen transition-colors">
        <TopInfoBar 
          mounted={state.mounted} 
          currentTime={state.currentTime} 
          weather={state.weather} 
          resolvedTheme={resolvedTheme}
          onToggleTheme={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
        />

        <PageHeader 
          allTags={allTags} 
          activeTag={state.activeTag} 
          onTagSelect={(id) => dispatch({ type: 'SET_TAG', payload: id })} 
        />

        <div className="max-w-7xl mx-auto py-6 sm:py-8 px-4 sm:px-6 lg:px-8">
          <div className="mb-8">
            <div className="relative">
              <label htmlFor={searchInputId} className="sr-only">Rechercher une actualité</label>
              <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" aria-hidden="true" />
              <input
                id={searchInputId}
                type="text"
                value={state.search}
                placeholder="Rechercher une actualité..."
                onChange={(e) => dispatch({ type: 'SET_SEARCH', payload: e.target.value })}
                onKeyDown={handleKeyDown}
                className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all shadow-sm"
              />
            </div>
          </div>

          {state.activeSearch && !state.loading && (
            <div className="mb-8 flex items-center justify-between bg-blue-50/50 dark:bg-blue-900/10 p-4 rounded-xl border border-blue-100 dark:border-blue-900/30">
              <p className="text-blue-800 dark:text-blue-300 font-medium">
                {filteredCount > 0 ? `${filteredCount} article${filteredCount > 1 ? 's' : ''} trouvé${filteredCount > 1 ? 's' : ''} pour "${state.activeSearch}"` : `Aucun article trouvé pour "${state.activeSearch}"`}
              </p>
              <button onClick={() => { dispatch({ type: 'SET_SEARCH', payload: '' }); dispatch({ type: 'SET_ACTIVE_SEARCH', payload: '' }); loadArticles('') }} className="text-blue-600 dark:text-blue-400 text-sm font-bold hover:underline">
                Effacer la recherche
              </button>
            </div>
          )}

          {state.error && (
            <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 mb-8 rounded-r" role="alert">
              <div className="flex">
                <AlertTriangle className="h-5 w-5 text-red-400" aria-hidden="true" />
                <div className="ml-3"><p className="text-sm text-red-700 dark:text-red-400">Erreur : {state.error}</p></div>
              </div>
            </div>
          )}

          {state.loading ? (
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
                  <ArticleCard key={article.id} article={article} isAdmin={state.isAdmin} onDelete={(id) => dispatch({ type: 'DELETE_ARTICLE', payload: id })} />
                ))}
              </div>
              {state.displayCount < filteredCount && (
                <div className="text-center py-8">
                  <button onClick={() => dispatch({ type: 'LOAD_MORE' })} className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors">Charger plus d'articles</button>
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
