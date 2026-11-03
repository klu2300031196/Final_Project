@echo off
title DevOps Continuous Testing Platform Launcher
color 0B
echo ======================================================================
echo    DEVOPS CONTINUOUS TESTING FRAMEWORK - ONE-CLICK LAUNCHER
echo ======================================================================
echo.
echo Starting Application Under Test (Port 5000) and Testing Hub (Port 8080)...
echo.
python scripts\start_devops_platform.py
pause
