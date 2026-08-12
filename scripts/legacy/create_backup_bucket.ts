
import { S3Client, CreateBucketCommand } from "@aws-sdk/client-s3";
import dotenv from "dotenv";

dotenv.config();
dotenv.config({ path: ".env.local" });

const s3 = new S3Client({
  endpoint: `https://s3.eu-central-003.backblazeb2.com`,
  region: "eu-central-003",
  credentials: {
    accessKeyId: process.env.B2_APPLICATION_KEY_ID || "",
    secretAccessKey: process.env.B2_APPLICATION_KEY || "",
  },
});

async function createBackupBucket() {
  // On ajoute un suffixe aléatoire ou spécifique pour l'unicité
  const bucketName = "mulhouse-news-backups-private";
  console.log(`Tentative de création du bucket privé : ${bucketName}...`);
  
  try {
    const command = new CreateBucketCommand({
      Bucket: bucketName,
      ACL: 'private', // S'assure que le bucket est privé
    });

    await s3.send(command);
    console.log(`✅ Succès ! Le bucket ${bucketName} a été créé.`);
    return bucketName;
  } catch (error: any) {
    if (error.name === 'BucketAlreadyExists' || error.name === 'BucketAlreadyOwnedByYou') {
      console.log(`ℹ️ Le bucket ${bucketName} existe déjà (probablement le vôtre).`);
      return bucketName;
    }
    console.error("❌ Erreur lors de la création du bucket :", error.message);
    return null;
  }
}

createBackupBucket();
