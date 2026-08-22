#!/usr/bin/env node

// Enregistrement des pharmacies de garde dans la base principale Turso
// (assocommercants, table pharmacies_garde) via l'API HTTP libSQL v2.
//
// Porté depuis assocommercants (scripts/pharmacies-save.ts +
// lib/pharmacies/save-pharmacies.ts) pour rapprocher le job du scraper
// déplacé ici. Même logique métier :
//  - payload à 1 pharmacie avec raw_content → ligne _RAW_SCRAPE_DATA_
//  - sinon upsert par (name, address normalisée, dateGarde)
//
// Usage : npx tsx scripts/pharmacies-save.ts <payload.json>
// Env : TURSO_DATABASE_URL (libsql://...), TURSO_AUTH_TOKEN ou DATABASE_AUTH_TOKEN

import fs from "fs"
import path from "path"

interface PharmacyInput {
  name: string
  address?: string | null
  phone?: string | null
  startTime?: string | null
  endTime?: string | null
  isNightGuard?: boolean
  isWeekend?: boolean
  raw_content?: unknown
}

interface SavePharmaciesResult {
  created: number
  updated: number
  errors: number
  rawDataSaved: boolean
}

const argsType = {
  str: (v: string | null | undefined) =>
    v == null ? { type: "null" as const } : { type: "text" as const, value: v },
  int: (v: number | null | undefined) =>
    v == null ? { type: "null" as const } : { type: "integer" as const, value: String(Math.trunc(v)) },
}

async function sql(
  urlBase: string,
  token: string,
  stmts: Array<{ sql: string; args: unknown[] }>
): Promise<Array<Record<string, { type: string; value: string }>[]> | null[]> {
  const resp = await fetch(`${urlBase}/v2/pipeline`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      requests: stmts.map((s) => ({
        type: "execute",
        stmt: { sql: s.sql, args: s.args },
      })),
    }),
  })
  if (!resp.ok) throw new Error(`Turso HTTP ${resp.status}: ${(await resp.text()).slice(0, 300)}`)
  const data = (await resp.json()) as {
    results: Array<
      | {
          type: "ok"
          response: { result: { cols: Array<{ name: string }>; rows: Array<Record<string, { type: string; value: string }>> } }
        }
      | { type: "error"; error: string }
    >
  }
  // L'API v2 renvoie les lignes comme tableaux [{type,value},...] : on les
  // transforme en objets nommés via les métadonnées de colonnes.
  return data.results.map((r) => {
    if (r.type !== "ok") throw new Error(`Turso SQL error: ${JSON.stringify(r)}`)
    const { cols, rows } = r.response.result
    return rows.map((row) =>
      Array.isArray(row)
        ? (Object.fromEntries(cols.map((c, i) => [c.name, row[i]])) as Record<string, { type: string; value: string }>)
        : row
    )
  })
}

