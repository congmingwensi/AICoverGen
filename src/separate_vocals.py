# -*- coding: utf-8 -*-
import os
import json
import hashlib
import shutil
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from mdx import run_mdx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mdxnet_models_dir = os.path.join(BASE_DIR, 'mdxnet_models')
output_dir = os.path.join(BASE_DIR, 'song_output')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(output_dir, exist_ok=True)


def get_file_hash(filepath):
    with open(filepath, 'rb') as f:
        file_hash = hashlib.blake2b()
        while chunk := f.read(8192):
            file_hash.update(chunk)
    return file_hash.hexdigest()[:11]


def separate_vocals_and_instrumental(audio_path):
    with open(os.path.join(mdxnet_models_dir, 'model_data.json')) as infile:
        mdx_model_params = json.load(infile)

    model_path = os.path.join(mdxnet_models_dir, 'UVR-MDX-NET-Voc_FT.onnx')
    
    vocals_path, instrumentals_path = run_mdx(
        mdx_model_params,
        output_dir,
        model_path,
        audio_path,
        denoise=True,
        keep_orig=True
    )
    
    return vocals_path, instrumentals_path


@app.route('/separate', methods=['POST'])
def separate_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        vocals_path, instrumentals_path = separate_vocals_and_instrumental(filepath)
        
        return jsonify({
            'success': True,
            'vocals_path': vocals_path,
            'instrumentals_path': instrumentals_path
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    try:
        return send_file(os.path.join(output_dir, filename), as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
