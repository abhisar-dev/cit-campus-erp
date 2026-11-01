@echo off
chcp 65001 >nul
title CIT CAMPUS ERP - NEON DATABASE TERMINAL
color 0B
cd /d "C:\Users\hp\cit-campus-erp"
node scripts\cit-neon-terminal.js
if %errorlevel% neq 0 (
    echo.
    echo [!] Terminal exited with status code %errorlevel%.
)
echo.
echo Press any key to close this terminal...
pause >nul
