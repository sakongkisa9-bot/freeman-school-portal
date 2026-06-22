@echo off
echo Clearing Windows Icon Cache...
echo.

taskkill /f /im explorer.exe
timeout /t 2 /nobreak >nul

del /f /q "%localappdata%\IconCache.db"
del /f /q "%localappdata%\Microsoft\Windows\Explorer\iconcache*"

echo Icon cache cleared.
echo Starting Windows Explorer...
start explorer.exe

echo.
echo Done! Please check if the icon displays correctly now.
pause
