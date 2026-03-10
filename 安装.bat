@echo off
chcp 65001 >nul
echo 🚀 B站字幕提取工具 - 一键安装
echo ================================

echo 📦 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.8+
    echo 💡 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python 环境正常

echo 📦 安装依赖包...
pip install requests pyyaml

echo 📁 创建输出目录...
if not exist "output" mkdir output

echo 🔧 检查 BBDown 工具...
if not exist "tools\BBDown\BBDown.exe" (
    echo ⚠️  未找到 BBDown 工具
    echo 💡 请确保 tools/BBDown/BBDown.exe 存在
) else (
    echo ✅ BBDown 工具正常
)

echo.
echo 🎉 安装完成！
echo.
echo 📋 使用方法：
echo    1. 运行 "python 下载字幕.py" 开始使用
echo    2. 首次使用建议先获取 Cookie：
echo       - 进入 tools/BBDown 目录
echo       - 运行 BBDown.exe --login
echo       - 按提示完成登录
echo.
echo 📁 字幕文件将保存在 output/ 目录
echo.
pause