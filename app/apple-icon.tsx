import { ImageResponse } from 'next/og'

export const size = {
  width: 180,
  height: 180,
}
export const contentType = 'image/png'

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          background: '#0f172a',
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <svg 
          viewBox="0 0 100 100" 
          fill="none" 
          style={{ width: '80%', height: '80%' }}
        >
          <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" />
          <circle cx="50" cy="50" r="10" stroke="#ca8a04" strokeWidth="3" />
          <line x1="50" y1="50" x2="50" y2="28" stroke="#ca8a04" strokeWidth="8" strokeLinecap="round" transform="rotate(-60 50 50)" />
          <line x1="50" y1="50" x2="50" y2="18" stroke="#ca8a04" strokeWidth="6" strokeLinecap="round" transform="rotate(60 50 50)" />
          <circle cx="50" cy="50" r="5" fill="#ca8a04" />
          {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
            <g key={a} transform={`rotate(${a} 50 50)`}>
              <rect x="47" y="10" width="6" height="40" fill="#a91101" opacity="0.3" />
              <path d="M 42,5 L 58,5 L 56,15 L 44,15 Z" fill="#a91101" />
            </g>
          ))}
        </svg>
      </div>
    ),
    { ...size }
  )
}
