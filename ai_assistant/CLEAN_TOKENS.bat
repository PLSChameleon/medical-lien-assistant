@echo off
title Clean Old Tokens
color 0E
cls

echo =====================================
echo  Token Cleanup Utility
echo =====================================
echo.
echo This will remove old authentication tokens to resolve conflicts.
echo.
pause

echo.
echo Cleaning up old tokens...
echo.

:: Delete old token files
if exist "token.pickle" (
    del /f /q "token.pickle"
    echo [✓] Removed token.pickle
)

if exist "credentials.json" (
    echo [!] Keeping credentials.json (OAuth client configuration)
)

if exist "user_credentials.json" (
    del /f /q "user_credentials.json"
    echo [✓] Removed user_credentials.json
)

if exist "gmail_token.json" (
    del /f /q "gmail_token.json"
    echo [✓] Removed gmail_token.json
)

if exist "token.json" (
    del /f /q "token.json"
    echo [✓] Removed token.json
)

:: Clean up any token files in subdirectories
if exist "tokens\" (
    rmdir /s /q "tokens"
    echo [✓] Removed tokens directory
)

if exist ".tokens\" (
    rmdir /s /q ".tokens"
    echo [✓] Removed .tokens directory
)

echo.
echo =====================================
echo  Cleanup Complete!
echo =====================================
echo.
echo Next steps:
echo 1. Run START_PROGRAM.bat to launch the application
echo 2. You will be prompted to authenticate with Gmail
echo 3. The authentication will be handled automatically
echo.
pause