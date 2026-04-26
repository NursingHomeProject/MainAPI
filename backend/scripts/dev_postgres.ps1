param(
    [ValidateSet("start", "stop", "status")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = (Resolve-Path (Join-Path $scriptDir "..")).Path
$legacyRuntimeDir = Join-Path $backendDir ".postgres-runtime"
$shortFallbackRuntimeDir = "C:\CasaAssistencialRuntime"
$configuredRuntimeDir = $env:CASA_ASSISTENCIAL_POSTGRES_RUNTIME_DIR
$preferredRuntimeDir = if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    $shortFallbackRuntimeDir
}
else {
    Join-Path $env:LOCALAPPDATA "CasaAssistencialPg"
}

function Test-RuntimeInitialized {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CandidateRuntimeDir
    )

    return (Test-Path (Join-Path $CandidateRuntimeDir "postgresql")) -or (Test-Path (Join-Path $CandidateRuntimeDir "data"))
}

function Resolve-RuntimeDir {
    if (-not [string]::IsNullOrWhiteSpace($configuredRuntimeDir)) {
        return [System.IO.Path]::GetFullPath($configuredRuntimeDir)
    }

    if (Test-RuntimeInitialized $legacyRuntimeDir) {
        return $legacyRuntimeDir
    }

    if (Test-RuntimeInitialized $shortFallbackRuntimeDir) {
        return $shortFallbackRuntimeDir
    }

    if (Test-RuntimeInitialized $preferredRuntimeDir) {
        return $preferredRuntimeDir
    }

    if (Test-Path $preferredRuntimeDir) {
        return $preferredRuntimeDir
    }

    if (Test-Path $legacyRuntimeDir) {
        return $legacyRuntimeDir
    }

    if (Test-Path $shortFallbackRuntimeDir) {
        return $shortFallbackRuntimeDir
    }

    return $preferredRuntimeDir
}

$runtimeDir = $null
$isUsingLegacyRuntime = $false
$isUsingShortFallbackRuntime = $false
$archivePath = $null
$extractDir = $null
$dataDir = $null
$logDir = $null
$logFile = $null
$stdoutLogFile = $null
$stderrLogFile = $null
$downloadUrl = "https://get.enterprisedb.com/postgresql/postgresql-17.8-1-windows-x64-binaries.zip"

$dbUser = "postgres"
$dbPassword = "postgres"
$dbName = "casa_assistencial"
$dbHost = "127.0.0.1"
$dbPort = 5432
$pidFile = $null
$recommendedProjectPath = "C:\ProjetoExtensao"
$projectPathWarningThreshold = 100
$estimatedMaxPostgresExtractedRelativePathLength = 100
$maxSafeExpandedPathLength = 240

function Set-RuntimeContext {
    param(
        [Parameter(Mandatory = $true)]
        [string]$NewRuntimeDir
    )

    $resolvedRuntimeDir = [System.IO.Path]::GetFullPath($NewRuntimeDir)
    $script:runtimeDir = $resolvedRuntimeDir
    $script:isUsingLegacyRuntime = $resolvedRuntimeDir -eq $legacyRuntimeDir
    $script:isUsingShortFallbackRuntime = $resolvedRuntimeDir -eq $shortFallbackRuntimeDir
    $script:archivePath = Join-Path $resolvedRuntimeDir "postgresql-17.8-1-windows-x64-binaries.zip"
    $script:extractDir = Join-Path $resolvedRuntimeDir "postgresql"
    $script:dataDir = Join-Path $resolvedRuntimeDir "data"
    $script:logDir = Join-Path $resolvedRuntimeDir "log"
    $script:logFile = Join-Path $script:logDir "postgres.log"
    $script:stdoutLogFile = Join-Path $script:logDir "postgres.stdout.log"
    $script:stderrLogFile = Join-Path $script:logDir "postgres.stderr.log"
    $script:pidFile = Join-Path $script:dataDir "postmaster.pid"
}

Set-RuntimeContext -NewRuntimeDir (Resolve-RuntimeDir)

function Get-LongPathsEnabled {
    try {
        $value = Get-ItemPropertyValue -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -ErrorAction Stop
        return [int]$value -eq 1
    }
    catch {
        return $null
    }
}

