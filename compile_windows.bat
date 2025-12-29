@echo off
REM Windows 编译脚本
REM 在 Windows 上双击此文件即可自动编译

echo ==========================================
echo Windows EXE 编译脚本
echo ==========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.7+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 检查 Python 版本...
python --version

echo.
echo [2/3] 安装依赖包...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

pip install pyinstaller
if errorlevel 1 (
    echo [错误] PyInstaller 安装失败
    pause
    exit /b 1
)

echo.
echo [3/3] 开始编译...
pyinstaller build.spec
if errorlevel 1 (
    echo [错误] 编译失败
    pause
    exit /b 1
)

echo.
echo ==========================================
echo 编译完成！
echo ==========================================
echo.
echo exe 文件位置: dist\DomainKiller.exe
echo.
echo 注意: 运行程序时需要以管理员身份运行
echo.
pause

