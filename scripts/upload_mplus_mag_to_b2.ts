import fs from 'fs';
import path from 'path';
import { S3Client, PutObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3';
import * as dotenv from 'dotenv';

// Charge les variables depuis .env ou .env.local
dotenv.config();
dotenv.config({ path: '.env.local' });

const PDF_DIR = path.join(process.cwd(), 'public', 'mplus-mag');
const B2_PREFIX = 'mplus-mag/';

// Configuration Backblaze B2 (via interface S3)
const b2Client = new S3Client({
  region: 'eu-central-003',
  endpoint: `https://${process.env.B2_ENDPOINT}`,
  credentials: {
    accessKeyId: process.env.B2_APPLICATION_KEY_ID || '',
    secretAccessKey: process.env.B2_APPLICATION_KEY || '',
  },
});

// Les fichiers locaux contiennent des accents ("été") mais la page génère des
// liens ASCII ("ete") : on normalise les clés B2 pour qu'elles correspondent aux liens.
function toAsciiKey(filename: string): string {
  return filename.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

async function main() {
  if (!process.env.B2_APPLICATION_KEY_ID) {
    console.error('ERREUR : Les variables Backblaze B2 ne sont pas configurées dans le .env');
    process.exit(1);
  }

  const files = fs.readdirSync(PDF_DIR).filter(f => f.toLowerCase().endsWith('.pdf'));
  console.log(`--- Upload de ${files.length} PDF M+Mag vers B2 (${process.env.B2_BUCKET_NAME}) ---`);

  let errors = 0;
  for (const file of files) {
    const key = B2_PREFIX + toAsciiKey(file);
    const filePath = path.join(PDF_DIR, file);
    const size = (fs.statSync(filePath).size / 1024 / 1024).toFixed(1);
    process.stdout.write(`Upload ${file} -> ${key} (${size} Mo)... `);

    try {
      await b2Client.send(new PutObjectCommand({
        Bucket: process.env.B2_BUCKET_NAME,
        Key: key,
        Body: fs.readFileSync(filePath),
        ContentType: 'application/pdf',
        // Force le téléchargement au clic (l'attribut HTML "download" est ignoré cross-origin)
        ContentDisposition: `attachment; filename="${toAsciiKey(file)}"`,
      }));

      // Vérifie que l'objet existe bien et a la bonne taille
      const head = await b2Client.send(new HeadObjectCommand({
        Bucket: process.env.B2_BUCKET_NAME,
        Key: key,
      }));
      if (head.ContentLength !== fs.statSync(filePath).size) {
        throw new Error(`taille distante ${head.ContentLength} != locale ${fs.statSync(filePath).size}`);
      }
      console.log('OK');
    } catch (error) {
      errors++;
      console.log('ECHEC');
      console.error(`  [!] ${file}:`, error);
    }
  }

  if (errors > 0) {
    console.error(`--- Terminé avec ${errors} erreur(s) ---`);
    process.exit(1);
  }
  console.log(`--- Terminé : ${files.length}/${files.length} fichiers uploadés et vérifiés ---`);
  console.log(`URLs publiques : ${process.env.B2_PUBLIC_URL}/${B2_PREFIX}<fichier>`);
}

main();
