'use client'

import React from 'react'
import { ChevronLeft, Copy, Check, Activity } from 'lucide-react'
import Link from 'next/link'
import { renderToStaticMarkup } from 'react-dom/server'

const variations = [
  {
    id: 'classic',
    name: 'Classique Fidèle',
    description: 'Respecte scrupuleusement les proportions du blason historique.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <rect x="46" y="15" width="8" height="70" fill="currentColor" />
        <rect x="15" y="46" width="70" height="8" fill="currentColor" />
        <circle cx="50" cy="50" r="32" stroke="currentColor" strokeWidth="8" fill="none" />
        <rect x="38" y="38" width="24" height="24" fill="currentColor" />
        <rect x="46" y="46" width="8" height="8" fill="white" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <path key={a} d="M 42,8 L 58,8 L 56,25 L 44,25 Z" fill="currentColor" transform={`rotate(${a} 50 50)`} />
        ))}
      </svg>
    )
  },
  {
    id: 'minimal',
    name: 'Minimaliste Flat',
    description: 'Une version épurée, sans contours, idéale pour les petits formats.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="28" fill="currentColor" />
        <circle cx="50" cy="50" r="18" fill="white" />
        <rect x="47" y="20" width="6" height="60" fill="currentColor" />
        <rect x="20" y="47" width="60" height="6" fill="currentColor" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <rect key={a} x="45" y="2" width="10" height="12" rx="1" fill="currentColor" transform={`rotate(${a} 50 50)`} />
        ))}
      </svg>
    )
  },
  {
    id: 'tech',
    name: 'Tech & Moderne',
    description: 'Lignes fines et moyeu hexagonal pour un aspect technologique.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="35" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" />
        <path d="M 50,20 L 50,80 M 20,50 L 80,50" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
        <path d="M 50,35 L 63,42.5 L 63,57.5 L 50,65 L 37,57.5 L 37,42.5 Z" fill="currentColor" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <rect key={a} x="48" y="5" width="4" height="15" fill="currentColor" transform={`rotate(${a} 50 50)`} />
        ))}
      </svg>
    )
  },
  {
    id: 'dynamic',
    name: 'Actu Dynamique',
    description: 'Effet de rotation et rayons asymétriques pour symboliser le mouvement.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="30" stroke="currentColor" strokeWidth="10" strokeDasharray="140 60" />
        {[0, 90, 180, 270].map((a) => (
          <rect key={a} x="46" y="20" width="8" height="30" fill="currentColor" transform={`rotate(${a} 50 50)`} />
        ))}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <path key={a} d="M 45,5 L 55,5 L 52,20 L 48,20 Z" fill="currentColor" opacity="0.8" transform={`rotate(${a+10} 50 50)`} />
        ))}
      </svg>
    )
  },
  {
    id: 'outline',
    name: 'Lignes Fines',
    description: 'Élégant et léger, construit uniquement avec des contours.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="30" stroke="currentColor" strokeWidth="2" />
        <circle cx="50" cy="50" r="8" stroke="currentColor" strokeWidth="2" />
        <path d="M 50,15 L 50,85 M 15,50 L 85,50" stroke="currentColor" strokeWidth="2" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <path key={a} d="M 44,5 L 56,5 L 56,15 L 44,15 Z" stroke="currentColor" strokeWidth="2" transform={`rotate(${a} 50 50)`} />
        ))}
      </svg>
    )
  },
  {
    id: 'geometric',
    name: 'Géométrique Abstrait',
    description: 'Déconstruction des formes pour un look artistique.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <rect x="45" y="45" width="10" height="10" fill="currentColor" transform="rotate(45 50 50)" />
        {[0, 90, 180, 270].map((a) => (
          <rect key={a} x="48" y="10" width="4" height="30" fill="currentColor" transform={`rotate(${a} 50 50)`} />
        ))}
        {[45, 135, 225, 315].map((a) => (
          <circle key={a} cx="50" cy="15" r="5" fill="currentColor" transform={`rotate(${a} 50 50)`} />
        ))}
        <circle cx="50" cy="50" r="40" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      </svg>
    )
  },
  {
    id: 'bold',
    name: 'Impact Brut',
    description: 'Rayons massifs et aubes larges pour une forte présence visuelle.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <rect x="42" y="15" width="16" height="70" fill="currentColor" />
        <rect x="15" y="42" width="70" height="16" fill="currentColor" />
        <circle cx="50" cy="50" r="35" stroke="currentColor" strokeWidth="12" fill="none" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <rect key={a} x="40" y="0" width="20" height="15" fill="currentColor" transform={`rotate(${a} 50 50)`} />
        ))}
      </svg>
    )
  },
  {
    id: 'eco',
    name: 'Eco Nature',
    description: 'Aubes arrondies rappelant des pétales pour un aspect plus doux.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="25" stroke="currentColor" strokeWidth="6" strokeLinecap="round" />
        <circle cx="50" cy="50" r="6" fill="currentColor" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <rect key={a} x="47" y="25" width="6" height="25" rx="3" fill="currentColor" transform={`rotate(${a} 50 50)`} />
        ))}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <circle key={a} cx="50" cy="8" r="7" fill="currentColor" transform={`rotate(${a} 50 50)`} />
        ))}
      </svg>
    )
  },
  {
    id: 'cyber',
    name: 'Cyber Grid',
    description: 'Inspiré par les circuits imprimés et le numérique.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <rect x="48" y="10" width="4" height="80" fill="currentColor" />
        <rect x="10" y="48" width="80" height="4" fill="currentColor" />
        <rect x="40" y="40" width="20" height="20" stroke="currentColor" strokeWidth="2" />
        <rect x="46" y="46" width="8" height="8" fill="currentColor" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <g key={a} transform={`rotate(${a} 50 50)`}>
            <rect x="45" y="2" width="10" height="4" fill="currentColor" />
            <rect x="49" y="6" width="2" height="10" fill="currentColor" />
          </g>
        ))}
      </svg>
    )
  },
  {
    id: 'gradient',
    name: 'Gradient Flow',
    description: 'Utilise des variations d\'opacité pour un effet de profondeur.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <defs>
          <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0.5" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="35" stroke="url(#grad)" strokeWidth="8" />
        <path d="M 50,15 L 50,85 M 15,50 L 85,50" stroke="currentColor" strokeWidth="6" opacity="0.6" />
        <circle cx="50" cy="50" r="4" fill="currentColor" />
        <circle cx="50" cy="50" r="1.5" fill="white" />
      </svg>
    )
  },
  {
    id: 'chronograph',
    name: 'Chrono Mulhouse',
    description: 'Style chronographe sportif avec des compteurs circulaires.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="45" stroke="currentColor" strokeWidth="4" />
        <circle cx="50" cy="32" r="12" stroke="currentColor" strokeWidth="1" opacity="0.5" />
        <circle cx="32" cy="55" r="12" stroke="currentColor" strokeWidth="1" opacity="0.5" />
        <circle cx="68" cy="55" r="12" stroke="currentColor" strokeWidth="1" opacity="0.5" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <rect key={a} x="48" y="2" width="4" height="8" fill="currentColor" transform={`rotate(${a} 50 50)`} />
        ))}
        <path d="M 50,50 L 50,20" stroke="red" strokeWidth="1" transform="rotate(120 50 50)" />
        <circle cx="50" cy="50" r="3" fill="currentColor" />
      </svg>
    )
  },
  {
    id: 'skeleton',
    name: 'Squelette Mécanique (#12)',
    description: 'La roue comme engrenage principal d\'un mouvement horloger complexe.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="currentColor" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="10" stroke="currentColor" strokeWidth="2" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <g key={a} transform={`rotate(${a} 50 50)`}>
            <rect x="47" y="10" width="6" height="40" fill="currentColor" opacity="0.3" />
            <path d="M 42,5 L 58,5 L 56,15 L 44,15 Z" fill="currentColor" />
          </g>
        ))}
        <line x1="50" y1="50" x2="70" y2="50" stroke="currentColor" strokeWidth="3" transform="rotate(-30 50 50)" />
        <line x1="50" y1="50" x2="50" y2="25" stroke="currentColor" strokeWidth="2" transform="rotate(45 50 50)" />
      </svg>
    )
  }
]

