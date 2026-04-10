# start.ps1 — Levanta el entorno de desarrollo de la Plataforma AI-Native (Windows)
# Requiere: Docker Desktop, PowerShell 7+
#Requires -Version 7.0

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$DevOpsDir   = "$PSScriptRoot"

# ─── Helpers ──────────────────────────────────────────────────────────────
function Log   { param($msg) Write-Host "[ainative] $msg" -ForegroundColor Green }
function Warn  { param($msg) Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Err   { param($msg) Write-Host "[error] $msg" -ForegroundColor Red; exit 1 }

# ─── 1. Verificar Docker ───────────────────────────────────────────────────
Log "Verificando Docker..."
try {
    docker info | Out-Null
} catch {
    Err "Docker no está corriendo. Abrí Docker Desktop antes de continuar."
}

# ─── 2. Archivo .env ───────────────────────────────────────────────────────
$EnvFile     = "$ProjectRoot\.env"
$EnvExample  = "$ProjectRoot\env.example"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Warn ".env no encontrado. Copiando desde env.example..."
        Copy-Item $EnvExample $EnvFile
        Warn "Revisá y completá las variables en $EnvFile antes de continuar en producción."
    } else {
        Err "No existe env.example en $ProjectRoot. Creá un .env manualmente."
    }
} else {
    Log ".env encontrado."
}

# ─── 3. Levantar servicios ─────────────────────────────────────────────────
Log "Levantando servicios con Docker Compose..."
Set-Location $DevOpsDir
docker compose up -d

# ─── 4. Esperar a que la DB esté lista ────────────────────────────────────
Log "Esperando que PostgreSQL esté disponible..."
$Retries = 30
$Ready   = $false
while ($Retries -gt 0 -and -not $Ready) {
    $result = docker compose exec -T db pg_isready -U ainative -d ainative 2>&1
    if ($LASTEXITCODE -eq 0) {
        $Ready = $true
    } else {
        $Retries--
        if ($Retries -le 0) {
            Err "PostgreSQL no respondió a tiempo. Revisá: docker compose logs db"
        }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
    }
}
Write-Host ""
Log "PostgreSQL listo."

# ─── 5. Migraciones Alembic ────────────────────────────────────────────────
Log "Ejecutando migraciones (alembic upgrade head)..."
docker compose exec -T api alembic upgrade head

# ─── 6. Seed de datos ──────────────────────────────────────────────────────
$SeedScript = "$ProjectRoot\backend\scripts\seed.py"
if (Test-Path $SeedScript) {
    Log "Cargando datos semilla..."
    docker compose exec -T api python scripts/seed.py
} else {
    Warn "No se encontró backend\scripts\seed.py — saltando seed de datos."
}

# ─── 7. URLs de acceso ────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Plataforma AI-Native — Dev Ready      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Frontend:   " -NoNewline; Write-Host "http://localhost:5173" -ForegroundColor Green
Write-Host "  API docs:   " -NoNewline; Write-Host "http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  API redoc:  " -NoNewline; Write-Host "http://localhost:8000/redoc" -ForegroundColor Green
Write-Host "  DB:         " -NoNewline; Write-Host "postgresql://ainative:ainative@localhost:5432/ainative" -ForegroundColor Green
Write-Host "  Redis:      " -NoNewline; Write-Host "redis://localhost:6379" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Log "Para ver logs: docker compose logs -f api"
