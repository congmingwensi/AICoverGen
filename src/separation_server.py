import os
import sys
import tempfile
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vocals_separate import separate_vocals

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'separation_output')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'ogg', 'm4a', 'aac', 'wma'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': '人声分离服务运行正常'})

@app.route('/separate', methods=['POST'])
def separate_audio():
    if 'file' not in request.files:
        return jsonify({'error': '未找到音频文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if file and allowed_file(file.filename):
        try:
            task_id = str(uuid.uuid4())[:8]
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            input_filename = f"{task_id}_input.{file_ext}"
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
            
            file.save(input_path)
            
            output_dir = os.path.join(app.config['OUTPUT_FOLDER'], task_id)
            os.makedirs(output_dir, exist_ok=True)
            
            vocals_path, instrumental_path = separate_vocals(input_path, output_dir)
            
            response = {
                'status': 'success',
                'task_id': task_id,
                'files': {
                    'vocals': {
                        'filename': os.path.basename(vocals_path),
                        'url': f'/download/{task_id}/{os.path.basename(vocals_path)}'
                    },
                    'instrumental': {
                        'filename': os.path.basename(instrumental_path),
                        'url': f'/download/{task_id}/{os.path.basename(instrumental_path)}'
                    }
                },
                'message': '音频分离成功'
            }
            
            return jsonify(response), 200
            
        except Exception as e:
            return jsonify({'error': f'分离失败: {str(e)}'}), 500
    else:
        return jsonify({'error': '不支持的文件格式。支持的格式: ' + ', '.join(ALLOWED_EXTENSIONS)}), 400

@app.route('/download/<task_id>/<filename>', methods=['GET'])
def download_file(task_id, filename):
    try:
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], task_id)
        return send_from_directory(output_dir, filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': f'文件下载失败: {str(e)}'}), 404

@app.route('/info', methods=['GET'])
def server_info():
    info = {
        'service': 'AI音频人声分离服务',
        'description': '使用MDX-Net模型分离音频中的人声和伴奏',
        'endpoints': {
            'health': 'GET /health - 健康检查',
            'separate': 'POST /separate - 上传音频并分离',
            'download': 'GET /download/<task_id>/<filename> - 下载分离结果',
            'info': 'GET /info - 获取服务信息'
        },
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'max_file_size': f"{app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)} MB"
    }
    return jsonify(info)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='人声分离Flask服务器')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    print(f"\n{'='*50}")
    print("AI音频人声分离服务启动")
    print(f"访问地址: http://{args.host}:{args.port}")
    print(f"健康检查: curl http://{args.host}:{args.port}/health")
    print(f"服务信息: curl http://{args.host}:{args.port}/info")
    print('='*50)
    
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
