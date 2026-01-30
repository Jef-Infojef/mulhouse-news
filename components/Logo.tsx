import React from 'react';

export function Logo({ className = "w-10 h-10" }: { className?: string }) {
  return (
    <svg 
      viewBox="0 0 100 100" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg" 
      className={className}
    >
      {/* Cercle Extérieur FIXÉ EN ROUGE (#a91101) */}
      <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
      
      {/* Cercle intérieur en OR MAT (#ca8a04) */}
      <circle cx="50" cy="50" r="10" stroke="#ca8a04" strokeWidth="2.5" />

      {/* Aiguilles en OR MAT (#ca8a04) - ULTRA BOLD (6px) */}
      {/* Aiguille des HEURES (courte et très épaisse) à 10h */}
      <line x1="50" y1="50" x2="50" y2="30" stroke="#ca8a04" strokeWidth="8" strokeLinecap="round" transform="rotate(-60 50 50)" />
      
      {/* Aiguille des MINUTES (longue et épaisse) à 10min */}
      <line x1="50" y1="50" x2="50" y2="20" stroke="#ca8a04" strokeWidth="6" strokeLinecap="round" transform="rotate(60 50 50)" />
      
      {/* Moyeu central (Point) en OR MAT */}
      <circle cx="50" cy="50" r="4" fill="#ca8a04" />

      {/* Partie Roue Mulhouse (FIXÉE EN ROUGE #a91101) */}
      {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
        <g key={a} transform={`rotate(${a} 50 50)`}>
          {/* Rayons internes opaques à 0.3 */}
          <rect x="47" y="10" width="6" height="40" fill="#a91101" opacity="0.3" />
          {/* Pales (Aubes) de la roue */}
          <path d="M 42,5 L 58,5 L 56,15 L 44,15 Z" fill="#a91101" />
        </g>
      ))}
    </svg>
  );
}
