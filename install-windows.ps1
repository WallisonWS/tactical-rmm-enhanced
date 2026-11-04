<#
.SYNOPSIS
    Tactical RMM Enhanced — Instalador Oficial para Windows (Windows 10/11 & Windows Server 2016/2019/2022/2025)
.DESCRIPTION
    Suporta 3 modos de instalacao no Windows:
      1. ServerNative : Instala e configura a Stack Nativa (Python 3.12, Node.js, Go, Frontend Vue 3 PT/EN/ES, API Django e compilacao dos Agentes Windows/Linux)
      2. ServerDocker : Instala e sobe a Stack completa via Docker Compose no Windows
      3. Agent        : Compila/baixa e instala o Agente Tactical RMM Enhanced (tacticalrmm.exe) como servico nativo do Windows com auto-recovery
.EXAMPLE
    .\install-windows.ps1 -Mode ServerNative
    .\install-windows.ps1 -Mode ServerDocker
    .\install-windows.ps1 -Mode Agent -ApiUrl "https://api.exemplo.com" -ClientId 1 -SiteId 1 -AuthToken "TOKEN"
#>

param(
    [ValidateSet("ServerNative", "ServerDocker", "Agent", "Interactive")]
    [string]$Mode = "Interactive",
    [string]$ApiUrl = "",
    [int]$ClientId = 1,
    [int]$SiteId = 1,
    [ValidateSet("server", "workstation")]
    [string]$AgentType = "server",
    [string]$AuthToken = "",
    [switch]$EnableRDP,
    [switch]$EnablePing,
    [switch]$Insecure
)

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step([string]$msg) {
    Write-Host "`n================================================================================" -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Cyan
}

if ($Mode -eq "Interactive") {
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "  Tactical RMM Enhanced v200 — Instalador Multi-Plataforma Windows" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "Escolha o modo de instalacao no Windows:"
    Write-Host "  [1] Servidor Nativo / Homologacao (API Django + Painel Vue 3 PT/EN/ES + Build Agentes Go)"
    Write-Host "  [2] Servidor via Docker Compose (Containers Completos no Windows)"
    Write-Host "  [3] Instalar Agente Endpoint nesta maquina Windows (Servico tacticalrmm)"
    $choice = Read-Host "Digite a opcao (1, 2 ou 3)"
    switch ($choice) {
        "1" { $Mode = "ServerNative" }
        "2" { $Mode = "ServerDocker" }
        "3" { $Mode = "Agent" }
        default { $Mode = "ServerNative" }
    }
}

function Ensure-WingetPackage([string]$cmdName, [string]$wingetId, [string]$friendlyName) {
    if (-not (Get-Command $cmdName -ErrorAction SilentlyContinue)) {
        Write-Host "[*] Instalando $friendlyName via Winget ($wingetId)..." -ForegroundColor Yellow
        winget install --id $wingetId --exact --silent --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "[OK] $friendlyName detectado no sistema." -ForegroundColor Green
    }
}