// Fonction utilitaire pour générer les variations strictes du #12 (Squelette)
const generateSkeletonVariations = (clockColor: string, name: string, id: string) => {
  return {
    id: `skeleton-pure-${id}`,
    name: name,
    description: `Structure #12 exacte. Roue Rouge (#a91101), Horlogerie ${name}.`,
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        {/* Partie Horlogerie (Cercles et Aiguilles) */}
        <circle cx="50" cy="50" r="32" stroke={clockColor} strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="10" stroke={clockColor} strokeWidth="2" />
        <line x1="50" y1="50" x2="70" y2="50" stroke={clockColor} strokeWidth="3" transform="rotate(-30 50 50)" />
        <line x1="50" y1="50" x2="50" y2="25" stroke={clockColor} strokeWidth="2" transform="rotate(45 50 50)" />
        
        {/* Partie Roue Mulhouse (FIXEE EN ROUGE #a91101) */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <g key={a} transform={`rotate(${a} 50 50)`}>
            <rect x="47" y="10" width="6" height="40" fill="#a91101" opacity="0.3" />
            <path d="M 42,5 L 58,5 L 56,15 L 44,15 Z" fill="#a91101" />
          </g>
        ))}
      </svg>
    )
  }
}

const bicolorVariations = [
  generateSkeletonVariations("#475569", "Slate Gray", "slate"),
  generateSkeletonVariations("#1f2937", "Anthracite", "dark"),
  generateSkeletonVariations("#ca8a04", "Gold Mat", "gold"),
  generateSkeletonVariations("#94a3b8", "Silver Steel", "silver"),
  generateSkeletonVariations("#1e3a8a", "Navy Blue", "navy"),
  generateSkeletonVariations("#92400e", "Antique Bronze", "bronze"),
  generateSkeletonVariations("#065f46", "Emerald Green", "emerald"),
  generateSkeletonVariations("#000000", "Deep Black", "black"),
  generateSkeletonVariations("#cbd5e1", "Light Chrome", "chrome"),
  generateSkeletonVariations("#f8fafc", "Ice White", "white"),
]

