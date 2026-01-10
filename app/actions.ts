'use server'

import prisma from '@/lib/prisma'

export async function getLatestArticles(limit = 100) {
  try {
    const articles = await prisma.article.findMany({
      orderBy: {
        publishedAt: 'desc',
      },
      take: limit,
    })
    
    // Log pour debug (visible dans les logs Vercel)
    console.log(`${articles.length} articles récupérés de la base.`)
    
    return articles
  } catch (error) {
    console.error('ERREUR PRISMA:', error)
    return []
  }
}