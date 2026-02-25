@echo off
echo ========================================
echo Pushing changes to GitHub...
echo ========================================

git add .
git commit -m "Auto push: %date% %time%"
git push origin main

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Push failed. Please check the logs above.
) else (
    echo.
    echo [SUCCESS] All changes pushed successfully!
)

echo ========================================
pause
