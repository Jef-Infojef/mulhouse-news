import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  console.log("Tentative d'ajout de la colonne 'content'...")
  try {
    await prisma.$executeRawUnsafe(`ALTER TABLE "Article" ADD COLUMN IF NOT EXISTS "content" TEXT;`)
    console.log("✅ Colonne 'content' ajoutée avec succès (ou déjà présente).")
  } catch (error) {
    console.error("❌ Erreur lors de l'ajout de la colonne :", error)
  }
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
