# ============================================================
# SMART TRANSPORT MONITORING - DATA CLEANER SCRIPT
# ============================================================
# Clears:
#  1. Backend memory & files (/clear endpoint + file resets)
#  2. All Road Defect & Traffic Alerts
#  3. Traffic Density Heatmap points
#  4. Uploaded & Local Evidence crops
#  5. SQLite Edge Queues
# ============================================================

$ProjectRoot = "C:\SIH\prototype\smart-transport-monitoring"
Set-Location $ProjectRoot

Write-Host ""
Write-Host "============================================================"
Write-Host "       CLEARING ALL PROTOTYPE RUNTIME DATA"
Write-Host "============================================================"
Write-Host ""

# 1. Trigger live backend reset if backend is currently running
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8001/clear" -Method POST -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($resp) {
        Write-Host "[OK] Backend live memory & files cleared via API."
    }
} catch {
    # Backend may be offline, proceed with direct file cleanup
}

# 2. Reset Backend Alert & Traffic Density Storage Files
$BackendAlerts = Join-Path $ProjectRoot "backend\data\alerts\alerts.jsonl"
$BackendDensity = Join-Path $ProjectRoot "backend\data\traffic\traffic_density.jsonl"
$BackendDensityOld = Join-Path $ProjectRoot "backend\data\traffic\density.jsonl"

if (Test-Path $BackendAlerts) {
    [System.IO.File]::WriteAllText($BackendAlerts, "")
    Write-Host "[OK] Cleared backend alerts ($BackendAlerts)"
}

if (Test-Path $BackendDensity) {
    [System.IO.File]::WriteAllText($BackendDensity, "")
    Write-Host "[OK] Cleared backend traffic density ($BackendDensity)"
}

if (Test-Path $BackendDensityOld) {
    [System.IO.File]::WriteAllText($BackendDensityOld, "")
    Write-Host "[OK] Cleared legacy density ($BackendDensityOld)"
}

# 3. Clear Backend Uploaded Evidence
$BackendEvidence = Join-Path $ProjectRoot "backend\data\evidence"
if (Test-Path $BackendEvidence) {
    Get-ChildItem -Path $BackendEvidence -File -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host "[OK] Cleared backend uploaded evidence images"
}

# 4. Reset Edge SQLite Queues & Local Evidence
$M1Queue = Join-Path $ProjectRoot "module1_road_defect\data\alerts\alert_queue.db"
$M2Queue = Join-Path $ProjectRoot "module2_traffic\data\alerts\traffic_queue.db"
$M1Evidence = Join-Path $ProjectRoot "module1_road_defect\data\evidence"

if (Test-Path $M1Queue) {
    Remove-Item $M1Queue -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Reset Module 1 Edge Queue ($M1Queue)"
}

if (Test-Path $M2Queue) {
    Remove-Item $M2Queue -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Reset Module 2 Edge Queue ($M2Queue)"
}

if (Test-Path $M1Evidence) {
    Get-ChildItem -Path $M1Evidence -File -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host "[OK] Cleared Module 1 local evidence crops"
}

Write-Host ""
Write-Host "============================================================"
Write-Host " ALL STORED DATA & HEATMAP POINTS CLEARED SUCCESSFULLY!"
Write-Host "============================================================"
Write-Host ""
