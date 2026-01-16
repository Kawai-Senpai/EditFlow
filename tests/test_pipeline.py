"""
Test the complete video processing pipeline.
Creates test videos and tests concatenation, splitting, and overlays.
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from core.config import FFMPEG_PATH, TEMP_DIR, OUTPUT_DIR
from core.video_processor import VideoProcessor, ProcessingJob

OK = "[OK]"
FAIL = "[FAIL]"


def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def create_test_video(name: str, duration: float, color: str = "blue") -> str:
    """Create a test video with given duration and color"""
    output_path = str(TEMP_DIR / f"{name}.mp4")

    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "lavfi", "-i", f"color=c={color}:duration={duration}:size=1920x1080:rate=30",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-vf", f"drawtext=text='{name}':fontsize=72:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode == 0 and Path(output_path).exists():
        return output_path
    print(f"{FAIL} Failed to create {name}: {result.stderr[:200]}")
    return None


def create_transparent_overlay(name: str, duration: float) -> str:
    """Create a transparent overlay (PNG sequence packed as video)"""
    output_path = str(TEMP_DIR / f"{name}_overlay.mov")

    # Create a transparent video with text (using png for alpha)
    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "lavfi", "-i", f"color=c=black@0:duration={duration}:size=1920x1080:rate=30,format=rgba",
        "-f", "lavfi", "-i", f"sine=frequency=880:duration={duration}",
        "-vf", f"drawtext=text='{name.upper()}':fontsize=48:fontcolor=white@0.8:x=(w-text_w)/2:y=50",
        "-c:v", "png",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0 and Path(output_path).exists():
        return output_path

    # Try with webm format as fallback
    output_path = str(TEMP_DIR / f"{name}_overlay.webm")
    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "lavfi", "-i", f"color=c=black@0:duration={duration}:size=1920x1080:rate=30,format=yuva420p",
        "-f", "lavfi", "-i", f"sine=frequency=880:duration={duration}",
        "-vf", f"drawtext=text='{name.upper()}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=50",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
        "-c:a", "libopus",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0 and Path(output_path).exists():
        return output_path

    # Final fallback: regular mp4
    output_path = str(TEMP_DIR / f"{name}_overlay.mp4")
    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "lavfi", "-i", f"color=c=black:duration={duration}:size=1920x1080:rate=30",
        "-f", "lavfi", "-i", f"sine=frequency=880:duration={duration}",
        "-vf", f"drawtext=text='{name.upper()}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=50",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0 and Path(output_path).exists():
        return output_path

    print(f"{FAIL} Failed to create overlay {name}: {result.stderr[:200]}")
    return None


def wait_for_job(processor: VideoProcessor, job: ProcessingJob, timeout: int = 300) -> bool:
    """Wait for a job to complete"""
    start = time.time()
    last_progress = -1

    while time.time() - start < timeout:
        if job.status == "completed":
            print(f"\n  Completed in {time.time() - start:.1f}s")
            return True
        if job.status == "failed":
            print(f"\n  Failed: {job.error}")
            return False
        if job.status == "cancelled":
            print("\n  Cancelled")
            return False

        if job.progress != last_progress:
            print(f"  Progress: {job.progress:.1f}%", end="\r")
            last_progress = job.progress

        time.sleep(0.2)

    print(f"\n  Timeout after {timeout}s")
    return False


def test_concatenation():
    """Test video concatenation"""
    print_header("Testing Video Concatenation")

    # Create test videos
    print("Creating test videos...")
    video1 = create_test_video("video1_red", 3, "red")
    video2 = create_test_video("video2_green", 3, "green")
    video3 = create_test_video("video3_blue", 3, "blue")

    if not all([video1, video2, video3]):
        print(f"{FAIL} Failed to create test videos")
        return False

    print(f"{OK} Test videos created")

    processor = VideoProcessor()
    job = processor.create_job()

    output_path = str(OUTPUT_DIR / "test_concat.mp4")

    print("Concatenating videos (cut transition)...")

    import threading

    def run_concat():
        try:
            processor.concatenate_videos(
                [video1, video2, video3],
                output_path,
                job,
                transition="cut",
                preset="youtube_1080p"
            )
            job.status = "completed"
        except Exception as e:
            job.status = "failed"
            job.error = str(e)

    thread = threading.Thread(target=run_concat)
    job.status = "processing"
    thread.start()

    success = wait_for_job(processor, job)
    thread.join(timeout=5)

    if success and Path(output_path).exists():
        # Verify output duration (should be ~9 seconds)
        info = processor.get_video_info(output_path)
        if info and 8 < info.duration < 10:
            print(f"{OK} Concatenation successful - Duration: {info.duration:.1f}s")
            return True
        print(f"{FAIL} Unexpected duration: {info.duration if info else 'unknown'}")
        return False
    print(f"{FAIL} Concatenation failed")
    return False


def test_crossfade():
    """Test video concatenation with crossfade"""
    print_header("Testing Crossfade Transition")

    # Use existing test videos if available
    video1 = str(TEMP_DIR / "video1_red.mp4")
    video2 = str(TEMP_DIR / "video2_green.mp4")

    if not Path(video1).exists() or not Path(video2).exists():
        print("Creating test videos...")
        video1 = create_test_video("cf_video1", 5, "orange")
        video2 = create_test_video("cf_video2", 5, "purple")

    if not all([video1, video2]):
        print(f"{FAIL} Failed to create test videos")
        return False

    processor = VideoProcessor()
    job = processor.create_job()

    output_path = str(OUTPUT_DIR / "test_crossfade.mp4")

    print("Concatenating with 1s crossfade...")

    import threading

    def run_concat():
        try:
            processor.concatenate_videos(
                [video1, video2],
                output_path,
                job,
                transition="crossfade",
                transition_duration=1.0,
                preset="youtube_1080p"
            )
            job.status = "completed"
        except Exception as e:
            job.status = "failed"
            job.error = str(e)

    thread = threading.Thread(target=run_concat)
    job.status = "processing"
    thread.start()

    success = wait_for_job(processor, job)
    thread.join(timeout=5)

    if success and Path(output_path).exists():
        info = processor.get_video_info(output_path)
        # Duration should be ~9s (5+5-1 crossfade)
        print(f"{OK} Crossfade successful - Duration: {info.duration:.1f}s")
        return True
    print(f"{FAIL} Crossfade failed")
    return False


def test_episode_split():
    """Test splitting into episodes"""
    print_header("Testing Episode Split")

    # Create a longer video
    print("Creating 30s test video...")
    long_video = create_test_video("long_video", 30, "navy")

    if not long_video:
        print(f"{FAIL} Failed to create test video")
        return False

    processor = VideoProcessor()
    job = processor.create_job()

    print("Splitting into 10s episodes with 2s overlap...")

    import threading
    episodes = []

    def run_split():
        try:
            result = processor.split_into_episodes(
                long_video,
                job,
                episode_duration=10,  # 10 second episodes
                overlap_seconds=2,    # 2 second overlap
                preset="youtube_1080p",
                output_prefix="TestEpisode"
            )
            episodes.extend(result)
            job.status = "completed"
        except Exception as e:
            job.status = "failed"
            job.error = str(e)

    thread = threading.Thread(target=run_split)
    job.status = "processing"
    thread.start()

    success = wait_for_job(processor, job, timeout=120)
    thread.join(timeout=5)

    if success and episodes:
        print(f"{OK} Split into {len(episodes)} episodes:")
        for ep in episodes:
            info = processor.get_video_info(ep)
            print(f"    - {Path(ep).name}: {info.duration:.1f}s")
        return True
    print(f"{FAIL} Episode split failed")
    return False


def cleanup_test_files():
    """Clean up all test files"""
    print_header("Cleaning Up")

    # Clean temp dir
    for f in TEMP_DIR.glob("*"):
        if f.is_file():
            f.unlink()
            print(f"  Deleted temp: {f.name}")

    # Clean output dir (only test files)
    for f in OUTPUT_DIR.glob("test_*.mp4"):
        f.unlink()
        print(f"  Deleted output: {f.name}")

    for f in OUTPUT_DIR.glob("TestEpisode*.mp4"):
        f.unlink()
        print(f"  Deleted output: {f.name}")

    print(f"{OK} Cleanup complete")


def main():
    print("\n" + "=" * 60)
    print("  VIDEO PROCESSING PIPELINE TEST")
    print("=" * 60)

    results = {}

    try:
        results['concatenation'] = test_concatenation()
        results['crossfade'] = test_crossfade()
        results['episode_split'] = test_episode_split()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    finally:
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
