Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = $PSScriptRoot
$backendDirectory = Join-Path $projectRoot "BE_ChatBot"
$frontendDirectory = Join-Path $projectRoot "FE_ChatBot"
$backendPython = Join-Path $backendDirectory ".venv\Scripts\python.exe"
$backendHealthUrl = "http://127.0.0.1:8000/health"
$frontendUrl = "http://127.0.0.1:5173"

$backendProcess = $null
$frontendProcess = $null
$exitCode = 0

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("THÔNG TIN", "THÀNH CÔNG", "CẢNH BÁO", "THẤT BẠI")]
        [string]$Level = "THÔNG TIN"
    )

    $color = switch ($Level) {
        "THÀNH CÔNG" { "Green" }
        "CẢNH BÁO" { "Yellow" }
        "THẤT BẠI" { "Red" }
        default { "Cyan" }
    }

    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [$Level] $Message" `
        -ForegroundColor $color
}

function Test-Url {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest `
            -Uri $Url `
            -UseBasicParsing `
            -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 400
    }
    catch {
        return $false
    }
}

function Wait-ForService {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Name,
        [string]$Url,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        $Process.Refresh()
        if ($Process.HasExited) {
            throw "$Name đã dừng trong lúc khởi động, mã thoát: $($Process.ExitCode)."
        }

        if (Test-Url -Url $Url) {
            return
        }

        Start-Sleep -Seconds 2
    }

    throw "$Name chưa sẵn sàng sau $TimeoutSeconds giây."
}

function Stop-ProcessTree {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Name
    )

    if ($null -eq $Process) {
        return
    }

    $Process.Refresh()
    if ($Process.HasExited) {
        Write-Log "$Name đã dừng trước đó." "CẢNH BÁO"
        return
    }

    Write-Log "Đang dừng $Name"
    & taskkill.exe /PID $Process.Id /T /F *> $null

    if ($LASTEXITCODE -eq 0) {
        Write-Log "Đã dừng $Name." "THÀNH CÔNG"
    }
    else {
        Write-Log "Không thể dừng hoàn toàn $Name. Hãy kiểm tra tiến trình PID $($Process.Id)." "CẢNH BÁO"
    }
}

try {
    Write-Log "Đang kiểm tra môi trường BE chạy local"

    if (-not (Test-Path -LiteralPath $backendPython -PathType Leaf)) {
        throw "Không tìm thấy Python của BE tại: $backendPython"
    }

    if (-not (Test-Path -LiteralPath (Join-Path $frontendDirectory "package.json") -PathType Leaf)) {
        throw "Không tìm thấy FE tại: $frontendDirectory"
    }

    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($null -eq $npmCommand) {
        throw "Không tìm thấy npm.cmd. Hãy cài đặt Node.js và mở lại terminal."
    }

    if (Test-Url -Url $backendHealthUrl) {
        throw "BE đã chạy tại $backendHealthUrl. Hãy dừng tiến trình cũ trước."
    }

    if (Test-Url -Url $frontendUrl) {
        throw "FE đã chạy tại $frontendUrl. Hãy dừng tiến trình cũ trước."
    }

    Write-Log "Đang khởi động BE"
    $backendProcess = Start-Process `
        -FilePath $backendPython `
        -ArgumentList @("-m", "uvicorn", "src.main:app", "--reload") `
        -WorkingDirectory $backendDirectory `
        -PassThru

    Write-Log "Đang chờ BE sẵn sàng tại $backendHealthUrl"
    Wait-ForService `
        -Process $backendProcess `
        -Name "BE" `
        -Url $backendHealthUrl `
        -TimeoutSeconds 180
    Write-Log "BE đã khởi động thành công." "THÀNH CÔNG"

    Write-Log "Đang khởi động FE"
    $frontendProcess = Start-Process `
        -FilePath $npmCommand.Source `
        -ArgumentList @("run", "dev", "--", "--strictPort") `
        -WorkingDirectory $frontendDirectory `
        -PassThru

    Write-Log "Đang chờ FE sẵn sàng tại $frontendUrl"
    Wait-ForService `
        -Process $frontendProcess `
        -Name "FE" `
        -Url $frontendUrl `
        -TimeoutSeconds 60
    Write-Log "FE đã khởi động thành công: $frontendUrl" "THÀNH CÔNG"

    Write-Host ""
    Write-Log "Nhấn Ctrl+C để dừng BE trước, sau đó dừng FE."
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
catch {
    $exitCode = 1
    Write-Log $_.Exception.Message "THẤT BẠI"
}
finally {
    Write-Host ""
    Write-Log "Bắt đầu dừng dự án local"
    Stop-ProcessTree -Process $backendProcess -Name "BE"
    Stop-ProcessTree -Process $frontendProcess -Name "FE"
    Write-Log "Đã hoàn tất quá trình dừng dự án local." "THÀNH CÔNG"
}

exit $exitCode
