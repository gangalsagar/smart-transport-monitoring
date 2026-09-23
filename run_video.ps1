# ============================================================
# SMART TRANSPORT MONITORING
# UNIFIED VIDEO PROCESSING LAUNCHER
# ============================================================
#
# Options:
#
# 1 - Process a new video
# 2 - Run the default shared video
# 3 - Run Module 1 independently
# 4 - Run Module 2 independently
# 5 - Show current shared video
# 0 - Exit
#
# ============================================================


$ProjectRoot = "C:\SIH\prototype\smart-transport-monitoring"

$SharedVideoDirectory = Join-Path $ProjectRoot "data\videos"

$DefaultVideoPath = Join-Path `
    $SharedVideoDirectory `
    "combined_test_video.mp4"


# ============================================================
# HEADER
# ============================================================

function Show-Header {

    Clear-Host

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " SMART TRANSPORT - UNIFIED VIDEO PROCESSING"
    Write-Host "============================================================"
    Write-Host ""

}


# ============================================================
# ACTIVATE ENVIRONMENT
# ============================================================

function Initialize-Environment {

    Set-Location $ProjectRoot

    $VenvPath = Join-Path `
        $ProjectRoot `
        ".venv\Scripts\Activate.ps1"

    if (-not (Test-Path $VenvPath)) {

        Write-Host ""
        Write-Host "ERROR: Python virtual environment not found."
        Write-Host ""
        Write-Host "Expected:"
        Write-Host $VenvPath
        Write-Host ""

        return $false
    }

    & $VenvPath

    return $true

}


# ============================================================
# PREPARE SHARED VIDEO
# ============================================================

