import { PrismaClient } from '@prisma/client';
import fs from 'fs';
import path from 'path';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

const prisma = new PrismaClient();
const IMAGE_DIR = path.join(process.cwd(), 'public', 'article-images');

const r2Client = new S3Client({
  region: 'auto',
  endpoint: process.env.R2_ENDPOINT,
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID || '',
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY || '',
  },
});

async function uploadToR2(filePath: string, filename: string): Promise<string | null> {
  try {
    const fileBuffer = fs.readFileSync(filePath);
    const contentType = filename.endsWith('.webp') ? 'image/webp' : 
                        filename.endsWith('.png') ? 'image/png' : 'image/jpeg';

    await r2Client.send(new PutObjectCommand({
      Bucket: process.env.R2_BUCKET_NAME,
      Key: filename,
      Body: fileBuffer,
      ContentType: contentType,
    }));

    return `${process.env.R2_PUBLIC_URL}/${filename}`;
  } catch (error) {
    console.error(`  [!] Erreur upload R2 pour ${filename}:`, error);
    return null;
  }
}

async function main() {
  if (!process.env.R2_ACCESS_KEY_ID) {
    console.error('ERREUR : Les variables R2 ne sont pas configurées dans le .env');
    return;
  }

  console.log('--- Synchronisation vers Cloudflare R2 ---');
  
  // On prend les articles qui ont une image locale mais pas encore de lien R2
  const articles = await prisma.article.findMany({
    where: {
      localImage: { not: null },
      r2Url: null
    },
    take: 500 // On procède par petits lots
  });

  console.log(`Articles à uploader : ${articles.length}`);

  for (const article of articles) {
    const localPath = path.join(IMAGE_DIR, article.localImage!);
    
    if (fs.existsSync(localPath)) {
      console.log(`Upload de ${article.localImage}...`);
      const r2Url = await uploadToR2(localPath, article.localImage!);
      
      if (r2Url) {
        await prisma.article.update({
          where: { id: article.id },
          data: { r2Url: r2Url }
        });
      }
    } else {
      console.warn(`  [!] Fichier manquant localement : ${article.localImage}`);
    }
  }

  console.log('--- Terminé ---');
}

main().catch(console.error).finally(() => prisma.$disconnect());
