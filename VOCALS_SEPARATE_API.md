# 人声分离API使用说明

## 概述
这个API提供了一个简单的接口，用于分离音频文件中的人声和伴奏。基于Flask服务器，可以随时调用。

## 安装依赖

```bash
pip install flask flask-cors
# 或者安装所有依赖
pip install -r requirements.txt
```

## 下载模型

在运行服务器之前，需要先下载MDX模型：

```bash
cd src
python download_models.py
```

这将下载必要的模型文件到 `mdxnet_models/` 目录。

## 启动服务器

### 方式1：基本启动
```bash
cd src
python separate_server.py
```

### 方式2：指定端口和主机
```bash
cd src
python separate_server.py --host 0.0.0.0 --port 5000
```

### 方式3：调试模式
```bash
cd src
python separate_server.py --debug
```

## API接口

### 1. 健康检查

**接口地址:** `GET /health`

**响应示例:**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T12:00:00.000000"
}
```

### 2. 服务器信息

**接口地址:** `GET /info`

**响应示例:**
```json
{
    "name": "Vocals Separation Server",
    "version": "1.0.0",
    "status": "running",
    "has_model": true,
    "model_path": "path/to/model.onnx",
    "allowed_extensions": ["wav", "mp3", "flac", "ogg", "m4a", "aac", "wma"],
    "max_file_size_mb": 200,
    "upload_folder": "path/to/uploads",
    "output_folder": "path/to/separated_output"
}
```

### 3. 分离人声和伴奏

**接口地址:** `POST /separate`

**请求方式:** `multipart/form-data`

**请求参数:**
- `file`: 音频文件（必需）
- `model_path`: 模型路径（可选）

**支持的音频格式:**
- wav, mp3, flac, ogg, m4a, aac, wma

**最大文件大小:** 200MB

**成功响应示例:**
```json
{
    "success": true,
    "message": "分离成功",
    "vocals_url": "/download/unique_id/filename_Vocals.wav",
    "instrumental_url": "/download/unique_id/filename_Instrumental.wav",
    "vocals_path": "full/path/to/filename_Vocals.wav",
    "instrumental_path": "full/path/to/filename_Instrumental.wav",
    "session_id": "unique_id"
}
```

**失败响应示例:**
```json
{
    "success": false,
    "message": "未找到音频文件"
}
```

### 4. 下载分离后的文件

**接口地址:** `GET /download/<session_id>/<filename>`

**响应:** 音频文件流

## 使用示例

### Python示例

```python
import requests

url = 'http://localhost:5000/separate'

files = {'file': open('test.mp3', 'rb')}

response = requests.post(url, files=files)

if response.status_code == 200:
    result = response.json()
    print(f"人声URL: {result['vocals_url']}")
    print(f"伴奏URL: {result['instrumental_url']}")
    
    # 下载文件
    vocals_response = requests.get('http://localhost:5000' + result['vocals_url'])
    with open('vocals.wav', 'wb') as f:
        f.write(vocals_response.content)
    
    instrumental_response = requests.get('http://localhost:5000' + result['instrumental_url'])
    with open('instrumental.wav', 'wb') as f:
        f.write(instrumental_response.content)
else:
    print(f"错误: {response.json()['message']}")
```

### cURL示例

```bash
# 上传文件并分离
curl -X POST -F "file=@test.mp3" http://localhost:5000/separate

# 下载人声文件
curl http://localhost:5000/download/<session_id>/filename_Vocals.wav -o vocals.wav

# 下载伴奏文件
curl http://localhost:5000/download/<session_id>/filename_Instrumental.wav -o instrumental.wav
```

### JavaScript示例

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:5000/separate', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        console.log('人声URL:', data.vocals_url);
        console.log('伴奏URL:', data.instrumental_url);
    } else {
        console.error('错误:', data.message);
    }
})
.catch(error => console.error('错误:', error));
```

## 直接使用函数

如果不想通过API使用，也可以直接调用分离函数：

```python
from vocals_separate import separate_vocals

vocals_path, instrumental_path = separate_vocals(
    audio_path='input.mp3',
    output_dir='output',
    model_path=None  # 使用默认模型
)

print(f"人声文件: {vocals_path}")
print(f"伴奏文件: {instrumental_path}")
```

## 注意事项

1. 首次使用需要下载模型文件
2. 分离大型音频文件可能需要较长时间
3. 确保服务器有足够的磁盘空间存储临时文件和输出文件
4. 建议使用GPU加速以获得更快的处理速度
5. 上传的文件会在处理完成后自动删除

## 文件存储

- 上传的临时文件: `uploads/` 目录
- 分离后的输出: `separated_output/<session_id>/` 目录
- 模型文件: `mdxnet_models/` 目录

## 故障排除

### 问题：服务器启动失败
**可能原因:**
- 端口被占用
- 模型文件缺失

**解决方案:**
- 使用 `--port` 参数指定其他端口
- 运行 `download_models.py` 下载模型

### 问题：分离失败
**可能原因:**
- 音频文件格式不支持
- 文件损坏
- 模型文件损坏

**解决方案:**
- 检查文件格式是否在支持列表中
- 尝试其他音频文件
- 重新下载模型文件

### 问题：下载文件失败
**可能原因:**
- Session ID错误
- 文件已被删除

**解决方案:**
- 检查Session ID是否正确
- 重新执行分离操作
