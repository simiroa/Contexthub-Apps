@echo off
echo Testing Market Registry Generation...
python .github/scripts/package_apps.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Success! 'market.json' has been generated in the root folder.
    echo Check the 'dist' folder for packaged ZIP files.
) else (
    echo.
    echo Error: Generation failed.
)
pause
