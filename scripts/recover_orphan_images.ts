/**
 * Rattrapage des images manquantes sur B2.
 *
 * Modes :
 *   (défaut)            localImage rempli mais r2Url vide (fichier perdu sur runner éphémère)
 *   --never-downloaded  imageUrl présente mais jamais passée par download_images (hors fenêtre 48h)
 *
 * Usage:
 *   npx tsx scripts/recover_orphan_images.ts
 *   npx tsx scripts/recover_orphan_images.ts --never-downloaded
 *   npx tsx scripts/recover_orphan_images.ts --dry-run --limit 10
 *   npx tsx scripts/recover_orphan_images.ts --from 2026-06-14 --to 2026-07-01
 */
import { PrismaClient } from '@prisma/client';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import * as dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';

dotenv.config();
dotenv.config({ path: '.env.local' });

const prisma = new PrismaClient();
const IMAGE_DIR = path.join(process.cwd(), 'public', 'article-images');

const b2Client = new S3Client({
  region: 'us-east-005',
  endpoint: `https://${process.env.B2_ENDPOINT}`,
  credentials: {
    accessKeyId: process.env.B2_APPLICATION_KEY_ID || '',
    secretAccessKey: process.env.B2_APPLICATION_KEY || '',
  },
});

type RecoveryMode = 'orphans' | 'never-downloaded';

function parseArgs() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const mode: RecoveryMode = args.includes('--never-downloaded') ? 'never-downloaded' : 'orphans';
  const limitIdx = args.indexOf('--limit');
  const limit = limitIdx >= 0 ? parseInt(args[limitIdx + 1], 10) : undefined;
  const fromIdx = args.indexOf('--from');
  const toIdx = args.indexOf('--to');
  const from = fromIdx >= 0 ? new Date(args[fromIdx + 1] + 'T00:00:00Z') : undefined;
  const to = toIdx >= 0 ? new Date(args[toIdx + 1] + 'T23:59:59Z') : undefined;
  return { dryRun, limit, from, to, mode };
}

function getExtensionFromContentType(contentType: string | null): string {
  if (!contentType) return 'jpg';
  const ct = contentType.toLowerCase();
  if (ct.includes('image/png')) return 'png';
  if (ct.includes('image/webp')) return 'webp';
  if (ct.includes('image/gif')) return 'gif';
  if (ct.includes('image/svg+xml')) return 'svg';
  if (ct.includes('image/avif')) return 'avif';
  return 'jpg';
}

function getContentType(filename: string): string {
  if (filename.endsWith('.webp')) return 'image/webp';
  if (filename.endsWith('.png')) return 'image/png';
  if (filename.endsWith('.gif')) return 'image/gif';
  if (filename.endsWith('.svg')) return 'image/svg+xml';
  if (filename.endsWith('.avif')) return 'image/avif';
  return 'image/jpeg';
}