// Fonction pour générer les variations avec CERCLE EXTÉRIEUR ROUGE
const generateRedRingVariations = (innerColor: string, name: string, id: string) => {
  return {
    id: `skeleton-redring-${id}`,
    name: name,
    description: `Structure #12. Roue & Cercle Ext. Rouges (#a91101), Aiguilles ${name}.`,
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        {/* Cercle Extérieur FIXÉ EN ROUGE */}
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        
        {/* Partie Variable (Cercle intérieur et Aiguilles) */}
        <circle cx="50" cy="50" r="10" stroke={innerColor} strokeWidth="2" />
        <line x1="50" y1="50" x2="70" y2="50" stroke={innerColor} strokeWidth="3" transform="rotate(-30 50 50)" />
        <line x1="50" y1="50" x2="50" y2="25" stroke={innerColor} strokeWidth="2" transform="rotate(45 50 50)" />
        
        {/* Partie Roue Mulhouse (FIXÉE EN ROUGE #a91101) */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <g key={a} transform={`rotate(${a} 50 50)`}>
            <rect x="47" y="10" width="6" height="40" fill="#a91101" opacity="0.3" />
            <path d="M 42,5 L 58,5 L 56,15 L 44,15 Z" fill="#a91101" />
          </g>
        ))}
      </svg>
    )
  }
}

const redRingVariations = [
  generateRedRingVariations("#475569", "Slate Gray", "slate"),
  generateRedRingVariations("#1f2937", "Anthracite", "dark"),
  generateRedRingVariations("#ca8a04", "Gold Mat", "gold"),
  generateRedRingVariations("#94a3b8", "Silver Steel", "silver"),
  generateRedRingVariations("#1e3a8a", "Navy Blue", "navy"),
  generateRedRingVariations("#92400e", "Antique Bronze", "bronze"),
  generateRedRingVariations("#000000", "Deep Black", "black"),
  generateRedRingVariations("#64748b", "Steel", "steel"),
  generateRedRingVariations("#334155", "Cool Grey", "cool"),
  generateRedRingVariations("#ffffff", "Pure White", "white"),
]

