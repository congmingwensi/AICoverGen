@echo off
echo ============================================
echo 人声分离服务器启动脚本
echo ============================================
echo.

echo 1. 检查并安装依赖...
pip install flask flask-cors
if errorlevel 1 (
    echo 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)
echo 依赖安装完成！
echo.

echo 2. 检查模型文件...
if not exist ..\mdxnet_models\*.onnx (
    echo 未找到模型文件，开始下载...
    python download_models.py
    if errorlevel 1 (
        echo 模型下载失败，请检查网络连接
        pause
        exit /b 1
    )
    echo 模型下载完成！
) else (
    echo 模型文件已存在
)
echo.

echo 3. 启动服务器...
echo 服务器地址: http://0.0.0.0:5000
echo 健康检查: http://localhost:5000/health
echo 按 Ctrl+C 停止服务器
echo.

python separate_server.py --host 0.0.0.0 --port 5000

pause