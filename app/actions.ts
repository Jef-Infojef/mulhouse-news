'use server'

import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

export async function getLatestArticles(limit = 50) {
  try {
    const articles = await prisma.article.findMany({
      orderBy: {
        publishedAt: 'desc',
      },
      take: limit,
    })
    return articles
  } catch (error) {
    console.error('Erreur lors de la récupération des articles:', error)
    return []
  }
}