async function main() {
  const filePath = process.argv[2]
  if (!filePath) {
    console.error("Usage: npx tsx scripts/pharmacies-save.ts <payload.json>")
    process.exit(1)
  }

  const rawUrl = (process.env.TURSO_DATABASE_URL || "").trim().replace(/^"|"$/g, "")
  const token = (
    process.env.TURSO_AUTH_TOKEN ||
    process.env.DATABASE_AUTH_TOKEN ||
    ""
  )
    .trim()
    .replace(/^"|"$/g, "")
  if (!rawUrl || !token) {
    console.error("TURSO_DATABASE_URL / TURSO_AUTH_TOKEN manquants")
    process.exit(1)
  }
  const urlBase = rawUrl.replace("libsql://", "https://").replace(/\/+$/, "")

  const payload = JSON.parse(fs.readFileSync(path.resolve(filePath), "utf-8"))
  const pharmacies: PharmacyInput[] = payload.pharmacies ?? []
  const codePostal: string = payload.code_postal || "68100"
  const villeInput: string = payload.ville || "MULHOUSE"
  const scrapeDate: string | undefined = payload.scrape_date

  console.log(`💊 Enregistrement de ${pharmacies.length} pharmacie(s)...`)

  // dateGarde = minuit UTC du jour de scrape — normalisation indispensable :
  // un calcul "minuit local" donnerait des valeurs différentes selon la TZ
  // d'exécution (CI UTC vs dev Europe/Paris) et casserait le dédoublonnage.
  const dateGarde = new Date()
  if (scrapeDate) {
    const d = new Date(scrapeDate)
    dateGarde.setUTCFullYear(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
  }
  dateGarde.setUTCHours(0, 0, 0, 0)

  const results: SavePharmaciesResult = {
    created: 0,
    updated: 0,
    errors: 0,
    rawDataSaved: false,
  }

  if (pharmacies.length === 1 && pharmacies[0].raw_content) {
    await sql(urlBase, token, [
      {
        sql: `INSERT INTO "pharmacies_garde"
                ("id","name","city","zipCode","dateGarde","rawData","scrapedAt","createdAt","updatedAt")
              VALUES (lower(hex(randomblob(16))),?1,?2,?3,?4,?5,?6,?6,?6)
              ON CONFLICT("name","city","dateGarde") DO UPDATE SET
                "rawData"=excluded."rawData", "scrapedAt"=excluded."scrapedAt",
                "updatedAt"=excluded."updatedAt"`,
        args: [
          "_RAW_SCRAPE_DATA_",
          villeInput,
          codePostal,
          dateGarde.toISOString(),
          JSON.stringify(pharmacies[0]),
          new Date().toISOString(),
        ].map((v) => ({ type: "text", value: v as string })),
      },
    ])
    results.rawDataSaved = true
    console.log("✅ Terminé")
    console.log(JSON.stringify(results, null, 2))
    return
  }

  for (const pharmacy of pharmacies) {
    let normalizedName = ""
    let normalizedCity = ""
    let finalZipCode = codePostal

    let branch = "none"
    let existingRowId: string | undefined
    try {
      const { name, address, phone, startTime, endTime, isNightGuard, isWeekend } = pharmacy
      if (!name) {
        results.errors++
        continue
      }

      normalizedName = name.trim()
      normalizedCity = villeInput.toUpperCase()
      const normalizedAddress = address?.trim() || ""

      if (normalizedAddress) {
        const addressParts = normalizedAddress.split(",")
        const lastPart = addressParts[addressParts.length - 1].trim()
        const match = lastPart.match(/(\d{5})\s+(.+)/)
        if (match) {
          finalZipCode = match[1]
          normalizedCity = match[2].toUpperCase()
        }
      }

      // Candidats par nom + jour (fenêtre ±26h), filtrage adresse en JS, et
      // comparaison par jour calendaire : tolère les écarts de format/fuseau
      // des anciennes lignes (ex. minuit local au lieu de minuit UTC).
      const rows = await sql(urlBase, token, [
        {
          sql: `SELECT "id","address","dateGarde" FROM "pharmacies_garde"
                WHERE "name" = ?1 AND "dateGarde" >= ?2 AND "dateGarde" <= ?3`,
          args: [
            argsType.str(normalizedName),
            argsType.str(new Date(dateGarde.getTime() - 26 * 3600 * 1000).toISOString()),
            argsType.str(new Date(dateGarde.getTime() + 26 * 3600 * 1000).toISOString()),
          ],
        },
      ])
      const sameDay = (iso: string) => {
        const t = Date.parse(iso)
        if (!Number.isFinite(t)) return false
        const a = new Date(t)
        const b = new Date(dateGarde.getTime())
        return a.getUTCFullYear() === b.getUTCFullYear() && a.getUTCMonth() === b.getUTCMonth() && a.getUTCDate() === b.getUTCDate()
      }
      const existing = (rows[0] || []).find((row) => {
        const addrOk =
          (row["address"]?.value ?? "") === normalizedAddress ||
          (!row["address"] && !normalizedAddress)
        return addrOk && sameDay(row["dateGarde"]?.value ?? "")
      })
      existingRowId = existing?.["id"]?.value
      branch = existingRowId ? "update" : "insert"
      if (existing) {
        await sql(urlBase, token, [
          {
            sql: `UPDATE "pharmacies_garde" SET
                    "address"=?1,"zipCode"=?2,"phone"=?3,"startTime"=?4,"endTime"=?5,
                    "isNightGuard"=?6,"isWeekend"=?7,"scrapedAt"=?8,"rawData"=?9,
                    "updatedAt"=?8
                  WHERE "id"=?10`,
            args: [
              argsType.str(normalizedAddress || null),
              argsType.str(finalZipCode),
              argsType.str(phone?.trim() || null),
              argsType.str(startTime || null),
              argsType.str(endTime || null),
              argsType.int(isNightGuard ? 1 : 0),
              argsType.int(isWeekend ? 1 : 0),
              { type: "text", value: new Date().toISOString() }, // scrapedAt + updatedAt
              { type: "text", value: JSON.stringify(pharmacy) },
              { type: "text", value: existing["id"].value },
            ],
          },
        ])
        results.updated++
      } else {
        await sql(urlBase, token, [
          {
            sql: `INSERT INTO "pharmacies_garde"
                    ("id","name","city","dateGarde",
                     "address","zipCode","phone","startTime","endTime",
                     "isNightGuard","isWeekend","scrapedAt","rawData",
                     "createdAt","updatedAt")
                  VALUES (lower(hex(randomblob(16))),?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?11,?11)`,
            args: [
              argsType.str(normalizedName),
              argsType.str(normalizedCity),
              { type: "text", value: dateGarde.toISOString() },
              argsType.str(normalizedAddress || null),
              argsType.str(finalZipCode),
              argsType.str(phone?.trim() || null),
              argsType.str(startTime || null),
              argsType.str(endTime || null),
              argsType.int(isNightGuard ? 1 : 0),
              argsType.int(isWeekend ? 1 : 0),
              { type: "text", value: new Date().toISOString() },
              { type: "text", value: JSON.stringify(pharmacy) },
            ],
          },
        ])
        results.created++
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      console.error("Erreur enregistrement pharmacie:", {
        name: normalizedName,
        city: normalizedCity,
        branch,
        existingRowId,
        error: message,
      })
      results.errors++
    }
  }

  console.log("✅ Terminé")
  console.log(JSON.stringify(results, null, 2))

  if (results.errors > 0 && results.created === 0 && results.updated === 0 && !results.rawDataSaved) {
    process.exit(1)
  }
}

main().catch((error) => {
  console.error("❌ Erreur:", error)
  process.exit(1)
})
