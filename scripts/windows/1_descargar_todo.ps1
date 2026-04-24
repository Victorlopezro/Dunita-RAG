# ============================================================
# rag-rack - Paso 1: Descargar Ollama, Qdrant y Python
# Sin permisos de administrador
#
# Ejecutar desde la carpeta raiz del proyecto:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\1_descargar_todo.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BinDir  = Join-Path $RootDir "bin"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  rag-rack - Descarga de dependencias" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Directorio raiz: $RootDir"
Write-Host "Directorio bin:  $BinDir"
Write-Host ""

# Crear directorio bin si no existe
if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir | Out-Null
    Write-Host "[OK] Carpeta bin/ creada." -ForegroundColor Green
}

# ----------------------------------------------------------
# 1. Descargar Ollama (instalador sin admin)
# ----------------------------------------------------------
$OllamaInstaller = Join-Path $BinDir "OllamaSetup.exe"
if (-not (Test-Path $OllamaInstaller)) {
    Write-Host "[...] Descargando Ollama para Windows..." -ForegroundColor Yellow
    $OllamaUrl = "https://ollama.com/download/OllamaSetup.exe"
    Invoke-WebRequest -Uri $OllamaUrl -OutFile $OllamaInstaller -UseBasicParsing
    Write-Host "[OK] Ollama descargado: $OllamaInstaller" -ForegroundColor Green
} else {
    Write-Host "[OK] Ollama ya descargado." -ForegroundColor Green
}

# ----------------------------------------------------------
# 2. Descargar Qdrant (binario portable, sin instalacion)
# ----------------------------------------------------------
$QdrantExe = Join-Path $BinDir "qdrant.exe"
if (-not (Test-Path $QdrantExe)) {
    Write-Host "[...] Descargando Qdrant portable para Windows..." -ForegroundColor Yellow
    $QdrantUrl = "https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-pc-windows-msvc.zip"
    $QdrantZip = Join-Path $BinDir "qdrant.zip"
    Invoke-WebRequest -Uri $QdrantUrl -OutFile $QdrantZip -UseBasicParsing
    Expand-Archive -Path $QdrantZip -DestinationPath $BinDir -Force
    Remove-Item $QdrantZip
    Write-Host "[OK] Qdrant portable extraido en: $BinDir" -ForegroundColor Green
} else {
    Write-Host "[OK] Qdrant ya descargado." -ForegroundColor Green
}

# ----------------------------------------------------------
# 3. Verificar Python 3.11+
# ----------------------------------------------------------
Write-Host ""
Write-Host "[...] Verificando Python..." -ForegroundColor Yellow
try {
    $PythonVersion = python --version 2>&1
    Write-Host "[OK] $PythonVersion encontrado." -ForegroundColor Green
} catch {
    Write-Host "[!] Python no encontrado en PATH." -ForegroundColor Red
    Write-Host ""
    Write-Host "Descarga Python 3.11 desde:" -ForegroundColor Yellow
    Write-Host "  https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "IMPORTANTE: Durante la instalacion, marca la casilla:" -ForegroundColor Yellow
    Write-Host "  [x] Add Python to PATH" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "El instalador de Python NO requiere permisos de administrador" -ForegroundColor Green
    Write-Host "si eliges 'Install for current user only'." -ForegroundColor Green
    Write-Host ""
    $DownloadPython = Read-Host "Descargar el instalador de Python ahora? (s/n)"
    if ($DownloadPython -eq "s") {
        $PythonInstaller = Join-Path $BinDir "python-3.11.9-amd64.exe"
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" `
            -OutFile $PythonInstaller -UseBasicParsing
        Write-Host "[OK] Instalador de Python descargado: $PythonInstaller" -ForegroundColor Green
        Write-Host "Ejecuta el instalador y marca 'Add Python to PATH'." -ForegroundColor Yellow
        Write-Host "Luego vuelve a ejecutar este script." -ForegroundColor Yellow
    }
    exit 1
}

# ----------------------------------------------------------
# Resumen
# ----------------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Descargas completadas." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Siguiente paso:" -ForegroundColor Yellow
Write-Host "  1. Ejecuta bin\OllamaSetup.exe para instalar Ollama" -ForegroundColor White
Write-Host "     (NO requiere admin, se instala en tu carpeta de usuario)" -ForegroundColor Green
Write-Host "  2. Luego ejecuta:" -ForegroundColor White
Write-Host "     powershell -ExecutionPolicy Bypass -File scripts\windows\2_instalar_python_deps.ps1" -ForegroundColor Cyan
Write-Host ""