// Fonction pour générer les variations 10h10 (Standard Horloger)
const generateTenTenVariations = (innerColor: string, name: string, id: string) => {
  return {
    id: `skeleton-tenten-${id}`,
    name: `10:10 ${name}`,
    description: `Structure #12. Roue & Cercle Ext. Rouges. Aiguilles ${name} positionnées à 10h10.`,
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        {/* Cercle Extérieur FIXÉ EN ROUGE */}
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        
        {/* Cercle intérieur */}
        <circle cx="50" cy="50" r="10" stroke={innerColor} strokeWidth="2" />

        {/* Aiguille des HEURES (courte) à 10h */}
        <line x1="50" y1="50" x2="50" y2="32" stroke={innerColor} strokeWidth="3" strokeLinecap="round" transform="rotate(-60 50 50)" />
        
        {/* Aiguille des MINUTES (longue) à 10min */}
        <line x1="50" y1="50" x2="50" y2="22" stroke={innerColor} strokeWidth="2" strokeLinecap="round" transform="rotate(60 50 50)" />
        
        {/* Partie Roue Mulhouse (FIXÉE EN ROUGE #a91101) */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <g key={a} transform={`rotate(${a} 50 50)`}>
            <rect x="47" y="10" width="6" height="40" fill="#a91101" opacity="0.3" />
            <path d="M 42,5 L 58,5 L 56,15 L 44,15 Z" fill="#a91101" />
          </g>
        ))}
      </svg>
    )
  }
}

const tenTenVariations = [
  generateTenTenVariations("#92400e", "Antique Bronze", "bronze"),
  generateTenTenVariations("#1f2937", "Anthracite", "dark"),
  generateTenTenVariations("#ca8a04", "Gold Mat", "gold"),
  generateTenTenVariations("#475569", "Slate Gray", "slate"),
  generateTenTenVariations("#94a3b8", "Silver", "silver"),
  generateTenTenVariations("#1e3a8a", "Navy Blue", "navy"),
  generateTenTenVariations("#000000", "Deep Black", "black"),
  generateTenTenVariations("#64748b", "Steel", "steel"),
  generateTenTenVariations("#ffffff", "Ice White", "white"),
  generateTenTenVariations("#065f46", "Emerald", "emerald"),
]

// Fonction pour générer les variations GOLD MATE avec AIGUILLES RENFORCÉES
const generateGoldBoldVariations = (strokeWidth: number, name: string, id: string) => {
  return {
    id: `skeleton-goldbold-${id}`,
    name: name,
    description: `Structure #12. Or Mat & Roue Rouge. Aiguilles renforcées (${strokeWidth}px) à 10h10.`,
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        {/* Cercle Extérieur FIXÉ EN ROUGE */}
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        
        {/* Cercle intérieur en Or Mat */}
        <circle cx="50" cy="50" r="10" stroke="#ca8a04" strokeWidth="2.5" />

        {/* Aiguille des HEURES (très épaisse) à 10h */}
        <line x1="50" y1="50" x2="50" y2="30" stroke="#ca8a04" strokeWidth={strokeWidth + 2} strokeLinecap="round" transform="rotate(-60 50 50)" />
        
        {/* Aiguille des MINUTES (épaisse) à 10min */}
        <line x1="50" y1="50" x2="50" y2="20" stroke="#ca8a04" strokeWidth={strokeWidth} strokeLinecap="round" transform="rotate(60 50 50)" />
        
        {/* Moyeu central renforcé */}
        <circle cx="50" cy="50" r="4" fill="#ca8a04" />

        {/* Partie Roue Mulhouse (FIXÉE EN ROUGE #a91101) */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <g key={a} transform={`rotate(${a} 50 50)`}>
            <rect x="47" y="10" width="6" height="40" fill="#a91101" opacity="0.3" />
            <path d="M 42,5 L 58,5 L 56,15 L 44,15 Z" fill="#a91101" />
          </g>
        ))}
      </svg>
    )
  }
}

