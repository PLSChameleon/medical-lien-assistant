@echo off
title Test Analyze Email Cache Feature
cls

echo ===============================================
echo     TEST ANALYZE EMAIL CACHE - FIXED VERSION
echo ===============================================
echo.
echo This tests the FIXED email cache analysis that resolves:
echo - "Missing from bootstrap" errors
echo - Cases not showing in stale cases tab
echo - UI freezing/"Not Responding" issues
echo.
echo FIXES APPLIED:
echo 1. EnhancedCollectionsTracker now properly saves data
echo 2. Stale cases tab uses correct tracker (enhanced)
echo 3. Worker thread correctly calls analyze_from_cache
echo 4. Data is saved to collections_tracking_enhanced.json
echo.
echo EXPECTED BEHAVIOR:
echo 1. Progress dialog with live updates (no freezing)
echo 2. Log messages showing email/case processing
echo 3. Analysis finds matches between emails and cases
echo 4. Stale cases tab shows categorized cases
echo 5. No more "missing from bootstrap" errors
echo.
echo TESTING STEPS:
echo 1. Start the application
echo 2. Go to Tools -^> Analyze Email Cache
echo 3. Wait for completion (watch the progress)
echo 4. Click "Stale Cases" tab
echo 5. Click "Refresh Analysis" button
echo 6. Verify cases appear in categories
echo.
echo BEFORE TESTING:
echo - Cases spreadsheet must be uploaded
echo - Email history must be downloaded
echo.
pause

echo.
echo Starting application...
python enhanced_gui_app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application failed to start.
    echo Please check if Python is installed and all dependencies are met.
    pause
    exit /b 1
)

pause