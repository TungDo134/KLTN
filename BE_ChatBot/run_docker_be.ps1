param(
    [switch]$Build
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$containerName = "be-chatbot-deploy"
$imageName = "be-chatbot:railway-free"
$envFilePath = Join-Path $PSScriptRoot ".env"
$firebaseFilePath = Join-Path $PSScriptRoot "config\firebase-service-account.json"

if (-not (Test-Path -LiteralPath $envFilePath)) {
    throw "Khong tim thay file .env"
}

if (-not (Test-Path -LiteralPath $firebaseFilePath)) {
    throw "Khong tim thay Firebase credentials file"
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop chua san sang"
}

Push-Location $PSScriptRoot

try {
    if ($Build) {
        Write-Host "Dang build lai Docker image..."
        docker build -t $imageName .
        if ($LASTEXITCODE -ne 0) {
            throw "Docker build that bai"
        }
    }
    else {
        docker image inspect $imageName *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "Khong tim thay image $imageName. Chay lai voi tham so -Build"
        }
    }

    $databaseLine = Get-Content -LiteralPath $envFilePath -Encoding utf8 |
        Where-Object { $_ -match '^\s*DOCKER_DATABASE_URL\s*=' } |
        Select-Object -First 1

    if (-not $databaseLine) {
        throw "Khong tim thay DOCKER_DATABASE_URL trong file .env"
    }

    $databaseUrl = $databaseLine.Substring($databaseLine.IndexOf("=") + 1).Trim()
    if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
        throw "DOCKER_DATABASE_URL trong file .env dang rong"
    }
    

    if (
        ($databaseUrl.StartsWith('"') -and $databaseUrl.EndsWith('"')) -or
        ($databaseUrl.StartsWith("'") -and $databaseUrl.EndsWith("'"))
    ) {
        $databaseUrl = $databaseUrl.Substring(1, $databaseUrl.Length - 2)
    }

    $dockerDatabaseUrl = $databaseUrl.Replace(
        "@localhost:",
        "@host.docker.internal:"
    ).Replace(
        "@127.0.0.1:",
        "@host.docker.internal:"
    )

    $hadFirebaseEnv = Test-Path Env:FIREBASE_CREDENTIALS_JSON
    $hadDatabaseEnv = Test-Path Env:DATABASE_URL
    $previousFirebaseEnv = if ($hadFirebaseEnv) {
        $env:FIREBASE_CREDENTIALS_JSON
    }
    else {
        $null
    }
    $previousDatabaseEnv = if ($hadDatabaseEnv) {
        $env:DATABASE_URL
    }
    else {
        $null
    }

    try {
        $env:FIREBASE_CREDENTIALS_JSON = Get-Content `
            -LiteralPath $firebaseFilePath `
            -Raw `
            -Encoding utf8
        $env:DATABASE_URL = $dockerDatabaseUrl

        $existingContainer = docker ps -a `
            --filter "name=$containerName" `
            --format "{{.Names}}" |
            Where-Object { $_ -eq $containerName }

        if ($existingContainer) {
            Write-Host "Dang xoa container cu..."
            docker rm -f $containerName | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "Khong the xoa container cu"
            }
        }

        Write-Host "Dang khoi dong backend Docker..."
        $containerId = docker run -d `
            --name $containerName `
            --env-file $envFilePath `
            -e FIREBASE_CREDENTIALS_JSON `
            -e DATABASE_URL `
            -e FRONTEND_URL=http://localhost:5173 `
            -e PORT=8000 `
            --memory=512m `
            --cpus=1 `
            -p 8000:8000 `
            $imageName

        if ($LASTEXITCODE -ne 0) {
            throw "Khong the khoi dong container"
        }

        Write-Host "Container da chay: $containerId"
        Write-Host "Health URL: http://127.0.0.1:8000/health"
        Write-Host "Xem log: docker logs -f $containerName"
    }
    finally {
        if ($hadFirebaseEnv) {
            $env:FIREBASE_CREDENTIALS_JSON = $previousFirebaseEnv
        }
        else {
            Remove-Item Env:FIREBASE_CREDENTIALS_JSON `
                -ErrorAction SilentlyContinue
        }

        if ($hadDatabaseEnv) {
            $env:DATABASE_URL = $previousDatabaseEnv
        }
        else {
            Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
        }
    }
}
finally {
    Pop-Location
}
