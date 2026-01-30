import { S3Client, ListObjectsV2Command, GetObjectCommand } from "@aws-sdk/client-s3";
import dotenv from "dotenv";
import fs from "fs";
import path from "path";
import { Readable } from "stream";
import { pipeline } from "stream/promises";

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

async function downloadAllImages() {
  const bucket = process.env.B2_BUCKET_NAME || "mulhouse-news-images";
  const localDir = "P:\\Backup\\images-articles";
  
  if (!fs.existsSync(localDir)) {
    fs.mkdirSync(localDir, { recursive: true });
  }

  console.log(`Début de la sauvegarde des images depuis B2 (${bucket}) vers ${localDir}...`);
  
  try {
    let continuationToken = undefined;
    let totalDownloaded = 0;
    let totalSkipped = 0;

    do {
      const listCommand = new ListObjectsV2Command({
        Bucket: bucket,
        ContinuationToken: continuationToken,
        // On ne télécharge que les fichiers à la racine (les images)
        // et on ignore le dossier database-backups s'il en reste
      });

      const response = await s3.send(listCommand);
      if (response.Contents) {
        // Filtrer pour ne garder que les images (fichiers à la racine finit par .jpg/png/webp)
        const images = response.Contents.filter(f => 
            !f.Key.includes('/') && (f.Key.endsWith('.jpg') || f.Key.endsWith('.png') || f.Key.endsWith('.webp'))
        );

        console.log(`Traitement d'un lot de ${images.length} images...`);

        // Téléchargement par paquets de 10 en parallèle pour ne pas saturer
        const batchSize = 10;
        for (let i = 0; i < images.length; i += batchSize) {
          const batch = images.slice(i, i + batchSize);
          await Promise.all(batch.map(async (file) => {
            const localPath = path.join(localDir, file.Key!);
            
            // Skip si le fichier existe déjà et a la même taille
            if (fs.existsSync(localPath) && fs.statSync(localPath).size === file.Size) {
              totalSkipped++;
              return;
            }

            try {
              const getCommand = new GetObjectCommand({ Bucket: bucket, Key: file.Key });
              const { Body } = await s3.send(getCommand);
              if (Body instanceof Readable) {
                await pipeline(Body, fs.createWriteStream(localPath));
                totalDownloaded++;
                if (totalDownloaded % 100 === 0) {
                    console.log(`  - ${totalDownloaded} images téléchargées...`);
                }
              }
            } catch (err) {
              console.error(`Erreur sur ${file.Key}:`, err.message);
            }
          }));
        }
      }
      continuationToken = response.NextContinuationToken;
    } while (continuationToken);

    console.log(`\n✅ Terminé !`);
    console.log(`Images téléchargées : ${totalDownloaded}`);
    console.log(`Images déjà présentes (skipped) : ${totalSkipped}`);
    console.log(`Total local : ${totalDownloaded + totalSkipped}`);

  } catch (error) {
    console.error("Erreur globale :", error);
  }
}

downloadAllImages();
