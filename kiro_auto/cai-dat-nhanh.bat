@echo off
chcp 65001 >nul 2>&1
title Kiro Auto-Reg - Cài đặt nhanh
color 0A

echo ============================================================
echo    KIRO AUTO-REGISTRATION TOOL - CÀI ĐẶT NHANH
echo    Tự động cài đặt mọi thứ cần thiết và khởi động tool
echo ============================================================
echo.

:: === BƯỚC 1: Tìm Python phù hợp ===
echo [1/5] Đang tìm Python trên máy...

set PYTHON_CMD=
set PYTHON_VER=

:: Thử python3 trước (ưu tiên)
where python3 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2 delims= " %%v in ('python3 --version 2^>^&1') do set PYTHON_VER=%%v
    set PYTHON_CMD=python3
    goto :found_python
)

:: Thử python
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VER=%%v
    set PYTHON_CMD=python
    goto :found_python
)

:: Thử py launcher (Windows Python Launcher - hỗ trợ nhiều version)
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    :: Thử py -3.12 trước
    py -3.12 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        for /f "tokens=2 delims= " %%v in ('py -3.12 --version 2^>^&1') do set PYTHON_VER=%%v
        set PYTHON_CMD=py -3.12
        goto :found_python
    )
    :: Thử py -3.11
    py -3.11 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        for /f "tokens=2 delims= " %%v in ('py -3.11 --version 2^>^&1') do set PYTHON_VER=%%v
        set PYTHON_CMD=py -3.11
        goto :found_python
    )
    :: Thử py -3.10
    py -3.10 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        for /f "tokens=2 delims= " %%v in ('py -3.10 --version 2^>^&1') do set PYTHON_VER=%%v
        set PYTHON_CMD=py -3.10
        goto :found_python
    )
    :: Thử py -3 (bất kỳ Python 3 nào)
    py -3 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        for /f "tokens=2 delims= " %%v in ('py -3 --version 2^>^&1') do set PYTHON_VER=%%v
        set PYTHON_CMD=py -3
        goto :found_python
    )
)

:: Thử các đường dẫn phổ biến
if exist "C:\Python312\python.exe" (
    set PYTHON_CMD=C:\Python312\python.exe
    for /f "tokens=2 delims= " %%v in ('"C:\Python312\python.exe" --version 2^>^&1') do set PYTHON_VER=%%v
    goto :found_python
)
if exist "C:\Python311\python.exe" (
    set PYTHON_CMD=C:\Python311\python.exe
    for /f "tokens=2 delims= " %%v in ('"C:\Python311\python.exe" --version 2^>^&1') do set PYTHON_VER=%%v
    goto :found_python
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    for /f "tokens=2 delims= " %%v in ('"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" --version 2^>^&1') do set PYTHON_VER=%%v
    goto :found_python
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    for /f "tokens=2 delims= " %%v in ('"%LOCALAPPDATA%\Programs\Python\Python311\python.exe" --version 2^>^&1') do set PYTHON_VER=%%v
    goto :found_python
)

:: Không tìm thấy Python
echo.
echo [LỖI] Không tìm thấy Python 3.10+ trên máy!
echo.
echo Vui lòng cài Python từ: https://www.python.org/downloads/
echo (Chọn phiên bản 3.11 hoặc 3.12, tick "Add to PATH" khi cài)
echo.
pause
exit /b 1

:found_python
echo    Đã tìm thấy: Python %PYTHON_VER%
echo    Lệnh sử dụng: %PYTHON_CMD%
echo.

:: === BƯỚC 2: Tạo Virtual Environment ===
echo [2/5] Tạo môi trường ảo (venv)...

if exist "venv" (
    echo    Đã có venv, bỏ qua...
) else (
    %PYTHON_CMD% -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [LỖI] Không thể tạo venv. Thử cài: %PYTHON_CMD% -m pip install virtualenv
        pause
        exit /b 1
    )
    echo    Đã tạo venv thành công!
)
echo.

:: Kích hoạt venv
call venv\Scripts\activate.bat

:: === BƯỚC 3: Cài đặt dependencies ===
echo [3/5] Cài đặt thư viện cần thiết...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [LỖI] Cài dependencies thất bại!
    pause
    exit /b 1
)
echo    Đã cài xong dependencies!
echo.

:: === BƯỚC 4: Cài Playwright Chromium ===
echo [4/5] Cài đặt trình duyệt Chromium (Playwright)...
playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo [CẢNH BÁO] Cài Playwright browser có thể thất bại.
    echo    Thử chạy thủ công: playwright install chromium
)
echo    Đã cài xong Chromium!
echo.

:: === BƯỚC 5: Tạo thư mục dữ liệu ===
echo [5/5] Tạo thư mục dữ liệu...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
echo    Đã tạo thư mục data/ và logs/
echo.

:: === HOÀN TẤT ===
echo ============================================================
echo    CÀI ĐẶT HOÀN TẤT! 
echo ============================================================
echo.
echo    Các lệnh sử dụng:
echo    ----------------------------------------------------------
echo    Đăng ký 1 account:    python main.py register
echo    Đăng ký 5 account:    python main.py register -n 5
echo    Chạy tự động:         python main.py schedule
echo    Xem danh sách:        python main.py list
echo    Chuyển account:       python main.py switch [ID]
echo    ----------------------------------------------------------
echo.
echo    Đang khởi động tool...
echo.

:: Chạy tool
python main.py status
echo.
echo ============================================================
echo    Nhấn phím bất kỳ để bắt đầu đăng ký tài khoản...
echo ============================================================
pause >nul

python main.py register
echo.
pause
