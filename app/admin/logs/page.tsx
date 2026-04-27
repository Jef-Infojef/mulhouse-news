'use client'

import { useReducer, useEffect, useCallback, useId, useState } from 'react'
import Link from 'next/link'
import { getScrapingLogs, getAppConfig, updateAppConfig, testEbraConnection, verifyAdminPassword, checkAdminAuth, revalidateSite } from '@/app/actions'
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
  Lock,
  Settings,
  Key,
  Save,
  X,
  Play,
  Activity,
  Eye,
  EyeOff,
  RefreshCw
} from 'lucide-react'

// --- Types ---

type State = {
  password: string
  isAuthenticated: boolean
  logs: any[]
  loading: boolean
  error: string | null
  expandedLog: string | null
  isConfigModalOpen: boolean
  ebraSession: string
  ebraPoool: string
  isSavingConfig: boolean
  isTestingConnection: boolean
  testResult: { success: boolean; message: string } | null
}

type Action =
  | { type: 'SET_PASSWORD'; payload: string }
  | { type: 'SET_AUTHENTICATED'; payload: boolean }
  | { type: 'SET_LOGS'; payload: any[] }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'TOGGLE_LOG'; payload: string | null }
  | { type: 'SET_CONFIG_MODAL'; payload: boolean }
  | { type: 'SET_CONFIG_DATA'; payload: { session: string; poool: string } }
  | { type: 'SET_EBRA_SESSION'; payload: string }
  | { type: 'SET_EBRA_POOOL'; payload: string }
  | { type: 'SET_SAVING_CONFIG'; payload: boolean }
  | { type: 'SET_TESTING_CONNECTION'; payload: boolean }
  | { type: 'SET_TEST_RESULT'; payload: { success: boolean; message: string } | null }

// --- Components ---

function LoginOverlay({ 
  password, 
  onPasswordChange, 
  onLogin, 
  inputId 
}: { 
  password: string, 
  onPasswordChange: (val: string) => void, 
  onLogin: (e: React.FormEvent) => void,
  inputId: string
}) {
  const [showPassword, setShowPassword] = useState(false)
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-700">
        <div className="flex justify-center mb-6">
          <div className="bg-blue-500/10 p-4 rounded-full">
            <Lock className="w-12 h-12 text-blue-500" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-center text-white mb-8">Administration Mulhouse News</h1>
        <form onSubmit={onLogin} className="space-y-6">
          <div>
            <label htmlFor={inputId} className="block text-sm font-medium text-gray-400 mb-2">Mot de passe d'accès</label>
            <div className="relative">
              <input
                id={inputId}
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => onPasswordChange(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg py-3 px-4 pr-12 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
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

function LogItem({ 
  log, 
  isExpanded, 
  onToggle 
}: { 
  log: any, 
  isExpanded: boolean, 
  onToggle: () => void 
}) {
  const detailsObj = log.details ? (typeof log.details === 'string' ? JSON.parse(log.details) : log.details) : null;
  const isDiscovery = detailsObj && !Array.isArray(detailsObj) && detailsObj.total_rss_items !== undefined;
  const articles = isDiscovery ? detailsObj.inserted_articles : (Array.isArray(detailsObj) ? detailsObj : []);

  return (
    <div 
      className={`bg-gray-800 rounded-2xl border transition-all ${
        isExpanded ? 'border-blue-500/50 ring-1 ring-blue-500/20' : 'border-gray-700 hover:border-gray-600'
      }`}
    >
      <div 
        role="button"
        tabIndex={0}
        className="p-4 md:p-6 cursor-pointer flex flex-wrap items-center justify-between gap-4 outline-none focus:ring-2 focus:ring-blue-500/50 rounded-2xl"
        onClick={onToggle}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onToggle()
          }
        }}
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
            <div className="flex items-center gap-2">
              <div className="font-bold text-white text-lg">
                {new Date(log.startedAt).toLocaleString('fr-FR', {
                  timeZone: 'Europe/Paris',
                  day: '2-digit',
                  month: 'long',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                isDiscovery ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
              }`}>
                {isDiscovery ? 'Découverte' : 'Enrichissement'}
              </span>
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-400 mt-1">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" /> 
                {log.finishedAt ? `${Math.round((new Date(log.finishedAt).getTime() - new Date(log.startedAt).getTime()) / 1000)}s` : 'En cours'}
              </span>
              <span className="flex items-center gap-1">
                {log.isConnected ? (
                  <><ShieldCheck className="w-3 h-3 text-green-500" /> <span className="text-green-500">Premium L'Alsace</span></>
                ) : (
                  <><ShieldAlert className="w-3 h-3 text-red-500" /> <span className="text-red-500">Non connecté (Premium)</span></>
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
          {isExpanded ? <ChevronUp className="text-gray-500" /> : <ChevronDown className="text-gray-500" />}
        </div>
      </div>

      {isExpanded && (
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
          
          <div className="mt-4">
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
              {articles.map((detail: any) => (
                <div key={detail.link} className="flex items-start justify-between gap-4 p-3 bg-gray-800/50 rounded-lg border border-gray-700/50 group">
                  <div className="flex-1 min-w-0">
                    <div className="text-white font-medium truncate">{detail.title}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <a
                        href={detail.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 break-all"
                        title={detail.link}
                      >
                        <LinkIcon className="w-3 h-3 shrink-0" /> {detail.link}
                      </a>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {detail.chars > 0 && <span className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded font-mono">{detail.chars} chars</span>}
                    <span className={`text-[10px] font-bold px-2 py-1 rounded uppercase ${
                      (detail.status === 'SUCCESS' || isDiscovery) ? 'bg-green-500/20 text-green-400' :
                      detail.status === 'FALLBACK' ? 'bg-blue-500/20 text-blue-400' :
                      detail.status === 'SESSION_LOST' ? 'bg-orange-500/10 text-orange-400' :
                      detail.status === 'SKIPPED' ? 'bg-gray-700 text-gray-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                      {isDiscovery ? 'INSÉRÉ' : (detail.status === 'SUCCESS' ? 'COMPLET' : (detail.status === 'FALLBACK' ? 'RÉSUMÉ' : (detail.status === 'SKIPPED' ? 'IGNORÉ' : detail.status)))}
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
          </div>
        </div>
      )}
    </div>
  )
}

