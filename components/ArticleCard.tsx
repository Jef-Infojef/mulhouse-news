'use client'

import Link from 'next/link'
import { useState, useMemo, useEffect } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import { ExternalLink, Calendar, Trash2, Info, X } from 'lucide-react'
import { deleteArticle } from '@/app/actions'
import { createPortal } from 'react-dom'

interface NewsTag {
  id: string
  name: string
  slug: string
  color: string | null
}

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
    content: string | null
    publishedAt: Date
    scrapedAt: Date
    createdAt: Date
    updatedAt: Date
    ArticleGoogleTag: { NewsTag: NewsTag }[]
  }
  isAdmin?: boolean
  onDelete?: (id: string) => void
}

export function ArticleCard({ article, isAdmin, onDelete }: ArticleProps) {
  const [imgUrl, setImgUrl] = useState<string | null>(article.imageUrl || article.r2Url || article.localImage)
  const [isUsingFallback, setIsUsingFallback] = useState(false)
  const [isUsingFavicon, setIsUsingFavicon] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDetails, setShowDetails] = useState(false)

  const getDomain = (url: string) => {
    try {
      return new URL(url).hostname
    } catch {
      return 'google.com'
    }
  }

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (!window.confirm('Voulez-vous vraiment supprimer cet article ?')) return

    setIsDeleting(true)
    try {
      const res = await deleteArticle(article.id)
      if (res.success) {
        onDelete?.(article.id)
      } else {
        alert('Erreur lors de la suppression : ' + res.error)
        setIsDeleting(false)
      }
    } catch (err) {
      alert('Erreur technique')
      setIsDeleting(false)
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
    <div
      onClick={() => window.open(article.link, '_blank', 'noopener,noreferrer')}
      className="group flex flex-col h-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl overflow-hidden hover:shadow-lg dark:hover:shadow-xl dark:hover:shadow-blue-900/50 transition-all duration-300 hover:-translate-y-1 cursor-pointer"
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
        {isAdmin && (
          <div className="absolute top-3 left-3 flex flex-col gap-2 z-10">
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="p-2 bg-white/90 hover:bg-red-500 text-red-600 hover:text-white rounded-full shadow-lg transition-all duration-200 disabled:opacity-50"
              title="Supprimer l'article"
            >
              <Trash2 size={16} className={isDeleting ? 'animate-pulse' : ''} />
            </button>
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); setShowDetails(true); }}
              className="p-2 bg-white/90 hover:bg-blue-500 text-blue-600 hover:text-white rounded-full shadow-lg transition-all duration-200"
              title="Voir les détails BDD"
            >
              <Info size={16} />
            </button>
          </div>
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

        {article.ArticleGoogleTag && article.ArticleGoogleTag.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {article.ArticleGoogleTag.map(({ NewsTag: tag }) => (
              <span
                key={tag.id}
                onClick={(e) => e.stopPropagation()}
                className={
                  tag.color
                    ? 'px-2 py-0.5 text-[10px] font-semibold rounded-full border'
                    : 'px-2 py-0.5 text-[10px] font-semibold rounded-full border bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-400 border-gray-200 dark:border-slate-700'
                }
                style={
                  tag.color
                    ? { backgroundColor: tag.color + '22', color: tag.color, borderColor: tag.color + '55' }
                    : undefined
                }
              >
                #{tag.name}
              </span>
            ))}
          </div>
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
                  
                  {showDetails && typeof document !== 'undefined' && createPortal(
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 overflow-hidden" onClick={(e) => { e.stopPropagation(); setShowDetails(false); }}>
                      <div className="bg-white dark:bg-slate-900 w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col rounded-2xl shadow-2xl border border-gray-200 dark:border-slate-800" onClick={e => e.stopPropagation()}>
                        <div className="p-4 border-b border-gray-100 dark:border-slate-800 flex justify-between items-center shrink-0">
                          <h3 className="font-bold text-lg">Détails de l'article (BDD)</h3>
                          <button onClick={() => setShowDetails(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-full">
                            <X size={20} />
                          </button>
                        </div>
                        
                        <div className="p-6 space-y-6 overflow-y-auto flex-1 custom-scrollbar">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                            {[
                              { label: 'ID', value: article.id },
                              { label: 'Source', value: article.source },
                              { label: 'Publié le', value: new Date(article.publishedAt).toLocaleString('fr-FR') },
                              { label: 'Scrapé le', value: new Date(article.scrapedAt).toLocaleString('fr-FR') },
                              { label: 'Créé le', value: new Date(article.createdAt).toLocaleString('fr-FR') },
                              { label: 'Mis à jour le', value: new Date(article.updatedAt).toLocaleString('fr-FR') },
                            ].map(field => (
                              <div key={field.label} className="p-3 bg-gray-50 dark:bg-slate-800/50 rounded-lg border border-gray-100 dark:border-slate-800">
                                <span className="text-gray-400 block mb-1 uppercase tracking-wider text-[10px]">{field.label}</span>
                                <span className="break-all font-semibold text-gray-700 dark:text-slate-300">{field.value || 'N/A'}</span>
                              </div>
                            ))}
                          </div>
            
                          <div className="space-y-4">
                            {[
                              { label: 'Titre', value: article.title },
                              { label: 'Lien Original', value: article.link, isLink: true },
                              { label: 'Image URL', value: article.imageUrl, isLink: true },
                              { label: 'R2 URL', value: article.r2Url, isLink: true },
                              { label: 'Local Image', value: article.localImage },
                            ].map(field => (
                              <div key={field.label} className="text-xs font-mono p-3 bg-gray-50 dark:bg-slate-800/50 rounded-lg border border-gray-100 dark:border-slate-800">
                                <span className="text-gray-400 block mb-1 uppercase tracking-wider text-[10px]">{field.label}</span>
                                {field.isLink && field.value ? (
                                  <a href={field.value} target="_blank" className="text-blue-500 hover:underline break-all">{field.value}</a>
                                ) : (
                                  <span className="break-all text-gray-700 dark:text-slate-300">{field.value || 'N/A'}</span>
                                )}
                              </div>
                            ))}
                          </div>
            
                          <div className="space-y-4">
                            <div className="text-xs font-mono p-3 bg-gray-50 dark:bg-slate-800/50 rounded-lg border border-gray-100 dark:border-slate-800">
                              <span className="text-gray-400 block mb-1 uppercase tracking-wider text-[10px]">Description (Résumé)</span>
                              <p className="text-gray-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">{article.description || 'N/A'}</p>
                            </div>
                            
                            <div className="text-xs font-mono p-3 bg-gray-50 dark:bg-slate-800/50 rounded-lg border border-gray-100 dark:border-slate-800">
                              <span className="text-gray-400 block mb-1 uppercase tracking-wider text-[10px]">Contenu Complet (Raw)</span>
                              <div className="max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                                <p className="text-gray-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed text-[11px]">
                                  {article.content || 'AUCUN CONTENU RÉCUPÉRÉ'}
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>,
                    document.body
                  )}
            
                </div>
              )
            }
            