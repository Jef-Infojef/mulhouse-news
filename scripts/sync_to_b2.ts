import fs from 'fs';
import path from 'path';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import * as convex from './convex_client_ts';

// Phase 4 : accès DB portés Prisma → Convex (scripts/convex_client_ts.ts).
// La logique réseau (upload B2, content-type, URL publique) est inchangée.

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
  if (!convex.useConvex()) {
    console.error('ERREUR : scripts images portés sur Convex (Phase 4) — définir CONVEX_DEPLOY_KEY et NEXT_PUBLIC_CONVEX_URL.');
    return;
  }

  console.log('--- Synchronisation vers Backblaze B2 (Convex) ---');
  
  // Tous les articles qui ont une image locale mais pas encore de lien R2/B2
  const articles = await convex.getImagesToUpload();
  console.log(`Articles à uploader : ${articles.length}`);

  for (const article of articles) {
    const localPath = path.join(IMAGE_DIR, article.localImage);
    
    if (fs.existsSync(localPath)) {
      process.stdout.write(`Upload de ${article.localImage}... `);
      const b2Url = await uploadToB2(localPath, article.localImage);
      
      if (b2Url) {
        await convex.updateArticleR2Url(article.id, b2Url);
        console.log('OK');
      }
    }
  }

  // --- Images de galerie (ArticleImage) ---
  const galleryImages = await convex.getArticleImagesToUpload();
  console.log(`Images de galerie à uploader : ${galleryImages.length}`);

  for (const img of galleryImages) {
    const localPath = path.join(IMAGE_DIR, img.localImage);
    
    if (fs.existsSync(localPath)) {
      process.stdout.write(`Upload de ${img.localImage}... `);
      const b2Url = await uploadToB2(localPath, img.localImage);
      
      if (b2Url) {
        await convex.updateArticleImageR2Url(img.id, b2Url);
        console.log('OK');
      }
    }
  }

  console.log('--- Terminé ---');
}

main().catch(console.error);
