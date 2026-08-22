# Backfill du contenu des articles lalsace.fr d'archive vers Convex PROD.
# Charge les identifiants prod depuis MulhouseGPT puis lance le scraper.
#
#   powershell -File scripts\run-content-backfill-prod.ps1            # run complet
#   powershell -File scripts\run-content-backfill-prod.ps1 --limit 20 # run test

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScraperArgs
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Get-Content C:\dev\MulhouseGPT\.env.local |
    Where-Object { $_ -match '^(CONVEX_DEPLOY_KEY|NEXT_PUBLIC_CONVEX_URL)=' } |
    ForEach-Object {
        $p = $_ -split '=', 2
        Set-Item "env:$($p[0])" $p[1]
    }

Write-Host "[*] Déploiement cible : $env:NEXT_PUBLIC_CONVEX_URL"
python scripts/scrape_content_full.py --archive @ScraperArgs
