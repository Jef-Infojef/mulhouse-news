import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV !== 'production'

// Les vignettes d'articles sont rendues par un <img> classique (ArticleCard), pas par
// next/image : aucun hôte distant n'a besoin d'être autorisé ici. `img-src` reste large
// car ces images viennent des sites de presse et du service favicon Google.
const csp = [
  "default-src 'self'",
  // Next injecte ses scripts d'hydratation en inline sans nonce : 'unsafe-inline' est
  // requis. 'unsafe-eval' n'est nécessaire qu'au React Refresh du mode dev.
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ''}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https: http:",
  "font-src 'self' data:",
  `connect-src 'self' https://api.open-meteo.com${isDev ? ' ws: wss:' : ''}`,
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
  'upgrade-insecure-requests',
].join('; ')

const nextConfig: NextConfig = {
  reactCompiler: true,
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
          { key: 'Content-Security-Policy', value: csp },
        ],
      },
    ]
  },
};

export default nextConfig;
