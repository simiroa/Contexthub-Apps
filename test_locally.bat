@echo off
echo Validating apps...
python .github/scripts/validate_apps.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: validate_apps.py found blocking issues. Aborting.
    pause
    exit /b 1
)

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
