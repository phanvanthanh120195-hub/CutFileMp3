import os
import json
import subprocess
import shutil
import threading
import tkinter as tk
from tkinter import filedialog
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'Output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_duration(input_file):
    """Gets the duration of the media file using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json',
        input_file
    ]
    try:
        # startupinfo to hide console window on Windows
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, startupinfo=startupinfo)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except Exception as e:
        raise Exception(f"Error getting duration: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/browse-file')
def browse_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(filetypes=[("MP3 Files", "*.mp3")])
    root.destroy()
    if file_path:
        return jsonify({'path': file_path})
    return jsonify({'path': None})

@app.route('/api/browse-folder')
def browse_folder():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    folder_path = filedialog.askdirectory()
    root.destroy()
    if folder_path:
        return jsonify({'path': folder_path})
    return jsonify({'path': None})

@app.route('/api/get-output-folder')
def get_output_folder():
    """Return the path to the project's Output folder"""
    output_path = os.path.abspath(OUTPUT_FOLDER)
    return jsonify({'path': output_path})

@app.route('/api/file-info', methods=['POST'])
def file_info():
    data = request.json
    file_path = data.get('path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        duration = get_duration(file_path)
        return jsonify({'duration': duration})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/file/<path:filename>')
def serve_file(filename):
    directory = os.path.dirname(filename)
    name = os.path.basename(filename)
    return send_from_directory(directory, name)

import zipfile
import io

# ... (existing imports)

@app.route('/api/split', methods=['POST'])
def split_file():
    data = request.json
    input_file = data.get('inputFile')
    output_dir = data.get('outputDir')
    segments = data.get('segments')
    create_zip = data.get('createZip', False)

    if not input_file or not os.path.exists(input_file):
        return jsonify({'error': 'Input file not found'}), 400
    if not output_dir:
        return jsonify({'error': 'Output directory not specified'}), 400
    if not segments:
        return jsonify({'error': 'No segments defined'}), 400

    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    errors = []
    created_files = []

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    for i, seg in enumerate(segments):
        start = seg.get('start')
        end = seg.get('end')
        output_name = seg.get('outputName')
        
        if not output_name.endswith('.mp3'):
            output_name += '.mp3'
            
        output_path = os.path.join(output_dir, output_name)
        
        cmd = [
            'ffmpeg',
            '-y',
            '-i', input_file,
            '-ss', str(start),
            '-to', str(end),
            '-c', 'copy',
            '-map', '0',
            '-vn',
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, startupinfo=startupinfo)
            results.append(output_name)
            created_files.append(output_path)
        except subprocess.CalledProcessError as e:
            errors.append(f"Error creating {output_name}: {e.stderr.decode() if e.stderr else 'Unknown error'}")

    zip_path = None
    if create_zip and created_files:
        zip_name = "segments.zip"
        zip_path = os.path.join(output_dir, zip_name)
        try:
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file in created_files:
                    zipf.write(file, os.path.basename(file))
            results.append(zip_name)
        except Exception as e:
            errors.append(f"Error creating zip: {str(e)}")

    return jsonify({'success': True, 'created': results, 'errors': errors, 'zipPath': zip_path})

@app.route('/api/list-mp3-files', methods=['POST'])
def list_mp3_files():
    """List all MP3 files in a folder with metadata"""
    data = request.json
    folder_path = data.get('folderPath')
    
    if not folder_path or not os.path.exists(folder_path):
        return jsonify({'error': 'Folder not found'}), 404
    
    if not os.path.isdir(folder_path):
        return jsonify({'error': 'Path is not a directory'}), 400
    
    mp3_files = []
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    try:
        # Get all MP3 files in the folder
        for filename in sorted(os.listdir(folder_path)):
            if filename.lower().endswith('.mp3'):
                file_path = os.path.join(folder_path, filename)
                try:
                    # Get duration
                    duration = get_duration(file_path)
                    # Get file size
                    size = os.path.getsize(file_path)
                    
                    mp3_files.append({
                        'filename': filename,
                        'path': file_path,
                        'duration': duration,
                        'size': size
                    })
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    continue
        
        return jsonify({'files': mp3_files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/join-mp3', methods=['POST'])
def join_mp3():
    """Join multiple MP3 files into a single output file"""
    data = request.json
    file_paths = data.get('filePaths')
    output_path = data.get('outputPath')
    
    if not file_paths or len(file_paths) == 0:
        return jsonify({'error': 'No files provided'}), 400
    
    if not output_path:
        return jsonify({'error': 'Output path not specified'}), 400
    
    # Verify all input files exist
    for file_path in file_paths:
        if not os.path.exists(file_path):
            return jsonify({'error': f'File not found: {file_path}'}), 404
    
    # Create a temporary file list for FFmpeg concat
    temp_list_path = os.path.join(os.path.dirname(output_path), 'temp_filelist.txt')
    
    try:
        # Write file list
        with open(temp_list_path, 'w', encoding='utf-8') as f:
            for file_path in file_paths:
                # Escape single quotes and use absolute paths
                escaped_path = file_path.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
        
        # Ensure output has .mp3 extension
        if not output_path.lower().endswith('.mp3'):
            output_path += '.mp3'
        
        # Run FFmpeg concat
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        cmd = [
            'ffmpeg',
            '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', temp_list_path,
            '-c', 'copy',
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            startupinfo=startupinfo
        )
        
        # Clean up temp file
        if os.path.exists(temp_list_path):
            os.remove(temp_list_path)
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else 'Unknown error'
            return jsonify({'error': f'FFmpeg error: {error_msg}'}), 500
        
        if not os.path.exists(output_path):
            return jsonify({'error': 'Output file was not created'}), 500
        
        return jsonify({
            'success': True,
            'outputPath': output_path,
            'message': f'Successfully joined {len(file_paths)} files'
        })
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_list_path):
            os.remove(temp_list_path)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Open browser automatically
    threading.Timer(1.5, lambda: subprocess.run(['start', 'http://127.0.0.1:5000'], shell=True)).start()
    app.run(debug=True, use_reloader=False)
