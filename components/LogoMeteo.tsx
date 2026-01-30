import React from 'react';

export function LogoMeteo({ className = "w-10 h-10" }: { className?: string }) {
  return (
    <svg 
      viewBox="0 0 100 100" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg" 
      className={className}
    >
      {/* Cercle Extérieur FIXÉ EN ROUGE ANDRINOPOLE (#a91101) */}
      <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
      
      {/* Thermomètre en OR MAT (#ca8a04) - Structure #72 */}
      <rect x="46" y="15" width="8" height="55" rx="4" stroke="#ca8a04" strokeWidth="1" />
      <rect x="48" y="20" width="4" height="50" fill="#ca8a04" />
      <circle cx="50" cy="72" r="8" fill="#ca8a04" />
      
      {/* Graduations dorées */}
      <g stroke="#ca8a04" strokeWidth="0.8">
        {[20, 25, 30, 35, 40, 45, 50, 55, 60].map(y => (
          <line key={y} x1="40" y1={y} x2="44" y2={y} />
        ))}
      </g>

      {/* Partie Roue Mulhouse (FIXÉE EN ROUGE #a91101) */}
      {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
        <g key={a} transform={`rotate(${a} 50 50)`}>
          <rect x="47" y="10" width="6" height="40" fill="#a91101" opacity="0.3" />
          <path d="M 42,5 L 58,5 L 56,15 L 44,15 Z" fill="#a91101" />
        </g>
      ))}
    </svg>
  );
}
