@echo off
chcp 65001 >nul
title 元素捕手 - 构建脚本

echo ============================================
echo      元素捕手 Element Crawler
echo ============================================
echo.

echo [1/3] 检查环境...
where adb >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 未找到 ADB，请确保 Android SDK platform-tools 已添加到环境变量
    pause
    exit /b 1
)

where scrcpy >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 警告: 未找到 scrcpy，请确保 scrcpy 已安装
)

echo [2/3] 安装 Python 依赖...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo 错误: Python 依赖安装失败
    pause
    exit /b 1
)

echo [3/3] 环境检查完成!
echo.
echo ============================================
echo 使用说明:
echo ============================================
echo 1. 在 Android 手机上安装并运行元素捕手.apk
echo 2. 授予无障碍权限给元素捕手应用
echo 3. 使用 USB 连接手机到电脑
echo 4. 运行 python main.py 启动 PC 端软件
echo 5. 在 PC 端软件中点击"连接设备"
echo.
echo 注意: 确保手机已开启 USB 调试模式
echo ============================================

pause
