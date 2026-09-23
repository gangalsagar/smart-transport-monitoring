# ============================================================
# SMART TRANSPORT MONITORING - SYSTEM LAUNCHER
# ============================================================
#
# Options:
#
# 1 - Start Backend + Dashboard
# 2 - Start Backend only
# 3 - Start Dashboard only
# 4 - Run Unified Video Pipeline (Module 1 + Module 2)
# 5 - Start Everything
# 0 - Exit
#
# ============================================================


$ProjectRoot = "C:\SIH\prototype\smart-transport-monitoring"

$BackendUrl = "http://127.0.0.1:8001"
$DashboardUrl = "http://localhost:5173"


function Show-Header {

    Clear-Host

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "     SMART TRANSPORT MONITORING SYSTEM LAUNCHER"
    Write-Host "============================================================"
    Write-Host ""

}


function Start-Backend {

    Write-Host ""
    Write-Host "Starting Central Backend..."
    Write-Host ""

    $BackendCommand = @"
Set-Location '$ProjectRoot'
& '$ProjectRoot\.venv\Scripts\Activate.ps1'

Write-Host ''
Write-Host '============================================================'
Write-Host 'CENTRAL BACKEND'
Write-Host '============================================================'
Write-Host ''

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
"@

    Start-Process powershell.exe `
        -ArgumentList "-NoExit", "-Command", $BackendCommand

    Write-Host "Backend launch command sent."
    Write-Host "Expected URL: $BackendUrl"

}


function Start-Dashboard {

    Write-Host ""
    Write-Host "Starting Dashboard..."
    Write-Host ""

    $DashboardPath = Join-Path $ProjectRoot "dashboard"

    $DashboardCommand = @"
Set-Location '$DashboardPath'

Write-Host ''
Write-Host '============================================================'
Write-Host 'SMART TRANSPORT DASHBOARD'
Write-Host '============================================================'
Write-Host ''

npm run dev
"@

    Start-Process powershell.exe `
        -ArgumentList "-NoExit", "-Command", $DashboardCommand

    Write-Host "Dashboard launch command sent."
    Write-Host "Expected URL: $DashboardUrl"

}


function Start-Unified-Pipeline {

    Write-Host ""
    Write-Host "Starting Unified Video Pipeline..."
    Write-Host ""
    Write-Host "Module 1: Road Defect Detection"
    Write-Host "Module 2: Traffic Monitoring & Density"
    Write-Host "Module 3: Incident & Collision Monitoring"
    Write-Host "Input: Shared Video Source"
    Write-Host ""

    $PipelineCommand = @"
Set-Location '$ProjectRoot'
& '$ProjectRoot\.venv\Scripts\Activate.ps1'

Write-Host ''
Write-Host '============================================================'
Write-Host 'UNIFIED EDGE PIPELINE'
Write-Host '============================================================'
Write-Host ''
Write-Host 'Shared Camera/Video -> Module 1 + Module 2 + Module 3'
Write-Host ''

python -m shared.runtime.edge_orchestrator
"@

    Start-Process powershell.exe `
        -ArgumentList "-NoExit", "-Command", $PipelineCommand

    Write-Host "Unified pipeline launch command sent."

}


function Start-Live-Camera-Pipeline {

    Write-Host ""
    Write-Host "Starting Unified Live Mobile Camera Pipeline..."
    Write-Host ""
    Write-Host "Module 1: Road Defect Detection"
    Write-Host "Module 2: Traffic Monitoring & Density"
    Write-Host "Module 3: Incident & Collision Monitoring"
    Write-Host "Input: Connected Mobile Camera (Index 1)"
    Write-Host "GPS: Windows Location Services"
    Write-Host ""

    $PipelineCommand = @"
Set-Location '$ProjectRoot'
& '$ProjectRoot\.venv\Scripts\Activate.ps1'

Write-Host ''
Write-Host '============================================================'
Write-Host 'UNIFIED LIVE CAMERA PIPELINE'
Write-Host '============================================================'
Write-Host ''
Write-Host 'Connected Mobile Camera (Index 1) -> Module 1 + Module 2 + Module 3'
Write-Host 'Press Ctrl+C to stop.'
Write-Host ''

python -m shared.runtime.edge_orchestrator --source live --index 1
"@

    Start-Process powershell.exe `
        -ArgumentList "-NoExit", "-Command", $PipelineCommand

    Write-Host "Unified live camera pipeline launch command sent."

}


