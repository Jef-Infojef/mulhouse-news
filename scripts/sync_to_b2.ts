import { PrismaClient } from '@prisma/client';
import fs from 'fs';
import path from 'path';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import * as dotenv from 'dotenv';

// Charge les variables depuis .env ou .env.local
dotenv.config();
dotenv.config({ path: '.env.local' });

const prisma = new PrismaClient();
const IMAGE_DIR = path.join(process.cwd(), 'public', 'article-images');

// Configuration Backblaze B2 (via interface S3)
const b2Client = new S3Client({
  region: 'us-east-005', // À adapter selon votre endpoint (ex: us-east-005)
  endpoint: `https://${process.env.B2_ENDPOINT}`,
  credentials: {
    accessKeyId: process.env.B2_APPLICATION_KEY_ID || '',
    secretAccessKey: process.env.B2_APPLICATION_KEY || '',
  },
});

async function uploadToB2(filePath: string, filename: string): Promise<string | null> {
  try {
    const fileBuffer = fs.readFileSync(filePath);
    const contentType = filename.endsWith('.webp') ? 'image/webp' : 
                        filename.endsWith('.png') ? 'image/png' : 'image/jpeg';

    await b2Client.send(new PutObjectCommand({
      Bucket: process.env.B2_BUCKET_NAME,
      Key: filename,
      Body: fileBuffer,
      ContentType: contentType,
    }));

    // L'URL publique Backblaze ressemble à : https://<f-xxx>.backblazeb2.com/file/<bucket-name>/<filename>
    return `${process.env.B2_PUBLIC_URL}/${filename}`;
  } catch (error) {
    console.error(`  [!] Erreur upload B2 pour ${filename}:`, error);
    return null;
  }
}

async function main() {
  if (!process.env.B2_APPLICATION_KEY_ID) {
    console.error('ERREUR : Les variables Backblaze B2 ne sont pas configurées dans le .env');
    return;
  }

  console.log('--- Synchronisation vers Backblaze B2 ---');
  
  // On prend tous les articles qui ont une image locale mais pas encore de lien R2/B2
  const articles = await prisma.article.findMany({
    where: {
      localImage: { not: null },
      r2Url: null
    }
    // take: 200 removed to process everything
  });

  console.log(`Articles à uploader : ${articles.length}`);

  for (const article of articles) {
    const localPath = path.join(IMAGE_DIR, article.localImage!);
    
    if (fs.existsSync(localPath)) {
      process.stdout.write(`Upload de ${article.localImage}... `);
      const b2Url = await uploadToB2(localPath, article.localImage!);
      
      if (b2Url) {
        await prisma.article.update({
          where: { id: article.id },
          data: { r2Url: b2Url } // On stocke l'URL de backup
        });
        console.log('OK');
      }
    }
  }

  console.log('--- Terminé ---');
}

main().catch(console.error).finally(() => prisma.$disconnect());
