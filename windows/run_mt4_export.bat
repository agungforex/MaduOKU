@echo off
REM Runs export_mt4_signal.py for every symbol/timeframe and writes the
REM latest reversal signal into MT4's Common\Files folder for the
REM MaduOKU_ReversalDashboard.mq4 indicator to read.
REM
REM EDIT THE THREE PATHS BELOW FOR YOUR MACHINE, then register this
REM script in Windows Task Scheduler (see windows/register_task.ps1).

setlocal

REM 1) Folder where you cloned/extracted the MaduOKU project
set "PROJECT_DIR=C:\MaduOKU"

REM 2) Python executable (use your venv's if you created one, e.g.
REM    "%PROJECT_DIR%\venv\Scripts\python.exe")
set "PYTHON_EXE=python"

REM 3) MT4's shared Common\Files folder (File -> Open Data Folder in
REM    MT4, then go up one level into Common\Files)
set "MT4_COMMON=C:\Users\%USERNAME%\AppData\Roaming\MetaQuotes\Terminal\Common\Files"

cd /d "%PROJECT_DIR%"
if not exist logs mkdir logs

echo [%date% %time%] Running MT4 signal export >> logs\mt4_export.log

"%PYTHON_EXE%" scripts\export_mt4_signal.py --symbol XAUUSD --mt4-common-files "%MT4_COMMON%" >> logs\mt4_export.log 2>&1
"%PYTHON_EXE%" scripts\export_mt4_signal.py --symbol BTCUSD --mt4-common-files "%MT4_COMMON%" >> logs\mt4_export.log 2>&1

endlocal
