import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Mulhouse Actu - Actualités locales et infos en temps réel",
  description: "Suivez toute l'actualité de Mulhouse et sa région. Presse locale, faits divers, économie et culture regroupés sur une seule plateforme.",
  keywords: ["Mulhouse", "actualités", "infos", "Alsace", "presse locale", "faits divers", "Haut-Rhin"],
  authors: [{ name: "Mulhouse Actu" }],
  openGraph: {
    title: "Mulhouse Actu - Toute l'actualité de Mulhouse",
    description: "Le meilleur de la presse locale mulhousienne réuni au même endroit.",
    url: "https://mulhouse-actu.vercel.app/",
    siteName: "Mulhouse Actu",
    locale: "fr_FR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Mulhouse Actu - Actualités locales",
    description: "Toute l'actualité de Mulhouse en temps réel.",
  },
  metadataBase: new URL("https://mulhouse-actu.vercel.app/"),
  alternates: {
    canonical: "/",
  },
  viewport: "width=device-width, initial-scale=1",
  robots: "index, follow",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
