import Image from 'next/image'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import { ExternalLink, Calendar, Newspaper } from 'lucide-react'

interface ArticleProps {
  article: {
    id: string
    title: string
    link: string
    imageUrl: string | null
    source: string | null
    description: string | null
    publishedAt: Date
  }
}

export function ArticleCard({ article }: ArticleProps) {
  // Fonction pour obtenir une couleur de badge selon la source
  const getSourceColor = (source: string | null) => {
    const s = source?.toLowerCase() || ''
    if (s.includes('l\'alsace')) return 'bg-red-100 dark:bg-red-950/60 text-red-900 dark:text-red-100'
    if (s.includes('dna')) return 'bg-blue-100 dark:bg-blue-950/60 text-blue-900 dark:text-blue-100'
    if (s.includes('mulhouse')) return 'bg-purple-100 dark:bg-purple-950/60 text-purple-900 dark:text-purple-100'
    return 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
  }

  // Extraction du domaine pour le favicon de secours
  const getDomain = (url: string) => {
    try {
      return new URL(url).hostname
    } catch {
      return ''
    }
  }

  const fallbackImageUrl = `https://www.google.com/s2/favicons?domain=${getDomain(article.link)}&sz=256`

  return (
    <Link
      href={article.link}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex flex-col h-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden hover:shadow-lg dark:hover:shadow-xl dark:hover:shadow-blue-900/50 transition-all duration-300 hover:-translate-y-1"
    >
      <div className="relative h-48 w-full overflow-hidden bg-gray-100 dark:bg-slate-700">
        <Image
          src={article.imageUrl || fallbackImageUrl}
          alt={article.title}
          fill
          className="object-cover transition-transform duration-500 group-hover:scale-105"
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          unoptimized={!article.imageUrl} // Évite les problèmes d'optimisation sur l'URL externe du favicon
        />
        <div className="absolute top-3 right-3">
          <span className={`px-3 py-1 text-xs font-semibold rounded-full ${getSourceColor(article.source)}`}>
            {article.source || 'Autre'}
          </span>
        </div>
      </div>

      <div className="flex flex-col flex-grow p-5">
        <h2 className="text-lg font-bold text-gray-900 dark:text-slate-50 line-clamp-4 mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-300 transition-colors">
          {article.title}
        </h2>
        {article.description && (
          <p className="text-sm text-gray-600 dark:text-slate-300 line-clamp-3 mb-3">
            {article.description}
          </p>
        )}

        <div className="mt-auto flex items-center justify-between text-sm text-gray-500 dark:text-slate-400 pt-4 border-t border-gray-100 dark:border-slate-700">
          <div className="flex items-center gap-1.5">
            <Calendar size={14} />
            <time dateTime={article.publishedAt.toISOString()}>
              {formatDistanceToNow(new Date(article.publishedAt), { addSuffix: true, locale: fr })
                .replace('environ ', '')
                .replace('minutes', 'mn')
                .replace('minute', 'mn')}
            </time>
          </div>
          <ExternalLink size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>
    </Link>
  )
}
