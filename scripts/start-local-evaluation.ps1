$ErrorActionPreference = 'Stop'
$runtimeRoot = 'C:\Users\William\.cache\sales-phase6'
$executable = Join-Path $runtimeRoot 'ollama-v0.40.2\ollama.exe'
$ownerFile = Join-Path $runtimeRoot 'server-owner.json'
if (-not (Test-Path -LiteralPath $executable)) { throw 'Verified runtime extraction not available yet.' }
if (Test-Path -LiteralPath $ownerFile) { throw 'Owner record exists; inspect and stop the prior owned session before starting another.' }
$freeKiB = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory
if ($freeKiB -lt 4194304) { throw 'At least 4 GiB free host RAM required before launch.' }
$freeVram = & nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits
if ($LASTEXITCODE -ne 0 -or [int]($freeVram | Select-Object -First 1) -lt 3072) { throw 'At least 3 GiB free GPU memory required.' }
if (Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue) { throw 'Port already owned by another listener; do not attach.' }
$models = Join-Path $runtimeRoot 'models'
New-Item -ItemType Directory -Path $models -Force | Out-Null
$env:OLLAMA_MODELS = $models
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_MAX_QUEUE = '1'
$env:OLLAMA_CONTEXT_LENGTH = '4096'
$env:OLLAMA_KEEP_ALIVE = '0'
$ownedServer = Start-Process -FilePath $executable -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'server.stdout.log') -RedirectStandardError (Join-Path $runtimeRoot 'server.stderr.log')
$record = @{pid=$ownedServer.Id; started_utc=$ownedServer.StartTime.ToUniversalTime().ToString('o'); executable=$executable; models=$models; host='127.0.0.1:11434'; no_cloud=$true; free_host_kib_before=$freeKiB; free_vram_mib_before=$freeVram}
$record | ConvertTo-Json | Set-Content -LiteralPath $ownerFile -Encoding UTF8
$record | ConvertTo-Json
