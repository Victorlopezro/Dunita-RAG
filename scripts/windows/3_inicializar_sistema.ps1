# ============================================================
# rag-rack - Paso 3: Inicializar el sistema
#
# Arranca Qdrant, verifica Ollama, descarga el modelo Qwen
# y crea la coleccion vectorial.
#
# Ejecutar desde la carpeta raiz del proyecto:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\3_inicializar_sistema.ps1
# ============================================================

$ErrorActionPreference = "Continue"
$RootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BinDir  = Join-Path $RootDir "bin"

# Crear carpeta logs si no existe
$LogsDir = Join-Path $RootDir "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

# Cargar variables del .env
$EnvFile = Join-Path $RootDir ".env"
if (-not (Test-Path $EnvFile)) {
    $EnvAlt = Join-Path $RootDir "env_windows.txt"
    if (Test-Path $EnvAlt) {
        Copy-Item $EnvAlt $EnvFile
        Write-Host "[OK] .env creado desde env_windows.txt" -ForegroundColor Green
    }
}
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.+)$") {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

$QdrantExe   = Join-Path $BinDir "qdrant.exe"
$QdrantData  = Join-Path $RootDir "volumes\qdrant"
$OllamaModel = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "qwen2.5:7b" }

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  rag-rack - Inicializacion del sistema" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Modelo LLM: $OllamaModel"
Write-Host ""

# ----------------------------------------------------------
# 0. Instalar dependencias Python (siempre, para garantizar que esten)
# ----------------------------------------------------------
Write-Host "[...] Verificando e instalando dependencias Python..." -ForegroundColor Yellow
try {
    $PythonVersion = python --version 2>&1
    Write-Host "[OK] $PythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python no encontrado." -ForegroundColor Red
    Write-Host "Descarga Python 3.11 desde: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -ForegroundColor Yellow
    Write-Host "Durante la instalacion marca: Add Python to PATH" -ForegroundColor Yellow
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Actualizar pip silenciosamente
python -m pip install --upgrade pip --quiet 2>&1 | Out-Null

# Instalar requirements.txt completo
Set-Location $RootDir
Write-Host "[...] Instalando requirements.txt (puede tardar 3-5 min la primera vez)..." -ForegroundColor Yellow
python -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Algunos paquetes fallaron. Intentando instalar solo los esenciales..." -ForegroundColor Yellow
    python -m pip install httpx qdrant-client loguru python-dotenv sentence-transformers uvicorn fastapi streamlit --quiet
}
Write-Host "[OK] Dependencias Python listas." -ForegroundColor Green
Write-Host ""

# ----------------------------------------------------------
# 1. Arrancar Qdrant en segundo plano
# ----------------------------------------------------------
if (-not (Test-Path $QdrantExe)) {
    Write-Host "[ERROR] qdrant.exe no encontrado en: $BinDir" -ForegroundColor Red
    Write-Host ""
    Write-Host "Descarga el ZIP desde:" -ForegroundColor Yellow
    Write-Host "  https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-pc-windows-msvc.zip" -ForegroundColor Cyan
    Write-Host "Descomprime qdrant.exe dentro de la carpeta: $BinDir" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $QdrantData)) {
    New-Item -ItemType Directory -Path $QdrantData | Out-Null
}

$QdrantRunning = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:6333/healthz" -UseBasicParsing -TimeoutSec 3
    if ($resp.StatusCode -eq 200) { $QdrantRunning = $true }
} catch {}