const goldBoldVariations = [
  generateGoldBoldVariations(3, "Gold Bold 3px", "3px"),
  generateGoldBoldVariations(4, "Gold Bold 4px", "4px"),
  generateGoldBoldVariations(5, "Gold Bold 5px", "5px"),
  generateGoldBoldVariations(6, "Gold Ultra 6px", "6px"),
  // On décline avec d'autres couleurs mais toujours en BOLD
  {
    id: `skeleton-slatebold`,
    name: "Slate Bold",
    description: `Structure #12. Slate & Roue Rouge. Aiguilles 4px à 10h10.`,
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="10" stroke="#475569" strokeWidth="3" />
        <line x1="50" y1="50" x2="50" y2="28" stroke="#475569" strokeWidth="6" strokeLinecap="round" transform="rotate(-60 50 50)" />
        <line x1="50" y1="50" x2="50" y2="18" stroke="#475569" strokeWidth="4" strokeLinecap="round" transform="rotate(60 50 50)" />
        <circle cx="50" cy="50" r="5" fill="#475569" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <g key={a} transform={`rotate(${a} 50 50)`}>
            <rect x="47" y="10" width="6" height="40" fill="#a91101" opacity="0.3" />
            <path d="M 42,5 L 58,5 L 56,15 L 44,15 Z" fill="#a91101" />
          </g>
        ))}
      </svg>
    )
  },
  {
    id: `skeleton-blackbold`,
    name: "Black Bold",
    description: `Structure #12. Black & Roue Rouge. Aiguilles 4px à 10h10.`,
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="10" stroke="#000000" strokeWidth="3" />
        <line x1="50" y1="50" x2="50" y2="28" stroke="#000000" strokeWidth="6" strokeLinecap="round" transform="rotate(-60 50 50)" />
        <line x1="50" y1="50" x2="50" y2="18" stroke="#000000" strokeWidth="4" strokeLinecap="round" transform="rotate(60 50 50)" />
        <circle cx="50" cy="50" r="5" fill="#000000" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <g key={a} transform={`rotate(${a} 50 50)`}>
            <rect x="47" y="10" width="6" height="40" fill="#a91101" opacity="0.3" />
            <path d="M 42,5 L 58,5 L 56,15 L 44,15 Z" fill="#a91101" />
          </g>
        ))}
      </svg>
    )
  }
]

const allVariations = [...variations, ...bicolorVariations, ...redRingVariations, ...tenTenVariations, ...goldBoldVariations]

export default function LogoVariationsPage() {
  const [copiedId, setCopiedId] = React.useState<string | null>(null)

  const copyToClipboard = (id: string, Component: any) => {
    const svgString = renderToStaticMarkup(<Component width="512" height="512" />)
    const finalSvg = svgString.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')
    navigator.clipboard.writeText(finalSvg)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-12">
          <Link href="/admin/logs" className="text-blue-400 hover:text-blue-300 flex items-center gap-2 mb-6 transition-colors">
            <ChevronLeft size={20} /> Retour aux logs
          </Link>
          <h1 className="text-4xl font-black text-white mb-4">Exploration du Logo</h1>
          <p className="text-gray-400 text-lg">Variations basées sur le design Squelette (#12) avec roue rouge fixe.</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {allVariations.map((v, index) => (
            <div key={v.id} className="bg-gray-800 border border-gray-700 rounded-3xl p-6 flex flex-col items-center group hover:border-red-500/50 transition-all hover:shadow-2xl hover:shadow-red-900/10 relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-gray-700/50 text-gray-400 text-xs font-black px-4 py-2 rounded-bl-2xl group-hover:bg-red-600 group-hover:text-white transition-colors">
                #{index + 1}
              </div>
              <div className="w-40 h-40 mb-8 text-red-600 group-hover:scale-110 transition-transform duration-500">
                <v.svg className="w-full h-full" />
              </div>
              <div className="text-center w-full">
                <h3 className="text-xl font-bold text-white mb-2">{v.name}</h3>
                <p className="text-sm text-gray-400 mb-6 min-h-[40px]">{v.description}</p>
                <div className="flex gap-2">
                  <button 
                    onClick={() => copyToClipboard(v.id, v.svg)}
                    className="flex-1 bg-gray-700 hover:bg-gray-600 text-white text-xs font-bold py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
                  >
                    {copiedId === v.id ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                    Copier SVG REEL
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        <footer className="mt-20 text-center border-t border-gray-800 pt-10">
          <p className="text-gray-500 text-sm italic">Inspiration basée sur le blason officiel de la ville de Mulhouse.</p>
        </footer>
      </div>
    </div>
  )
}
