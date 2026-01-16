# -*- coding: utf-8 -*-
import requests
import os

API_URL = 'http://localhost:5000'


def test_separate_audio(audio_file_path):
    with open(audio_file_path, 'rb') as f:
        files = {'audio': f}
        response = requests.post(f'{API_URL}/separate', files=files)
    
    if response.status_code == 200:
        result = response.json()
        print('Separation successful!')
        print(f'Vocals: {result["vocals_path"]}')
        print(f'Instrumentals: {result["instrumentals_path"]}')
        return result
    else:
        print(f'Error: {response.json()}')
        return None


def test_download_file(filename, output_path):
    response = requests.get(f'{API_URL}/download/{filename}')
    
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f'File downloaded to {output_path}')
        return True
    else:
        print(f'Error downloading file: {response.json()}')
        return False


def test_health():
    response = requests.get(f'{API_URL}/health')
    print(response.json())


if __name__ == '__main__':
    print('Testing health endpoint...')
    test_health()
    
    audio_file = input('Please enter the path to the audio file: ')
    
    if os.path.exists(audio_file):
        print(f'\nTesting separation with {audio_file}...')
        result = test_separate_audio(audio_file)
        
        if result:
            vocals_filename = os.path.basename(result['vocals_path'])
            inst_filename = os.path.basename(result['instrumentals_path'])
            
            test_download_file(vocals_filename, f'downloaded_{vocals_filename}')
            test_download_file(inst_filename, f'downloaded_{inst_filename}')
    else:
        print(f'Audio file not found: {audio_file}')