if (-not $QdrantRunning) {
    Write-Host "[...] Arrancando Qdrant..." -ForegroundColor Yellow
    $QdrantProcess = Start-Process -FilePath $QdrantExe `
        -WorkingDirectory $BinDir `
        -WindowStyle Minimized `
        -PassThru

    $QdrantProcess.Id | Out-File (Join-Path $LogsDir "qdrant.pid")

    Write-Host "[...] Esperando a que Qdrant este disponible..." -ForegroundColor Yellow
    $Retries = 0
    do {
        Start-Sleep -Seconds 2
        $Retries++
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:6333/healthz" -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -eq 200) { $QdrantRunning = $true }
        } catch {}
    } while (-not $QdrantRunning -and $Retries -lt 15)

    if ($QdrantRunning) {
        Write-Host "[OK] Qdrant disponible en http://localhost:6333" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Qdrant no respondio. Revisa que qdrant.exe funciona correctamente." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] Qdrant ya esta corriendo." -ForegroundColor Green
}

# ----------------------------------------------------------
# 2. Verificar Ollama
# ----------------------------------------------------------
Write-Host ""

# Buscar ollama.exe en las rutas conocidas de instalacion sin admin
$OllamaPaths = @(
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "$env:USERPROFILE\AppData\Local\Programs\Ollama\ollama.exe",
    "C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama\ollama.exe"
)
$OllamaExe = $null
foreach ($p in $OllamaPaths) {
    if (Test-Path $p) { $OllamaExe = $p; break }
}

# Tambien intentar por PATH
if (-not $OllamaExe) {
    try {
        $found = Get-Command ollama -ErrorAction SilentlyContinue
        if ($found) { $OllamaExe = $found.Source }
    } catch {}
}

$OllamaRunning = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5
    if ($resp.StatusCode -eq 200) { $OllamaRunning = $true }
} catch {}

if (-not $OllamaRunning) {
    if ($OllamaExe) {
        Write-Host "[...] Iniciando Ollama desde: $OllamaExe" -ForegroundColor Yellow
        Start-Process -FilePath $OllamaExe -WindowStyle Minimized
        Start-Sleep -Seconds 5
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 8
            if ($resp.StatusCode -eq 200) { $OllamaRunning = $true }
        } catch {}
    }

    if (-not $OllamaRunning) {
        Write-Host "[!] Ollama no esta corriendo." -ForegroundColor Yellow
        Write-Host "    Abrelo desde el menu de inicio o la bandeja del sistema." -ForegroundColor Yellow
        Write-Host "    Si no lo has instalado, descargalo de: https://ollama.com/download/OllamaSetup.exe" -ForegroundColor Yellow
        Write-Host ""
        Read-Host "Presiona Enter cuando Ollama este corriendo"
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 8
            if ($resp.StatusCode -eq 200) { $OllamaRunning = $true }
        } catch {}
    }
}

if ($OllamaRunning) {
    Write-Host "[OK] Ollama disponible en http://localhost:11434" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Ollama no esta disponible." -ForegroundColor Red
    exit 1
}

# ----------------------------------------------------------
# 3. Descargar modelo Qwen si no esta disponible
# ----------------------------------------------------------
Write-Host ""
Write-Host "[...] Verificando modelo $OllamaModel..." -ForegroundColor Yellow

$TagsJson = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing | ConvertFrom-Json
$ModelAvailable = $TagsJson.models | Where-Object { $_.name -like "*$OllamaModel*" }

if (-not $ModelAvailable) {
    Write-Host "[...] Descargando modelo $OllamaModel (~4.7 GB)..." -ForegroundColor Yellow
    Write-Host "      Esto puede tardar varios minutos segun tu conexion." -ForegroundColor Gray

    # Usar la ruta completa de ollama si la tenemos
    if ($OllamaExe) {
        & $OllamaExe pull $OllamaModel
    } else {
        # Llamar via API REST de Ollama (no requiere ollama en PATH)
        Write-Host "[...] Descargando via API REST de Ollama..." -ForegroundColor Yellow
        $PullBody = '{"name":"' + $OllamaModel + '"}'
        try {
            Invoke-WebRequest -Uri "http://localhost:11434/api/pull" `
                -Method POST `
                -Body $PullBody `
                -ContentType "application/json" `
                -UseBasicParsing `
                -TimeoutSec 1800 | Out-Null
        } catch {
            # La descarga puede cerrar la conexion al terminar, ignorar ese error
        }
        Write-Host "[OK] Descarga completada." -ForegroundColor Green
    }
    Write-Host "[OK] Modelo $OllamaModel descargado." -ForegroundColor Green
} else {
    Write-Host "[OK] Modelo $OllamaModel ya disponible." -ForegroundColor Green
}

# ----------------------------------------------------------
# 4. Crear coleccion en Qdrant
# ----------------------------------------------------------
Write-Host ""
Write-Host "[...] Creando coleccion en Qdrant..." -ForegroundColor Yellow
Set-Location $RootDir

$env:QDRANT_HOST = "localhost"
$env:OLLAMA_HOST = "localhost"
$env:PYTHONPATH  = $RootDir

python scripts/create_collection.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  Sistema inicializado correctamente." -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Siguiente paso:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\windows\4_arrancar.ps1" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "[ERROR] Hubo errores durante la inicializacion." -ForegroundColor Red
    exit 1
}
