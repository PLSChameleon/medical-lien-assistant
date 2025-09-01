@echo off
echo.
echo Checking configuration...
echo =========================
echo.

echo Current directory:
cd
echo.

echo Checking for config.env:
if exist config.env (
    echo config.env FOUND
    echo.
    echo First few lines of config.env:
    type config.env | findstr "OPEN_AI_API_KEY"
) else (
    echo config.env NOT FOUND - This is the problem!
    echo Please make sure config.env is in the ai_assistant folder
)
echo.

echo Checking Python:
python --version
echo.

echo Testing environment loading:
python -c "import os; from dotenv import load_dotenv; load_dotenv(); key=os.getenv('OPEN_AI_API_KEY'); print('API Key found:', 'Yes' if key else 'No'); print('Key starts with:', key[:10] if key else 'NOT FOUND')"
echo.

pause