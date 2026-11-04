@echo off
title Client Radar - Junaid Warraich
echo ========================================================
echo   Starting Client Radar: Scanning Live Remote Opportunities
echo ========================================================
echo.
cd /d "%~dp0"
python main.py
echo.
echo Opening interactive opportunities dashboard in your browser...
start "" "%~dp0output\opportunities.html"
echo.
echo Done! Check the browser window that just opened.
pause