if ($Mode -eq "ServerNative") {
    Write-Step "Verificando dependencias (Python 3.12, Node.js LTS, Go) no Windows..."
    Ensure-WingetPackage "python" "Python.Python.3.12" "Python 3.12"
    Ensure-WingetPackage "node" "OpenJS.NodeJS.LTS" "Node.js LTS"
    Ensure-WingetPackage "go" "GoLang.Go" "Go Compiler"

    Write-Step "Configurando Backend API (Django + DRF)..."
    $ApiDir = Join-Path $RepoRoot "api\tacticalrmm"
    $VenvDir = Join-Path $RepoRoot "api\env"
    if (-not (Test-Path $VenvDir)) {
        python -m venv $VenvDir
    }
    $PipExe = Join-Path $VenvDir "Scripts\pip.exe"
    $PyExe = Join-Path $VenvDir "Scripts\python.exe"

    & $PipExe install --upgrade pip setuptools wheel
    & $PipExe install -r (Join-Path $ApiDir "requirements.txt")

    Write-Step "Instalando e Compilando Frontend Web Multi-Idioma (PT-BR / EN-US / ES-ES)..."
    $WebDir = Join-Path $RepoRoot "web"
    Push-Location $WebDir
    npm install --legacy-peer-deps
    npm run build
    Pop-Location

    Write-Step "Compilando Binarios do Agente Go para Windows (amd64/386) e Linux (amd64/arm64)..."
    $AgentDir = Join-Path $RepoRoot "rmmagent"
    $OutAgentsDir = Join-Path $WebDir "dist\agents"
    New-Item -ItemType Directory -Force -Path $OutAgentsDir | Out-Null

    if (Get-Command "go" -ErrorAction SilentlyContinue) {
        Push-Location $AgentDir
        $env:CGO_ENABLED = "0"
        $env:GOOS = "windows"; $env:GOARCH = "amd64"
        go build -ldflags="-s -w" -o (Join-Path $OutAgentsDir "tacticalagent-windows-amd64.exe") .
        $env:GOOS = "windows"; $env:GOARCH = "386"
        go build -ldflags="-s -w" -o (Join-Path $OutAgentsDir "tacticalagent-windows-386.exe") .
        $env:GOOS = "linux"; $env:GOARCH = "amd64"
        go build -ldflags="-s -w" -o (Join-Path $OutAgentsDir "tacticalagent-linux-amd64") .
        $env:GOOS = "linux"; $env:GOARCH = "arm64"
        go build -ldflags="-s -w" -o (Join-Path $OutAgentsDir "tacticalagent-linux-arm64") .
        Pop-Location
        Write-Host "[OK] Binarios Windows e Linux compilados em: $OutAgentsDir" -ForegroundColor Green
    }

    Write-Step "Instalacao ServerNative concluida!"
    Write-Host "Para iniciar o Painel Web em modo interativo:" -ForegroundColor Yellow
    Write-Host "  cd `"$WebDir`" && npm run dev" -ForegroundColor White
    Write-Host "Para iniciar a API Django:" -ForegroundColor Yellow
    Write-Host "  cd `"$ApiDir`" && ..\env\Scripts\python.exe manage.py runserver 0.0.0.0:8000" -ForegroundColor White
}
elseif ($Mode -eq "ServerDocker") {
    Write-Step "Verificando Docker Desktop no Windows..."
    Ensure-WingetPackage "docker" "Docker.DockerDesktop" "Docker Desktop"
    $DockerDir = Join-Path $RepoRoot "docker"
    Push-Location $DockerDir
    if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
        Copy-Item ".env.example" ".env"
        Write-Host "[!] Arquivo .env criado em $DockerDir\.env. Edite os dominios/senhas antes de ir para producao." -ForegroundColor Yellow
    }
    docker compose up -d --build
    Pop-Location
    Write-Step "Containers Docker do Tactical RMM Enhanced iniciados!"
}
elseif ($Mode -eq "Agent") {
    Write-Step "Instalando Agente Tactical RMM Enhanced no Windows..."
    $InstallDir = "C:\Program Files\TacticalAgent"
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    $TargetExe = Join-Path $InstallDir "tacticalrmm.exe"

    # Compila localmente se estiver no repositorio e Go estiver instalado
    $AgentSrc = Join-Path $RepoRoot "rmmagent"
    if ((Test-Path $AgentSrc) -and (Get-Command "go" -ErrorAction SilentlyContinue)) {
        Write-Host "[*] Compilando agente nativo a partir de $AgentSrc..." -ForegroundColor Cyan
        Push-Location $AgentSrc
        go build -ldflags="-s -w" -o $TargetExe .
        Pop-Location
    }

    if (-not (Test-Path $TargetExe)) {
        Write-Error "Binario $TargetExe nao encontrado. Compile com Go ou use o script PowerShell gerado pelo Painel Web."
        exit 1
    }

    # Configura exclusoes basicas do Windows Defender para o caminho oficial do agente
    Try {
        Add-MpPreference -ExclusionPath "$InstallDir\*" -ErrorAction SilentlyContinue
        Add-MpPreference -ExclusionPath "C:\Program Files\Mesh Agent\*" -ErrorAction SilentlyContinue
        Add-MpPreference -ExclusionPath "C:\ProgramData\TacticalRMM\*" -ErrorAction SilentlyContinue
    } Catch {}

    if ($ApiUrl -ne "" -and $AuthToken -ne "") {
        $installArgs = @("-m", "install", "--api", $ApiUrl, "--client-id", "$ClientId", "--site-id", "$SiteId", "--agent-type", $AgentType, "--auth", $AuthToken)
        if ($EnableRDP)  { $installArgs += "--rdp" }
        if ($EnablePing) { $installArgs += "--ping" }
        if ($Insecure)   { $installArgs += "--insecure" }

        & $TargetExe @installArgs
        sc.exe failure tacticalrmm reset= 0 actions= restart/5000/restart/5000/restart/5000 | Out-Null
        Write-Step "Agente Windows registrado e servico configurado com auto-recuperacao!"
    } else {
        Write-Step "Binario instalado em $TargetExe!"
        Write-Host "Para registrar no servidor, execute:" -ForegroundColor Yellow
        Write-Host "  `"$TargetExe`" -m install --api https://api.seudominio.com --client-id 1 --site-id 1 --agent-type $AgentType --auth SEU_TOKEN" -ForegroundColor White
    }
}
