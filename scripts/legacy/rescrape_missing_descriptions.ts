
import { PrismaClient } from '@prisma/client';
import { execSync } from 'child_process';

const prisma = new PrismaClient();

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      content: { not: null },
      description: null
    }
  });

  console.log(`--- Rescraping ${articles.length} descriptions ---`);

  for (const art of articles) {
    console.log(`Processing: ${art.title.substring(0, 50)}...`);
    let description = null;

    try {
      // Fetch HTML
      const html = execSync(`curl -s -L -m 10 "${art.link}"`, { encoding: 'utf-8', maxBuffer: 1024 * 1024 * 2 });
      
      // Try og:description
      const ogMatch = html.match(/property="og:description" content="(.*?)"/);
      description = ogMatch ? ogMatch[1] : null;

      // Try meta description
      if (!description) {
        const metaMatch = html.match(/name="description" content="(.*?)"/);
        description = metaMatch ? metaMatch[1] : null;
      }

      // Final fallback: Use start of content if still null
      if (!description && art.content) {
        description = art.content.split('\n')[0].substring(0, 200).trim() + '...';
        console.log(`  [Fallback] Used content snippet.`);
      }

      if (description) {
        // Decode HTML entities briefly if needed (simple ones)
        description = description.replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&nbsp;/g, ' ');
        
        await prisma.article.update({
          where: { id: art.id },
          data: { description: description }
        });
        console.log(`  ✅ Success: ${description.substring(0, 50)}...`);
      } else {
        console.log(`  ❌ Failed to get any description.`);
      }

    } catch (e) {
      console.log(`  ⚠️ Error fetching ${art.link}: ${e.message}`);
      // Fallback on error too
      if (art.content) {
         const fallbackDesc = art.content.split('\n')[0].substring(0, 200).trim() + '...';
         await prisma.article.update({
            where: { id: art.id },
            data: { description: fallbackDesc }
          });
          console.log(`  [Error-Fallback] Used content snippet.`);
      }
    }
  }

  console.log('\n--- Rescraping complete ---');
}

main().finally(() => prisma.$disconnect());