function Set-SharedVideo {

    param(
        [string]$VideoPath
    )

    if (-not (Test-Path $VideoPath)) {

        Write-Host ""
        Write-Host "ERROR: Video file not found."
        Write-Host ""
        Write-Host "Provided path:"
        Write-Host $VideoPath
        Write-Host ""

        return $false
    }


    if (-not (Test-Path $SharedVideoDirectory)) {

        New-Item `
            -ItemType Directory `
            -Force `
            -Path $SharedVideoDirectory | Out-Null

    }


    $FullVideoPath = (Resolve-Path $VideoPath).Path


    Write-Host ""
    Write-Host "Preparing shared video input..."
    Write-Host ""
    Write-Host "Source:"
    Write-Host $FullVideoPath
    Write-Host ""
    Write-Host "Shared Input:"
    Write-Host $DefaultVideoPath
    Write-Host ""


    Copy-Item `
        -Path $FullVideoPath `
        -Destination $DefaultVideoPath `
        -Force


    Write-Host "Shared video successfully prepared."

    return $true

}


# ============================================================
# RUN UNIFIED PIPELINE (FILE)
# ============================================================

function Start-UnifiedPipeline {

    Write-Host ""

    Write-Host "============================================================"
    Write-Host "STARTING UNIFIED VIDEO PIPELINE (FILE)"
    Write-Host "============================================================"

    Write-Host ""
    Write-Host "Input Video:"
    Write-Host $DefaultVideoPath
    Write-Host ""

    Write-Host "Shared Source:"
    Write-Host "  ONE VIDEO SOURCE"
    Write-Host ""

    Write-Host "Running:"
    Write-Host "  Module 1 - Road Defect Detection"
    Write-Host "  Module 2 - Traffic Monitoring"
    Write-Host ""

    python -m shared.runtime.edge_orchestrator --source file

    $ExitCode = $LASTEXITCODE


    Write-Host ""
    Write-Host "============================================================"

    if ($ExitCode -eq 0) {

        Write-Host "UNIFIED VIDEO PROCESSING COMPLETE"

    }
    else {

        Write-Host "UNIFIED VIDEO PROCESSING FAILED"
        Write-Host "Exit Code: $ExitCode"

    }

    Write-Host "============================================================"

}


# ============================================================
# RUN UNIFIED LIVE CAMERA PIPELINE (CONNECTED MOBILE CAMERA)
# ============================================================

function Start-LiveCameraPipeline {

    Write-Host ""

    Write-Host "============================================================"
    Write-Host "STARTING UNIFIED LIVE CAMERA PIPELINE"
    Write-Host "============================================================"

    Write-Host ""
    Write-Host "Input Camera:"
    Write-Host "  Connected Mobile Camera (Windows Camera Device, Index 1)"
    Write-Host ""

    Write-Host "Shared Source:"
    Write-Host "  ONE LIVE CAMERA CAPTURE"
    Write-Host ""

    Write-Host "Running:"
    Write-Host "  Module 1 - Road Defect Detection"
    Write-Host "  Module 2 - Traffic Monitoring"
    Write-Host "  SharedGPSService - Windows Location"
    Write-Host ""
    Write-Host "Press Ctrl+C at any time to stop."
    Write-Host ""

    python -m shared.runtime.edge_orchestrator --source live --index 1

    $ExitCode = $LASTEXITCODE

    Write-Host ""
    Write-Host "============================================================"

    if ($ExitCode -eq 0) {

        Write-Host "UNIFIED LIVE CAMERA STREAM COMPLETE"

    }
    else {

        Write-Host "UNIFIED LIVE CAMERA STREAM STOPPED (Code: $ExitCode)"

    }

    Write-Host "============================================================"

}



# ============================================================
# PROCESS NEW VIDEO
# ============================================================

function Process-NewVideo {

    Write-Host ""

    Write-Host "============================================================"
    Write-Host "PROCESS NEW VIDEO"
    Write-Host "============================================================"

    Write-Host ""
    Write-Host "Paste the full path of your input video."
    Write-Host ""
    Write-Host "Example:"
    Write-Host "C:\Videos\test_video.mp4"
    Write-Host ""

    $VideoPath = Read-Host "Video path"


    if ([string]::IsNullOrWhiteSpace($VideoPath)) {

        Write-Host ""
        Write-Host "No video path provided."

        return

    }


    $Prepared = Set-SharedVideo `
        -VideoPath $VideoPath


    if ($Prepared) {

        Start-UnifiedPipeline

    }

}


# ============================================================
# RUN DEFAULT VIDEO
# ============================================================

function Process-DefaultVideo {

    Write-Host ""

    if (-not (Test-Path $DefaultVideoPath)) {

        Write-Host "ERROR: Default shared video does not exist."

        Write-Host ""
        Write-Host "Expected:"
        Write-Host $DefaultVideoPath

        return

    }


    Write-Host "Using default shared video:"
    Write-Host $DefaultVideoPath

    Start-UnifiedPipeline

}


# ============================================================
# RUN MODULE 1 INDEPENDENTLY
# ============================================================

function Start-Module1 {

    Write-Host ""

    Write-Host "============================================================"
    Write-Host "STARTING MODULE 1 INDEPENDENTLY"
    Write-Host "============================================================"

    Write-Host ""
    Write-Host "Road Defect Detection"
    Write-Host ""

    # Change this command only if your standalone
    # Module 1 entry point is different.

    python -m module1_road_defect.edge_runtime

}


# ============================================================
# RUN MODULE 2 INDEPENDENTLY
# ============================================================

function Start-Module2 {

    Write-Host ""

    Write-Host "============================================================"
    Write-Host "STARTING MODULE 2 INDEPENDENTLY"
    Write-Host "============================================================"

    Write-Host ""
    Write-Host "Traffic Monitoring"
    Write-Host ""

    python -m module2_traffic.edge_runtime

}


# ============================================================
# SHOW CURRENT VIDEO
# ============================================================

function Show-CurrentVideo {

    Write-Host ""

    Write-Host "============================================================"
    Write-Host "CURRENT SHARED VIDEO"
    Write-Host "============================================================"

    Write-Host ""

    if (Test-Path $DefaultVideoPath) {

        $VideoInfo = Get-Item $DefaultVideoPath

        Write-Host "Video:"
        Write-Host $VideoInfo.FullName

        Write-Host ""

        Write-Host "File Size:"
        Write-Host $VideoInfo.Length

        Write-Host ""

        Write-Host "Last Modified:"
        Write-Host $VideoInfo.LastWriteTime

    }
    else {

        Write-Host "No shared video currently exists."

        Write-Host ""
        Write-Host "Expected location:"
        Write-Host $DefaultVideoPath

    }

}


# ============================================================
# MAIN MENU
# ============================================================

while ($true) {

    Show-Header


    Write-Host "Select an option:"
    Write-Host ""

    Write-Host "  [1] Process a NEW video with Module 1 + Module 2"
    Write-Host "  [2] Run the DEFAULT shared video"
    Write-Host ""
    Write-Host "  [3] Run Module 1 independently"
    Write-Host "  [4] Run Module 2 independently"
    Write-Host ""
    Write-Host "  [5] Show current shared video"
    Write-Host "  [6] Stream LIVE MOBILE CAMERA (Index 1, Module 1 + Module 2)"
    Write-Host ""
    Write-Host "  [0] Exit"
    Write-Host ""


    $Choice = Read-Host "Enter option"


    if ($Choice -eq "0") {

        Write-Host ""
        Write-Host "Exiting video processing launcher."
        Write-Host ""

        break

    }


    $EnvironmentReady = Initialize-Environment


    if (-not $EnvironmentReady) {

        Write-Host ""
        Read-Host "Press ENTER to return to menu"

        continue

    }


    switch ($Choice) {


        "1" {

            Process-NewVideo

        }


        "2" {

            Process-DefaultVideo

        }


        "3" {

            Start-Module1

        }


        "4" {

            Start-Module2

        }


        "5" {

            Show-CurrentVideo

        }


        "6" {

            Start-LiveCameraPipeline

        }


        default {

            Write-Host ""
            Write-Host "Invalid option."

        }

    }


    Write-Host ""
    Read-Host "Press ENTER to return to menu"

}