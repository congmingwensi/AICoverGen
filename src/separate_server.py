import os
import sys
import tempfile
import uuid
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vocals_separate import separate_vocals

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'separated_output')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'ogg', 'm4a', 'aac', 'wma'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_model_path():
    """获取MDX模型路径"""
    mdxnet_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mdxnet_models')
    for file in os.listdir(mdxnet_dir):
        if file.endswith('.onnx'):
            return os.path.join(mdxnet_dir, file)
    return None

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/separate', methods=['POST'])
def separate_audio():
    """
    上传音频文件并分离人声和伴奏
    
    Request:
        - file: 音频文件
        - model_path: (可选) 模型路径
        
    Response:
        {
            'success': bool,
            'message': str,
            'vocals_url': str (可选),
            'instrumental_url': str (可选),
            'vocals_path': str (可选),
            'instrumental_path': str (可选)
        }
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未找到音频文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': '文件名不能为空'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': f'不支持的文件格式，支持的格式: {ALLOWED_EXTENSIONS}'}), 400
    
    unique_id = str(uuid.uuid4())
    
    filename = file.filename
    extension = os.path.splitext(filename)[1].lower()
    upload_filename = f"{unique_id}{extension}"
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], upload_filename)
    
    file.save(upload_path)
    
    output_subdir = os.path.join(app.config['OUTPUT_FOLDER'], unique_id)
    
    try:
        model_path = request.form.get('model_path', None) or get_model_path()
        
        if model_path is None:
            return jsonify({'success': False, 'message': '未找到MDX模型文件'}), 500
        
        vocals_path, instrumental_path = separate_vocals(
            audio_path=upload_path,
            output_dir=output_subdir,
            model_path=model_path
        )
        
        vocals_filename = os.path.basename(vocals_path)
        instrumental_filename = os.path.basename(instrumental_path)
        
        return jsonify({
            'success': True,
            'message': '分离成功',
            'vocals_url': f'/download/{unique_id}/{vocals_filename}',
            'instrumental_url': f'/download/{unique_id}/{instrumental_filename}',
            'vocals_path': vocals_path,
            'instrumental_path': instrumental_path,
            'session_id': unique_id
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'分离失败: {str(e)}'}), 500
    
    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)

@app.route('/download/<session_id>/<filename>', methods=['GET'])
def download_file(session_id, filename):
    """下载分离后的音频文件"""
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
    
    if not os.path.exists(output_dir):
        return jsonify({'success': False, 'message': '会话不存在'}), 404
    
    file_path = os.path.join(output_dir, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'message': '文件不存在'}), 404
    
    return send_from_directory(output_dir, filename, as_attachment=True)

@app.route('/info', methods=['GET'])
def server_info():
    """获取服务器信息"""
    model_path = get_model_path()
    
    return jsonify({
        'name': 'Vocals Separation Server',
        'version': '1.0.0',
        'status': 'running',
        'has_model': model_path is not None,
        'model_path': model_path if model_path else 'Not found',
        'allowed_extensions': list(ALLOWED_EXTENSIONS),
        'max_file_size_mb': app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024),
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'output_folder': app.config['OUTPUT_FOLDER']
    })

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='人声分离Flask服务器')
    parser.add_argument('--host', help='服务器主机地址', default='0.0.0.0')
    parser.add_argument('--port', help='服务器端口', type=int, default=5000)
    parser.add_argument('--debug', help='调试模式', action='store_true')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("人声分离服务器启动")
    print(f"访问地址: http://{args.host}:{args.port}")
    print("健康检查: http://{}:{}/health".format(args.host, args.port))
    print("服务器信息: http://{}:{}/info".format(args.host, args.port))
    print("API文档: POST http://{}:{}/separate".format(args.host, args.port))
    print("=" * 60)
    
    app.run(host=args.host, port=args.port, debug=args.debug)
