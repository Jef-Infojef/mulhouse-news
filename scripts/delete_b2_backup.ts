import { S3Client, DeleteObjectCommand } from '@aws-sdk/client-s3';
import * as dotenv from 'dotenv';
dotenv.config();
dotenv.config({ path: '.env.local' });

async function deleteBackup() {
  const client = new S3Client({
    region: 'us-east-005',
    endpoint: `https://${process.env.B2_ENDPOINT}`,
    credentials: {
      accessKeyId: process.env.B2_APPLICATION_KEY_ID || '',
      secretAccessKey: process.env.B2_APPLICATION_KEY || '',
    },
  });

  const fileKey = 'database-backups/backup-supabase-2026-01-30_12-09-40.sql.gz';

  console.log(`Suppression de : ${fileKey}...`);

  try {
    const command = new DeleteObjectCommand({
      Bucket: process.env.B2_BUCKET_NAME,
      Key: fileKey,
    });

    await client.send(command);
    console.log('SUCCÈS : Le fichier a été supprimé.');
  } catch (err) {
    console.error('ÉCHEC de la suppression :', err);
  }
}

deleteBackup();
