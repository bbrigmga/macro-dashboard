##############################################################################
# Setup-Task-Scheduler.ps1
#
# Registers a Windows Task Scheduler job that runs the IV scraper
# Monday-Friday at 4:30 PM Eastern time (30 min after market close).
#
# Run once from an elevated (Admin) PowerShell prompt:
#   cd "u:\Code Hero\Macro Dashboard"
#   .\scripts\setup_task_scheduler.ps1
#
# To remove the task later:
#   Unregister-ScheduledTask -TaskName "MacroDashboard_IVScrape" -Confirm:$false
##############################################################################

$TaskName    = "MacroDashboard_IVScrape"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe   = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$Script      = Join-Path $ProjectRoot "scripts\scrape_iv.py"
$LogFile     = Join-Path $ProjectRoot "logs\task_scheduler.log"

# Verify files exist before registering
if (-not (Test-Path $PythonExe)) {
    Write-Error "Python not found at: $PythonExe`nMake sure the venv is set up first."
    exit 1
}
if (-not (Test-Path $Script)) {
    Write-Error "Scraper script not found at: $Script"
    exit 1
}

# Ensure logs directory exists
$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Build the action: python scripts/scrape_iv.py >> logs\task_scheduler.log 2>&1
# We wrap in cmd /c so we can redirect stdout+stderr to the log file
$CmdArgs = "/c `"`"$PythonExe`" `"$Script`" >> `"$LogFile`" 2>&1`""
$Action  = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $CmdArgs `
               -WorkingDirectory $ProjectRoot

# Trigger: Mon-Fri at 16:30 (4:30 PM local time)
# Adjust if your machine clock is not Eastern — e.g. change to 21:30 for UTC.
$Trigger = New-ScheduledTaskTrigger -Weekly `
               -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
               -At "4:30 PM"

# Run whether logged on or not; do not store password
$Principal = New-ScheduledTaskPrincipal `
               -UserId $env:USERNAME `
               -LogonType InteractiveToken `
               -RunLevel Limited

# Settings: don't run on battery-only, stop after 30 min if still running
$Settings = New-ScheduledTaskSettingsSet `
               -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
               -MultipleInstances IgnoreNew `
               -StartWhenAvailable     # Run ASAP if machine was off at trigger time

# Remove existing task with the same name if present
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Removing existing task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Register the task
Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $Action `
    -Trigger   $Trigger `
    -Principal $Principal `
    -Settings  $Settings `
    -Description "Scrapes daily implied volatility for the Macro Dashboard ETF universe (Mon-Fri 4:30 PM)." | Out-Null

Write-Host ""
Write-Host "Task registered successfully!" -ForegroundColor Green
Write-Host "  Task name : $TaskName"
Write-Host "  Schedule  : Monday-Friday at 4:30 PM (local time)"
Write-Host "  Python    : $PythonExe"
Write-Host "  Script    : $Script"
Write-Host "  Log file  : $LogFile"
Write-Host ""
Write-Host "To verify, open Task Scheduler and look for '$TaskName',"
Write-Host "or run:  Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
Write-Host ""
Write-Host "To run it immediately for testing:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
