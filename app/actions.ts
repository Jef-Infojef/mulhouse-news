'use server'

import prisma from '@/lib/prisma'

export async function getLatestArticles() {
  try {
    const articles = await prisma.article.findMany({
      orderBy: {
        publishedAt: 'desc',
      },
    })

    console.log(`${articles.length} articles récupérés.`)
    return { articles, error: null }
  } catch (error: any) {
    console.error('ERREUR PRISMA:', error)
    return { articles: [], error: error.message || String(error) }
  }
}
