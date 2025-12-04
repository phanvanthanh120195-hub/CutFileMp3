import FreeSimpleGUI as sg
import subprocess
import os
import random
import string
import sys
import json
import shutil
import threading

def get_random_string(length=5):
    """Generates a random string of fixed length using lowercase letters and digits."""
    letters_and_digits = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))

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

def split_mp3_thread(window, input_file, segment_length, output_dir):
    """Splits the MP3 file into segments (runs in a thread)."""
    try:
        if not os.path.exists(input_file):
            window.write_event_value('-LOG-', f"Error: Input file '{input_file}' not found.")
            window.write_event_value('-DONE-', None)
            return

        if shutil.which('ffmpeg') is None:
            window.write_event_value('-LOG-', "Error: ffmpeg not found. Please ensure ffmpeg is installed and in your PATH.")
            window.write_event_value('-DONE-', None)
            return

        window.write_event_value('-LOG-', f"Getting duration for: {input_file}")
        try:
            duration = get_duration(input_file)
        except Exception as e:
            window.write_event_value('-LOG-', str(e))
            window.write_event_value('-DONE-', None)
            return

        num_segments = int(duration // segment_length) + (1 if duration % segment_length > 0 else 0)
        
        window.write_event_value('-LOG-', f"Total duration: {duration:.2f}s")
        window.write_event_value('-LOG-', f"Splitting into {num_segments} segments of {segment_length}s each...")

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = os.path.dirname(os.path.abspath(input_file))

        created_files = 0
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        for i in range(num_segments):
            start_time = i * segment_length
            index = i + 1
            rand_suffix = get_random_string()
            output_filename = f"{index}_{rand_suffix}.mp3"
            output_path = os.path.join(output_dir, output_filename)
            
            while os.path.exists(output_path):
                rand_suffix = get_random_string()
                output_filename = f"{index}_{rand_suffix}.mp3"
                output_path = os.path.join(output_dir, output_filename)

            cmd = [
                'ffmpeg',
                '-y',
                '-i', input_file,
                '-ss', str(start_time),
                '-t', str(segment_length),
                '-c', 'copy',
                '-map', '0',
                '-vn',
                output_path
            ]

            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, startupinfo=startupinfo)
                window.write_event_value('-LOG-', f"Created: {output_filename}")
                created_files += 1
            except subprocess.CalledProcessError as e:
                window.write_event_value('-LOG-', f"Error creating segment {index}: {e.stderr.decode() if e.stderr else 'Unknown error'}")

        window.write_event_value('-LOG-', f"Done. Created {created_files} files in '{output_dir}'.")
        
    except Exception as e:
        window.write_event_value('-LOG-', f"An unexpected error occurred: {e}")
    finally:
        window.write_event_value('-DONE-', None)

def main():
    sg.theme('SystemDefault')

    layout = [
        [sg.Text("Input MP3 File:")],
        [sg.Input(key='-FILE-', enable_events=True), sg.FileBrowse(file_types=(("MP3 Files", "*.mp3"),))],
        [sg.Text("Segment Length (seconds):")],
        [sg.Input("30", key='-LENGTH-')],
        [sg.Text("Output Folder:")],
        [sg.Input(key='-FOLDER-'), sg.FolderBrowse()],
        [sg.Button("Start Split"), sg.Button("Exit")],
        [sg.Multiline(size=(60, 15), key='-LOG-', autoscroll=True, disabled=True)]
    ]

    window = sg.Window("MP3 Splitter Tool", layout)

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == "Exit":
            break

        if event == "Start Split":
            input_file = values['-FILE-']
            output_dir = values['-FOLDER-']
            length_str = values['-LENGTH-']

            if not input_file:
                sg.popup_error("Please select an input file.")
                continue
            
            if not output_dir:
                 sg.popup_error("Please select an output folder.")
                 continue

            try:
                segment_length = float(length_str)
                if segment_length <= 0:
                    raise ValueError
            except ValueError:
                sg.popup_error("Segment length must be a positive number.")
                continue

            window['-LOG-'].update("") # Clear log
            window['Start Split'].update(disabled=True)
            
            # Start thread
            threading.Thread(target=split_mp3_thread, args=(window, input_file, segment_length, output_dir), daemon=True).start()

        if event == '-LOG-':
            window['-LOG-'].update(values[event] + '\n', append=True)
        
        if event == '-DONE-':
            window['Start Split'].update(disabled=False)
            sg.popup("Processing Complete!")

    window.close()

if __name__ == "__main__":
    main()
