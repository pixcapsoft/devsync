@echo off
REM DevSync build script
REM Produces:
REM   dist\
REM     DevSyncGUI.exe       <- GUI (onefile, windowed)
REM     cli\
REM       cli.exe            <- CLI (onefile, console)
REM
REM The GUI discovers cli\cli.exe at runtime beside itself.
REM To ship a CLI update, simply replace cli\cli.exe — no GUI rebuild needed.

echo.
echo  ===  DevSync Builder  ===
echo.

REM ── Preflight ────────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from python.org and add to PATH.
    pause & exit /b 1
)

REM ── Dependencies ─────────────────────────────────────────────────────────────
echo [1/4] Installing dependencies...
pip install customtkinter watchdog pyinstaller --quiet
if errorlevel 1 ( echo [ERROR] pip install failed & pause & exit /b 1 )

REM ── Build CLI ────────────────────────────────────────────────────────────────
echo [2/4] Building CLI (cli\cli.exe)...
cd cli
pyinstaller cli.spec --clean --noconfirm --distpath ..\dist\cli
if errorlevel 1 ( echo [ERROR] CLI build failed & pause & cd .. & exit /b 1 )
cd ..

REM ── Build GUI ────────────────────────────────────────────────────────────────
echo [3/4] Building GUI (DevSyncGUI.exe)...
pyinstaller gui.spec --clean --noconfirm --distpath dist
if errorlevel 1 ( echo [ERROR] GUI build failed & pause & exit /b 1 )

REM ── Assemble final layout ────────────────────────────────────────────────────
echo [4/4] Assembling dist folder...

REM PyInstaller puts onefile output in dist\<name>\<name>.exe — flatten it
if exist dist\DevSyncGUI\DevSyncGUI.exe (
    move /Y dist\DevSyncGUI\DevSyncGUI.exe dist\DevSyncGUI.exe >nul
    rmdir /S /Q dist\DevSyncGUI
)
REM Same for CLI subfolder
if exist dist\cli\cli\cli.exe (
    move /Y dist\cli\cli\cli.exe dist\cli\cli.exe >nul
    rmdir /S /Q dist\cli\cli
)

echo.
echo  ===  Build complete!  ===
echo.
echo  dist\
echo    DevSyncGUI.exe
echo    cli\
echo      cli.exe
echo.
echo  Ship the entire dist\ folder. The GUI will not start without cli\cli.exe.
echo.
pause

