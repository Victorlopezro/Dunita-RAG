# ============================================================
# rag-rack - Paso 0: Configuracion inicial (ejecutar UNA sola vez)
#
# Crea el archivo .env y prepara las carpetas necesarias.
#
# Ejecutar desde la carpeta raiz del proyecto:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\0_configurar.ps1
# ============================================================

$RootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  rag-rack - Configuracion inicial" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Directorio del proyecto: $RootDir"
Write-Host ""

# ----------------------------------------------------------
# 1. Crear .env desde env_windows.txt
# ----------------------------------------------------------
$EnvDest   = Join-Path $RootDir ".env"
$EnvSource = Join-Path $RootDir "env_windows.txt"

if (Test-Path $EnvDest) {
    Write-Host "[OK] El archivo .env ya existe." -ForegroundColor Green
} elseif (Test-Path $EnvSource) {
    Copy-Item -Path $EnvSource -Destination $EnvDest
    Write-Host "[OK] .env creado correctamente desde env_windows.txt" -ForegroundColor Green
} else {
    Write-Host "[ERROR] No se encontro env_windows.txt en: $RootDir" -ForegroundColor Red
    Write-Host "        Asegurate de haber descomprimido el ZIP completo." -ForegroundColor Yellow
    exit 1
}

# ----------------------------------------------------------
# 2. Crear carpetas necesarias
# ----------------------------------------------------------
$Dirs = @("bin", "logs", "volumes\qdrant", "volumes\ollama", "data\raw", "data\parsed", "data\chunks", "data\eval")
foreach ($Dir in $Dirs) {
    $FullPath = Join-Path $RootDir $Dir
    if (-not (Test-Path $FullPath)) {
        New-Item -ItemType Directory -Path $FullPath | Out-Null
        Write-Host "[OK] Carpeta creada: $Dir" -ForegroundColor Green
    }
}

# ----------------------------------------------------------
# 3. Mostrar configuracion activa
# ----------------------------------------------------------
Write-Host ""
Write-Host "Configuracion activa (.env):" -ForegroundColor Yellow
Get-Content $EnvDest | Where-Object { $_ -notmatch "^#" -and $_.Trim() -ne "" } | ForEach-Object {
    Write-Host "  $_" -ForegroundColor Gray
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Configuracion completada." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Siguientes pasos:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Instala Ollama (NO requiere admin):" -ForegroundColor White
Write-Host "     https://ollama.com/download/OllamaSetup.exe" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Descarga qdrant.exe y ponlo en la carpeta bin\" -ForegroundColor White
Write-Host "     https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-pc-windows-msvc.zip" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. Instala dependencias Python:" -ForegroundColor White
Write-Host "     powershell -ExecutionPolicy Bypass -File scripts\windows\2_instalar_python_deps.ps1" -ForegroundColor Cyan
Write-Host ""
