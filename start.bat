@echo off
REM AnnSetu — one-command SIH demo launcher (run from the project root)
echo.
echo =============================================
echo   AnnSetu - starting the SIH demo stack
echo =============================================
echo.

docker compose up --build -d
if errorlevel 1 (
  echo.
  echo Startup failed. Please start Docker Desktop and run this file again.
  pause
  exit /b 1
)

echo.
echo Services are starting. The first run can take a minute while demo data is seeded.
echo.
echo   App:      http://localhost:5173
echo   API Docs: http://localhost:8000/docs
echo.
echo Demo farmer: 9876543210 / farmer123
echo Demo staff:  9876543220 / staff123
echo Demo officer: 9876543230 / officer123
echo.
pause
