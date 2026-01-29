'use client'

import { useState, useEffect } from 'react'
import { getScrapingLogs } from '@/app/actions'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { 
  ShieldCheck, 
  ShieldAlert, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  XCircle, 
  ChevronDown, 
  ChevronUp,
  Link as LinkIcon,
  Search,
  Lock
} from 'lucide-react'

export default function AdminLogsPage() {
  const [password, setPassword] = useState('')
  const [isAuthenticated, setIsConnected] = useState(false)
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedLog, setExpandedLog] = useState<string | null>(null)

  useEffect(() => {
    const auth = document.cookie.split('; ').find(row => row.startsWith('admin_auth='))?.split('=')[1]
    if (auth === 'true') {
      setIsConnected(true)
      fetchLogs()
    }
  }, [])

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    if (password === '1122') {
      document.cookie = "admin_auth=true; path=/; max-age=" + (30 * 24 * 60 * 60) // 30 jours
      setIsConnected(true)
      fetchLogs()
    } else {
      alert('Mot de passe incorrect')
    }
  }

  const fetchLogs = async () => {
    setLoading(true)
    const { logs, error } = await getScrapingLogs()
    if (error) setError(error)
    else setLogs(logs)
    setLoading(false)
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-700">
          <div className="flex justify-center mb-6">
            <div className="bg-blue-500/10 p-4 rounded-full">
              <Lock className="w-12 h-12 text-blue-500" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-center text-white mb-8">Administration Mulhouse News</h1>
          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">Mot de passe d'accès</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg py-3 px-4 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="••••"
                autoFocus
              />
            </div>
            <button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition-colors shadow-lg shadow-blue-900/20"
            >
              Se connecter
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <header className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-white flex items-center gap-3">
              <Search className="text-blue-500" /> Journaux de Scraping
            </h1>
            <p className="text-gray-400 mt-1">Suivi en temps réel de l'enrichissement des articles</p>
          </div>
          <button 
            onClick={fetchLogs}
            className="bg-gray-800 hover:bg-gray-700 text-sm font-medium py-2 px-4 rounded-lg border border-gray-700 transition-colors"
          >
            Actualiser
          </button>
        </header>

        {error && (
          <div className="bg-red-900/20 border border-red-500 text-red-200 p-4 rounded-xl mb-6 flex items-center gap-3">
            <AlertCircle /> {error}
          </div>
        )}

        <div className="space-y-4">
          {loading ? (
            <div className="text-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-gray-400">Chargement des rapports...</p>
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-20 bg-gray-800 rounded-2xl border border-gray-700">
              <p className="text-gray-400 text-lg">Aucun log trouvé en base de données.</p>
            </div>
          ) : (
            logs.map((log) => (
              <div 
                key={log.id} 
                className={`bg-gray-800 rounded-2xl border transition-all ${
                  expandedLog === log.id ? 'border-blue-500/50 ring-1 ring-blue-500/20' : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <div 
                  className="p-4 md:p-6 cursor-pointer flex flex-wrap items-center justify-between gap-4"
                  onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
                >
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-xl ${
                      log.status === 'SUCCESS' ? 'bg-green-500/10 text-green-500' :
                      log.status === 'SESSION_LOST' ? 'bg-orange-500/10 text-orange-500' :
                      'bg-red-500/10 text-red-500'
                    }`}>
                      {log.status === 'SUCCESS' ? <CheckCircle2 className="w-6 h-6" /> :
                       log.status === 'SESSION_LOST' ? <ShieldAlert className="w-6 h-6" /> :
                       <XCircle className="w-6 h-6" />}
                    </div>
                    <div>
                      <div className="font-bold text-white text-lg">
                        {new Intl.DateTimeFormat('fr-FR', {
                          day: '2-digit',
                          month: 'long',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                          timeZone: 'Europe/Paris'
                        }).format(new Date(log.startedAt))}
                      </div>
                      <div className="flex items-center gap-3 text-sm text-gray-400 mt-1">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" /> 
                          {log.finishedAt ? `${Math.round((new Date(log.finishedAt).getTime() - new Date(log.startedAt).getTime()) / 1000)}s` : 'En cours'}
                        </span>
                        <span className="flex items-center gap-1">
                          {log.isConnected ? (
                            <><ShieldCheck className="w-3 h-3 text-green-500" /> <span className="text-green-500">Connecté</span></>
                          ) : (
                            <><ShieldAlert className="w-3 h-3 text-red-500" /> <span className="text-red-500">Non connecté</span></>
                          )}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className="text-2xl font-black text-white">{log.successCount}</div>
                      <div className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">Réussis</div>
                    </div>
                    <div className="text-right">
                      <div className={`text-2xl font-black ${log.errorCount > 0 ? 'text-red-400' : 'text-gray-600'}`}>{log.errorCount}</div>
                      <div className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">Échecs</div>
                    </div>
                    {expandedLog === log.id ? <ChevronUp className="text-gray-500" /> : <ChevronDown className="text-gray-500" />}
                  </div>
                </div>

                {expandedLog === log.id && (
                  <div className="border-t border-gray-700 p-6 bg-gray-900/50 rounded-b-2xl">
                    {!log.isConnected && log.status !== 'TEST_LOG' && (
                      <div className="bg-orange-500/10 border border-orange-500/30 text-orange-400 p-4 rounded-xl mb-6 flex items-center gap-3">
                        <ShieldAlert className="shrink-0" />
                        <div className="text-sm">
                          <strong>Mode limité (EBRA) :</strong> La session abonné est expirée ou invalide. Seuls les chapôs et métadonnées sont récupérés pour L'Alsace, DNA et Est Républicain pour éviter les contenus tronqués.
                        </div>
                      </div>
                    )}

                    {log.errorMessage && (
                      <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl mb-6 font-mono text-sm">
                        <strong>ERREUR CRITIQUE :</strong> {log.errorMessage}
                      </div>
                    )}
                    
                    {(() => {
                      const detailsObj = log.details ? (typeof log.details === 'string' ? JSON.parse(log.details) : log.details) : null;
                      const isDiscovery = detailsObj && !Array.isArray(detailsObj) && detailsObj.total_rss_items !== undefined;
                      const articles = isDiscovery ? detailsObj.inserted_articles : (Array.isArray(detailsObj) ? detailsObj : []);

                      return (
                        <>
                          {isDiscovery && (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                              <div className="bg-gray-800 p-3 rounded-xl border border-gray-700">
                                <div className="text-[10px] uppercase text-gray-500 font-bold mb-1">Items RSS</div>
                                <div className="text-xl font-bold text-white">{detailsObj.total_rss_items}</div>
                              </div>
                              <div className="bg-gray-800 p-3 rounded-xl border border-gray-700">
                                <div className="text-[10px] uppercase text-gray-500 font-bold mb-1">Doublons Titre</div>
                                <div className="text-xl font-bold text-gray-400">{detailsObj.duplicates_title}</div>
                              </div>
                              <div className="bg-gray-800 p-3 rounded-xl border border-gray-700">
                                <div className="text-[10px] uppercase text-gray-500 font-bold mb-1">Doublons Lien</div>
                                <div className="text-xl font-bold text-gray-400">{detailsObj.duplicates_link}</div>
                              </div>
                              <div className="bg-gray-800 p-3 rounded-xl border border-gray-700">
                                <div className="text-[10px] uppercase text-gray-500 font-bold mb-1 text-red-400">Erreurs Google</div>
                                <div className={`text-xl font-bold ${detailsObj.google_decode_errors > 0 ? 'text-red-400' : 'text-gray-400'}`}>
                                  {detailsObj.google_decode_errors}
                                </div>
                              </div>
                            </div>
                          )}

                          <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
                            {isDiscovery ? `Articles découverts (${articles.length})` : `Détails du traitement (${articles.length})`}
                          </h3>
                          
                          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                            {articles.map((detail: any, idx: number) => (
                              <div key={idx} className="flex items-start justify-between gap-4 p-3 bg-gray-800/50 rounded-lg border border-gray-700/50 group">
                                <div className="flex-1 min-w-0">
                                  <div className="text-white font-medium truncate">{detail.title}</div>
                                  <div className="flex items-center gap-2 mt-1">
                                    <a 
                                      href={detail.link} 
                                      target="_blank" 
                                      className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 truncate max-w-md"
                                    >
                                      <LinkIcon className="w-3 h-3" /> {detail.link}
                                    </a>
                                  </div>
                                </div>
                                <div className="flex items-center gap-3">
                                  {detail.chars > 0 && <span className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded font-mono">{detail.chars} chars</span>}
                                  <span className={`text-[10px] font-bold px-2 py-1 rounded uppercase ${
                                    (detail.status === 'SUCCESS' || isDiscovery) ? 'bg-green-500/20 text-green-400' :
                                    detail.status === 'SESSION_LOST' ? 'bg-orange-500/10 text-orange-400' :
                                    detail.status === 'SKIPPED' ? 'bg-gray-700 text-gray-400' :
                                    'bg-red-500/20 text-red-400'
                                  }`}>
                                    {isDiscovery ? 'NOUVEAU' : (detail.status === 'SKIPPED' ? 'IGNORÉ' : detail.status)}
                                  </span>
                                </div>
                              </div>
                            ))}
                            {articles.length === 0 && (
                              <div className="text-center py-4 text-gray-500 italic">
                                Aucun article traité dans ce log.
                              </div>
                            )}
                          </div>
                        </>
                      )
                    })()}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #374151; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #4b5563; }
      `}</style>
    </div>
  )
}
