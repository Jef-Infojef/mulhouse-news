import { NextResponse } from 'next/server'
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'

// Les PDF M+Mag sont servis depuis le site officiel mplusinfo.fr
// (page « Le Mag » -> https://www.mplusinfo.fr/le-mag). Chaque numéro y est
// hébergé sous une URL stable sur assets.mulhouse.omerloclients.com/issue_pdf.
//
// On PROXIFIE ici le PDF (streaming) au lieu de simplement rediriger : le serveur
// mplusinfo sert le fichier en « inline » (pas de Content-Disposition: attachment),
// ce qui ouvrirait le PDF dans le navigateur au lieu de le télécharger. En passant
// par cette route on force le téléchargement. Le streaming évite de bufferiser le
// fichier en mémoire et permet de dépasser les limites de réponse de Vercel.
//
// Fallback : si le numéro n'est pas dans la liste, on garde la présignature B2
// (bucket privé), qui sert elle aussi le fichier en téléchargement (attachment).
const MPLUSINFO_PDF: Record<string, string> = {
  '36': '4ebcdccf-7b81-4ec5-96e6-9f42ebebd2ff.pdf',
  '35': '29ac4dad-7bb9-4db6-840a-9c8c3aad0a98.pdf',
  '34': '565758d0-4d48-42b1-832c-592a9262a6a3.pdf',
  '33': '500a46b2-6b99-41a0-8099-69c86e48b574.pdf',
  '32': 'a8a86739-6f61-4b8d-a197-a6fe07f28fca.pdf',
  '31': '77d40a75-99af-4b50-a7e5-a8cb02a77d04.pdf',
  '30': 'eae5978b-e604-44ca-b06a-027eaf312109.pdf',
  '29': '0cfdc4e4-8455-41dd-adc7-fbf6b3b93990.pdf',
  '28': '0564cb7d-1d25-4743-aa59-a72536ca8f83.pdf',
  '27': '05c9914a-a4b2-47c3-9dca-e0cd3f171a85.pdf',
  '26': '6d69b528-e4ca-44f1-8a41-2783bc492147.pdf',
  '25': 'd8f6a0e0-43b7-4fb1-89b9-f89290284c04.pdf',
  '24': '11444fbb-de2e-4c86-9347-f06aaa9e7313.pdf',
  '23': 'd6709f12-cd2f-4a36-b512-8d2bb2a5d7da.pdf',
  '22': 'b81c6905-296b-42bc-b8b1-104164918a09.pdf',
  '21': '60b07fb2-1ea2-4825-b1dd-5de6c55e5106.pdf',
  '20': 'ef339b95-51cf-4941-81e6-920da0a009eb.pdf',
  '19': '4a437772-0fee-4b1f-a8bb-a3c434fa596b.pdf',
  '18': 'de3f2fef-4656-4fae-b0ff-b3d7a1c5be6e.pdf',
  '17': 'f061d5f7-dbfc-404c-a616-67f3cc6f24a0.pdf',
  '16': 'e7786eae-1314-4f2f-ad6d-73c58218e008.pdf',
  '15': 'db078ff4-5a7a-4c7d-905a-cc63975acd71.pdf',
}

// Fallback B2 (bucket privé) : si un numéro n'est pas listé ci-dessus.
const b2Client = new S3Client({
  region: 'eu-central-003',
  endpoint: `https://${process.env.B2_ENDPOINT}`,
  credentials: {
    accessKeyId: process.env.B2_APPLICATION_KEY_ID || '',
    secretAccessKey: process.env.B2_APPLICATION_KEY || '',
  },
})

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ filename: string }> }
) {
  const { filename } = await params
  if (!/^M_Mag_(\d{1,3})_[a-z]+_\d{4}\.pdf$/.test(filename)) {
    return new NextResponse('Fichier introuvable', { status: 404 })
  }

  // 1) Source principale : proxy du PDF officiel (force le téléchargement).
  const num = filename.replace(/^M_Mag_/, '').split('_')[0]
  const assetId = MPLUSINFO_PDF[num]
  if (assetId) {
    const upstream = `https://assets.mulhouse.omerloclients.com/issue_pdf/${assetId}`
    try {
      const res = await fetch(upstream)
      if (!res.ok || !res.body) {
        console.error(`[M+Mag] Échec proxy mplusinfo (${assetId}) : ${res.status}`)
        return new NextResponse('Fichier introuvable', { status: 502 })
      }
      // Retourne le PDF en streaming avec Content-Disposition: attachment pour
      // forcer le téléchargement, quel que soit le comportement du serveur amont.
      return new Response(res.body, {
        status: 200,
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': `attachment; filename="${filename}"`,
          'Content-Length': res.headers.get('content-length') ?? '',
          'Cache-Control': 'public, max-age=86400',
          'X-Content-Type-Options': 'nosniff',
        },
      })
    } catch (error) {
      console.error('[M+Mag] Erreur réseau proxy mplusinfo:', error)
      return new NextResponse('Erreur serveur', { status: 502 })
    }
  }

  // 2) Fallback : présignature B2 si le numéro n'est pas connu.
  try {
    const url = await getSignedUrl(
      b2Client,
      new GetObjectCommand({
        Bucket: process.env.B2_BUCKET_NAME,
        Key: `mplus-mag/${filename}`,
      }),
      { expiresIn: 3600 }
    )
    // B2 met déjà Content-Disposition: attachment (cf. script d'upload) → redirection OK.
    return NextResponse.redirect(url, 307)
  } catch (error) {
    console.error('[M+Mag] Erreur présignature B2:', error)
    return new NextResponse('Erreur serveur', { status: 500 })
  }
}

