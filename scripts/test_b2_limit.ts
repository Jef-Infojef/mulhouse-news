
import { S3Client, GetObjectCommand, ListObjectsV2Command } from "@aws-sdk/client-s3";
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

async function testSingleDownload() {
  const bucket = process.env.B2_BUCKET_NAME || "mulhouse-news-images";
  try {
    const list = await s3.send(new ListObjectsV2Command({ Bucket: bucket, MaxKeys: 1 }));
    if (!list.Contents || list.Contents.length === 0) {
        console.log("No files found in bucket.");
        return;
    }
    const key = list.Contents[0].Key;
    console.log(`Testing download of: ${key}...`);
    await s3.send(new GetObjectCommand({ Bucket: bucket, Key: key }));
    console.log("✅ Download successful! You are NOT blocked yet.");
  } catch (error: any) {
    console.log(`❌ Download failed.`);
    console.log(`Error Name: ${error.name}`);
    console.log(`Error Message: ${error.message}`);
    if (error.message.includes("429") || error.name.includes("LimitExceeded")) {
        console.log("👉 Confirmed: Daily API limit reached.");
    }
  }
}

testSingleDownload();