function ConfigModal({ 
  state, 
  dispatch, 
  onSave, 
  onTest, 
  sessionInputId, 
  pooolInputId 
}: { 
  state: State, 
  dispatch: React.Dispatch<Action>,
  onSave: () => void,
  onTest: () => void,
  sessionInputId: string,
  pooolInputId: string
}) {
  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 border border-gray-700 rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        <div className="p-6 border-b border-gray-700 flex justify-between items-center">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Key className="text-blue-500" /> Configuration Session Premium
          </h2>
          <button onClick={() => dispatch({ type: 'SET_CONFIG_MODAL', payload: false })} className="text-gray-400 hover:text-white">
            <X className="w-6 h-6" />
          </button>
        </div>
        
        <div className="p-6 space-y-4">
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 text-sm text-blue-200 leading-relaxed">
            Configurez ici les deux paramètres clés de la session Premium. Vous les trouverez dans l'onglet <strong>Application &gt; Cookies</strong> de votre navigateur sur le site de l'Alsace.
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor={sessionInputId} className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-2">Session (.XCONNECT_SESSION)</label>
              <textarea 
                id={sessionInputId}
                value={state.ebraSession}
                onChange={(e) => dispatch({ type: 'SET_EBRA_SESSION', payload: e.target.value })}
                placeholder="2=42F64..."
                className="w-full bg-gray-900 border border-gray-700 rounded-xl p-3 text-gray-100 font-mono text-xs h-32 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all resize-none"
              />
            </div>
            <div>
              <label htmlFor={pooolInputId} className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-2">Paywall (_poool)</label>
              <textarea 
                id={pooolInputId}
                value={state.ebraPoool}
                onChange={(e) => dispatch({ type: 'SET_EBRA_POOOL', payload: e.target.value })}
                placeholder="9aab6ee3..."
                className="w-full bg-gray-900 border border-gray-700 rounded-xl p-3 text-gray-100 font-mono text-xs h-32 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all resize-none"
              />
            </div>
          </div>

          {state.testResult && (
            <div className={`p-4 rounded-xl text-sm flex items-center gap-3 animate-in fade-in slide-in-from-top-2 duration-200 ${
              state.testResult.success ? 'bg-green-500/10 border border-green-500/20 text-green-400' : 'bg-red-500/10 border border-red-500/20 text-red-400'
            }`}>
              {state.testResult.success ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
              {state.testResult.message}
            </div>
          )}
        </div>
        
        <div className="p-6 bg-gray-900/50 border-t border-gray-700 flex justify-between items-center">
          <button 
            onClick={onTest}
            disabled={state.isTestingConnection || !state.ebraSession}
            className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white text-sm font-bold py-2 px-4 rounded-lg transition-all flex items-center gap-2"
          >
            {state.isTestingConnection ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Tester la connexion
          </button>
          
          <div className="flex gap-3">
            <button 
              onClick={() => dispatch({ type: 'SET_CONFIG_MODAL', payload: false })}
              className="px-6 py-2 text-sm font-medium text-gray-400 hover:text-white transition-colors"
            >
              Annuler
            </button>
            <button 
              onClick={onSave}
              disabled={state.isSavingConfig}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold py-2 px-6 rounded-lg transition-all flex items-center gap-2"
            >
              {state.isSavingConfig ? <Clock className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Sauvegarder
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- Main Page ---

const initialState: State = {
  password: '',
  isAuthenticated: false,
  logs: [],
  loading: false,
  error: null,
  expandedLog: null,
  isConfigModalOpen: false,
  ebraSession: '',
  ebraPoool: '',
  isSavingConfig: false,
  isTestingConnection: false,
  testResult: null,
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_PASSWORD': return { ...state, password: action.payload }
    case 'SET_AUTHENTICATED': return { ...state, isAuthenticated: action.payload }
    case 'SET_LOGS': return { ...state, logs: action.payload }
    case 'SET_LOADING': return { ...state, loading: action.payload }
    case 'SET_ERROR': return { ...state, error: action.payload }
    case 'TOGGLE_LOG': return { ...state, expandedLog: state.expandedLog === action.payload ? null : action.payload }
    case 'SET_CONFIG_MODAL': return { ...state, isConfigModalOpen: action.payload, testResult: null }
    case 'SET_CONFIG_DATA': return { ...state, ebraSession: action.payload.session, ebraPoool: action.payload.poool }
    case 'SET_EBRA_SESSION': return { ...state, ebraSession: action.payload }
    case 'SET_EBRA_POOOL': return { ...state, ebraPoool: action.payload }
    case 'SET_SAVING_CONFIG': return { ...state, isSavingConfig: action.payload }
    case 'SET_TESTING_CONNECTION': return { ...state, isTestingConnection: action.payload }
    case 'SET_TEST_RESULT': return { ...state, testResult: action.payload }
    default: return state
  }
}

export default function AdminLogsPage() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const [isRevalidating, setIsRevalidating] = useState(false)
  const [revalidateMsg, setRevalidateMsg] = useState<string | null>(null)
  const passwordInputId = useId()
  const sessionInputId = useId()
  const pooolInputId = useId()

  const handleRevalidate = async () => {
    setIsRevalidating(true)
    setRevalidateMsg(null)
    const res = await revalidateSite()
    setRevalidateMsg(res.success ? 'Cache purgé ✓' : 'Erreur')
    setIsRevalidating(false)
    setTimeout(() => setRevalidateMsg(null), 3000)
  }

  const fetchLogs = useCallback(async () => {
    dispatch({ type: 'SET_LOADING', payload: true })
    const { logs, error } = await getScrapingLogs()
    if (error) dispatch({ type: 'SET_ERROR', payload: error })
    else dispatch({ type: 'SET_LOGS', payload: logs || [] })
    dispatch({ type: 'SET_LOADING', payload: false })
  }, [])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    const result = await verifyAdminPassword(state.password)
    if (result.success) {
      dispatch({ type: 'SET_AUTHENTICATED', payload: true })
      fetchLogs()
    } else {
      alert('Mot de passe incorrect')
    }
  }

  useEffect(() => {
    checkAdminAuth().then(authenticated => {
      if (authenticated) {
        dispatch({ type: 'SET_AUTHENTICATED', payload: true })
        fetchLogs()
      }
    })
  }, [fetchLogs])

  const openConfigModal = async () => {
    dispatch({ type: 'SET_CONFIG_MODAL', payload: true })
    const resSession = await getAppConfig('EBRA_SESSION')
    const resPoool = await getAppConfig('EBRA_POOOL')
    dispatch({ 
      type: 'SET_CONFIG_DATA', 
      payload: { 
        session: resSession.value || '', 
        poool: resPoool.value || '' 
      } 
    })
  }

  const handleSaveConfig = async () => {
    dispatch({ type: 'SET_SAVING_CONFIG', payload: true })
    const res1 = await updateAppConfig('EBRA_SESSION', state.ebraSession)
    const res2 = await updateAppConfig('EBRA_POOOL', state.ebraPoool)
    
    if (res1.success && res2.success) {
      dispatch({ type: 'SET_TEST_RESULT', payload: { success: true, message: 'Configuration sauvegardée ! Vous pouvez maintenant tester la connexion.' } })
    } else {
      alert('Erreur lors de la sauvegarde')
    }
    dispatch({ type: 'SET_SAVING_CONFIG', payload: false })
  }

  const handleTestConnection = async () => {
    if (!state.ebraSession) return alert('Veuillez saisir la session avant de tester')
    dispatch({ type: 'SET_TESTING_CONNECTION', payload: true })
    dispatch({ type: 'SET_TEST_RESULT', payload: null })
    const result = await testEbraConnection(state.ebraSession, state.ebraPoool)
    dispatch({ type: 'SET_TEST_RESULT', payload: result })
    dispatch({ type: 'SET_TESTING_CONNECTION', payload: false })
  }

  if (!state.isAuthenticated) {
    return (
      <LoginOverlay 
        password={state.password}
        onPasswordChange={(val) => dispatch({ type: 'SET_PASSWORD', payload: val })}
        onLogin={handleLogin}
        inputId={passwordInputId}
      />
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
          <div className="flex gap-2">
            <Link
              href="/admin/logos"
              className="bg-red-600/20 hover:bg-red-600/30 text-red-400 text-sm font-medium py-2 px-4 rounded-lg border border-red-500/30 transition-colors flex items-center gap-2"
            >
              <Activity className="w-4 h-4" /> Galerie Logos
            </Link>
            <button 
              onClick={openConfigModal}
              className="bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 text-sm font-medium py-2 px-4 rounded-lg border border-blue-500/30 transition-colors flex items-center gap-2"
            >
              <Settings className="w-4 h-4" /> Configuration EBRA
            </button>
            <button
              onClick={handleRevalidate}
              disabled={isRevalidating}
              className="bg-green-600/20 hover:bg-green-600/30 disabled:opacity-50 text-green-400 text-sm font-medium py-2 px-4 rounded-lg border border-green-500/30 transition-colors flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${isRevalidating ? 'animate-spin' : ''}`} />
              {revalidateMsg ?? 'Forcer le refresh'}
            </button>
            <button
              onClick={fetchLogs}
              className="bg-gray-800 hover:bg-gray-700 text-sm font-medium py-2 px-4 rounded-lg border border-gray-700 transition-colors"
            >
              Actualiser
            </button>
          </div>
        </header>

        {state.error && (
          <div className="bg-red-900/20 border border-red-500 text-red-200 p-4 rounded-xl mb-6 flex items-center gap-3">
            <AlertCircle /> {state.error}
          </div>
        )}

        <div className="space-y-4">
          {state.loading ? (
            <div className="text-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-gray-400">Chargement des rapports...</p>
            </div>
          ) : state.logs.length === 0 ? (
            <div className="text-center py-20 bg-gray-800 rounded-2xl border border-gray-700">
              <p className="text-gray-400 text-lg">Aucun log trouvé en base de données.</p>
            </div>
          ) : (
            state.logs.map((log) => (
              <LogItem 
                key={log.id} 
                log={log} 
                isExpanded={state.expandedLog === log.id}
                onToggle={() => dispatch({ type: 'TOGGLE_LOG', payload: log.id })}
              />
            ))
          )}
        </div>
      </div>

      {state.isConfigModalOpen && (
        <ConfigModal 
          state={state}
          dispatch={dispatch}
          onSave={handleSaveConfig}
          onTest={handleTestConnection}
          sessionInputId={sessionInputId}
          pooolInputId={pooolInputId}
        />
      )}

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #374151; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #4b5563; }
      `}</style>
    </div>
  )
}
