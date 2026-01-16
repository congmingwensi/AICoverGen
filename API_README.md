# 人声伴奏分离API服务器

这是一个基于Flask的REST API服务器，用于分离音乐文件中的人声和伴奏。

## 功能

- 上传音频文件（支持mp3、wav等格式）
- 使用MDX-Net模型分离人声和伴奏
- 下载分离后的音频文件

## 安装

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 下载MDX-Net模型：
```bash
python src/download_models.py
```

## 运行服务器

```bash
python src/separate_vocals.py
```

服务器将在 `http://localhost:5000` 上运行。

## API端点

### 1. 分离音频

**端点**: `POST /separate`

**参数**:
- `audio`: 音频文件（multipart/form-data）

**响应**:
```json
{
  "success": true,
  "vocals_path": "song_output/xxx_Vocals.wav",
  "instrumentals_path": "song_output/xxx_Instrumental.wav"
}
```

**示例** (Python):
```python
import requests

with open('song.mp3', 'rb') as f:
    files = {'audio': f}
    response = requests.post('http://localhost:5000/separate', files=files)
    result = response.json()
    print(result)
```

### 2. 下载文件

**端点**: `GET /download/<filename>`

**参数**:
- `filename`: 要下载的文件名

**响应**: 音频文件（二进制）

**示例** (Python):
```python
import requests

response = requests.get('http://localhost:5000/download/xxx_Vocals.wav')
with open('vocals.wav', 'wb') as f:
    f.write(response.content)
```

### 3. 健康检查

**端点**: `GET /health`

**响应**:
```json
{
  "status": "healthy"
}
```

## 测试

运行测试脚本：
```bash
python test_api.py
```

确保在项目根目录下有一个名为 `test_audio.mp3` 的测试音频文件。

## 注意事项

- 服务器支持的最大文件大小为500MB
- 分离后的文件保存在 `song_output` 目录中
- 需要确保已安装ffmpeg和sox
- 建议使用GPU以获得更快的处理速度
