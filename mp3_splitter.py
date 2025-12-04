import argparse
import subprocess
import os
import random
import string
import sys
import json
import shutil

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
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except subprocess.CalledProcessError as e:
        print(f"Error getting duration: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, json.JSONDecodeError, ValueError):
        print("Error parsing duration from ffprobe output.", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: ffprobe not found. Please ensure ffmpeg is installed and in your PATH.", file=sys.stderr)
        sys.exit(1)

def split_mp3(input_file, segment_length, output_dir):
    """Splits the MP3 file into segments."""
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.", file=sys.stderr)
        sys.exit(1)

    if segment_length <= 0:
        print("Error: Segment length must be greater than 0.", file=sys.stderr)
        sys.exit(1)

    # Check if ffmpeg is available
    if shutil.which('ffmpeg') is None:
        print("Error: ffmpeg not found. Please ensure ffmpeg is installed and in your PATH.", file=sys.stderr)
        sys.exit(1)

    duration = get_duration(input_file)
    num_segments = int(duration // segment_length) + (1 if duration % segment_length > 0 else 0)
    
    print(f"Total duration: {duration:.2f}s")
    print(f"Splitting into {num_segments} segments of {segment_length}s each...")

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = os.path.dirname(os.path.abspath(input_file))

    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    created_files = 0
    
    for i in range(num_segments):
        start_time = i * segment_length
        # Ensure we don't go past the end, though ffmpeg handles this gracefully usually.
        # For the last segment, we can just let it run to end or specify duration.
        # Specifying duration is safer to ensure equal chunks except last.
        
        index = i + 1
        rand_suffix = get_random_string()
        output_filename = f"{index}_{rand_suffix}.mp3"
        output_path = os.path.join(output_dir, output_filename)
        
        # Handle existing file
        while os.path.exists(output_path):
            rand_suffix = get_random_string()
            output_filename = f"{index}_{rand_suffix}.mp3"
            output_path = os.path.join(output_dir, output_filename)

        cmd = [
            'ffmpeg',
            '-y', # Overwrite if we somehow generated a name that exists (though we check above)
            '-i', input_file,
            '-ss', str(start_time),
            '-t', str(segment_length),
            '-c', 'copy', # Fast stream copy
            '-map', '0', # Map all streams
            '-vn', # Disable video
            output_path
        ]

        # Suppress ffmpeg output unless error
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print(f"Created: {output_filename}")
            created_files += 1
        except subprocess.CalledProcessError as e:
            print(f"Error creating segment {index}: {e.stderr.decode()}", file=sys.stderr)

    print(f"Done. Created {created_files} files in '{output_dir}'.")

def main():
    parser = argparse.ArgumentParser(description="Split MP3 file into equal length segments.")
    parser.add_argument("input_file", help="Path to the input MP3 file.")
    parser.add_argument("--segment-length", type=float, default=30.0, help="Segment length in seconds (default: 30).")
    parser.add_argument("--output-dir", help="Directory to save output files (default: same as input).")

    args = parser.parse_args()

    split_mp3(args.input_file, args.segment_length, args.output_dir)

if __name__ == "__main__":
    main()
