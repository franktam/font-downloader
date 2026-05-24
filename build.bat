@echo off
chcp 65001 >nul
echo ========================================
echo   字体识别下载工具 - 打包脚本
echo ========================================
echo.

:: 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

:: 安装依赖
echo [1/3] 正在安装依赖库...
python -m pip install requests beautifulsoup4 Pillow fonttools cssutils pyinstaller --quiet
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo      依赖安装完成 ✓

:: 清理旧构建产物
echo [2/3] 清理旧构建...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist "字体下载工具.spec" del /q "字体下载工具.spec"

:: 执行打包
echo [3/3] 正在打包（约需 1-2 分钟）...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "字体下载工具" ^
    --hidden-import fonttools ^
    --hidden-import fonttools.ttLib ^
    --hidden-import fonttools.ttLib.tables ^
    --hidden-import cssutils ^
    --hidden-import bs4 ^
    --hidden-import PIL ^
    --hidden-import PIL.ImageFont ^
    --collect-all fonttools ^
    font_downloader.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败，请查看上方错误信息
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包成功！
echo   可执行文件：dist\字体下载工具.exe
echo ========================================
echo.

:: 询问是否打开输出目录
set /p open_dir="是否立即打开 dist 目录？(y/n): "
if /i "%open_dir%"=="y" explorer dist

pause
