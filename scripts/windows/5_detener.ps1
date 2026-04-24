# ============================================================
# rag-rack - Detener todos los servicios
#
# Ejecutar desde la carpeta raiz del proyecto:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\5_detener.ps1
# ============================================================

$RootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogsDir = Join-Path $RootDir "logs"

Write-Host ""
Write-Host "============================================" -ForegroundColor Yellow
Write-Host "  rag-rack - Deteniendo servicios" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Yellow
Write-Host ""

# Detener Qdrant por PID guardado
$PidFile = Join-Path $LogsDir "qdrant.pid"
if (Test-Path $PidFile) {
    $QdrantPid = Get-Content $PidFile
    try {
        Stop-Process -Id $QdrantPid -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Qdrant detenido (PID: $QdrantPid)." -ForegroundColor Green
    } catch {
        Write-Host "[!] Qdrant ya estaba detenido." -ForegroundColor Yellow
    }
    Remove-Item $PidFile -ErrorAction SilentlyContinue
} else {
    Get-Process -Name "qdrant" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Qdrant detenido." -ForegroundColor Green
}

# Detener uvicorn (API FastAPI) - buscar por linea de comandos
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
    if ($_.CommandLine -like "*uvicorn*") {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] API FastAPI detenida." -ForegroundColor Green
    }
    if ($_.CommandLine -like "*streamlit*") {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Streamlit detenido." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "[OK] Servicios detenidos." -ForegroundColor Green
Write-Host "     Ollama sigue corriendo en la bandeja del sistema." -ForegroundColor Gray
Write-Host "     Para cerrarlo: clic derecho en su icono -> Quit" -ForegroundColor Gray
Write-Host ""
