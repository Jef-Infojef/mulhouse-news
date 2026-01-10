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

    console.log(`${articles.length} articles récupérés.`)
    return { articles, error: null }
  } catch (error: any) {
    console.error('ERREUR PRISMA:', error)
    return { articles: [], error: error.message || String(error) }
  }
}

export async function getArticlesWithPagination(skip = 0, take = 20, search = '') {
  try {
    const where = search ? {
      OR: [
        { title: { contains: search, mode: 'insensitive' as const } },
        { description: { contains: search, mode: 'insensitive' as const } },
        { source: { contains: search, mode: 'insensitive' as const } },
      ]
    } : undefined

    const [articles, total] = await prisma.$transaction([
      prisma.article.findMany({
        where,
        orderBy: {
          publishedAt: 'desc',
        },
        skip,
        take,
      }),
      prisma.article.count({ where })
    ])

    return { articles, total, error: null }
  } catch (error: any) {
    console.error('ERREUR PRISMA:', error)
    return { articles: [], total: 0, error: error.message || String(error) }
  }
}