function Start-Backend-And-Dashboard {

    Write-Host ""
    Write-Host "Starting Backend and Dashboard..."
    Write-Host ""

    Start-Backend

    Write-Host ""
    Write-Host "Waiting for backend startup..."
    Start-Sleep -Seconds 4

    Start-Dashboard

    Write-Host ""
    Write-Host "Waiting for dashboard startup..."
    Start-Sleep -Seconds 5

    Write-Host ""
    Write-Host "Opening dashboard..."

    Start-Process $DashboardUrl

}


function Start-Everything {

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "STARTING COMPLETE SMART TRANSPORT SYSTEM"
    Write-Host "============================================================"
    Write-Host ""

    # --------------------------------------------------------
    # BACKEND
    # --------------------------------------------------------

    Start-Backend

    Write-Host ""
    Write-Host "Waiting for backend..."
    Start-Sleep -Seconds 5


    # --------------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------------

    Start-Dashboard

    Write-Host ""
    Write-Host "Waiting for dashboard..."
    Start-Sleep -Seconds 6


    # --------------------------------------------------------
    # OPEN DASHBOARD
    # --------------------------------------------------------

    Write-Host ""
    Write-Host "Opening dashboard..."

    Start-Process $DashboardUrl


    # --------------------------------------------------------
    # UNIFIED VIDEO PIPELINE
    # --------------------------------------------------------

    Start-Unified-Pipeline


    Write-Host ""
    Write-Host "============================================================"
    Write-Host "SYSTEM LAUNCH COMPLETE"
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "Backend:"
    Write-Host "  $BackendUrl"
    Write-Host ""
    Write-Host "Dashboard:"
    Write-Host "  $DashboardUrl"
    Write-Host ""
    Write-Host "Pipeline:"
    Write-Host "  Module 1 + Module 2 running simultaneously"
    Write-Host ""

}


# ============================================================
# MAIN MENU
# ============================================================


while ($true) {

    Show-Header

    Write-Host "Select an option:"
    Write-Host ""

    Write-Host "  [1] Start Backend + Dashboard"
    Write-Host "  [2] Start Backend only"
    Write-Host "  [3] Start Dashboard only"
    Write-Host "  [4] Run Unified Video Pipeline (Pre-recorded File)"
    Write-Host "  [5] START EVERYTHING (Backend + Dashboard + File Pipeline)"
    Write-Host "  [6] Stream LIVE MOBILE CAMERA (Connected Phone Camera + GPS)"
    Write-Host ""
    Write-Host "  [0] Exit"
    Write-Host ""

    $Choice = Read-Host "Enter option"


    switch ($Choice) {

        "1" {

            Start-Backend-And-Dashboard

            Write-Host ""
            Read-Host "Press ENTER to return to menu"

        }


        "2" {

            Start-Backend

            Write-Host ""
            Read-Host "Press ENTER to return to menu"

        }


        "3" {

            Start-Dashboard

            Write-Host ""
            Read-Host "Press ENTER to return to menu"

        }


        "4" {

            Start-Unified-Pipeline

            Write-Host ""
            Read-Host "Press ENTER to return to menu"

        }


        "5" {

            Start-Everything


            Write-Host ""
            Read-Host "Press ENTER to return to menu"

        }


        "6" {

            Start-Live-Camera-Pipeline

            Write-Host ""
            Read-Host "Press ENTER to return to menu"

        }


        "0" {

            Write-Host ""
            Write-Host "Exiting Smart Transport System Launcher."
            Write-Host ""

            break

        }


        default {

            Write-Host ""
            Write-Host "Invalid option. Please choose 0, 1, 2, 3, 4, or 5."
            Start-Sleep -Seconds 2

        }

    }


    if ($Choice -eq "0") {

        break

    }

}
