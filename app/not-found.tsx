export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">404 - Page Non Trouvée</h1>
        <p className="text-gray-400">Désolé, la page que vous recherchez n'existe pas.</p>
        <a href="/" className="mt-6 inline-block px-6 py-3 bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
          Retour à l'accueil
        </a>
      </div>
    </div>
  )
}
