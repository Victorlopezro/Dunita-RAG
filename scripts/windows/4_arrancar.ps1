# ============================================================
# rag-rack - Paso 4: Arrancar el sistema completo
#
# Arranca Qdrant, la API FastAPI y el frontend Streamlit.
# Ollama debe estar ya corriendo.
#
# Ejecutar desde la carpeta raiz del proyecto:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\4_arrancar.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BinDir  = Join-Path $RootDir "bin"
$LogsDir = Join-Path $RootDir "logs"

# Crear carpeta logs si no existe
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

# Cargar variables del .env (o env_windows.txt si .env no existe)
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

# Forzar localhost para modo sin Docker
$env:QDRANT_HOST      = "localhost"
$env:OLLAMA_HOST      = "localhost"
$env:FRONTEND_API_URL = "http://localhost:8000"
$env:PYTHONPATH       = $RootDir

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  rag-rack - Arrancando el sistema" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ----------------------------------------------------------
# 1. Arrancar Qdrant
# ----------------------------------------------------------
$QdrantExe  = Join-Path $BinDir "qdrant.exe"
$QdrantData = Join-Path $RootDir "volumes\qdrant"

if (-not (Test-Path $QdrantData)) {
    New-Item -ItemType Directory -Path $QdrantData | Out-Null
}

$QdrantRunning = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:6333/healthz" -UseBasicParsing -TimeoutSec 3
    if ($resp.StatusCode -eq 200) { $QdrantRunning = $true }
} catch {}

if (-not $QdrantRunning) {
    if (-not (Test-Path $QdrantExe)) {
        Write-Host "[ERROR] qdrant.exe no encontrado en: $BinDir" -ForegroundColor Red
        Write-Host "Descarga desde: https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-pc-windows-msvc.zip" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "[...] Arrancando Qdrant..." -ForegroundColor Yellow
    $QdrantProcess = Start-Process -FilePath $QdrantExe `
        -WorkingDirectory $BinDir `
        -WindowStyle Minimized `
        -PassThru
    $QdrantProcess.Id | Out-File (Join-Path $LogsDir "qdrant.pid")

    Start-Sleep -Seconds 3
    $Retries = 0
    do {
        Start-Sleep -Seconds 2
        $Retries++
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:6333/healthz" -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -eq 200) { $QdrantRunning = $true }
        } catch {}
    } while (-not $QdrantRunning -and $Retries -lt 10)

    if ($QdrantRunning) {
        Write-Host "[OK] Qdrant corriendo en http://localhost:6333" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Qdrant no respondio." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] Qdrant ya esta corriendo." -ForegroundColor Green
}

# ----------------------------------------------------------
# 2. Verificar Ollama
# ----------------------------------------------------------
$OllamaRunning = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5
    if ($resp.StatusCode -eq 200) { $OllamaRunning = $true }
} catch {}

if ($OllamaRunning) {
    Write-Host "[OK] Ollama corriendo en http://localhost:11434" -ForegroundColor Green
} else {
    # Intentar arrancar Ollama automaticamente
    $OllamaPaths = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Ollama\ollama.exe"
    )
    foreach ($p in $OllamaPaths) {
        if (Test-Path $p) {
            Write-Host "[...] Iniciando Ollama..." -ForegroundColor Yellow
            Start-Process -FilePath $p -WindowStyle Minimized
            Start-Sleep -Seconds 5
            try {
                $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 8
                if ($resp.StatusCode -eq 200) { $OllamaRunning = $true }
            } catch {}
            break
        }
    }
    if (-not $OllamaRunning) {
        Write-Host "[!] Ollama no esta corriendo. Abrelo desde el menu de inicio." -ForegroundColor Yellow
        Read-Host "Presiona Enter cuando Ollama este corriendo"
    }
}

# ----------------------------------------------------------
# 3. Arrancar la API FastAPI en una nueva ventana
# ----------------------------------------------------------
Write-Host ""
Write-Host "[...] Arrancando API FastAPI (puerto 8000)..." -ForegroundColor Yellow

# Verificar que uvicorn esta instalado
$UvicornCheck = python -c "import uvicorn; print('ok')" 2>&1
if ($UvicornCheck -ne "ok") {
    Write-Host "[!] uvicorn no encontrado. Instalando..." -ForegroundColor Yellow
    python -m pip install uvicorn fastapi --quiet
}

$ApiCmd = "cd `"$RootDir`"; " +
          "`$env:PYTHONPATH='$RootDir'; " +
          "`$env:QDRANT_HOST='localhost'; " +
          "`$env:OLLAMA_HOST='localhost'; " +
          "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $ApiCmd -WindowStyle Normal

# Esperar hasta 60 segundos a que la API este lista
Write-Host "[...] Esperando a que la API este lista (puede tardar hasta 60 seg la primera vez)..." -ForegroundColor Yellow
$ApiRunning = $false
$Retries = 0
do {
    Start-Sleep -Seconds 3
    $Retries++
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing -TimeoutSec 3
        if ($resp.StatusCode -eq 200) { $ApiRunning = $true }
    } catch {}
} while (-not $ApiRunning -and $Retries -lt 20)

if ($ApiRunning) {
    Write-Host "[OK] API corriendo en http://localhost:8000" -ForegroundColor Green
    Write-Host "     Documentacion: http://localhost:8000/docs" -ForegroundColor Gray
} else {
    Write-Host "[!] La API tardo en arrancar. Revisa la ventana de PowerShell que se abrio." -ForegroundColor Yellow
    Write-Host "    Si hay errores de importacion, ejecuta primero:" -ForegroundColor Yellow
    Write-Host "    powershell -ExecutionPolicy Bypass -File scripts\windows\2_instalar_python_deps.ps1" -ForegroundColor White
}

# ----------------------------------------------------------
# 4. Arrancar el frontend Streamlit en una nueva ventana
# ----------------------------------------------------------
Write-Host ""
Write-Host "[...] Arrancando frontend Streamlit (puerto 8501)..." -ForegroundColor Yellow

$FrontendCmd = "cd `"$RootDir`"; " +
               "`$env:FRONTEND_API_URL='http://localhost:8000'; " +
               "python -m streamlit run frontend/app.py --server.port 8501 --server.address localhost --browser.gatherUsageStats false"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendCmd -WindowStyle Normal

Start-Sleep -Seconds 6

# ----------------------------------------------------------
# Resumen
# ----------------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  rag-rack arrancado" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Chatbot:    http://localhost:8501" -ForegroundColor Cyan
Write-Host "  API docs:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Qdrant UI:  http://localhost:6333/dashboard" -ForegroundColor Cyan
Write-Host ""
Write-Host "Abriendo el chatbot en el navegador..." -ForegroundColor Yellow
Start-Process "http://localhost:8501"
Write-Host ""
Write-Host "Para detener todo:" -ForegroundColor Gray
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\windows\5_detener.ps1" -ForegroundColor Gray
Write-Host ""
