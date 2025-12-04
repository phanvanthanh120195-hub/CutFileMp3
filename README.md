# MP3 Splitter Tool

A simple command-line tool to split MP3 files into equal-length segments using `ffmpeg`.

## Prerequisites

1.  **Python 3**: Ensure Python is installed.
2.  **FFmpeg**: This tool requires `ffmpeg` and `ffprobe` to be installed and available in your system's PATH.
    *   **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, and add the `bin` folder to your System Environment Variables -> Path.
    *   **macOS**: `brew install ffmpeg`
    *   **Linux**: `sudo apt install ffmpeg`

## Usage

Open your terminal or command prompt and run:

```bash
python mp3_splitter.py <input_file> [options]
```

### Arguments

*   `input_file`: Path to the MP3 file you want to split.
*   `--segment-length`: (Optional) Length of each segment in seconds. Default is 30.
*   `--output-dir`: (Optional) Directory to save the output files. If not specified, files are saved in the same directory as the input file.

### Examples

**1. Default split (30 seconds) in the same directory:**

```bash
python mp3_splitter.py my_song.mp3
```

**2. Split into 10-second segments:**

```bash
python mp3_splitter.py my_song.mp3 --segment-length 10
```

**3. Split and save to a specific folder:**

```bash
python mp3_splitter.py my_song.mp3 --output-dir ./output_folder
```

## Output Format

Files are named in the format: `<index>_<rand5>.mp3`
Example: `1_a7x4k.mp3`, `2_z9p1q.mp3`
