@echo off
setlocal enabledelayedexpansion
title Kiro Auto-Reg - Quick Install
color 0A

echo ============================================================
echo    KIRO AUTO-REGISTRATION TOOL - CAI DAT NHANH
echo    Tu dong cai dat moi thu can thiet va khoi dong tool
echo ============================================================
echo.

:: === BUOC 1: Tim Python phu hop ===
echo [1/5] Dang tim Python tren may...
echo.

set PYTHON_CMD=
set PYTHON_FOUND=0

:: Thu py launcher truoc (ho tro nhieu version Python tren Windows)
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo    Tim thay Python Launcher (py)...
    
    py -3.12 --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PYTHON_CMD=py -3.12
        set PYTHON_FOUND=1
        echo    Su dung: py -3.12
        goto :python_ok
    )
    py -3.11 --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PYTHON_CMD=py -3.11
        set PYTHON_FOUND=1
        echo    Su dung: py -3.11
        goto :python_ok
    )
    py -3.10 --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PYTHON_CMD=py -3.10
        set PYTHON_FOUND=1
        echo    Su dung: py -3.10
        goto :python_ok
    )
    py -3 --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PYTHON_CMD=py -3
        set PYTHON_FOUND=1
        echo    Su dung: py -3
        goto :python_ok
    )
)

:: Thu python
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PYTHON_CMD=python
        set PYTHON_FOUND=1
        echo    Su dung: python
        goto :python_ok
    )
)

:: Thu python3
where python3 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python3 --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PYTHON_CMD=python3
        set PYTHON_FOUND=1
        echo    Su dung: python3
        goto :python_ok
    )
)

:: Tim trong cac thu muc pho bien
if exist "C:\Python312\python.exe" (
    set "PYTHON_CMD=C:\Python312\python.exe"
    set PYTHON_FOUND=1
    echo    Su dung: C:\Python312\python.exe
    goto :python_ok
)
if exist "C:\Python311\python.exe" (
    set "PYTHON_CMD=C:\Python311\python.exe"
    set PYTHON_FOUND=1
    echo    Su dung: C:\Python311\python.exe
    goto :python_ok
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    set PYTHON_FOUND=1
    echo    Su dung: %LOCALAPPDATA%\Programs\Python\Python312\python.exe
    goto :python_ok
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    set PYTHON_FOUND=1
    echo    Su dung: %LOCALAPPDATA%\Programs\Python\Python311\python.exe
    goto :python_ok
)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    set PYTHON_FOUND=1
    echo    Su dung: %LOCALAPPDATA%\Programs\Python\Python310\python.exe
    goto :python_ok
)

:: Khong tim thay
echo.
echo [LOI] Khong tim thay Python 3.10+ tren may!
echo.
echo Vui long cai Python tu: https://www.python.org/downloads/
echo (Chon phien ban 3.11 hoac 3.12)
echo.
echo QUAN TRONG: Tick "Add Python to PATH" khi cai dat!
echo.
pause
exit /b 1

:python_ok
echo.
%PYTHON_CMD% --version
echo.

:: === BUOC 2: Tao Virtual Environment ===
echo [2/5] Tao moi truong ao (venv)...

if exist "venv\Scripts\activate.bat" (
    echo    Da co venv, bo qua...
) else (
    %PYTHON_CMD% -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [LOI] Khong the tao venv!
        echo    Thu chay: %PYTHON_CMD% -m pip install virtualenv
        pause
        exit /b 1
    )
    echo    Da tao venv thanh cong!
)
echo.

:: Kich hoat venv
call venv\Scripts\activate.bat

:: === BUOC 3: Cai dat dependencies ===
echo [3/5] Cai dat thu vien Python...
echo.

pip install --upgrade pip --quiet 2>nul
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LOI] Cai dependencies that bai!
    echo    Kiem tra ket noi mang va thu lai.
    pause
    exit /b 1
)
echo.
echo    Da cai xong dependencies!
echo.

:: === BUOC 4: Cai Playwright Chromium ===
echo [4/5] Cai dat trinh duyet Chromium (Playwright)...
echo    (Lan dau mat vai phut de download ~150MB)
echo.

playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CANH BAO] Cai Playwright co the that bai.
    echo    Thu chay thu cong: playwright install chromium
    echo.
)
echo.
echo    Da cai xong Chromium!
echo.

:: === BUOC 5: Tao thu muc ===
echo [5/5] Tao thu muc du lieu...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
echo    Da tao thu muc data\ va logs\
echo.

:: === Tao file start.bat tien ich ===
(
echo @echo off
echo call "%%~dp0venv\Scripts\activate.bat"
echo python "%%~dp0main.py" %%*
) > start.bat

:: === HOAN TAT ===
echo ============================================================
echo    CAI DAT HOAN TAT!
echo ============================================================
echo.
echo    Cac lenh su dung:
echo    ----------------------------------------------------------
echo    Dang ky 1 account:    start.bat register
echo    Dang ky 5 account:    start.bat register -n 5
echo    Chay tu dong:         start.bat schedule
echo    Xem danh sach:        start.bat list
echo    Chuyen account:       start.bat switch [ID]
echo    Xem trang thai:       start.bat status
echo    ----------------------------------------------------------
echo.
echo    Hoac dung truc tiep (khi venv da active):
echo    python main.py register
echo.

:: Kiem tra he thong
echo Dang kiem tra he thong...
echo.
python main.py status 2>nul
echo.
echo ============================================================
echo    Nhan phim bat ky de bat dau dang ky tai khoan...
echo ============================================================
pause >nul

python main.py register
echo.
echo Hoan tat! Nhan phim bat ky de dong.
pause >nul
