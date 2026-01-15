import json
import os
import sys

def check_dependencies():
    """检查必要的依赖是否已安装"""
    required_packages = {
        'librosa': 'librosa',
        'numpy': 'numpy',
        'torch': 'torch',
        'onnxruntime': 'onnxruntime-gpu',
        'soundfile': 'soundfile',
        'tqdm': 'tqdm'
    }
    
    missing_packages = []
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n⚠️  缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        print("或安装所有依赖:")
        print("pip install -r requirements.txt")
        print()
        sys.exit(1)

check_dependencies()

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import mdx

def load_model_params():
    """加载MDX模型参数配置"""
    model_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mdxnet_models', 'model_data.json')
    with open(model_data_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def separate_vocals(audio_path, output_dir, model_path=None):
    """
    分离音频文件中的人声和伴奏
    
    Args:
        audio_path: 输入音频文件路径
        output_dir: 输出目录
        model_path: MDX模型路径，如果为None则使用默认模型
        
    Returns:
        tuple: (vocals_path, instrumental_path)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    if model_path is None:
        mdxnet_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mdxnet_models')
        for file in os.listdir(mdxnet_dir):
            if file.endswith('.onnx'):
                model_path = os.path.join(mdxnet_dir, file)
                break
        
        if model_path is None:
            raise ValueError("未找到MDX模型文件，请确保mdxnet_models目录中存在.onnx模型文件")
    
    model_params = load_model_params()
    
    vocals_path, instrumental_path = mdx.run_mdx(
        model_params=model_params,
        output_dir=output_dir,
        model_path=model_path,
        filename=audio_path,
        exclude_main=False,
        exclude_inversion=False,
        suffix='Vocals',
        invert_suffix='Instrumental',
        denoise=False,
        keep_orig=True,
        m_threads=2
    )
    
    return vocals_path, instrumental_path

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='分离音频中的人声和伴奏')
    parser.add_argument('audio_path', help='输入音频文件路径')
    parser.add_argument('--output_dir', help='输出目录', default='output_separated')
    parser.add_argument('--model_path', help='MDX模型路径', default=None)
    
    args = parser.parse_args()
    
    try:
        vocals, instrumental = separate_vocals(args.audio_path, args.output_dir, args.model_path)
        print(f"人声文件: {vocals}")
        print(f"伴奏文件: {instrumental}")
    except Exception as e:
        print(f"错误: {e}")
