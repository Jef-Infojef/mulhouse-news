'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { ChevronLeft, FileText, Download, BookOpen } from 'lucide-react'
import Link from 'next/link'
import { Logo } from '@/components/Logo'

// Les PDF et les jaquettes sont servis depuis le site officiel M+ (mplusinfo.fr,
// page « Le Mag »). Les téléchargements passent par /mplus-mag/download/<fichier>
// qui redirige vers le PDF officiel ; les jaquettes sont des images externes
// (assets.mulhouse.omerloclients.com), autorisées par le CSP (« img-src https »).

// Jaquettes (couvertures) des numéros.
// - La plupart viennent de mplusinfo.fr (page « Le Mag ») : URLs externes
//   assets.mulhouse.omerloclients.com, autorisées par le CSP (« img-src https »).
// - Les numéros 29 → 33 n'ont pas de couverture distincte publiée sur le site :
//   on a extrait la vraie jaquette (1re page) de chaque PDF, hébergée en local
//   dans /public/mplus-mag/covers/ (chemin relatif → servi par Vercel).
const MPLUSINFO_COVER: Record<string, string> = {
  '36': 'c5f7a79e-b65c-4417-a0a0-6c20a23cd2ed.JPG',
  '35': '641858d4-ba84-4abf-88f9-521e6ded02ca.JPG',
  '34': 'b8900c7a-c46d-4732-b03c-f5563a06106e.JPG',
  '33': '/mplus-mag/covers/cover33.jpg',
  '32': '/mplus-mag/covers/cover32.jpg',
  '31': '/mplus-mag/covers/cover31.jpg',
  '30': '/mplus-mag/covers/cover30.jpg',
  '29': '/mplus-mag/covers/cover29.jpg',
  '28': 'd2366d1a-2ca0-4783-9d9a-e1e5d4a64390.jpg',
  '27': 'c71d501c-dc62-45a8-8bf8-a98538242d48.jpg',
  '26': 'ef96dc3a-4c83-4cef-b9aa-b8751eaa3484.jpg',
  '25': 'f2981791-14b7-4ec1-bc41-a388ef8e1310.jpg',
  '24': 'a53cad09-31b5-4ad0-8d20-20ab5e9ec812.jpg',
  '23': '21f76b16-8f45-4b84-a1a1-50aa3b04227d.jpg',
  '22': 'c76036d3-7bba-4bca-b009-ae750e54d0a9.jpg',
  '21': '02a8ca82-d2f9-4ffe-89b6-6c4dbea1e7ab.jpg',
  '20': '3b94ab11-ad20-40fb-afbe-a66c35d67a27.jpg',
  '19': '93a4f8ed-2036-42c6-b749-50755cd672d0.jpg',
  '18': 'c290c838-60a5-43bb-9189-d26304124712.jpg',
  '17': 'ec8c6633-b250-48b7-8af2-f42ab1db8b5d.jpg',
  '16': '8ccfddd8-9fde-4793-95f5-e6edc2c0d44c.jpg',
  '15': 'fcd1955e-4358-4d24-a0ac-41ebedf48052.jpg',
}

const SEASONS: Record<string, string> = {
  printemps: 'Printemps',
  ete: 'Été',
  automne: 'Automne',
  hiver: 'Hiver',
}

const MAGAZINES = [
  { num: 36, season: 'ete', year: 2026 },
  { num: 35, season: 'printemps', year: 2026 },
  { num: 34, season: 'hiver', year: 2025 },
  { num: 33, season: 'automne', year: 2025 },
  { num: 32, season: 'ete', year: 2025 },
  { num: 31, season: 'printemps', year: 2025 },
  { num: 30, season: 'hiver', year: 2024 },
  { num: 29, season: 'automne', year: 2024 },
  { num: 28, season: 'ete', year: 2024 },
  { num: 27, season: 'printemps', year: 2024 },
  { num: 26, season: 'hiver', year: 2023 },
  { num: 25, season: 'automne', year: 2023 },
  { num: 24, season: 'ete', year: 2023 },
  { num: 23, season: 'printemps', year: 2023 },
  { num: 22, season: 'hiver', year: 2022 },
  { num: 21, season: 'automne', year: 2022 },
  { num: 20, season: 'ete', year: 2022 },
  { num: 19, season: 'printemps', year: 2022 },
  { num: 18, season: 'hiver', year: 2021 },
  { num: 17, season: 'automne', year: 2021 },
  { num: 16, season: 'ete', year: 2021 },
  { num: 15, season: 'printemps', year: 2021 },
]

