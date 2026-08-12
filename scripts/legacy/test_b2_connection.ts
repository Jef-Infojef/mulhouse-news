import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import * as dotenv from 'dotenv';
dotenv.config();
dotenv.config({ path: '.env.local' });

async function test() {
  console.log('Test de connexion B2...');
  console.log('Endpoint:', process.env.B2_ENDPOINT);
  console.log('Bucket:', process.env.B2_BUCKET_NAME);

  const client = new S3Client({
    region: 'us-east-005', // Valeur par défaut pour B2
    endpoint: `https://${process.env.B2_ENDPOINT}`,
    credentials: {
      accessKeyId: process.env.B2_APPLICATION_KEY_ID || '',
      secretAccessKey: process.env.B2_APPLICATION_KEY || '',
    },
  });

  try {
    await client.send(new PutObjectCommand({
      Bucket: process.env.B2_BUCKET_NAME,
      Key: 'test_connection.txt',
      Body: 'Connexion OK',
    }));
    console.log('SUCCÈS : Le fichier test_connection.txt a été envoyé !');
  } catch (err) {
    console.error('ÉCHEC :', err);
  }
}
test();
