import { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: 'https://mulhouse-actu.vercel.app/',
      lastModified: new Date(),
      changeFrequency: 'always',
      priority: 1,
    },
  ]
}
