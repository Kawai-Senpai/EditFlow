"""
Test script to verify FFmpeg installation and basic video operations.
This creates a simple test video and verifies FFmpeg/FFprobe work correctly.
"""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from core.config import FFMPEG_PATH, FFPROBE_PATH, TEMP_DIR, OUTPUT_DIR

OK = "[OK]"
FAIL = "[FAIL]"


def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def test_ffmpeg_installed():
    """Check if FFmpeg is installed and accessible"""
    print_header("Testing FFmpeg Installation")

    try:
        result = subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"{OK} FFmpeg found: {version_line}")
            return True
        print(f"{FAIL} FFmpeg error: {result.stderr}")
        return False
    except FileNotFoundError:
        print(f"{FAIL} FFmpeg not found at: {FFMPEG_PATH}")
        return False
    except Exception as e:
        print(f"{FAIL} FFmpeg error: {e}")
        return False


def test_ffprobe_installed():
    """Check if FFprobe is installed and accessible"""
    print_header("Testing FFprobe Installation")

    try:
        result = subprocess.run([FFPROBE_PATH, "-version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"{OK} FFprobe found: {version_line}")
            return True
        print(f"{FAIL} FFprobe error: {result.stderr}")
        return False
    except FileNotFoundError:
        print(f"{FAIL} FFprobe not found at: {FFPROBE_PATH}")
        return False
    except Exception as e:
        print(f"{FAIL} FFprobe error: {e}")
        return False


def create_test_video():
    """Create a simple test video using FFmpeg"""
    print_header("Creating Test Video")

    test_video = str(TEMP_DIR / "test_video.mp4")

    # Create a 5 second test video with color bars and tone
    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=5:size=1920x1080:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        test_video
    ]

    print(f"Running: {' '.join(cmd[:5])}...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and Path(test_video).exists():
            size = Path(test_video).stat().st_size / 1024
            print(f"{OK} Test video created: {test_video} ({size:.1f} KB)")
            return test_video
        print(f"{FAIL} Failed to create test video")
        print(f"  stderr: {result.stderr[:500]}")
        return None
    except Exception as e:
        print(f"{FAIL} Error creating test video: {e}")
        return None


def test_video_info(video_path):
    """Test getting video info using FFprobe"""
    print_header("Testing Video Info (FFprobe)")

    if not video_path:
        print(f"{FAIL} No video to test")
        return False

    import json

    cmd = [
        FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)

            # Find video stream
            video_stream = None
            audio_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                elif stream.get('codec_type') == 'audio':
                    audio_stream = stream

            if video_stream:
                print(f"{OK} Video info retrieved successfully:")
                print(f"  - Resolution: {video_stream.get('width')}x{video_stream.get('height')}")
                print(f"  - Codec: {video_stream.get('codec_name')}")
                print(f"  - FPS: {video_stream.get('r_frame_rate')}")
                print(f"  - Duration: {data.get('format', {}).get('duration')} seconds")

                if audio_stream:
                    print(f"  - Audio: {audio_stream.get('codec_name')}")

                return True
            print(f"{FAIL} No video stream found")
            return False
        print(f"{FAIL} FFprobe failed: {result.stderr}")
        return False
    except Exception as e:
        print(f"{FAIL} Error: {e}")
        return False


def test_video_processing(video_path):
    """Test basic video processing (re-encode)"""
    print_header("Testing Video Processing")

    if not video_path:
        print(f"{FAIL} No video to test")
        return False

    output_path = str(TEMP_DIR / "test_output.mp4")

    cmd = [
        FFMPEG_PATH, "-y",
        "-i", video_path,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "128k",
        "-progress", "pipe:2", "-nostats",
        output_path
    ]

    print("Re-encoding video...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        # Check for progress output
        progress_found = "out_time_ms=" in result.stderr

        if result.returncode == 0 and Path(output_path).exists():
            size = Path(output_path).stat().st_size / 1024
            print(f"{OK} Video processed successfully: {output_path} ({size:.1f} KB)")
            print(f"  - Progress reporting: {OK if progress_found else FAIL}")
            return True
        print(f"{FAIL} Failed to process video")
        print(f"  stderr: {result.stderr[:500]}")
        return False
    except Exception as e:
        print(f"{FAIL} Error: {e}")
        return False


def test_video_processor_class():
    """Test the VideoProcessor class"""
    print_header("Testing VideoProcessor Class")

    try:
        from core.video_processor import VideoProcessor, ProcessingJob

        processor = VideoProcessor()
        print(f"{OK} VideoProcessor imported successfully")

        # Create a test job
        job = processor.create_job()
        print(f"{OK} Job created: {job.id}")

        return True
    except ImportError as e:
        print(f"{FAIL} Import error: {e}")
        return False
    except Exception as e:
        print(f"{FAIL} Error: {e}")
        return False


def cleanup_test_files():
    """Clean up test files"""
    print_header("Cleaning Up")

    test_files = [
        TEMP_DIR / "test_video.mp4",
        TEMP_DIR / "test_output.mp4"
    ]

    for f in test_files:
        if f.exists():
            f.unlink()
            print(f"  Deleted: {f}")

    print(f"{OK} Cleanup complete")


def main():
    print("\n" + "=" * 60)
    print("  VIDEO SCRIPT TOOL - FFmpeg Test Suite")
    print("=" * 60)
    print(f"\nFFmpeg path: {FFMPEG_PATH}")
    print(f"FFprobe path: {FFPROBE_PATH}")
    print(f"Temp dir: {TEMP_DIR}")
    print(f"Output dir: {OUTPUT_DIR}")

    results = {}

    # Run tests
    results['ffmpeg'] = test_ffmpeg_installed()
    results['ffprobe'] = test_ffprobe_installed()

    if results['ffmpeg'] and results['ffprobe']:
        test_video = create_test_video()
        results['create_video'] = test_video is not None

        if test_video:
            results['video_info'] = test_video_info(test_video)
            results['video_process'] = test_video_processing(test_video)

    results['processor_class'] = test_video_processor_class()

    # Cleanup
    cleanup_test_files()

    # Summary
    print_header("Test Summary")

    all_passed = True
    for test_name, passed in results.items():
        status = f"{OK} PASS" if passed else f"{FAIL} FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + ("All tests passed!" if all_passed else "Some tests failed!"))

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