// Composant d'affichage d'une jaquette avec repli sur l'icône si l'image échoue.
function MagCover({ src, alt }: { src: string; alt: string }) {
  const [error, setError] = React.useState(false)
  if (error) {
    return (
      <FileText
        size={80}
        className="text-red-500/80 dark:text-red-400/60 group-hover:scale-110 transition-transform duration-300"
      />
    )
  }
  return (
    // <img> classique (pas next/image) : hôtes distants non autorisés dans ce projet.
    <img
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setError(true)}
      className="h-52 w-40 object-cover object-top rounded-lg shadow-lg ring-1 ring-black/10 dark:ring-white/10 group-hover:scale-105 transition-transform duration-300"
    />
  )
}

export default function MplusMagPage() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.05 }
    }
  }

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1 }
  }

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
      <nav className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-slate-600 dark:text-slate-400"
              >
                <ChevronLeft size={24} />
              </Link>
              <div className="flex items-center gap-2">
                <Logo />
                <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-red-600 to-amber-600 dark:from-red-400 dark:to-amber-400">
                  M+Mag Archives
                </span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="space-y-16"
        >
          <motion.div variants={itemVariants} className="text-center space-y-6 max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-medium text-sm mb-4">
              <BookOpen size={18} />
              <span>Archives</span>
            </div>
            <h1 className="text-4xl md:text-6xl font-extrabold text-slate-900 dark:text-white leading-tight">
              M+Mag
            </h1>
            <p className="text-lg md:text-xl text-slate-600 dark:text-slate-400 leading-relaxed">
              Retrouvez tous les numéros du magazine M+Mag en téléchargement gratuit.
              Des archives qui retracent l&apos;actualité et la vie de Mulhouse au fil des saisons.
            </p>
          </motion.div>

          <motion.section variants={itemVariants} className="space-y-8">
            <div className="flex items-center gap-3">
              <div className="h-8 w-1.5 bg-red-600 rounded-full"></div>
              <h2 className="text-3xl font-bold text-slate-900 dark:text-white">
                Tous les numéros
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {MAGAZINES.map((mag) => {
                const filename = `M_Mag_${mag.num}_${mag.season}_${mag.year}.pdf`
                const seasonLabel = SEASONS[mag.season] || mag.season
                const coverId = MPLUSINFO_COVER[String(mag.num)]
                const coverUrl = coverId
                  ? coverId.startsWith('/')
                    ? coverId
                    : `https://assets.mulhouse.omerloclients.com/assets/${coverId}`
                  : null

                return (
                  <motion.div
                    key={mag.num}
                    whileHover={{ y: -5 }}
                    className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col group"
                  >
                    <div className="bg-gradient-to-br from-red-50 to-amber-50 dark:from-red-950/40 dark:to-amber-950/40 p-8 flex items-center justify-center border-b border-slate-100 dark:border-slate-800">
                      <div className="relative">
                        {coverUrl ? (
                          <MagCover src={coverUrl} alt={`N°${mag.num} - ${seasonLabel} ${mag.year}`} />
                        ) : (
                          <FileText
                            size={80}
                            className="text-red-500/80 dark:text-red-400/60 group-hover:scale-110 transition-transform duration-300"
                          />
                        )}
                        <span className="absolute -top-2 -right-2 bg-red-600 text-white text-xs font-bold rounded-full w-8 h-8 flex items-center justify-center shadow-lg">
                          N°{mag.num}
                        </span>
                      </div>
                    </div>
                    <div className="p-5 space-y-3 flex flex-col flex-grow">
                      <div className="text-center space-y-1">
                        <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                          N°{mag.num} — {seasonLabel}
                        </h3>
                        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                          {mag.year}
                        </p>
                      </div>
                      <div className="flex-grow" />
                      <a
                        href={`/mplus-mag/download/${filename}`}
                        download
                        className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-700 text-white font-semibold text-sm transition-colors shadow-sm"
                      >
                        <Download size={16} />
                        Télécharger
                      </a>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </motion.section>

          <motion.div variants={itemVariants} className="text-center pt-12 border-t border-slate-200 dark:border-slate-800">
            <p className="text-slate-500 dark:text-slate-500 text-sm">
              © {new Date().getFullYear()} Mulhouse Actu — Archives M+Mag
            </p>
          </motion.div>
        </motion.div>
      </div>
    </main>
  )
}
