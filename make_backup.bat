@echo off
set PROJECT_NAME=Mulhouse-News
set TARGET_DIR=P:\backups

echo [*] Verification du lecteur P:
if not exist "P:\" (
    echo [!] Erreur : Le lecteur P: n'est pas accessible.
    exit /b 1
)

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

echo [*] Preparation de la sauvegarde (exclusion node_modules, .git, .next)...
powershell -Command "$date = Get-Date -Format 'yyyyMMdd_HHmm'; $zipPath = Join-Path '%TARGET_DIR%' ('%PROJECT_NAME%_' + $date + '.zip'); echo \"[*] Creation de $zipPath...\"; Get-ChildItem -Path '.' -Exclude 'node_modules','.git','.next','*.log','nextjs-logs.txt','error_log.txt' | Compress-Archive -DestinationPath $zipPath -Force; if (Test-Path $zipPath) { $size = [math]::Round((Get-Item $zipPath).Length / 1MB, 2); echo \"[OK] Sauvegarde terminee : $zipPath ($size Mo)\" } else { exit 1 }"

if %errorlevel% neq 0 (
    echo [!] Une erreur est survenue pendant la compression.
)

