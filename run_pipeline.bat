@echo off
title DevOps Continuous Testing Pipeline
color 0A
echo ======================================================================
echo    TRIGGERING FULL DEVOPS CONTINUOUS TESTING PIPELINE
echo ======================================================================
echo.
python -m engine.test_runner
echo.
echo Opening Executive Quality Gate Report in default browser...
start reports\executive_dashboard.html
pause
