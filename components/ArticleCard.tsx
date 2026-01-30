'use client'

import Link from 'next/link'
import { useState, useMemo, useEffect } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import { ExternalLink, Calendar } from 'lucide-react'

interface ArticleProps {
  article: {
    id: string
    title: string
    link: string
    imageUrl: string | null
    localImage: string | null
    r2Url: string | null
    source: string | null
    description: string | null
    publishedAt: Date
  }
}

export function ArticleCard({ article }: ArticleProps) {
  const [imgUrl, setImgUrl] = useState<string | null>(article.imageUrl || article.r2Url || article.localImage)
  const [isUsingFallback, setIsUsingFallback] = useState(false)
  const [isUsingFavicon, setIsUsingFavicon] = useState(false)

  const getDomain = (url: string) => {
    try {
      return new URL(url).hostname
    } catch {
      return 'google.com'
    }
  }

  const faviconUrl = useMemo(() => {
    return 'https://www.google.com/s2/favicons?domain=' + getDomain(article.link) + '&sz=256'
  }, [article.link])

  useEffect(() => {
    setImgUrl(article.imageUrl || article.r2Url || article.localImage || faviconUrl)
    setIsUsingFallback(!article.imageUrl && (!!article.r2Url || !!article.localImage))
    setIsUsingFavicon(!article.imageUrl && !article.r2Url && !article.localImage)
  }, [article.id, article.imageUrl, article.r2Url, article.localImage, faviconUrl])

  const handleImageError = () => {
    if (!isUsingFallback && !isUsingFavicon && (article.r2Url || article.localImage)) {
      setImgUrl(article.r2Url || article.localImage)
      setIsUsingFallback(true)
      return
    }
    if (!isUsingFavicon) {
      setImgUrl(faviconUrl)
      setIsUsingFavicon(true)
      return
    }
  }

  const getSourceColor = (source: string | null) => {
    const s = source?.toLowerCase() || ''
    if (s.includes("l'alsace")) return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
    if (s.includes('dna')) return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200'
    if (s.includes('mplus') || s.includes('mulhouse')) return 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-200'
    if (s.includes('france bleu')) return 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
    if (s.includes('france 3')) return 'bg-blue-600 text-white'
    return 'bg-gray-100 dark:bg-slate-800 text-gray-800 dark:text-gray-200'
  }

  return (
    <Link
      href={article.link}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex flex-col h-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl overflow-hidden hover:shadow-lg dark:hover:shadow-xl dark:hover:shadow-blue-900/50 transition-all duration-300 hover:-translate-y-1"
    >
      <div className="relative h-48 w-full overflow-hidden bg-gray-100 dark:bg-slate-800">
        {imgUrl && (
          <img
            src={imgUrl}
            alt={article.title}
            className={'w-full h-full transition-transform duration-500 group-hover:scale-105 ' + (isUsingFavicon ? 'object-contain p-12' : 'object-cover')}
            onError={handleImageError}
          />
        )}
        <div className="absolute top-3 right-3">
          <span className={'px-3 py-1 text-[10px] font-bold uppercase rounded-full shadow-sm ' + getSourceColor(article.source)}>
            {article.source || 'Autre'}
          </span>
        </div>
      </div>

      <div className="flex flex-col flex-grow p-5" title={article.description || ''}>
        <h2 className="text-lg font-bold text-gray-900 dark:text-slate-50 line-clamp-3 mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-tight">
          {article.title}
        </h2>

        {article.description && (
          <p className="text-sm text-gray-600 dark:text-slate-400 line-clamp-3 mb-3 leading-relaxed">
            {article.description}
          </p>
        )}

        <div className="mt-auto flex items-center justify-between text-xs text-gray-500 dark:text-slate-500 pt-4 border-t border-gray-100 dark:border-slate-800">
          <div className="flex items-center gap-1.5">
            <Calendar size={14} className="text-blue-500" />
            <span>
              {article.publishedAt ? formatDistanceToNow(new Date(article.publishedAt), { addSuffix: true, locale: fr })
                .replace('environ ', '')
                .replace('minutes', 'mn')
                .replace('minute', 'mn') : ''}
            </span>
          </div>
          <ExternalLink size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>
    </Link>
  )
}