async function downloadImage(
  url: string,
  id: string,
  articleLink?: string | null
): Promise<string | null> {
  try {
    let finalUrl = url.trim();

    if (finalUrl === 'image.png' || finalUrl === 'undefined' || !finalUrl || finalUrl.includes('placeholder.jpg')) {
      return null;
    }

    if (finalUrl.startsWith('//')) {
      finalUrl = 'https:' + finalUrl;
    } else if (finalUrl.startsWith('/')) {
      if (!articleLink) return null;
      try {
        const urlObj = new URL(articleLink);
        finalUrl = `${urlObj.protocol}//${urlObj.hostname}${finalUrl}`;
      } catch {
        return null;
      }
    } else if (!finalUrl.startsWith('http')) {
      if (!articleLink) return null;
      try {
        const basePath = articleLink.substring(0, articleLink.lastIndexOf('/') + 1);
        finalUrl = basePath + finalUrl;
      } catch {
        return null;
      }
    }

    finalUrl = finalUrl.replace(/&amp;/g, '&');

    let referer = 'https://www.google.com/';
    try {
      const urlObj = new URL(finalUrl);
      referer = `${urlObj.protocol}//${urlObj.hostname}/`;
    } catch {
      /* ignore */
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    const response = await fetch(finalUrl, {
      signal: controller.signal,
      headers: {
        'User-Agent':
          'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        Accept: 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        Referer: referer,
        Connection: 'keep-alive',
      },
    });

    clearTimeout(timeout);

    if (!response.ok) {
      if (response.status !== 404) {
        console.error(`  [!] HTTP ${response.status} pour ${finalUrl}`);
      }
      return null;
    }

    const contentType = response.headers.get('content-type');
    const ext = getExtensionFromContentType(contentType);
    const filename = `${id}.${ext}`;
    const filePath = path.join(IMAGE_DIR, filename);

    const buffer = Buffer.from(await response.arrayBuffer());
    if (buffer.length < 500) {
      console.warn(`  [?] Image suspecte (${buffer.length} octets) pour ${finalUrl}`);
      return null;
    }

    await fs.promises.writeFile(filePath, buffer);
    return filename;
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    if (error instanceof Error && error.name === 'AbortError') {
      console.error(`  [!] Timeout pour ${url}`);
    } else {
      console.error(`  [!] Erreur téléchargement : ${message}`);
    }
    return null;
  }
}

async function uploadToB2(filePath: string, filename: string): Promise<string | null> {
  try {
    const fileBuffer = fs.readFileSync(filePath);
    await b2Client.send(
      new PutObjectCommand({
        Bucket: process.env.B2_BUCKET_NAME,
        Key: filename,
        Body: fileBuffer,
        ContentType: getContentType(filename),
      })
    );
    return `${process.env.B2_PUBLIC_URL}/${filename}`;
  } catch (error) {
    console.error(`  [!] Erreur upload B2 pour ${filename}:`, error);
    return null;
  }
}

type ArticleRow = {
  id: string;
  imageUrl: string | null;
  link: string | null;
  localImage: string | null;
  publishedAt: Date;
};

async function recoverArticle(article: ArticleRow, dryRun: boolean): Promise<'uploaded' | 'redownloaded' | 'failed'> {
  const existingPath = article.localImage ? path.join(IMAGE_DIR, article.localImage) : null;
  const hadLocalFile = !!(existingPath && fs.existsSync(existingPath));
  let filename = article.localImage;

  if (hadLocalFile) {
    if (dryRun) {
      console.log(`  [dry-run] Upload local existant : ${filename}`);
      return 'uploaded';
    }
  } else {
    if (!article.imageUrl) return 'failed';

    if (dryRun) {
      console.log(`  [dry-run] Retéléchargement depuis imageUrl`);
      return 'redownloaded';
    }

    const downloaded = await downloadImage(article.imageUrl, article.id, article.link);
    if (!downloaded) return 'failed';
    filename = downloaded;
  }

  const localPath = path.join(IMAGE_DIR, filename!);
  const b2Url = await uploadToB2(localPath, filename!);
  if (!b2Url) return 'failed';

  const updateData: { r2Url: string; localImage?: string } = { r2Url: b2Url };
  if (filename !== article.localImage) {
    updateData.localImage = filename;
  }

  await prisma.article.update({
    where: { id: article.id },
    data: updateData,
  });

  return hadLocalFile ? 'uploaded' : 'redownloaded';
}

async function main() {
  const { dryRun, limit, from, to, mode } = parseArgs();

  if (!dryRun && !process.env.B2_APPLICATION_KEY_ID) {
    console.error('ERREUR : variables Backblaze B2 manquantes dans .env');
    process.exit(1);
  }

  if (!fs.existsSync(IMAGE_DIR)) {
    fs.mkdirSync(IMAGE_DIR, { recursive: true });
  }

  const publishedAt: { gte?: Date; lte?: Date } = {};
  if (from) publishedAt.gte = from;
  if (to) publishedAt.lte = to;

  const articles = await prisma.article.findMany({
    where: {
      r2Url: null,
      imageUrl: { not: null, notIn: ['', 'null'] },
      ...(mode === 'never-downloaded'
        ? { localImage: null }
        : { localImage: { not: null } }),
      ...(Object.keys(publishedAt).length > 0 ? { publishedAt } : {}),
    },
    select: {
      id: true,
      imageUrl: true,
      link: true,
      localImage: true,
      publishedAt: true,
    },
    orderBy: { publishedAt: 'asc' },
    ...(limit ? { take: limit } : {}),
  });

  console.log(
    mode === 'never-downloaded'
      ? '--- Rattrapage images jamais téléchargées ---'
      : '--- Rattrapage images orphelines ---'
  );
  if (dryRun) console.log('Mode : DRY-RUN (aucune écriture)');
  if (from || to) {
    console.log(`Période : ${from?.toISOString().slice(0, 10) ?? '…'} → ${to?.toISOString().slice(0, 10) ?? '…'}`);
  }
  console.log(`Articles à traiter : ${articles.length}`);

  const stats = { uploaded: 0, redownloaded: 0, failed: 0 };
  const BATCH_SIZE = 5;

  for (let i = 0; i < articles.length; i += BATCH_SIZE) {
    const batch = articles.slice(i, i + BATCH_SIZE);

    await Promise.all(
      batch.map(async (article, batchIdx) => {
        const n = i + batchIdx + 1;
        const localExists = article.localImage
          ? fs.existsSync(path.join(IMAGE_DIR, article.localImage))
          : false;
        process.stdout.write(
          `[${n}/${articles.length}] ${article.id.slice(0, 8)}… ` +
            `${localExists ? 'local OK' : 'retéléchargement'}… `
        );

        const result = await recoverArticle(article, dryRun);
        stats[result === 'failed' ? 'failed' : result]++;
        console.log(result === 'failed' ? 'ÉCHEC' : 'OK');
      })
    );

    if ((i + BATCH_SIZE) % 50 === 0 || i + BATCH_SIZE >= articles.length) {
      const done = Math.min(i + BATCH_SIZE, articles.length);
      console.log(`Progression : ${done}/${articles.length}`);
    }
  }

  console.log('\n--- Résumé ---');
  console.log(`Upload direct (fichier local) : ${stats.uploaded}`);
  console.log(`Retéléchargés + uploadés       : ${stats.redownloaded}`);
  console.log(`Échecs                         : ${stats.failed}`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => await prisma.$disconnect());