function Show-RuntimeLocation {
    if ($isUsingLegacyRuntime) {
        Write-Host "Usando runtime legado do PostgreSQL em $runtimeDir." -ForegroundColor Yellow
        Write-Host "Novas instalações usam $preferredRuntimeDir para evitar erro de caminho muito longo no Windows." -ForegroundColor Yellow
        return
    }

    if ($isUsingShortFallbackRuntime -and $runtimeDir -ne $preferredRuntimeDir) {
        Write-Host "Usando runtime curto alternativo do PostgreSQL em $runtimeDir." -ForegroundColor Yellow
        return
    }

    Write-Host "Runtime do PostgreSQL: $runtimeDir" -ForegroundColor DarkGray
}

function Show-ProjectPathWarning {
    if ($backendDir.Length -lt $projectPathWarningThreshold) {
        return
    }

    Write-Host "Aviso: o projeto esta em um caminho relativamente longo:" -ForegroundColor Yellow
    Write-Host $backendDir -ForegroundColor Yellow
    Write-Host "Para reduzir risco com ferramentas do Windows, prefira algo como $recommendedProjectPath." -ForegroundColor Yellow
    Write-Host "Se a extracao do PostgreSQL ainda falhar, configure CASA_ASSISTENCIAL_POSTGRES_RUNTIME_DIR para um caminho curto, como C:\CasaAssistencialRuntime." -ForegroundColor Yellow
}

function Show-LongPathSupportStatus {
    $longPathsEnabled = Get-LongPathsEnabled
    if ($null -eq $longPathsEnabled) {
        Write-Host "Nao foi possivel confirmar se o Windows tem suporte a caminhos longos habilitado." -ForegroundColor DarkGray
        return
    }

    if ($longPathsEnabled) {
        Write-Host "Suporte a caminhos longos do Windows: habilitado." -ForegroundColor DarkGray
        return
    }

    Write-Host "Suporte a caminhos longos do Windows: desabilitado." -ForegroundColor Yellow
}

function Assert-RuntimePathSafety {
    if (Get-PgBinDir) {
        return
    }

    $projectedExpandedPathLength = $runtimeDir.Length + 1 + $estimatedMaxPostgresExtractedRelativePathLength
    if ($projectedExpandedPathLength -le $maxSafeExpandedPathLength) {
        return
    }

    $longPathsEnabled = Get-LongPathsEnabled
    $longPathsMessage = if ($null -eq $longPathsEnabled) {
        "Nao foi possivel confirmar se o suporte a caminhos longos do Windows esta habilitado."
    }
    elseif ($longPathsEnabled) {
        "Mesmo com suporte a caminhos longos habilitado, a extracao ainda pode falhar em ferramentas comuns do Windows."
    }
    else {
        "O suporte a caminhos longos do Windows parece estar desabilitado."
    }

    $runtimeHint = if ($isUsingLegacyRuntime) {
        "O runtime legado em .postgres-runtime fica dentro do repositorio e aumenta o risco de erro por caminho muito longo. Remova esse runtime legado ou defina CASA_ASSISTENCIAL_POSTGRES_RUNTIME_DIR para migrar o setup para um caminho curto."
    }
    else {
        "Escolha um caminho mais curto usando CASA_ASSISTENCIAL_POSTGRES_RUNTIME_DIR, por exemplo C:\CasaAssistencialRuntime."
    }

    throw @"
Risco detectado de erro por caminho muito longo no Windows antes da extracao do PostgreSQL.
Projeto: $backendDir
Runtime selecionado: $runtimeDir
Comprimento estimado de caminho expandido: $projectedExpandedPathLength caracteres
$longPathsMessage
$runtimeHint
Mova o projeto para uma pasta mais curta, como $recommendedProjectPath, ou configure CASA_ASSISTENCIAL_POSTGRES_RUNTIME_DIR para um caminho curto.
"@
}

function Test-IsLongPathFailure {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    return $Message -match '(?i)(path.+too long|file name.+too long|caminho.+muito longo|nome do arquivo.+muito longo)'
}

function Test-ShouldExtractZipEntry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EntryName
    )

    if ($EntryName -like 'pgsql/bin/*') {
        return $true
    }

    if ($EntryName -like 'pgsql/lib/*') {
        if ($EntryName -like 'pgsql/lib/pgxs/*' -or $EntryName -like 'pgsql/lib/pkgconfig/*') {
            return $false
        }

        if ($EntryName -match '\.(lib|a)$') {
            return $false
        }

        return $true
    }

    if ($EntryName -like 'pgsql/share/*') {
        return $EntryName -notlike 'pgsql/share/doc/*'
    }

    return $false
}

