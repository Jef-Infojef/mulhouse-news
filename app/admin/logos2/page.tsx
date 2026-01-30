'use client'

import React from 'react'
import { ChevronLeft, Copy, Check } from 'lucide-react'
import Link from 'next/link'
import { renderToStaticMarkup } from 'react-dom/server'

const variations = [
  {
    id: 'weather-sun',
    name: 'Mulhouse Ensoleillé',
    description: 'Le moyeu central devient un soleil rayonnant.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="12" fill="#f59e0b" /> {/* Soleil central */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map(a => (
          <line key={a} x1="50" y1="50" x2={50 + 18 * Math.cos(a * Math.PI / 180)} y2={50 + 18 * Math.sin(a * Math.PI / 180)} stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" />
        ))}
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
    id: 'weather-cloud',
    name: 'Mulhouse Nuageux',
    description: 'Un nuage stylisé occupe le centre de la roue.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M35,55 Q35,45 45,45 Q45,35 55,35 Q65,35 65,45 Q75,45 75,55 Q75,65 65,65 L45,65 Q35,65 35,55 Z" fill="#94a3b8" />
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
    id: 'weather-rain',
    name: 'Mulhouse Pluvieux',
    description: 'Des gouttes de pluie tombent à travers les rayons.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <g stroke="#3b82f6" strokeWidth="2" strokeLinecap="round">
          <line x1="45" y1="40" x2="42" y2="50" />
          <line x1="55" y1="45" x2="52" y2="55" />
          <line x1="48" y1="55" x2="45" y2="65" />
        </g>
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
    id: 'weather-storm',
    name: 'Mulhouse Orageux',
    description: 'Un éclair dynamique brise la symétrie centrale.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M55,30 L40,55 L50,55 L45,75 L60,45 L50,45 Z" fill="#eab308" />
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
    id: 'weather-snow',
    name: 'Mulhouse Hivernal',
    description: 'Un flocon de neige géométrique au cœur de la roue.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <g stroke="#7dd3fc" strokeWidth="2" strokeLinecap="round">
          {[0, 60, 120, 180, 240, 300].map(a => (
            <g key={a} transform={`rotate(${a} 50 50)`}>
              <line x1="50" y1="50" x2="50" y2="35" />
              <path d="M46,40 L50,37 L54,40" fill="none" />
            </g>
          ))}
        </g>
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
    id: 'weather-wind',
    name: 'Mulhouse Venteux',
    description: 'Des lignes de souffle traversent le mécanisme.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <g stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" fill="none">
          <path d="M30,45 Q45,40 50,50 T70,45" />
          <path d="M35,55 Q50,50 55,60 T75,55" opacity="0.6" />
        </g>
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
    id: 'weather-thermometer',
    name: 'Mulhouse Température',
    description: 'Le centre devient une jauge de température.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="47" y="30" width="6" height="30" rx="3" fill="#ef4444" />
        <circle cx="50" cy="60" r="8" fill="#ef4444" />
        <rect x="49" y="35" width="2" height="15" fill="white" opacity="0.5" />
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
    id: 'weather-rainbow',
    name: 'Mulhouse Arc-en-ciel',
    description: 'Une arche colorée au-dessus de la croix centrale.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M30,60 A25,25 0 0,1 70,60" stroke="#ef4444" strokeWidth="2" fill="none" />
        <path d="M33,60 A22,22 0 0,1 67,60" stroke="#f59e0b" strokeWidth="2" fill="none" />
        <path d="M36,60 A19,19 0 0,1 64,60" stroke="#10b981" strokeWidth="2" fill="none" />
        <path d="M39,60 A16,16 0 0,1 61,60" stroke="#3b82f6" strokeWidth="2" fill="none" />
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
    id: 'weather-moon',
    name: 'Mulhouse Nuit',
    description: 'Un croissant de lune serein pour la météo nocturne.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M60,40 A15,15 0 1,0 60,70 A12,12 0 1,1 60,40 Z" fill="#fde047" />
        <circle cx="40" cy="35" r="1" fill="white" />
        <circle cx="45" cy="45" r="0.5" fill="white" />
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
    id: 'weather-eclipse',
    name: 'Mulhouse Éclipse',
    description: 'Jeu d\'ombre et de lumière sur le cercle intérieur.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="15" fill="#1e293b" />
        <circle cx="55" cy="45" r="15" fill="#f59e0b" clipPath="circle(15 at 50 50)" />
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
    id: 'weather-sunrise',
    name: 'Mulhouse Aurore',
    description: 'Le soleil émerge du bas de la roue.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M30,65 A20,20 0 0,1 70,65 L30,65 Z" fill="#fdba74" />
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
    id: 'weather-partly-cloudy',
    name: 'Mulhouse Éclaircies',
    description: 'Le soleil joue à cache-cache avec un nuage.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="45" cy="45" r="10" fill="#f59e0b" />
        <path d="M45,60 Q45,52 53,52 Q53,45 60,45 Q68,45 68,52 Q75,52 75,60 Q75,68 68,68 L53,68 Q45,68 45,60 Z" fill="#cbd5e1" />
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
    id: 'weather-heavy-rain',
    name: 'Mulhouse Déluge',
    description: 'Pluie battante symbolisée par de nombreuses stries.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <g stroke="#2563eb" strokeWidth="1.5" strokeLinecap="round">
          {[35, 42, 50, 58, 65].map(x => (
            <line key={x} x1={x} y1="35" x2={x-5} y2="65" />
          ))}
        </g>
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
    id: 'weather-tornado',
    name: 'Mulhouse Tornade',
    description: 'Un tourbillon de vent centré dans le mécanisme.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M35,35 Q65,35 50,50 Q35,65 65,65" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" />
        <path d="M40,42 Q60,42 50,50 Q40,58 60,58" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" opacity="0.6" />
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
    id: 'weather-stars',
    name: 'Mulhouse Nuit Étoilée',
    description: 'Des étoiles scintillantes au centre de la roue.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M50,35 L52,45 L60,45 L53,50 L55,60 L50,55 L45,60 L47,50 L40,45 L48,45 Z" fill="#fde047" />
        <circle cx="35" cy="40" r="1" fill="white" />
        <circle cx="65" cy="55" r="1.5" fill="white" />
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
    id: 'weather-fog',
    name: 'Mulhouse Brouillard',
    description: 'Lignes horizontales estompant le moyeu.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <g stroke="#cbd5e1" strokeWidth="3" strokeLinecap="round">
          <line x1="35" y1="40" x2="65" y2="40" />
          <line x1="30" y1="50" x2="70" y2="50" opacity="0.7" />
          <line x1="35" y1="60" x2="65" y2="60" opacity="0.4" />
        </g>
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
    id: 'weather-hail',
    name: 'Mulhouse Grêle',
    description: 'Des billes de glace percutent le mécanisme.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="45" cy="40" r="3" fill="#e2e8f0" />
        <circle cx="55" cy="48" r="3" fill="#e2e8f0" />
        <circle cx="48" cy="58" r="3" fill="#e2e8f0" />
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
    id: 'weather-humidity',
    name: 'Mulhouse Humidité',
    description: 'Une goutte d\'eau pure suspendue au centre.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M50,35 Q62,55 50,65 Q38,55 50,35 Z" fill="#60a5fa" />
        <circle cx="48" cy="45" r="1.5" fill="white" opacity="0.5" />
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
    id: 'weather-solar-rays',
    name: 'Mulhouse Canicule',
    description: 'Rayonnements solaires intenses dépassant les rayons.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        {[0, 22, 45, 67, 90, 112, 135, 157, 180, 202, 225, 247, 270, 292, 315, 337].map(a => (
          <line key={a} x1="50" y1="50" x2={50 + 25 * Math.cos(a * Math.PI / 180)} y2={50 + 25 * Math.sin(a * Math.PI / 180)} stroke="#ef4444" strokeWidth="1" strokeDasharray="2 2" />
        ))}
        <circle cx="50" cy="50" r="10" fill="#f59e0b" />
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
    id: 'weather-cyclone',
    name: 'Mulhouse Cyclone',
    description: 'Une spirale météo dynamique.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M50,35 A15,15 0 0,1 65,50 A15,15 0 0,1 50,65 A15,15 0 0,1 35,50 A15,15 0 0,1 50,35" stroke="#94a3b8" strokeWidth="4" strokeDasharray="10 5" />
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
    id: 'weather-cold-wave',
    name: 'Mulhouse Grand Froid',
    description: 'Des cristaux de givre bleutés sur l\'horloge.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M40,50 L50,40 L60,50 L50,60 Z" stroke="#0ea5e9" strokeWidth="2" />
        <line x1="35" y1="35" x2="65" y2="65" stroke="#0ea5e9" strokeWidth="1" />
        <line x1="65" y1="35" x2="35" y2="65" stroke="#0ea5e9" strokeWidth="1" />
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
    id: 'weather-heat-wave',
    name: 'Mulhouse Canicule 2',
    description: 'Cercle central vibrant de chaleur.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="12" stroke="#ef4444" strokeWidth="4" strokeDasharray="2 2" />
        <circle cx="50" cy="50" r="6" fill="#f59e0b" />
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
    id: 'weather-barometer',
    name: 'Mulhouse Baromètre',
    description: 'Une aiguille de précision pour la pression atmosphérique.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="15" stroke="#94a3b8" strokeWidth="1" />
        <line x1="50" y1="50" x2="50" y2="38" stroke="#1e293b" strokeWidth="2" strokeLinecap="round" transform="rotate(-120 50 50)" />
        <text x="50" y="55" textAnchor="middle" fill="#1e293b" fontSize="4" fontWeight="bold">hPa</text>
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
    id: 'weather-cloud-rain',
    name: 'Mulhouse Giboulées',
    description: 'Nuage avec pluie intégrée au centre.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <g transform="translate(-2 -2)">
          <path d="M35,50 Q35,42 43,42 Q43,35 50,35 Q57,35 57,42 Q65,42 65,50 Q65,58 57,58 L43,58 Q35,58 35,50 Z" fill="#94a3b8" />
          <line x1="45" y1="60" x2="43" y2="65" stroke="#3b82f6" strokeWidth="1.5" />
          <line x1="55" y1="60" x2="53" y2="65" stroke="#3b82f6" strokeWidth="1.5" />
        </g>
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
    id: 'weather-lightning-cloud',
    name: 'Mulhouse Électrique',
    description: 'Éclair sortant d\'un nuage sombre.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M35,45 Q35,37 43,37 Q43,30 50,30 Q57,30 57,37 Q65,37 65,45 Q65,53 57,53 L43,53 Q35,53 35,45 Z" fill="#475569" />
        <path d="M52,50 L45,65 L50,65 L48,75" stroke="#fbbf24" strokeWidth="2" fill="none" />
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
    id: 'weather-moon-stars',
    name: 'Mulhouse Minuit',
    description: 'Lune et étoiles pour une météo dégagée de nuit.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M55,40 A12,12 0 1,0 55,65 A10,10 0 1,1 55,40 Z" fill="#fde047" />
        <circle cx="40" cy="45" r="1" fill="white" />
        <circle cx="65" cy="40" r="0.8" fill="white" />
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
    id: 'weather-haze',
    name: 'Mulhouse Brume',
    description: 'Le soleil voilé par une fine brume.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="45" r="10" fill="#f59e0b" opacity="0.5" />
        <g stroke="#94a3b8" strokeWidth="2" strokeLinecap="round">
          <line x1="35" y1="55" x2="65" y2="55" />
          <line x1="30" y1="62" x2="70" y2="62" />
        </g>
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
    id: 'weather-frost',
    name: 'Mulhouse Gelée',
    description: 'Une structure de glace hexagonale.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M50,35 L63,42.5 L63,57.5 L50,65 L37,57.5 L37,42.5 Z" stroke="#7dd3fc" strokeWidth="2" />
        <circle cx="50" cy="50" r="4" fill="#7dd3fc" />
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
    id: 'weather-sun-shower',
    name: 'Mulhouse Pluie-Soleil',
    description: 'Le soleil brille sous la pluie.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="45" cy="40" r="8" fill="#f59e0b" />
        <g stroke="#3b82f6" strokeWidth="2" strokeLinecap="round">
          <line x1="55" y1="50" x2="52" y2="60" />
          <line x1="65" y1="50" x2="62" y2="60" />
        </g>
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
    id: 'sun-var-bright',
    name: 'Soleil Éclatant',
    description: 'Variation du #1 avec un jaune plus vif et des rayons plus longs.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="10" fill="#fbbf24" />
        {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map(a => (
          <line key={a} x1="50" y1="50" x2={50 + 22 * Math.cos(a * Math.PI / 180)} y2={50 + 22 * Math.sin(a * Math.PI / 180)} stroke="#fbbf24" strokeWidth="1.5" />
        ))}
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
    id: 'sun-var-heraldic',
    name: 'Soleil Héraldique',
    description: 'Un soleil avec un visage stylisé, rappelant les anciens blasons.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="14" fill="#f59e0b" />
        <circle cx="46" cy="48" r="1.5" fill="#78350f" />
        <circle cx="54" cy="48" r="1.5" fill="#78350f" />
        <path d="M45,54 Q50,58 55,54" stroke="#78350f" strokeWidth="1" fill="none" strokeLinecap="round" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map(a => (
          <path key={a} d="M50,32 L53,22 L47,22 Z" fill="#f59e0b" transform={`rotate(${a} 50 50)`} />
        ))}
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
    id: 'sun-var-geometric',
    name: 'Soleil Géométrique',
    description: 'Rayons formés par des triangles précis pour un look moderne.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="10" fill="#fde047" />
        {[...Array(16)].map((_, i) => (
          <path key={i} d="M50,38 L52,25 L48,22 Z" fill="#fde047" transform={`rotate(${i * 22.5} 50 50)`} />
        ))}
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
    id: 'sun-var-halo',
    name: 'Soleil à Halo',
    description: 'Effet de diffusion de lumière autour du cœur du soleil.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="18" fill="#f59e0b" opacity="0.2" />
        <circle cx="50" cy="50" r="12" fill="#f59e0b" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map(a => (
          <line key={a} x1="50" y1="30" x2="50" y2="20" stroke="#f59e0b" strokeWidth="3" strokeLinecap="round" transform={`rotate(${a} 50 50)`} />
        ))}
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
    id: 'sun-var-corona',
    name: 'Couronne Solaire',
    description: 'Focus sur la périphérie du soleil avec des rayons fins.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="15" stroke="#fde047" strokeWidth="1" strokeDasharray="1 2" />
        {[...Array(24)].map((_, i) => (
          <line key={i} x1="50" y1="35" x2="50" y2="22" stroke="#fde047" strokeWidth="0.5" transform={`rotate(${i * 15} 50 50)`} />
        ))}
        <circle cx="50" cy="50" r="8" fill="#fde047" />
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
    id: 'sun-var-flame',
    name: 'Soleil Flamboyant',
    description: 'Rayons ondulés suggérant la chaleur intense.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="10" fill="#ef4444" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map(a => (
          <path key={a} d="M50,40 Q55,30 50,20 Q45,30 50,40" fill="#f59e0b" transform={`rotate(${a} 50 50)`} />
        ))}
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
    id: 'sun-var-minimal',
    name: 'Soleil Minimal',
    description: 'Juste un cercle parfait et des points cardinaux.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="12" stroke="#f59e0b" strokeWidth="3" />
        {[0, 90, 180, 270].map(a => (
          <circle key={a} cx={50 + 20 * Math.cos(a * Math.PI / 180)} cy={50 + 20 * Math.sin(a * Math.PI / 180)} r="2" fill="#f59e0b" />
        ))}
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
    id: 'sun-var-eclipse-ring',
    name: 'Soleil Annulaire',
    description: 'Une éclipse totale où seule la couronne est visible en blanc-or.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="14" stroke="#fef08a" strokeWidth="2" />
        <circle cx="50" cy="50" r="13" fill="#0f172a" />
        {[...Array(32)].map((_, i) => (
          <line key={i} x1="50" y1="36" x2="50" y2="34" stroke="#fef08a" strokeWidth="0.5" transform={`rotate(${i * 11.25} 50 50)`} />
        ))}
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
    id: 'sun-var-zenith',
    name: 'Soleil au Zénith',
    description: 'Le soleil positionné tout en haut du mécanisme.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="25" r="10" fill="#f59e0b" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map(a => (
          <line key={a} x1="50" y1="25" x2={50 + 15 * Math.cos(a * Math.PI / 180)} y2={25 + 15 * Math.sin(a * Math.PI / 180)} stroke="#f59e0b" strokeWidth="1" />
        ))}
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
    id: 'sun-var-abstract',
    name: 'Soleil Abstrait',
    description: 'Composition de cercles et de lignes pour un soleil design.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="8" fill="#f59e0b" />
        <circle cx="50" cy="50" r="15" stroke="#f59e0b" strokeWidth="1" strokeDasharray="4 4" />
        {[0, 90, 180, 270].map(a => (
          <rect key={a} x="49" y="30" width="2" height="10" fill="#f59e0b" transform={`rotate(${a} 50 50)`} />
        ))}
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
    id: 'sun-cloud-1',
    name: 'Soleil & Grand Nuage',
    description: 'Un large nuage passant devant un soleil éclatant.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="60" cy="40" r="10" fill="#fbbf24" />
        <path d="M30,60 Q30,50 40,50 Q40,40 52,40 Q62,40 62,50 Q75,50 75,60 Q75,70 62,70 L40,70 Q30,70 30,60 Z" fill="#94a3b8" />
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
    id: 'sun-cloud-2',
    name: 'Rayons à travers Nuages',
    description: 'Les rayons du soleil percent derrière un nuage central.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <g opacity="0.8">
          {[0, 45, 90, 135, 180, 225, 270, 315].map(a => (
            <line key={a} x1="50" y1="50" x2={50 + 20 * Math.cos(a * Math.PI / 180)} y2={50 + 20 * Math.sin(a * Math.PI / 180)} stroke="#f59e0b" strokeWidth="3" strokeLinecap="round" />
          ))}
        </g>
        <path d="M35,55 Q35,45 45,45 Q45,35 55,35 Q65,35 65,45 Q75,45 75,55 Q75,65 65,65 L45,65 Q35,65 35,55 Z" fill="#cbd5e1" />
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
    id: 'sun-cloud-3',
    name: 'Ciel Variable',
    description: 'Alternance de petits nuages et d\'un soleil central.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="10" fill="#f59e0b" />
        <path d="M25,45 Q25,40 30,40 Q30,35 35,35 Q40,35 40,40 Q45,40 45,45 Q45,50 40,50 L30,50 Q25,50 25,45 Z" fill="#cbd5e1" opacity="0.7" />
        <path d="M60,65 Q60,60 65,60 Q65,55 70,55 Q75,55 75,60 Q80,60 80,65 Q80,70 75,70 L65,70 Q60,70 60,65 Z" fill="#cbd5e1" opacity="0.7" />
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
    id: 'sun-cloud-4',
    name: 'Bords Nuageux',
    description: 'Le soleil au centre avec des nuages en périphérie.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="12" fill="#f59e0b" />
        <g opacity="0.5">
          <path d="M15,50 Q15,45 20,45 T30,50" stroke="#94a3b8" strokeWidth="2" fill="none" />
          <path d="M70,50 Q70,45 75,45 T85,50" stroke="#94a3b8" strokeWidth="2" fill="none" />
        </g>
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
    id: 'sun-cloud-5',
    name: 'Horizon Variable',
    description: 'Soleil se couchant (ou se levant) derrière une barre de nuages.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="45" r="15" fill="#f59e0b" />
        <rect x="25" y="55" width="50" height="10" rx="5" fill="#475569" />
        <rect x="35" y="50" width="30" height="8" rx="4" fill="#475569" opacity="0.8" />
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
    id: 'sun-cloud-6',
    name: 'Nuage de Chaleur',
    description: 'Effet de brume de chaleur autour d\'un soleil et nuage.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="40" cy="45" r="12" stroke="#f59e0b" strokeWidth="1" strokeDasharray="2 2" />
        <circle cx="40" cy="45" r="8" fill="#f59e0b" />
        <path d="M50,55 Q50,48 58,48 Q58,42 65,42 Q72,42 72,48 Q78,48 78,55 Q78,62 72,62 L58,62 Q50,62 50,55 Z" fill="#cbd5e1" />
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
    id: 'sun-cloud-7',
    name: 'Équilibre Variable',
    description: 'Composition symétrique soleil et nuage.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M25,50 A12,12 0 1,1 50,50" stroke="#f59e0b" strokeWidth="4" strokeLinecap="round" />
        <path d="M50,50 A12,12 0 1,0 75,50" stroke="#94a3b8" strokeWidth="4" strokeLinecap="round" />
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
    id: 'sun-cloud-8',
    name: 'Nuage en Rayons',
    description: 'Les rayons du soleil intègrent des formes nuageuses.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="10" fill="#fde047" />
        <g opacity="0.6">
          <circle cx="35" cy="35" r="5" fill="#cbd5e1" />
          <circle cx="65" cy="35" r="4" fill="#cbd5e1" />
          <circle cx="50" cy="70" r="6" fill="#cbd5e1" />
        </g>
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
    id: 'sun-cloud-9',
    name: 'Minimal Variable',
    description: 'Style icône moderne épuré.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="42" cy="42" r="8" fill="#f59e0b" />
        <path d="M45,55 L65,55" stroke="#94a3b8" strokeWidth="4" strokeLinecap="round" />
        <path d="M50,48 L60,48" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" opacity="0.7" />
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
    id: 'sun-cloud-10',
    name: 'Soleil Couchant Nuageux',
    description: 'Un soleil orange sombre derrière des nuages de fin de journée.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="55" r="12" fill="#ea580c" />
        <path d="M30,50 L70,50" stroke="#1e293b" strokeWidth="2" strokeDasharray="4 2" />
        <path d="M35,45 Q50,40 65,45" stroke="#475569" strokeWidth="3" strokeLinecap="round" opacity="0.6" />
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
    id: 'temp-cloud-1',
    name: 'Température & Nuage Bas',
    description: 'Le thermomètre surplombé par un nuage sombre.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M35,35 Q35,28 43,28 Q43,22 50,22 Q57,22 57,28 Q65,28 65,35 Q65,42 57,42 L43,42 Q35,42 35,35 Z" fill="#94a3b8" />
        <rect x="47" y="40" width="6" height="20" rx="3" fill="#ef4444" />
        <circle cx="50" cy="65" r="8" fill="#ef4444" />
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
    id: 'temp-cloud-2',
    name: 'Température & Ciel Gris',
    description: 'Deux nuages entourant le thermomètre central.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="47" y="30" width="6" height="30" rx="3" fill="#ef4444" />
        <circle cx="50" cy="60" r="8" fill="#ef4444" />
        <path d="M25,40 Q25,35 30,35 T40,40" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" opacity="0.6" />
        <path d="M60,40 Q70,35 75,40" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" opacity="0.6" />
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
    id: 'temp-cloud-3',
    name: 'Froid & Brume',
    description: 'Thermomètre bleu (froid) sous une brume épaisse.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="47" y="45" width="6" height="15" rx="3" fill="#3b82f6" />
        <circle cx="50" cy="65" r="8" fill="#3b82f6" />
        <g stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round">
          <line x1="30" y1="25" x2="70" y2="25" />
          <line x1="35" y1="32" x2="65" y2="32" opacity="0.7" />
          <line x1="40" y1="39" x2="60" y2="39" opacity="0.4" />
        </g>
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
    id: 'temp-cloud-4',
    name: 'Chaleur & Cumulus',
    description: 'Thermomètre haut sous un petit nuage blanc.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="47" y="25" width="6" height="35" rx="3" fill="#dc2626" />
        <circle cx="50" cy="65" r="8" fill="#dc2626" />
        <path d="M60,30 Q60,25 65,25 Q65,20 70,20 Q75,20 75,25 Q80,25 80,30 L60,30 Z" fill="white" opacity="0.8" />
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
    id: 'temp-cloud-5',
    name: 'Tempête de Neige',
    description: 'Thermomètre très bas entouré de flocons et nuages.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="47" y="55" width="6" height="10" rx="3" fill="#0ea5e9" />
        <circle cx="50" cy="70" r="8" fill="#0ea5e9" />
        <circle cx="35" cy="35" r="2" fill="#7dd3fc" />
        <circle cx="65" cy="40" r="1.5" fill="#7dd3fc" />
        <circle cx="50" cy="30" r="2.5" fill="#7dd3fc" />
        <path d="M30,45 Q40,40 50,45 T70,45" stroke="#cbd5e1" strokeWidth="2" fill="none" opacity="0.5" />
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
    id: 'temp-cloud-6',
    name: 'Nuage Pluvieux & Temp.',
    description: 'Le thermomètre semble sous la pluie d\'un nuage.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M35,30 Q35,22 43,22 Q43,15 50,15 Q57,15 57,22 Q65,22 65,30 Q65,38 57,38 L43,38 Q35,38 35,30 Z" fill="#475569" />
        <rect x="47" y="45" width="6" height="20" rx="3" fill="#f97316" />
        <circle cx="50" cy="70" r="8" fill="#f97316" />
        <line x1="40" y1="42" x2="38" y2="48" stroke="#3b82f6" strokeWidth="1" />
        <line x1="60" y1="42" x2="58" y2="48" stroke="#3b82f6" strokeWidth="1" />
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
    id: 'temp-cloud-7',
    name: 'Ciel Menaçant',
    description: 'Thermomètre entouré par un nuage d\'orage sombre.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="15" fill="#1e293b" opacity="0.1" />
        <rect x="47" y="35" width="6" height="25" rx="3" fill="#ea580c" />
        <circle cx="50" cy="65" r="8" fill="#ea580c" />
        <path d="M30,35 L45,35 Q50,25 55,35 L70,35 Q75,45 65,55 L35,55 Q25,45 30,35 Z" fill="#334155" />
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
    id: 'temp-cloud-8',
    name: 'Brouillard Givrant',
    description: 'Le thermomètre bleu dans une atmosphère vaporeuse.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="47" y="40" width="6" height="20" rx="3" fill="#60a5fa" />
        <circle cx="50" cy="65" r="8" fill="#60a5fa" />
        <ellipse cx="50" cy="35" rx="25" ry="10" fill="#cbd5e1" opacity="0.4" />
        <ellipse cx="50" cy="45" rx="20" ry="8" fill="#cbd5e1" opacity="0.3" />
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
    id: 'temp-cloud-9',
    name: 'Éclaircies Thermiques',
    description: 'Le soleil et un nuage au-dessus du thermomètre.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="40" cy="25" r="8" fill="#f59e0b" />
        <path d="M45,35 Q45,28 53,28 Q53,22 60,22 Q68,22 68,28 Q75,28 75,35 Q75,42 68,42 L53,42 Q45,42 45,35 Z" fill="#cbd5e1" />
        <rect x="47" y="45" width="6" height="20" rx="3" fill="#fbbf24" />
        <circle cx="50" cy="70" r="8" fill="#fbbf24" />
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
    id: 'temp-cloud-10',
    name: 'Douceur Printanière',
    description: 'Thermomètre modéré sous des nuages légers.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="47" y="40" width="6" height="25" rx="3" fill="#10b981" />
        <circle cx="50" cy="70" r="8" fill="#10b981" />
        <path d="M30,30 Q40,25 50,30 T70,30" stroke="#94a3b8" strokeWidth="1.5" fill="none" opacity="0.4" />
        <path d="M35,38 Q45,33 55,38 T75,38" stroke="#94a3b8" strokeWidth="1.5" fill="none" opacity="0.4" />
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
    id: 'temp-large-1',
    name: 'Mega Thermomètre Froid',
    description: 'Un thermomètre imposant sur tout l\'axe central, indiquant un froid glacial.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="46" y="20" width="8" height="55" rx="4" fill="#1e293b" opacity="0.2" />
        <rect x="48" y="55" width="4" height="15" rx="2" fill="#3b82f6" />
        <circle cx="50" cy="72" r="10" fill="#3b82f6" />
        <circle cx="50" cy="72" r="4" fill="white" opacity="0.3" />
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
    id: 'temp-large-2',
    name: 'Mega Thermomètre Chaud',
    description: 'Le mercure monte haut dans ce design vertical dominant.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="46" y="20" width="8" height="55" rx="4" fill="#1e293b" opacity="0.2" />
        <rect x="48" y="25" width="4" height="45" rx="2" fill="#ef4444" />
        <circle cx="50" cy="72" r="10" fill="#ef4444" />
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
    id: 'temp-large-3',
    name: 'Thermomètre de Précision',
    description: 'Design élancé avec des graduations visibles.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="48" y="20" width="4" height="50" fill="#ef4444" opacity="0.8" />
        <circle cx="50" cy="75" r="8" fill="#ef4444" />
        {[30, 40, 50, 60].map(y => (
          <line key={y} x1="53" y1={y} x2="56" y2={y} stroke="#ef4444" strokeWidth="1" />
        ))}
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
    id: 'temp-large-4',
    name: 'Thermomètre Hivernal XXL',
    description: 'Dominance du bleu sur un grand thermomètre central.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="45" y="15" width="10" height="60" rx="5" stroke="#60a5fa" strokeWidth="2" />
        <rect x="48" y="50" width="4" height="20" fill="#60a5fa" />
        <circle cx="50" cy="72" r="10" fill="#60a5fa" />
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
    id: 'temp-large-5',
    name: 'Impact Thermique',
    description: 'Un thermomètre massif et opaque qui traverse toute la roue.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="44" y="15" width="12" height="55" rx="6" fill="#1e293b" opacity="0.1" />
        <rect x="47" y="25" width="6" height="45" rx="3" fill="#f97316" />
        <circle cx="50" cy="75" r="12" fill="#f97316" />
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
    id: 'temp-large-6',
    name: 'Thermomètre & Soleil Duo',
    description: 'Grand thermomètre associé à un soleil éclatant.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="25" cy="25" r="8" fill="#f59e0b" />
        <rect x="47" y="20" width="6" height="45" rx="3" fill="#ef4444" />
        <circle cx="50" cy="70" r="10" fill="#ef4444" />
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
    id: 'temp-large-7',
    name: 'Thermomètre Sous la Neige',
    description: 'Grande jauge bleue dans un univers hivernal.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="47" y="30" width="6" height="40" rx="3" fill="#0ea5e9" />
        <circle cx="50" cy="75" r="10" fill="#0ea5e9" />
        <path d="M25,25 L35,25 M65,25 L75,25" stroke="#7dd3fc" strokeWidth="2" opacity="0.5" />
        <circle cx="30" cy="20" r="1.5" fill="#7dd3fc" />
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
    id: 'temp-large-8',
    name: 'Minimalist Mega Temp',
    description: 'Lignes épurées pour un grand thermomètre moderne.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M50,20 L50,65" stroke="#ef4444" strokeWidth="6" strokeLinecap="round" />
        <circle cx="50" cy="75" r="10" stroke="#ef4444" strokeWidth="4" />
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
    id: 'temp-large-9',
    name: 'Double Jauge XXL',
    description: 'Thermomètre avec double graduation imposante.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="46" y="15" width="8" height="55" rx="4" fill="#cbd5e1" />
        <rect x="48" y="25" width="4" height="45" fill="#f97316" />
        <circle cx="50" cy="72" r="10" fill="#f97316" />
        <g stroke="#1e293b" strokeWidth="0.5">
          {[20, 30, 40, 50, 60].map(y => (
            <line key={y} x1="42" y1={y} x2="45" y2={y} />
          ))}
        </g>
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
    id: 'temp-large-10',
    name: 'Thermomètre Vertical Pur',
    description: 'Ligne de mercure rouge traversant verticalement toute la roue.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <line x1="50" y1="15" x2="50" y2="70" stroke="#dc2626" strokeWidth="8" strokeLinecap="round" />
        <circle cx="50" cy="75" r="12" fill="#dc2626" />
        <circle cx="50" cy="75" r="4" fill="white" opacity="0.2" />
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
    id: 'gold-temp-1',
    name: 'Double Jauge Or Mat',
    description: 'Structure #69 avec les couleurs Or du logo principal.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="46" y="15" width="8" height="55" rx="4" fill="#ca8a04" opacity="0.2" />
        <rect x="48" y="25" width="4" height="45" fill="#ca8a04" />
        <circle cx="50" cy="72" r="10" fill="#ca8a04" />
        <g stroke="#1e293b" strokeWidth="0.5">
          {[20, 30, 40, 50, 60].map(y => (
            <line key={y} x1="42" y1={y} x2="45" y2={y} />
          ))}
        </g>
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
    id: 'gold-temp-2',
    name: 'Or Mat & Soleil',
    description: 'Le thermomètre or surmonté d\'un petit soleil assorti.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="22" r="6" fill="#ca8a04" />
        <rect x="46" y="30" width="8" height="40" rx="4" fill="#ca8a04" opacity="0.2" />
        <rect x="48" y="35" width="4" height="35" fill="#ca8a04" />
        <circle cx="50" cy="72" r="10" fill="#ca8a04" />
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
    id: 'gold-temp-3',
    name: 'Or Mat Précision XXL',
    description: 'Double graduation dorée très marquée.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="46" y="15" width="8" height="55" rx="4" stroke="#ca8a04" strokeWidth="1" />
        <rect x="48" y="20" width="4" height="50" fill="#ca8a04" />
        <circle cx="50" cy="72" r="8" fill="#ca8a04" />
        <g stroke="#ca8a04" strokeWidth="0.8">
          {[20, 25, 30, 35, 40, 45, 50, 55, 60].map(y => (
            <line key={y} x1="40" y1={y} x2="44" y2={y} />
          ))}
        </g>
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
    id: 'gold-temp-4',
    name: 'Or Mat Minimal Jauge',
    description: 'Structure épurée avec moyeu doré.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <line x1="50" y1="20" x2="50" y2="65" stroke="#ca8a04" strokeWidth="6" strokeLinecap="round" />
        <circle cx="50" cy="72" r="10" stroke="#ca8a04" strokeWidth="3" />
        <circle cx="50" cy="72" r="4" fill="#ca8a04" />
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
    id: 'gold-temp-5',
    name: 'Double Colonne Or',
    description: 'Deux thermomètres dorés symétriques.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="42" y="25" width="4" height="40" rx="2" fill="#ca8a04" opacity="0.4" />
        <rect x="54" y="25" width="4" height="40" rx="2" fill="#ca8a04" opacity="0.4" />
        <circle cx="50" cy="50" r="12" stroke="#ca8a04" strokeWidth="2" strokeDasharray="2 2" />
        <circle cx="50" cy="50" r="6" fill="#ca8a04" />
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
    id: 'gold-temp-6',
    name: 'Moyeu Solaire Or',
    description: 'Le thermomètre XXL fusionné avec un moyeu rayonnant.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="47" y="15" width="6" height="55" fill="#ca8a04" />
        <circle cx="50" cy="50" r="12" fill="#ca8a04" stroke="#ffffff" strokeWidth="2" />
        {[0, 90, 180, 270].map(a => (
          <line key={a} x1="50" y1="50" x2={50 + 18 * Math.cos(a * Math.PI / 180)} y2={50 + 18 * Math.sin(a * Math.PI / 180)} stroke="#ca8a04" strokeWidth="2" />
        ))}
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
    id: 'gold-temp-7',
    name: 'Cadran Thermique Or',
    description: 'Thermomètre XXL sur un cadran de montre doré.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <circle cx="50" cy="50" r="20" stroke="#ca8a04" strokeWidth="1" opacity="0.3" />
        <rect x="48" y="20" width="4" height="50" rx="2" fill="#ca8a04" />
        <circle cx="50" cy="72" r="8" fill="#ca8a04" />
        <line x1="50" y1="50" x2="65" y2="35" stroke="#ca8a04" strokeWidth="2" strokeLinecap="round" />
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
    id: 'gold-temp-8',
    name: 'Thermomètre Industrial Or',
    description: 'Look robuste avec rivets dorés.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <rect x="45" y="15" width="10" height="60" rx="2" stroke="#ca8a04" strokeWidth="2" />
        <circle cx="50" cy="22" r="2" fill="#ca8a04" />
        <circle cx="50" cy="68" r="6" fill="#ca8a04" />
        <rect x="48" y="28" width="4" height="35" fill="#ca8a04" opacity="0.6" />
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
    id: 'gold-temp-9',
    name: 'Mercury Or Mat',
    description: 'Effet de remplissage liquide doré.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <path d="M47,20 L53,20 L53,65 A3,3 0 0,1 50,68 A3,3 0 0,1 47,65 Z" fill="#ca8a04" opacity="0.3" />
        <path d="M47,45 L53,45 L53,65 A3,3 0 0,1 50,68 A3,3 0 0,1 47,65 Z" fill="#ca8a04" />
        <circle cx="50" cy="75" r="10" fill="#ca8a04" />
        <circle cx="48" cy="72" r="2" fill="white" opacity="0.4" />
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
    id: 'gold-temp-10',
    name: 'Thermomètre Royal Or',
    description: 'Design élancé et prestigieux en Or Mat.',
    svg: (props: any) => (
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
        <circle cx="50" cy="50" r="32" stroke="#a91101" strokeWidth="6" strokeDasharray="2 1" />
        <line x1="50" y1="15" x2="50" y2="70" stroke="#ca8a04" strokeWidth="8" strokeLinecap="round" />
        <circle cx="50" cy="75" r="12" fill="#ca8a04" />
        <circle cx="50" cy="75" r="4" fill="white" opacity="0.2" />
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

export default function LogoWeatherPage() {
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
          <h1 className="text-4xl font-black text-white mb-4">Logo Météo Mulhouse</h1>
          <p className="text-gray-400 text-lg">La roue de Mulhouse fusionnée avec les éléments du ciel.</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {variations.map((v, index) => (
            <div key={v.id} className="bg-gray-800 border border-gray-700 rounded-3xl p-6 flex flex-col items-center group hover:border-red-500/50 transition-all hover:shadow-2xl hover:shadow-red-900/10 relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-gray-700/50 text-gray-400 text-xs font-black px-4 py-2 rounded-bl-2xl group-hover:bg-red-600 group-hover:text-white transition-colors">
                #{index + 1}
              </div>
              <div className="w-48 h-48 mb-8 group-hover:scale-110 transition-transform duration-500">
                <v.svg className="w-full h-full" />
              </div>
              <div className="text-center w-full">
                <h3 className="text-xl font-bold text-white mb-2">{v.name}</h3>
                <p className="text-sm text-gray-400 mb-6 min-h-[40px]">{v.description}</p>
                <button 
                  onClick={() => copyToClipboard(v.id, v.svg)}
                  className="w-full bg-gray-700 hover:bg-gray-600 text-white text-xs font-bold py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  {copiedId === v.id ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                  Copier SVG
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
