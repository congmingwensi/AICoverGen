import os
import json
import shlex
import subprocess
import gc
import librosa
import numpy as np
from pathlib import Path
from src.mdx import run_mdx
from src.rvc import Config, load_hubert, get_vc, rvc_infer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
mdxnet_models_dir = os.path.join(BASE_DIR, "mdxnet_models")
rvc_models_dir = os.path.join(BASE_DIR, "rvc_models")
output_root = os.path.join(BASE_DIR, "song_output")


def convert_to_stereo_wav(audio_path: str) -> str:
    """
    仿照 main.py 里的 convert_to_stereo：
    - 保证是双声道
    - 保证是 wav
    """
    wave, sr = librosa.load(audio_path, mono=False, sr=44100)
    need_convert = (
        not isinstance(wave[0], np.ndarray)  # 单声道
        or not audio_path.lower().endswith(".wav")  # 不是 wav
    )
    if need_convert:
        out_path = f"{os.path.splitext(audio_path)[0]}_stereo.wav"
        cmd = shlex.split(
            f'ffmpeg -y -loglevel error -i "{audio_path}" -ac 2 -f wav "{out_path}"'
        )
        subprocess.run(cmd, check=True)
        return out_path
    else:
        return audio_path


def load_mdx_params():
    data_path = os.path.join(mdxnet_models_dir, "model_data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_rvc_model_paths(voice_model: str):
    rvc_model_filename, rvc_index_filename = None, None
    model_dir = os.path.join(rvc_models_dir, voice_model)
    if not os.path.isdir(model_dir):
        raise FileNotFoundError(f"RVC 模型目录不存在: {model_dir}")

    for file in os.listdir(model_dir):
        ext = os.path.splitext(file)[1].lower()
        if ext == ".pth":
            rvc_model_filename = file
        elif ext == ".index":
            rvc_index_filename = file

    if rvc_model_filename is None:
        raise FileNotFoundError(f"RVC 模型目录中未找到 .pth: {model_dir}")

    rvc_model_path = os.path.join(model_dir, rvc_model_filename)
    rvc_index_path = os.path.join(model_dir, rvc_index_filename) if rvc_index_filename else ""
    return rvc_model_path, rvc_index_path


def rvc_convert_vocals(
    voice_model: str,
    input_vocals_path: str,
    output_path: str,
    pitch_change: int = 0,
    f0_method: str = "rmvpe",
    index_rate: float = 0.5,
    filter_radius: int = 3,
    rms_mix_rate: float = 0.25,
    protect: float = 0.33,
    crepe_hop_length: int = 128,
    device: str = "cuda:0",
    is_half: bool = True,
):
    rvc_model_path, rvc_index_path = get_rvc_model_paths(voice_model)

    hubert_path = os.path.join(rvc_models_dir, "hubert_base.pt")
    if not os.path.isfile(hubert_path):
        raise FileNotFoundError(f"未找到 hubert_base.pt: {hubert_path}")

    config = Config(device, is_half)
    hubert_model = load_hubert(device, config.is_half, hubert_path)
    cpt, version, net_g, tgt_sr, vc = get_vc(device, config.is_half, config, rvc_model_path)

    rvc_infer(
        rvc_index_path,
        index_rate,
        input_vocals_path,
        output_path,
        pitch_change,
        f0_method,
        cpt,
        version,
        net_g,
        filter_radius,
        tgt_sr,
        rms_mix_rate,
        protect,
        crepe_hop_length,
        vc,
        hubert_model,
    )

    del hubert_model, cpt, net_g, vc
    gc.collect()


def separate_vocals_two_stage(input_audio: str,
                              base_model_name: str = "UVR-MDX-NET-Voc_FT.onnx",
                              clean_vocal_model_name: str = "UVR_MDXNET_KARA_2.onnx",
                              lead_vocal_model_name: str = "Reverb_HQ_By_FoxJoy.onnx",
                              device: str = "cuda",
                              progress_callback=None):
    """
    三阶段处理：
    1. 整首歌 -> base_model 分离出 人声 + 伴奏
    2. 人声 -> clean_vocal_model 分离出 主唱(Main) + 和声/备份(Backup)
    3. 主唱(Main) -> lead_vocal_model 分离出 去混响(DeReverb) + 混响成分(Reverb)
    返回: (raw_vocals_path, instrumental_path, main_vocals_path, backup_vocals_path, main_dereverb_path, main_reverb_path)
    """
    if progress_callback:
        progress_callback(5, "正在加载模型参数...")
    
    mdx_params = load_mdx_params()

    song_id = os.path.splitext(os.path.basename(input_audio))[0]
    song_dir = os.path.join(output_root, song_id)
    os.makedirs(song_dir, exist_ok=True)

    if progress_callback:
        progress_callback(10, "正在转换音频格式...")
    
    stereo_path = convert_to_stereo_wav(input_audio)
    
    if progress_callback:
        progress_callback(15, "正在加载基础模型...")
    
    base_model_path = os.path.join(mdxnet_models_dir, base_model_name)
    
    if progress_callback:
        progress_callback(20, "正在进行第一阶段分离（人声+伴奏）...")
    
    raw_vocals_path, instrumental_path = run_mdx(
        mdx_params,
        song_dir,
        base_model_path,
        stereo_path,
        denoise=True,
        keep_orig=True,
    )

    if progress_callback:
        progress_callback(45, "正在进行第二阶段分离（主唱+和声）...")
    
    clean_model_path = os.path.join(mdxnet_models_dir, clean_vocal_model_name)
    backup_vocals_path, main_vocals_path = run_mdx(
        mdx_params,
        song_dir,
        clean_model_path,
        raw_vocals_path,
        suffix="Backup",
        invert_suffix="Main",
        denoise=True,
        keep_orig=True,
    )

    if progress_callback:
        progress_callback(70, "正在进行第三阶段分离（去混响）...")
    
    lead_model_path = os.path.join(mdxnet_models_dir, lead_vocal_model_name)
    main_reverb_path, main_dereverb_path = run_mdx(
        mdx_params,
        song_dir,
        lead_model_path,
        main_vocals_path,
        suffix="Reverb",
        invert_suffix="DeReverb",
        denoise=True,
        keep_orig=True,
    )
    
    if progress_callback:
        progress_callback(85, "分离完成")
    
    return (
        raw_vocals_path,
        instrumental_path,
        main_vocals_path,
        backup_vocals_path,
        main_dereverb_path,
        main_reverb_path,
    )


def main_func(input_audio: str, voice_model: str = None, device: str = "cuda", progress_callback=None) -> tuple[str, str]:
    """
    主入口函数：接收音频文件，返回最终的人声和伴奏路径。
    
    Args:
        input_audio: 输入音频路径
        voice_model: (可选) RVC 模型文件夹名称。如果不传，则只进行分离。
        device: 运行设备，默认 cuda
        progress_callback: 进度回调函数，接收 (progress, status) 参数
        
    Returns:
        (final_vocal_path, instrumental_path): 元组，包含最终人声文件路径和伴奏文件路径
    """
    
    if not os.path.exists(input_audio):
        raise FileNotFoundError(f"输入文件不存在: {input_audio}")

    if progress_callback:
        progress_callback(0, "开始处理...")
    
    print(f"🚀 开始处理: {os.path.basename(input_audio)}")
    
    # 1. 调用原有的三阶段分离逻辑
    (
        raw_vocals,
        instrumental,
        main_vocals,
        backup_vocals,
        main_dereverb,
        main_reverb,
    ) = separate_vocals_two_stage(input_audio, device=device, progress_callback=progress_callback)

    # 默认选择 "去混响后的主唱" 作为最佳人声素材
    # 如果分离失败导致文件缺失，则回退到 main_vocals 或 raw_vocals
    best_clean_vocal = main_dereverb if os.path.exists(main_dereverb) else main_vocals
    
    final_vocal_path = best_clean_vocal

    # 2. 如果指定了 RVC 模型，则进行变声推理
    if voice_model:
        if progress_callback:
            progress_callback(90, "正在进行RVC变声...")
        
        print(f"🎤 检测到 RVC 模型 '{voice_model}'，准备进行变声...")
        
        # 构造输出路径：song_output/歌名/歌名_rvc.wav
        song_id = os.path.splitext(os.path.basename(input_audio))[0]
        rvc_out_path = os.path.join(output_root, song_id, f"{song_id}_rvc_{voice_model}.wav")
        
        try:
            # 调用 RVC 推理 (使用最佳干声作为输入)
            rvc_convert_vocals(
                voice_model=voice_model,
                input_vocals_path=best_clean_vocal,
                output_path=rvc_out_path,
                device=device
            )
            final_vocal_path = rvc_out_path
            print("✅ RVC 变声完成")
        except Exception as e:
            print(f"❌ RVC 变声失败，将返回原声: {e}")
            # 如果 RVC 失败，保持 final_vocal_path 为原声，不中断程序

    if progress_callback:
        progress_callback(100, "处理完成")
    
    return final_vocal_path, instrumental


# --- 新的程序入口 ---
if __name__ == "__main__":
    import sys
    
    # 简单的参数检查
    if len(sys.argv) < 2:
        print("用法: python split_vocals.py <音乐文件路径> [RVC模型名称]")
        sys.exit(1)

    input_path = sys.argv[1]
    # 如果有第3个参数，则作为模型名
    model_arg = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        # 调用封装好的函数
        vocal, inst = main_func(input_path, voice_model=model_arg)
        
        print("\n" + "="*30)
        print("🎉 处理流程结束！")
        print(f"🎹 最终伴奏: {inst}")
        print(f"🎤 最终人声: {vocal}")
        print("="*30 + "\n")
        
    except Exception as err:
        print(f"🚨 发生错误: {err}")
        sys.exit(1)