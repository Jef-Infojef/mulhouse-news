import { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Mulhouse Actu',
    short_name: 'MulhouseActu',
    description: 'Toute l\'actualité de Mulhouse en temps réel',
    start_url: '/',
    display: 'standalone',
    background_color: '#0f172a',
    theme_color: '#a91101',
    icons: [
      {
        src: '/icon?text=MA',
        sizes: 'any',
        type: 'image/x-icon',
      },
      {
        src: '/apple-icon',
        sizes: '180x180',
        type: 'image/png',
      },
    ],
  }
}