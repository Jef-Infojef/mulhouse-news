param(
    [string]$Model = "glm-4.7"
)

# Configuration pour l'API BigModel (GLM)
$env:ANTHROPIC_BASE_URL = "https://open.bigmodel.cn/api/anthropic"
$env:ANTHROPIC_MODEL = $Model

# Vérification de la clé API
if (-not $env:ANTHROPIC_API_KEY -or $env:ANTHROPIC_API_KEY -eq "VOTRE_TOKEN_ICI") {
    Write-Host "--- Configuration GLM ---" -ForegroundColor Cyan
    $key = Read-Host "Veuillez entrer votre clé API BigModel (ANTHROPIC_API_KEY)"
    if ($key) { 
        $env:ANTHROPIC_API_KEY = $key 
        Write-Host "Clé configurée pour cette session." -ForegroundColor Gray
    } else { 
        Write-Host "Erreur : Clé API requise." -ForegroundColor Red
        exit 
    }
}

Write-Host "🚀 Lancement de Claude Code (Modèle : $env:ANTHROPIC_MODEL)" -ForegroundColor Green
Write-Host "URL API : $env:ANTHROPIC_BASE_URL" -ForegroundColor Gray

# Lancement de Claude avec les arguments passés au script
claude @args
