<#
.SYNOPSIS
    Déclenche le workflow « Scrape Mulhouse News » depuis ce poste, toutes les 15 minutes.

.DESCRIPTION
    Le travail tourne toujours chez GitHub : cette tâche n'envoie que le coup
    d'envoi, via `gh workflow run`. Elle existe parce que le cron de GitHub ne
    tient pas ses rendez-vous sur ce dépôt.

    Mesuré le 2026-09-16 :
      - `scrape-news` (*/5, 288 dus/jour), `m68-publish-scheduled` (*/15, 96 dus)
        et `m68-airport-sync` (1/heure, 24 dus) reçoivent le MÊME nombre de runs
        planifiés : 5 à 7 par jour. La fréquence demandée n'a aucun effet.
      - Ces runs partent groupés, à quelques minutes d'écart, jamais à la minute
        demandée. `Cinema Scrape` (cron « 0 2 * * * ») a été livré à 07h33 UTC,
        soit 5 h 33 de retard.
      - Le 27/08 les trois se sont effondrés le même jour, de ~20/jour à ~6, sans
        qu'aucun fichier de workflow n'ait bougé. `assocommercants`, même compte,
        n'a pas connu cette rupture : c'est ce dépôt qui est plafonné.
      - En regard, les 15 derniers `workflow_dispatch` du dépôt ont tous démarré
        à la seconde où ils ont été créés. Zéro attente.

    D'où ce choix : le déclenchement vient d'ici, l'exécution reste là-bas.

    Cadence : toutes les 15 minutes, soit 96 lancements par jour. L'écart médian
    entre deux parutions d'articles est de 28 minutes (mesuré sur 14 jours), donc
    un quart d'heure passe sous la cadence réelle de la source.

    Pas de risque d'empilement : le workflow porte `concurrency: scrape-news` avec
    `cancel-in-progress: false`. Pendant qu'un run tourne, le suivant attend ; si
    un troisième arrive, GitHub annule celui qui patientait. Des runs `cancelled`
    dans l'historique sont donc NORMAUX, pas des échecs.

    Prérequis : `gh` authentifié sur ce poste (trousseau Windows), jeton portant
    la portée `workflow`. La tâche s'exécute en session interactive, comme les
    autres tâches MulhouseGPT, afin que `gh` accède bien à ce trousseau.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\Planifier-ScrapeNews.ps1
    powershell -ExecutionPolicy Bypass -File scripts\Planifier-ScrapeNews.ps1 -IntervalleMinutes 10
    powershell -ExecutionPolicy Bypass -File scripts\Planifier-ScrapeNews.ps1 -Supprimer
#>

param(
    [int]$IntervalleMinutes = 15,
    [string]$Depot = "Jef-Infojef/mulhouse-news",
    [string]$Workflow = "scrape-news.yml",
    [switch]$Supprimer
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $ScriptDir "logs"
$TaskName = "MulhouseGPT-ScrapeNews-15min"

if ($Supprimer) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "🗑️ Tâche '$TaskName' supprimée du Planificateur de Tâches." -ForegroundColor Yellow
    return
}

if ($IntervalleMinutes -lt 5) {
    Write-Host "❌ Intervalle trop court : 5 minutes au minimum." -ForegroundColor Red
    return
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$GhExe = (Get-Command gh.exe -ErrorAction SilentlyContinue).Source
if (-not $GhExe) {
    Write-Host "❌ gh.exe introuvable dans le PATH. Installer GitHub CLI, puis `gh auth login`." -ForegroundColor Red
    return
}

$Log = Join-Path $LogDir "scrape-news-dispatch.log"
$WscriptExe = "$env:SystemRoot\System32\wscript.exe"
$VbsPath = Join-Path $ScriptDir "dispatch-scrape-news.vbs"
$CmdPath = Join-Path $ScriptDir "dispatch-scrape-news.cmd"

# Génère le script batch d'exécution
$CmdContent = @"
@echo off
setlocal
echo [%date% %time%] dispatch $Workflow >> "$Log"
"$GhExe" workflow run $Workflow -R $Depot --ref main >> "$Log" 2>&1
"@
Set-Content -Path $CmdPath -Value $CmdContent -Encoding ASCII

# Génère le lanceur VBScript silencieux (SW_HIDE = 0 : aucune fenêtre console n'apparaît)
$VbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "%comspec% /c ""$CmdPath""", 0, True
"@
Set-Content -Path $VbsPath -Value $VbsContent -Encoding ASCII

$Action = New-ScheduledTaskAction -Execute $WscriptExe -Argument "`"$VbsPath`"" -WorkingDirectory $ScriptDir

# Départ à minuit puis répétition, pour couvrir la journée entière quel que soit
# le moment de l'installation.
#
# La durée est bornée à dix ans, pas « infinie » : [TimeSpan]::MaxValue produit
# P99999999DT23H59M59S, que le Planificateur refuse (« valeur hors limites »), et
# il le refuse APRÈS avoir laissé croire que tout allait bien.
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalleMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

# IgnoreNew : si un `gh` se fige, les lancements suivants passent leur tour au
# lieu de s'empiler. ExecutionTimeLimit court : un dispatch dure une seconde.
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

# -ErrorAction Stop : sans lui, un refus du Planificateur n'interrompt pas le
# script, qui annonçait alors une tâche créée qui n'existait pas.
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "Déclenche le workflow GitHub « Scrape Mulhouse News » toutes les $IntervalleMinutes minutes. Le cron de GitHub ne délivre que 5 à 7 runs par jour sur ce dépôt (mesuré le 2026-09-16), quelle que soit la fréquence demandée." `
        -Force -ErrorAction Stop | Out-Null
} catch {
    Write-Host "❌ Le Planificateur a refusé la tâche : $($_.Exception.Message)" -ForegroundColor Red
    return
}

$ParJour = [math]::Floor(1440 / $IntervalleMinutes)
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✅ Tâche '$TaskName' créée." -ForegroundColor Green
Write-Host "  Cadence : toutes les $IntervalleMinutes minutes ($ParJour lancements/jour)" -ForegroundColor Gray
Write-Host "  Cible   : $Depot / $Workflow" -ForegroundColor Gray
Write-Host "  Journal : $Log" -ForegroundColor DarkGray
Write-Host "  Suivi   : gh run list --workflow=$Workflow --limit 20" -ForegroundColor DarkGray
Write-Host "============================================================" -ForegroundColor Cyan
