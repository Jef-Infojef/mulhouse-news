import { NextResponse } from 'next/server'
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'

// Les PDF M+Mag (≈136 Mo) sont stockés sur Backblaze B2 (bucket privé : B2 exige un
// historique de paiement pour autoriser un bucket public). On redirige vers une URL
// présignée : le téléchargement part directement de B2, pas de la bande passante Vercel.
const b2Client = new S3Client({
  region: 'eu-central-003',
  endpoint: `https://${process.env.B2_ENDPOINT}`,
  credentials: {
    accessKeyId: process.env.B2_APPLICATION_KEY_ID || '',
    secretAccessKey: process.env.B2_APPLICATION_KEY || '',
  },
})

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ filename: string }> }
) {
  const { filename } = await params
  if (!/^M_Mag_\d{1,3}_[a-z]+_\d{4}\.pdf$/.test(filename)) {
    return new NextResponse('Fichier introuvable', { status: 404 })
  }

  try {
    const url = await getSignedUrl(
      b2Client,
      new GetObjectCommand({
        Bucket: process.env.B2_BUCKET_NAME,
        Key: `mplus-mag/${filename}`,
      }),
      { expiresIn: 3600 }
    )
    return NextResponse.redirect(url, 307)
  } catch (error) {
    console.error('[M+Mag] Erreur présignature B2:', error)
    return new NextResponse('Erreur serveur', { status: 500 })
  }
}
