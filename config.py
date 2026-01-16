"""
Application configuration
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PROFILES_DIR = DATA_DIR / "profiles"
TEMP_DIR = DATA_DIR / "temp"
OUTPUT_DIR = DATA_DIR / "output"

# Ensure directories exist
for dir_path in [DATA_DIR, PROFILES_DIR, TEMP_DIR, OUTPUT_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Server settings
HOST = "127.0.0.1"
PORT = 5000
DEBUG = False

# FFmpeg settings
FFMPEG_PATH = "ffmpeg"  # Assumes ffmpeg is in PATH
FFPROBE_PATH = "ffprobe"

# Hardware acceleration encoders
# These will be tested at startup to see what's available
HW_ENCODERS = {
    "nvenc": {
        "name": "NVIDIA NVENC",
        "codec": "h264_nvenc",
        "preset": "p4",  # p1 (fastest) to p7 (slowest/best)
        "extra_args": ["-rc", "vbr", "-cq", "23", "-b:v", "0"],
        "test_cmd": ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "nullsrc=s=256x256:d=1", "-c:v", "h264_nvenc", "-f", "null", "-"]
    },
    "qsv": {
        "name": "Intel QuickSync",
        "codec": "h264_qsv",
        "preset": "medium",
        "extra_args": ["-global_quality", "23"],
        "test_cmd": ["ffmpeg", "-hide_banner", "-init_hw_device", "qsv=hw", "-f", "lavfi", "-i", "nullsrc=s=256x256:d=1", "-c:v", "h264_qsv", "-f", "null", "-"]
    },
    "amf": {
        "name": "AMD AMF",
        "codec": "h264_amf",
        "preset": "balanced",
        "extra_args": ["-rc", "vbr_latency", "-qp_i", "23", "-qp_p", "23"],
        "test_cmd": ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "nullsrc=s=256x256:d=1", "-c:v", "h264_amf", "-f", "null", "-"]
    },
    "software": {
        "name": "Software (libx264)",
        "codec": "libx264",
        "preset": "medium",
        "extra_args": ["-crf", "21"],
        "test_cmd": None  # Always available
    }
}

# YouTube output presets
OUTPUT_PRESETS = {
    "youtube_4k": {
        "name": "YouTube 4K (2160p)",
        "width": 3840,
        "height": 2160,
        "bitrate": "45M",
        "audio_bitrate": "384k",
        "codec": "libx264",
        "preset": "slow",
        "crf": 18,
        "audio_codec": "aac",
        "format": "mp4"
    },
    "youtube_1440p": {
        "name": "YouTube 1440p",
        "width": 2560,
        "height": 1440,
        "bitrate": "24M",
        "audio_bitrate": "384k",
        "codec": "libx264",
        "preset": "slow",
        "crf": 20,
        "audio_codec": "aac",
        "format": "mp4"
    },
    "youtube_1080p": {
        "name": "YouTube 1080p",
        "width": 1920,
        "height": 1080,
        "bitrate": "12M",
        "audio_bitrate": "320k",
        "codec": "libx264",
        "preset": "medium",
        "crf": 21,
        "audio_codec": "aac",
        "format": "mp4"
    },
    "youtube_1080p_fast": {
        "name": "YouTube 1080p (Fast)",
        "width": 1920,
        "height": 1080,
        "bitrate": "12M",
        "audio_bitrate": "320k",
        "codec": "libx264",
        "preset": "fast",
        "crf": 23,
        "audio_codec": "aac",
        "format": "mp4"
    },
    "youtube_720p": {
        "name": "YouTube 720p",
        "width": 1280,
        "height": 720,
        "bitrate": "7.5M",
        "audio_bitrate": "256k",
        "codec": "libx264",
        "preset": "medium",
        "crf": 23,
        "audio_codec": "aac",
        "format": "mp4"
    },
    "original": {
        "name": "Original Quality (Copy)",
        "width": None,
        "height": None,
        "bitrate": None,
        "audio_bitrate": None,
        "codec": "copy",
        "preset": None,
        "crf": None,
        "audio_codec": "copy",
        "format": "mp4"
    }
}

# Transition types
TRANSITIONS = {
    "cut": {
        "name": "Cut (Instant)",
        "description": "Instant switch between clips"
    },
    "crossfade": {
        "name": "Crossfade",
        "description": "Dissolve between clips"
    },
    "fade_black": {
        "name": "Fade to Black",
        "description": "Fade out to black, then fade in"
    },
    "dip_white": {
        "name": "Dip to White",
        "description": "Dip to white between clips"
    }
}
