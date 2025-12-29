# Windows PowerShell 编译脚本
# 在 PowerShell 中运行: .\compile_windows.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Windows EXE 编译脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "[1/3] 检查 Python 版本..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host $pythonVersion -ForegroundColor Green
} catch {
    Write-Host "[错误] 未找到 Python，请先安装 Python 3.7+" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[2/3] 安装依赖包..." -ForegroundColor Yellow
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] pip 升级失败" -ForegroundColor Red
    exit 1
}

pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 依赖安装失败" -ForegroundColor Red
    exit 1
}

pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] PyInstaller 安装失败" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3/3] 开始编译..." -ForegroundColor Yellow
pyinstaller build.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 编译失败" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "编译完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "exe 文件位置: dist\DomainKiller.exe" -ForegroundColor Cyan
Write-Host ""
Write-Host "注意: 运行程序时需要以管理员身份运行" -ForegroundColor Yellow
Write-Host ""

