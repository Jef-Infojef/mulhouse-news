
import { PrismaClient } from '@prisma/client';
import { BeautifulSoup } from 'jsdom'; // On n'a pas jsdom installé forcément, on va utiliser une approche plus simple
import { execSync } from 'child_process';

const prisma = new PrismaClient();

async function main() {
  const url = 'https://www.lalsace.fr/culture-loisirs/2026/01/28/on-fait-quoi-ce-week-end-du-30-janvier-au-1er-fevrier-dans-le-sud-alsace';
  console.log(`Analyse de la page : ${url}`);

  // Utilisation de curl via shell pour récupérer le HTML (plus simple)
  try {
    const html = execSync(`curl -s -L "${url}"`, { encoding: 'utf-8', maxBuffer: 1024 * 1024 * 5 });
    
    // Regex pour trouver og:image
    const ogMatch = html.match(/property="og:image" content="(.*?)"/);
    let imageUrl = ogMatch ? ogMatch[1] : null;

    if (!imageUrl) {
        const twitterMatch = html.match(/name="twitter:image" content="(.*?)"/);
        imageUrl = twitterMatch ? twitterMatch[1] : null;
    }

    if (imageUrl) {
      console.log(`✅ Image trouvée : ${imageUrl}`);
      await prisma.article.update({
        where: { link: url },
        data: { imageUrl: imageUrl }
      });
      console.log('Base de données mise à jour avec succès.');
    } else {
      console.log('❌ Aucune image trouvée via regex.');
      // Tentative via LD+JSON simple
      const ldMatch = html.match(/"image":\s*"(.*?)"/);
      if (ldMatch) {
          imageUrl = ldMatch[1];
          console.log(`✅ Image trouvée (LD): ${imageUrl}`);
          await prisma.article.update({
            where: { link: url },
            data: { imageUrl: imageUrl }
          });
      }
    }
  } catch (error) {
    console.error('Erreur :', error.message);
  }
}

main().finally(() => prisma.$disconnect());
