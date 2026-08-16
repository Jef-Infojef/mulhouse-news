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
      { src: '/icons/icon-16x16.png', sizes: '16x16', type: 'image/png' },
      { src: '/icons/icon-32x32.png', sizes: '32x32', type: 'image/png' },
      { src: '/icons/icon-48x48.png', sizes: '48x48', type: 'image/png' },
      { src: '/icons/icon-96x96.png', sizes: '96x96', type: 'image/png' },
      { src: '/icons/icon-128x128.png', sizes: '128x128', type: 'image/png' },
      { src: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icons/icon-256x256.png', sizes: '256x256', type: 'image/png' },
      { src: '/icons/icon-384x384.png', sizes: '384x384', type: 'image/png' },
      { src: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/icons/icon-maskable-192x192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
      { src: '/icons/icon-maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  }
}