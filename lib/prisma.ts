import { ConvexHttpClient } from 'convex/browser'

// Phase 2 de la migration Convex : le client d'accès aux données applicatives
// est désormais Convex (cloud) et plus Prisma/Supabase.
//
// Le paquet Prisma et `prisma generate` restent dans le build tant que les
// scripts GitHub Actions (scripts/*.ts, Phase 3) n'ont pas migré : le retrait
// complet de Prisma du build interviendra après la Phase 3.

const convexUrl = process.env.NEXT_PUBLIC_CONVEX_URL

if (!convexUrl) {
  throw new Error(
    'NEXT_PUBLIC_CONVEX_URL est manquante : définissez-la dans .env.local ' +
      '(URL du déploiement Convex cloud, ex. https://friendly-chicken-952.convex.cloud).'
  )
}

export const convex = new ConvexHttpClient(convexUrl)

export default convex