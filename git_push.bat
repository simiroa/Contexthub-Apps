@echo off
echo ========================================
echo Pushing changes to GitHub...
echo ========================================

git add .
git commit -m "Auto push: %date% %time%"

echo.
echo Pulling latest changes from remote...
git pull origin main

echo.
echo Pushing changes to GitHub...
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
