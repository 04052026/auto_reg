@echo off
title Kiro Auto-Reg - Quick Install
color 0A

echo ============================================================
echo    KIRO AUTO-REGISTRATION TOOL - CAI DAT NHANH
echo ============================================================
echo.

:: === TIM PYTHON ===
echo [1/5] Dang tim Python...

set "PYTHON_CMD="

:: Thu py launcher (uu tien nhat tren Windows)
py -3.12 --version >nul 2>&1 && set "PYTHON_CMD=py -3.12" && goto :found
py -3.11 --version >nul 2>&1 && set "PYTHON_CMD=py -3.11" && goto :found
py -3.10 --version >nul 2>&1 && set "PYTHON_CMD=py -3.10" && goto :found
py -3 --version >nul 2>&1 && set "PYTHON_CMD=py -3" && goto :found

:: Thu python trong PATH
python --version >nul 2>&1 && set "PYTHON_CMD=python" && goto :found

:: Thu duong dan pho bien
if exist "C:\Python312\python.exe" set "PYTHON_CMD=C:\Python312\python.exe" && goto :found
if exist "C:\Python311\python.exe" set "PYTHON_CMD=C:\Python311\python.exe" && goto :found
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe" && goto :found
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe" && goto :found
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe" && goto :found

:: Khong tim thay
echo.
echo [LOI] Khong tim thay Python 3.10+
echo.
echo Tai Python tai: https://www.python.org/downloads/
echo QUAN TRONG: Tick "Add Python to PATH" khi cai!
echo.
pause
exit /b 1

:found
echo    OK: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

:: === TAO VENV ===
echo [2/5] Tao virtual environment...
if exist "venv\Scripts\activate.bat" (
    echo    Da co venv, bo qua.
) else (
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo [LOI] Tao venv that bai!
        pause
        exit /b 1
    )
    echo    Tao venv thanh cong.
)
echo.

:: Kich hoat venv
call venv\Scripts\activate.bat

:: === CAI DEPENDENCIES ===
echo [3/5] Cai thu vien Python...
pip install --upgrade pip --quiet 2>nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [LOI] Cai thu vien that bai! Kiem tra mang.
    pause
    exit /b 1
)
echo    Cai thu vien thanh cong.
echo.

:: === CAI PLAYWRIGHT ===
echo [4/5] Cai Chromium browser (Playwright)...
echo    (Download ~150MB, cho vai phut)
playwright install chromium
echo    Chromium da san sang.
echo.

:: === TAO THU MUC ===
echo [5/5] Tao thu muc...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
echo    OK.
echo.

:: === TAO START.BAT ===
echo @echo off> start.bat
echo call "%%~dp0venv\Scripts\activate.bat">> start.bat
echo python "%%~dp0main.py" %%*>> start.bat

:: === HOAN TAT ===
echo ============================================================
echo    CAI DAT HOAN TAT!
echo ============================================================
echo.
echo    SU DUNG:
echo    -----------------------------------------
echo    start.bat register         Dang ky 1 acc
echo    start.bat register -n 5    Dang ky 5 acc
echo    start.bat schedule         Chay tu dong
echo    start.bat list             Xem danh sach
echo    start.bat switch 1         Chuyen account
echo    start.bat status           Trang thai
echo    -----------------------------------------
echo.
python main.py status 2>nul
echo.
echo Nhan phim bat ky de dang ky tai khoan...
pause >nul
python main.py register
pause
