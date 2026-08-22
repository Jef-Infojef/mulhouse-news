#!/usr/bin/env node

/**
 * Weather History Backfill Script for GitHub Actions
 * Runs directly in CI/CD, no Vercel timeout issues
 * Fetches weather data from Open-Meteo Archive API
 */

import { PrismaClient } from "@prisma/client"

const databaseUrl = process.env.DATABASE_URL
if (!databaseUrl) {
  throw new Error("DATABASE_URL must be defined")
}

const prisma = new PrismaClient({
  log: [
    { level: "error", emit: "stdout" },
    { level: "warn", emit: "stdout" },
  ],
} as any)

const DELAY_BETWEEN_REQUESTS = 1000 // 1s between requests to respect API rate limits
const MAX_RETRIES = 3 // Retry up to 3 times on timeout
const FETCH_TIMEOUT = 30000 // 30s timeout for fetch

async function fetchWeatherData(
  lat: number,
  lon: number,
  year: number,
  targetMonth: number,
  targetDay: number,
  attempt: number = 1
): Promise<{ tempMax: number; tempMin: number; weatherCode: number } | null> {
  const dateStr = `${year}-${String(targetMonth).padStart(2, "0")}-${String(targetDay).padStart(2, "0")}`
  const url = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}&start_date=${dateStr}&end_date=${dateStr}&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=auto`

  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT)

    const res = await fetch(url, { signal: controller.signal })
    clearTimeout(timeoutId)

    if (!res.ok) {
      console.warn(`[WEATHER-BACKFILL] Archive API returned ${res.status} for year ${year}`)
      return null
    }

    const data = await res.json()
    if (data.daily?.time?.[0]) {
      return {
        tempMax: Math.round(data.daily.temperature_2m_max[0]),
        tempMin: Math.round(data.daily.temperature_2m_min[0]),
        weatherCode: data.daily.weather_code[0] || 0,
      }
    }
    return null
  } catch (err) {
    const isTimeout = err instanceof Error && (err.name === "AbortError" || err.message.includes("timeout"))

    if (isTimeout && attempt < MAX_RETRIES) {
      console.log(`[WEATHER-BACKFILL] Timeout for year ${year}, retrying (attempt ${attempt + 1}/${MAX_RETRIES})...`)
      await new Promise((r) => setTimeout(r, 2000))
      return fetchWeatherData(lat, lon, year, targetMonth, targetDay, attempt + 1)
    }

    console.error(
      `[WEATHER-BACKFILL] Error fetching year ${year}:`,
      err instanceof Error ? err.message : String(err)
    )
    return null
  }
}

async function backfillWeatherHistory() {
  const startTime = Date.now()

  try {
    const location = process.env.WEATHER_LOCATION || "Mulhouse"
    console.log(`[WEATHER-BACKFILL] Starting full backfill for ${location}`)

    let lat = 47.7467
    let lon = 7.3389

    try {
      const geoRes = await fetch(
        `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(location)}&count=1&language=fr&format=json`
      )
      if (geoRes.ok) {
        const geoData = await geoRes.json()
        if (geoData.results?.[0]) {
          lat = geoData.results[0].latitude
          lon = geoData.results[0].longitude
          console.log(`[WEATHER-BACKFILL] Using coordinates: ${lat}, ${lon}`)
        }
      }
    } catch (err) {
      console.error("[WEATHER-BACKFILL] Error fetching coordinates:", err)
    }

    const delayDays = 10
    const targetDate = new Date()
    targetDate.setDate(targetDate.getDate() - delayDays)

    const targetMonth = targetDate.getMonth() + 1
    const targetDay = targetDate.getDate()
    const targetYear = targetDate.getFullYear()

    console.log(`[WEATHER-BACKFILL] Backfilling for ${targetDay}/${targetMonth} (History from 1940 to ${targetYear})`)

    let successCount = 0
    let skippedCount = 0
    let errorCount = 0

    const yearsToFetch = []
    for (let y = 1940; y <= targetYear; y++) {
      yearsToFetch.push(y)
    }

    for (let i = 0; i < yearsToFetch.length; i++) {
      const year = yearsToFetch[i]

      if (i % 10 === 0) {
        console.log(`[WEATHER-BACKFILL] Progress: ${i}/${yearsToFetch.length} years...`)
      }

      try {
        const existing = await prisma.weatherHistory.findUnique({
          where: {
            location_day_month_year: {
              location: location.toLowerCase(),
              day: targetDay,
              month: targetMonth,
              year,
            },
          },
        })

        if (existing) {
          console.log(`  ✓ ${year}: Already in database (skipped)`)
          skippedCount++
        } else {
          const data = await fetchWeatherData(lat, lon, year, targetMonth, targetDay)

          if (data) {
            await prisma.weatherHistory.create({
              data: {
                location: location.toLowerCase(),
                day: targetDay,
                month: targetMonth,
                year,
                tempMax: data.tempMax,
                tempMin: data.tempMin,
                weatherCode: data.weatherCode,
              },
            })
            console.log(`  ✓ ${year}: Added (Max=${data.tempMax}°C, Min=${data.tempMin}°C)`)
            successCount++
          } else {
            console.log(`  ✗ ${year}: No data from API`)
            errorCount++
          }
        }
      } catch (err) {
        console.error(`  ✗ ${year}: Database error - ${err instanceof Error ? err.message : String(err)}`)
        errorCount++
      }

      if (i < yearsToFetch.length - 1) {
        await new Promise((r) => setTimeout(r, DELAY_BETWEEN_REQUESTS))
      }
    }

    const duration = Math.round((Date.now() - startTime) / 1000)
    console.log(`[WEATHER-BACKFILL] ✓ Complete in ${duration}s`)
    console.log(`[WEATHER-BACKFILL] Results: ${successCount} added, ${skippedCount} skipped, ${errorCount} errors`)

    if (successCount === 0 && skippedCount === 0 && errorCount > 0) {
      throw new Error(`All ${errorCount} operations failed — check database credentials (DATABASE_URL)`)
    }

    return {
      success: true,
      location,
      day: targetDay,
      month: targetMonth,
      added: successCount,
      skipped: skippedCount,
      errors: errorCount,
      durationSeconds: duration,
    }
  } catch (err) {
    console.error("[WEATHER-BACKFILL] Critical error:", err)
    throw err
  } finally {
    await prisma.$disconnect()
  }
}

backfillWeatherHistory()
  .then((result) => {
    console.log("[WEATHER-BACKFILL] Final result:", result)
    process.exit(0)
  })
  .catch((err) => {
    console.error("[WEATHER-BACKFILL] Fatal error:", err)
    process.exit(1)
  })