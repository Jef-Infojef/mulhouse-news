import { S3Client, ListObjectsV2Command } from '@aws-sdk/client-s3';
import * as dotenv from 'dotenv';
dotenv.config();
dotenv.config({ path: '.env.local' });

async function findSqlGz() {
  const client = new S3Client({
    region: 'us-east-005',
    endpoint: `https://${process.env.B2_ENDPOINT}`,
    credentials: {
      accessKeyId: process.env.B2_APPLICATION_KEY_ID || '',
      secretAccessKey: process.env.B2_APPLICATION_KEY || '',
    },
  });

  let continuationToken = undefined;
  const foundFiles: any[] = [];

  try {
    do {
      const command = new ListObjectsV2Command({
        Bucket: process.env.B2_BUCKET_NAME,
        ContinuationToken: continuationToken,
      });

      const response = await client.send(command);
      
      if (response.Contents) {
        for (const item of response.Contents) {
          const key = item.Key || '';
          if (key.endsWith('.sql.gz')) {
            foundFiles.push(item);
          }
        }
      }
      continuationToken = response.NextContinuationToken;
    } while (continuationToken);

    if (foundFiles.length > 0) {
      console.log('\n--- Fichiers .sql.gz trouvés ---');
      foundFiles.forEach(item => {
        console.log(`${item.Key} (${(item.Size! / (1024 * 1024)).toFixed(2)} MB)`);
      });
    } else {
      console.log('\nAucun fichier .sql.gz trouvé.');
    }
  } catch (err) {
    console.error('Erreur :', err);
  }
}

findSqlGz();