function Expand-PostgresRuntimeArchive {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($archivePath)

    try {
        foreach ($entry in $zip.Entries) {
            if (-not (Test-ShouldExtractZipEntry -EntryName $entry.FullName)) {
                continue
            }

            $destinationPath = Join-Path $extractDir $entry.FullName.Replace('/', [IO.Path]::DirectorySeparatorChar)
            $destinationDirectory = Split-Path -Parent $destinationPath

            if (-not [string]::IsNullOrWhiteSpace($destinationDirectory)) {
                New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null
            }

            if ([string]::IsNullOrEmpty($entry.Name)) {
                continue
            }

            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destinationPath, $true)
        }
    }
    finally {
        $zip.Dispose()
    }
}

function Try-UseShortFallbackRuntime {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Reason
    )

    if ($runtimeDir -eq $shortFallbackRuntimeDir) {
        return $false
    }

    if ([string]::IsNullOrWhiteSpace($shortFallbackRuntimeDir)) {
        return $false
    }

    Write-Host "Foi detectado risco de erro por caminho longo no runtime atual." -ForegroundColor Yellow
    Write-Host $Reason -ForegroundColor Yellow
    Write-Host "Tentando automaticamente um caminho curto alternativo: $shortFallbackRuntimeDir" -ForegroundColor Yellow
    Set-RuntimeContext -NewRuntimeDir $shortFallbackRuntimeDir
    Show-RuntimeLocation
    return $true
}

function Get-PgBinDir {
    if (-not (Test-Path $extractDir)) {
        return $null
    }

    $pgCtl = Get-ChildItem -Path $extractDir -Recurse -Filter "pg_ctl.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if ($null -eq $pgCtl) {
        return $null
    }

    return $pgCtl.Directory.FullName
}

function Ensure-Binaries {
    New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

    if (Get-PgBinDir) {
        return
    }

    try {
        Assert-RuntimePathSafety
    }
    catch {
        if (-not (Try-UseShortFallbackRuntime -Reason $_.Exception.Message)) {
            throw
        }

        Ensure-Binaries
        return
    }

    if (-not (Test-Path $archivePath)) {
        Write-Host "Baixando PostgreSQL 17.8..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath
    }

    if (Test-Path $extractDir) {
        Remove-Item -LiteralPath $extractDir -Recurse -Force
    }

    Write-Host "Extraindo runtime enxuto do PostgreSQL..." -ForegroundColor Cyan
    Write-Host "Mantendo somente os componentes necessarios para o backend local (bin, lib e share)." -ForegroundColor DarkGray
    try {
        Expand-PostgresRuntimeArchive
    }
    catch {
        if (-not (Test-IsLongPathFailure -Message $_.Exception.ToString())) {
            throw
        }

        if (-not (Try-UseShortFallbackRuntime -Reason "A extracao do PostgreSQL falhou com uma mensagem compativel com caminho muito longo.")) {
            throw
        }

        Ensure-Binaries
        return
    }
}

function Test-PostgresRunning {
    if (-not (Test-Path $pidFile)) {
        return $false
    }

    $probe = Test-NetConnection -ComputerName $dbHost -Port $dbPort -WarningAction SilentlyContinue
    return $probe.TcpTestSucceeded
}

function Wait-ForPostgresReady {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if (Test-PostgresRunning) {
            return
        }
        Start-Sleep -Seconds 1
    }

    if (Test-Path $stderrLogFile) {
        Get-Content $stderrLogFile -Tail 20 | Write-Host
    }
    throw "O PostgreSQL nao ficou pronto para aceitar conexoes."
}

function Invoke-PgCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar $Executable."
    }
}

function Ensure-Cluster {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BinDir
    )

    if (Test-Path (Join-Path $dataDir "PG_VERSION")) {
        return
    }

    New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null

    $passwordFile = Join-Path $runtimeDir "postgres-password.txt"
    Set-Content -Path $passwordFile -Value $dbPassword -NoNewline

    try {
        Write-Host "Inicializando cluster local..." -ForegroundColor Cyan
        Invoke-PgCommand -Executable (Join-Path $BinDir "initdb.exe") -Arguments @(
            "-D", $dataDir,
            "-U", $dbUser,
            "-A", "scram-sha-256",
            "--pwfile=$passwordFile"
        )
    }
    finally {
        if (Test-Path $passwordFile) {
            Remove-Item -LiteralPath $passwordFile -Force
        }
    }
}

