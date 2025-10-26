# Download and extract Node.js 20 LTS portable for Windows (x64) into the repo root
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\get_node20.ps1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Ensure TLS 1.2 for Invoke-WebRequest on older PowerShell
try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch {}

$zipName = 'node-v20.18.1-win-x64.zip'
$zipPath = Join-Path -Path (Get-Location) -ChildPath $zipName
$extractDir = Join-Path -Path (Get-Location) -ChildPath 'node-v20.18.1-win-x64'
$url = 'https://nodejs.org/dist/v20.18.1/node-v20.18.1-win-x64.zip'

Write-Host "Downloading Node.js 20 LTS portable from $url"
if (-not (Test-Path -Path $zipPath)) {
  Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
} else {
  Write-Host "Archive already exists: $zipPath"
}

Write-Host "Extracting to $extractDir"
if (Test-Path -Path $extractDir) {
  Write-Host "Removing existing directory $extractDir"
  Remove-Item -Recurse -Force -Path $extractDir
}

Expand-Archive -Path $zipPath -DestinationPath . -Force

if (-not (Test-Path -Path (Join-Path $extractDir 'node.exe'))) {
  # Some Node zips may create a nested folder; try to fix structure
  $nested = Get-ChildItem -Path $extractDir -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($null -ne $nested) {
    Write-Host "Detected nested folder structure: $($nested.FullName). Promoting contents..."
    $tmp = Join-Path -Path (Get-Location) -ChildPath 'node20_tmp_promote'
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    New-Item -ItemType Directory -Path $tmp | Out-Null
    Move-Item -Path (Join-Path $extractDir '*') -Destination $tmp
    Remove-Item -Recurse -Force $extractDir
    New-Item -ItemType Directory -Path $extractDir | Out-Null
    Move-Item -Path (Join-Path $tmp '*') -Destination $extractDir
    Remove-Item -Recurse -Force $tmp
  }
}

if (Test-Path -Path (Join-Path $extractDir 'node.exe')) {
  Write-Host "Success: Node 20 portable is ready at $extractDir"
  Write-Host "Version check:"
  & (Join-Path $extractDir 'node.exe') -v
} else {
  Write-Error "Failed to prepare Node 20 portable at $extractDir"
}
