@echo off
REM ====================================================================
REM Live Entry Monitor - Simple Auto Starter
REM Save this as: run_entry_monitor.bat
REM ====================================================================

echo ====================================================================
echo LIVE ENTRY MONITOR - AUTO STARTER
echo Starting at: %date% %time%
echo ====================================================================

REM Change to your project directory
cd /d "C:\Users\PC\OneDrive\projects\strongtrendz.com-"

REM Check if it's a weekday (Skip weekends)
for /f %%i in ('powershell -command "Get-Date -Format 'dddd'"') do set DAY=%%i

if /i "%DAY%"=="Saturday" (
    echo Market closed on Saturday. Exiting...
    timeout /t 5
    exit /b
)

if /i "%DAY%"=="Sunday" (
    echo Market closed on Sunday. Exiting...  
    timeout /t 5
    exit /b
)

REM Check current time - if before 9:30 AM, show waiting message
for /f "tokens=1-2 delims=:" %%a in ("%time%") do (
    set HOUR=%%a
    set MINUTE=%%b
)

REM Remove leading space from hour
set HOUR=%HOUR: =%

REM Calculate total minutes since midnight
set /a CURRENT_MINUTES=%HOUR%*60+%MINUTE%
set /a MARKET_OPEN_MINUTES=9*60+30

if %CURRENT_MINUTES% LSS %MARKET_OPEN_MINUTES% (
    set /a WAIT_MINUTES=%MARKET_OPEN_MINUTES%-%CURRENT_MINUTES%
    echo Market opens at 9:30 AM. Waiting %WAIT_MINUTES% minutes...
    echo You can close this window and the scheduler will start at 9:30 AM
    timeout /t 10
)

REM Run the live entry monitor
echo.
echo Starting Live Entry Monitor...
echo Press Ctrl+C to stop monitoring
echo.

python live_entry_monitor.py --interval 60 --tolerance 0.5

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Program exited with error code %ERRORLEVEL%
    echo Check the error message above.
    echo.
    echo COMMON ISSUES:
    echo - Make sure live_entry_monitor.py is in the same folder
    echo - Check if Python is installed and in PATH
    echo - Ensure you have internet connection for live data
    echo - Verify JSON report exists in output folder
    pause
) else (
    echo.
    echo Entry monitoring session ended normally at: %date% %time%
    timeout /t 5
)