function Ensure-Database {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BinDir
    )

    $env:PGPASSWORD = $dbPassword
    try {
        $psql = Join-Path $BinDir "psql.exe"
        $createdb = Join-Path $BinDir "createdb.exe"

        $dbExists = & $psql -h $dbHost -p $dbPort -U $dbUser -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname = '$dbName';"
        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao consultar bancos existentes."
        }

        if ($dbExists -ne "1") {
            Write-Host "Criando database $dbName..." -ForegroundColor Cyan
            Invoke-PgCommand -Executable $createdb -Arguments @(
                "-h", $dbHost,
                "-p", $dbPort,
                "-U", $dbUser,
                $dbName
            )
        }
    }
    finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
}

function Start-Postgres {
    Show-RuntimeLocation
    Show-LongPathSupportStatus
    Show-ProjectPathWarning
    Ensure-Binaries
    $binDir = Get-PgBinDir
    if ($null -eq $binDir) {
        throw "Nao foi possivel localizar os binarios do PostgreSQL extraidos."
    }

    Ensure-Cluster -BinDir $binDir
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null

    $pgCtl = Join-Path $binDir "pg_ctl.exe"
    if (Test-PostgresRunning) {
        Write-Host "PostgreSQL ja esta em execucao." -ForegroundColor Green
    }
    else {
        Write-Host "Subindo PostgreSQL local na porta $dbPort..." -ForegroundColor Cyan
        if (Test-Path $stdoutLogFile) {
            Remove-Item -LiteralPath $stdoutLogFile -Force
        }
        if (Test-Path $stderrLogFile) {
            Remove-Item -LiteralPath $stderrLogFile -Force
        }

        Start-Process -FilePath (Join-Path $binDir "postgres.exe") -ArgumentList @(
            "-D", $dataDir,
            "-p", "$dbPort",
            "-h", $dbHost
        ) -RedirectStandardOutput $stdoutLogFile -RedirectStandardError $stderrLogFile -WindowStyle Hidden | Out-Null

        Wait-ForPostgresReady
    }

    Ensure-Database -BinDir $binDir
    Write-Host "PostgreSQL pronto em ${dbHost}:$dbPort." -ForegroundColor Green
}

function Stop-Postgres {
    Show-RuntimeLocation
    Show-LongPathSupportStatus
    Show-ProjectPathWarning
    $binDir = Get-PgBinDir
    if ($null -eq $binDir) {
        Write-Host "Binarios do PostgreSQL ainda nao foram baixados." -ForegroundColor Yellow
        return
    }

    $pgCtl = Join-Path $binDir "pg_ctl.exe"
    if (-not (Test-PostgresRunning)) {
        Write-Host "PostgreSQL ja esta parado." -ForegroundColor Yellow
        return
    }

    Write-Host "Parando PostgreSQL local..." -ForegroundColor Cyan
    & $pgCtl -D $dataDir -w stop
    if ($LASTEXITCODE -eq 0) {
        return
    }

    if (-not (Test-Path $pidFile)) {
        throw "Falha ao parar o PostgreSQL e o PID nao foi encontrado para fallback."
    }

    $pid = Get-Content $pidFile | Select-Object -First 1
    try {
        Stop-Process -Id ([int]$pid) -Force
    }
    catch {
        throw "Falha ao parar o PostgreSQL. Execute o script stop no mesmo contexto em que o start foi executado."
    }
}

function Show-Status {
    Show-RuntimeLocation
    Show-LongPathSupportStatus
    Show-ProjectPathWarning
    if (-not (Test-Path $pidFile)) {
        Write-Host "PostgreSQL local ainda nao foi inicializado." -ForegroundColor Yellow
        return
    }

    if (Test-PostgresRunning) {
        Write-Host "PostgreSQL em execucao em ${dbHost}:$dbPort." -ForegroundColor Green
    }
    else {
        Write-Host "PostgreSQL parado." -ForegroundColor Yellow
    }
}

switch ($Action) {
    "start" { Start-Postgres }
    "stop" { Stop-Postgres }
    "status" { Show-Status }
}
