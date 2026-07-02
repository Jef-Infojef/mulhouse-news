import { createHmac, timingSafeEqual } from 'crypto'
import { cookies } from 'next/headers'

const SESSION_DURATION_S = 30 * 24 * 60 * 60
const COOKIE_NAME = 'admin_auth'

function getSecret(): string | null {
  // AUTH_SECRET dédié si défini, sinon on dérive du mot de passe admin
  return process.env.AUTH_SECRET?.trim() || process.env.ADMIN_PASSWORD?.trim() || null
}

function sign(expiresAt: number, secret: string): string {
  return createHmac('sha256', secret).update(`admin-session:${expiresAt}`).digest('hex')
}

export function safeEqual(a: string, b: string): boolean {
  // Comparaison en temps constant, y compris sur des longueurs différentes
  const ha = createHmac('sha256', 'cmp').update(a).digest()
  const hb = createHmac('sha256', 'cmp').update(b).digest()
  return timingSafeEqual(ha, hb)
}

export async function createAdminSession(): Promise<boolean> {
  const secret = getSecret()
  if (!secret) return false
  const expiresAt = Math.floor(Date.now() / 1000) + SESSION_DURATION_S
  const token = `${expiresAt}.${sign(expiresAt, secret)}`
  const cookieStore = await cookies()
  cookieStore.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: SESSION_DURATION_S,
    sameSite: 'strict',
  })
  return true
}

export async function isAdminAuthenticated(): Promise<boolean> {
  const secret = getSecret()
  if (!secret) return false
  const cookieStore = await cookies()
  const token = cookieStore.get(COOKIE_NAME)?.value
  if (!token) return false
  const [expStr, sig] = token.split('.')
  const expiresAt = Number(expStr)
  if (!Number.isFinite(expiresAt) || !sig) return false
  if (expiresAt < Date.now() / 1000) return false
  return safeEqual(sig, sign(expiresAt, secret))
}
