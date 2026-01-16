# -*- coding: utf-8 -*-
import requests
import os

API_URL = 'http://localhost:5000'


def separate_audio(audio_file_path):
    """
    Separate vocals and instrumental from audio file
    
    Args:
        audio_file_path (str): Path to the audio file
        
    Returns:
        dict: Dictionary containing paths to vocals and instrumental files
    """
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f'Audio file not found: {audio_file_path}')
    
    with open(audio_file_path, 'rb') as f:
        files = {'audio': f}
        response = requests.post(f'{API_URL}/separate', files=files)
    
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        raise Exception(f'Separation failed: {response.json()}')


def download_file(filename, output_path):
    """
    Download separated audio file
    
    Args:
        filename (str): File name
        output_path (str): Save path
        
    Returns:
        bool: Whether download was successful
    """
    response = requests.get(f'{API_URL}/download/{filename}')
    
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    else:
        raise Exception(f'Download failed: {response.json()}')


if __name__ == '__main__':
    audio_file = input('Please enter the path to the audio file: ')
    
    try:
        print('Separating audio...')
        result = separate_audio(audio_file)
        
        print('Separation successful!')
        print(f'Vocals: {result["vocals_path"]}')
        print(f'Instrumental: {result["instrumentals_path"]}')
        
        vocals_filename = os.path.basename(result['vocals_path'])
        inst_filename = os.path.basename(result['instrumentals_path'])
        
        download_choice = input('Download the separated files? (y/n): ')
        if download_choice.lower() == 'y':
            output_dir = input('Enter save directory (default: current directory): ') or '.'
            
            vocals_output = os.path.join(output_dir, vocals_filename)
            inst_output = os.path.join(output_dir, inst_filename)
            
            print(f'Downloading vocals to {vocals_output}...')
            download_file(vocals_filename, vocals_output)
            
            print(f'Downloading instrumental to {inst_output}...')
            download_file(inst_filename, inst_output)
            
            print('All files downloaded!')
        
    except Exception as e:
        print(f'Error: {e}')
