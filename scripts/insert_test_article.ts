import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const url = "https://www.lalsace.fr/culture-loisirs/2026/01/25/marches-de-noel-carnavals-bals-dansants-quel-est-le-prix-a-payer-pour-faire-la-fete"
  
  // Vérifie si déjà présent (peut-être sous un autre lien ?)
  const existing = await prisma.article.findFirst({
    where: { link: url }
  })

  if (existing) {
    console.log("Article déjà présent.")
    return
  }

  await prisma.article.create({
    data: {
      title: "Marchés de Noël, carnavals, bals dansants… : quel est le prix à payer pour faire la fête ?",
      link: url,
      source: "lalsace.fr",
      publishedAt: new Date(), // Aujourd'hui
      description: "Test insertion pour scraping paywall"
    }
  })
  console.log("Article de test inséré.")
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
