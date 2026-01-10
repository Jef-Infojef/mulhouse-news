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
    if (s.includes('l\'alsace')) return 'bg-red-100 text-red-800'
    if (s.includes('dna')) return 'bg-blue-100 text-blue-800'
    if (s.includes('mulhouse')) return 'bg-purple-100 text-purple-800'
    return 'bg-gray-100 text-gray-800'
  }

  return (
    <Link 
      href={article.link} 
      target="_blank" 
      rel="noopener noreferrer"
      className="group flex flex-col h-full bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition-all duration-300 hover:-translate-y-1"
    >
      <div className="relative h-48 w-full overflow-hidden bg-gray-100">
        {article.imageUrl ? (
          <Image
            src={article.imageUrl}
            alt={article.title}
            fill
            className="object-cover transition-transform duration-500 group-hover:scale-105"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            <Newspaper size={48} />
          </div>
        )}
        <div className="absolute top-3 right-3">
          <span className={`px-3 py-1 text-xs font-semibold rounded-full ${getSourceColor(article.source)}`}>
            {article.source || 'Autre'}
          </span>
        </div>
      </div>

      <div className="flex flex-col flex-grow p-5">
        <h2 className="text-lg font-bold text-gray-900 line-clamp-2 mb-2 group-hover:text-blue-600 transition-colors">
          {article.title}
        </h2>
        {article.description && (
          <p className="text-sm text-gray-600 line-clamp-4 mb-3">
            {article.description}
          </p>
        )}

        <div className="mt-auto flex items-center justify-between text-sm text-gray-500 pt-4 border-t border-gray-100">
          <div className="flex items-center gap-1.5">
            <Calendar size={14} />
            <time dateTime={article.publishedAt.toISOString()}>
              {formatDistanceToNow(new Date(article.publishedAt), { addSuffix: true, locale: fr })}
            </time>
          </div>
          <ExternalLink size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>
    </Link>
  )
}
