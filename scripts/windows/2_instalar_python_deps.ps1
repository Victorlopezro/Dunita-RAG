# ============================================================
# rag-rack - Paso 2: Instalar dependencias Python
#
# Ejecutar desde la carpeta raiz del proyecto:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\2_instalar_python_deps.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  rag-rack - Instalacion de dependencias" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verificar Python
try {
    $PythonVersion = python --version 2>&1
    Write-Host "[OK] $PythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python no encontrado." -ForegroundColor Red
    Write-Host "Descarga Python 3.11 desde: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -ForegroundColor Yellow
    Write-Host "Durante la instalacion marca: Add Python to PATH" -ForegroundColor Yellow
    exit 1
}

# Actualizar pip
Write-Host "[...] Actualizando pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Instalar dependencias del proyecto
Write-Host "[...] Instalando dependencias de rag-rack..." -ForegroundColor Yellow
Write-Host "      (puede tardar 3-5 minutos la primera vez)" -ForegroundColor Gray
Write-Host ""

Set-Location $RootDir
python -m pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[OK] Dependencias instaladas correctamente." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERROR] Hubo errores durante la instalacion." -ForegroundColor Red
    Write-Host "Revisa los mensajes anteriores e intenta de nuevo." -ForegroundColor Yellow
    exit 1
}

# Instalar Playwright para Crawl4AI
Write-Host ""
Write-Host "[...] Instalando navegador para Crawl4AI (Playwright)..." -ForegroundColor Yellow
python -m playwright install chromium 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Playwright no se pudo instalar (no critico, solo afecta scraping web)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Dependencias instaladas." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Siguiente paso:" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\windows\3_inicializar_sistema.ps1" -ForegroundColor White
Write-Host ""
