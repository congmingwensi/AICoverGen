@echo off
cd /d "%~dp0"

echo ============================================
echo 人声分离服务器启动器
echo ============================================
echo.

echo [1] 安装依赖
echo [2] 下载模型
echo [3] 启动服务器
echo [4] 完整安装并启动
echo [5] 退出
echo.
set /p choice="请选择操作 (1-5): "

if "%choice%"=="1" goto install_deps
if "%choice%"=="2" goto download_models
if "%choice%"=="3" goto start_server
if "%choice%"=="4" goto full_install
if "%choice%"=="5" exit

echo 无效选择
goto end

:install_deps
echo 正在安装依赖...
cd src
pip install flask flask-cors
cd ..
echo 依赖安装完成！
pause
goto end

:download_models
echo 正在下载模型...
cd src
python download_models.py
cd ..
echo 模型下载完成！
pause
goto end

:start_server
echo 正在启动服务器...
cd src
python separate_server.py --host 0.0.0.0 --port 5000
cd ..
goto end

:full_install
echo 完整安装流程...
echo.
echo 步骤1: 安装依赖...
cd src
pip install flask flask-cors
echo.
echo 步骤2: 下载模型...
python download_models.py
echo.
echo 步骤3: 启动服务器...
python separate_server.py --host 0.0.0.0 --port 5000
cd ..
goto end

:end
echo 完成！
