import os
import subprocess
import random
import shutil
import glob
import math
import json

INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"
MUSIC_FOLDER = "music"

# Angle to zoom mapping
# Each angle has a specific zoom factor to hide its corners
ANGLE_ZOOM_MAP = {
    -3: 1.085,  # 8.5% zoom for 3° left
    -2: 1.05,  # 5% zoom for 2° left
    -1: 1.025,  # 2.5% zoom for 1° left
    1: 1.025,   # 2.5% zoom for 1° right
    2: 1.05,   # 5% zoom for 2° right
    3: 1.085,   # 8.5% zoom for 3° right
}

def clear_output_folder():
    if os.path.exists(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_video_files(folder):
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
    files = {}
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.isfile(filepath):
            _, ext = os.path.splitext(filename)
            if ext.lower() in video_extensions:
                key = filepath.lower()
                files[key] = filepath
    return sorted(files.values())

def get_video_resolution(video_path):
    """Get video width and height"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        width = data['streams'][0]['width']
        height = data['streams'][0]['height']
        return width, height
    except:
        return 1920, 1080

def get_random_filters():
    filters = []
    if random.random() > 0.3:
        rs = random.uniform(-0.05, 0.05)
        gs = random.uniform(-0.05, 0.05)
        bs = random.uniform(-0.05, 0.05)
        rm = random.uniform(-0.05, 0.05)
        gm = random.uniform(-0.05, 0.05)
        bm = random.uniform(-0.05, 0.05)
        filters.append(f"colorbalance=rs={rs:.3f}:gs={gs:.3f}:bs={bs:.3f}:rm={rm:.3f}:gm={gm:.3f}:bm={bm:.3f}")
    if random.random() > 0.5:
        brightness = random.uniform(-0.02, 0.02)
        contrast = random.uniform(0.98, 1.02)
        filters.append(f"eq=brightness={brightness:.3f}:contrast={contrast:.3f}")
    if random.random() > 0.5:
        saturation = random.uniform(0.95, 1.05)
        filters.append(f"eq=saturation={saturation:.3f}")
    return filters

def uniquify_video(input_video, music_video, output_video):
    """
    Process video with:
    1. Random angle selection from ANGLE_ZOOM_MAP
    2. Corresponding fixed zoom for that angle
    3. All other uniquification (mirror, filters, etc.)
    """

    # Get original resolution
    orig_w, orig_h = get_video_resolution(input_video)

    # SELECT ONE RANDOM ANGLE with its fixed zoom
    angle_degrees = random.choice(list(ANGLE_ZOOM_MAP.keys()))
    zoom_factor = ANGLE_ZOOM_MAP[angle_degrees]
    angle_radians = angle_degrees * math.pi / 180

    # Random parameters (rest of uniquification)
    mirror = random.random() > 0.5

    # Build filter chain
    filter_parts = []

    # 1. Rotate with black background
    filter_parts.append(f"rotate={angle_radians:.6f}:fillcolor=black")

    # 2. Apply zoom corresponding to this angle to hide corners
    zoom_w = int(orig_w / zoom_factor)
    zoom_h = int(orig_h / zoom_factor)
    zoom_w = zoom_w if zoom_w % 2 == 0 else zoom_w - 1
    zoom_h = zoom_h if zoom_h % 2 == 0 else zoom_h - 1
    filter_parts.append(f"crop={zoom_w}:{zoom_h}:(iw-{zoom_w})/2:(ih-{zoom_h})/2")

    # 3. Scale to VERTICAL 1080x1920 (Instagram Reels format)
    filter_parts.append("scale=1080:1920:force_original_aspect_ratio=decrease")
    filter_parts.append("pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black")

    # 4. Mirror if needed
    if mirror:
        filter_parts.append("hflip")

    # 5. Add random visual filters
    random_filters = get_random_filters()
    filter_parts.extend(random_filters)

    video_filter = ",".join(filter_parts)

    # Step 1: Process video without audio
    temp_video = output_video.replace('.mp4', '_temp.mp4')
    cmd1 = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "error",
        "-i", input_video,
        "-filter:v", video_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        "-y",
        temp_video
    ]

    try:
        subprocess.run(cmd1, check=True)
    except Exception as e:
        print(f"  ✗ Video failed")
        return

    # Step 2: Add audio from music video
    cmd2 = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "error",
        "-i", temp_video,
        "-i", music_video,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-map_metadata", "-1",
        "-movflags", "+faststart",
        "-y",
        output_video
    ]

    try:
        subprocess.run(cmd2, check=True)
        mirror_str = "🔀" if mirror else "  "
        print(f"✓ {os.path.basename(output_video)} | Angle: {angle_degrees:+3d}° | Zoom: {zoom_factor:.4f}x | Mirror: {mirror_str}")
        if os.path.exists(temp_video):
            os.remove(temp_video)
    except Exception as e:
        print(f"  ✗ Audio merge failed")
        if os.path.exists(temp_video):
            os.remove(temp_video)

def main():
    print("=" * 85)
    print("Instagram Video Uniquifier (Random Angle + Fixed Zoom)")
    print("=" * 85)

    if not os.path.exists(INPUT_FOLDER) or not os.path.exists(MUSIC_FOLDER):
        print("Error: input or music folder missing!")
        return

    input_videos = get_video_files(INPUT_FOLDER)
    music_videos = get_video_files(MUSIC_FOLDER)

    if not input_videos or not music_videos:
        print("No videos found!")
        return

    print(f"\nSource: {len(input_videos)} videos")
    print(f"Music: {len(music_videos)} tracks")
    print(f"Creating {len(input_videos) * len(music_videos)} outputs\n")

    print("Angle-to-Zoom Mapping:")
    for angle, zoom in sorted(ANGLE_ZOOM_MAP.items()):
        print(f"  {angle:+3d}° → {zoom:.4f}x zoom ({(zoom-1)*100:.1f}% crop)")
    print()

    clear_output_folder()

    for i, input_video in enumerate(input_videos, 1):
        for j, music_video in enumerate(music_videos, 1):
            output_filename = f"{i}.{j}.mp4"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            uniquify_video(input_video, music_video, output_path)

    print("\n" + "=" * 85)
    print(f"Done! Created {len(input_videos) * len(music_videos)} unique videos")
    print("Format: 1080x1920 vertical | Corners hidden by corresponding zoom!")
    print("=" * 85)

if __name__ == "__main__":
    main()
