@echo off
title Smart AI Expense Manager
echo =====================================================
echo      🚀 Starting Smart AI Expense Manager...
echo =====================================================
echo.
echo 1. Opening Dashboard in your browser...
timeout /t 3 >nul
start http://127.0.0.1:5000

echo 2. Starting AI Engine & Server...
echo    (Keep this window open while using the app)
echo.
python run.py
pause
