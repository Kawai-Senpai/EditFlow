"""
Flask API for EditFlow application
"""
import os
import json
import threading
import uuid
import hashlib
import subprocess
import tkinter as tk
import webbrowser
from tkinter import filedialog
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from core.config import (
    HOST, PORT, DEBUG, OUTPUT_PRESETS, TRANSITIONS,
    PROFILES_DIR, TEMP_DIR, OUTPUT_DIR, FFMPEG_PATH,
    THUMBNAIL_FRAMES_DIR
)
from core.profile_manager import profile_manager
from core.video_processor import video_processor
from core.render_preset_manager import render_preset_manager
from core.thumbnail_processor import thumbnail_processor
from core.thumbnail_settings_manager import thumbnail_settings_manager
from core.audio_preset_manager import audio_preset_manager
from core.voice_effects_processor import voice_effects_processor


app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Store active processing threads
processing_threads = {}
thumbnail_threads = {}

# Supported video extensions
VIDEO_EXTENSIONS = [
    ('Video Files', '*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v *.ts *.mts'),
    ('All Files', '*.*')
]

IMAGE_EXTENSIONS = [
    ('Image Files', '*.jpg *.jpeg *.png *.webp'),
    ('All Files', '*.*')
]

ALLOWED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_FONT_EXTS = {'.ttf', '.otf', '.ttc', '.woff', '.woff2'}


def _normalize_output_name(name: str, default_ext: str = ".mp4") -> tuple[str, str]:
    safe_name = secure_filename(name or "output")
    base = Path(safe_name)
    if base.suffix:
        stem = base.stem
        suffix = base.suffix
    else:
        stem = base.name
        suffix = default_ext
    if not stem:
        stem = "output"
    return stem, suffix


def _unique_output_path(base_dir: Path, name: str, token: str | None = None) -> str:
    stem, suffix = _normalize_output_name(name)
    candidate = base_dir / f"{stem}{suffix}"
    if not candidate.exists():
        return str(candidate)
    if token:
        candidate = base_dir / f"{stem}_{token}{suffix}"
        if not candidate.exists():
            return str(candidate)
    for i in range(1, 1000):
        candidate = base_dir / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return str(candidate)
    unique = base_dir / f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
    return str(unique)


def _unique_output_prefix(base_dir: Path, prefix: str, token: str | None = None) -> str:
    safe_prefix = secure_filename(prefix or "Episode")
    if not safe_prefix:
        safe_prefix = "Episode"
    def _has_conflict(value: str) -> bool:
        return any(base_dir.glob(f"{value}_*.mp4"))

    if not _has_conflict(safe_prefix):
        return safe_prefix
    if token:
        candidate_prefix = f"{safe_prefix}_{token}"
        if not _has_conflict(candidate_prefix):
            return candidate_prefix
    for i in range(1, 1000):
        candidate_prefix = f"{safe_prefix}_{i}"
        if not _has_conflict(candidate_prefix):
            return candidate_prefix
    return f"{safe_prefix}_{uuid.uuid4().hex[:8]}"


def _resolve_output_dir(output_dir: str | None, create: bool = True) -> Path:
    """Resolve output directory from user input or fall back to default."""
    if not output_dir:
        return OUTPUT_DIR

    candidate = Path(output_dir).expanduser()
    try:
        candidate = candidate.resolve()
    except Exception:
        candidate = Path(output_dir).expanduser()

    if candidate.exists():
        if not candidate.is_dir():
            raise ValueError("Output path is not a directory")
    else:
        if create:
            candidate.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError("Output folder not found")

    return candidate


def _safe_image_path(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("Image path is required")
    path = Path(raw_path).expanduser()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Image not found: {raw_path}")
    if path.suffix.lower() not in ALLOWED_IMAGE_EXTS:
        raise ValueError("Unsupported image format")
    return path


def _safe_font_path(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("Font path is required")
    path = Path(raw_path).expanduser()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Font not found: {raw_path}")
    if path.suffix.lower() not in ALLOWED_FONT_EXTS:
        raise ValueError("Unsupported font format")

    fonts_dir = Path("C:/Windows/Fonts").resolve()
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        raise FileNotFoundError(f"Font not found: {raw_path}")
    try:
        resolved.relative_to(fonts_dir)
    except ValueError:
        raise ValueError("Font must be inside Windows Fonts directory")
    return resolved


def _video_signature(video_path: str) -> str:
    path = Path(video_path)
    stat = path.stat()
    signature = f"{path.resolve()}|{stat.st_mtime}|{stat.st_size}"
    return hashlib.md5(signature.encode("utf-8")).hexdigest()[:12]


def _extract_video_frames(video_path: str, frame_count: int = 12, scale_width: int = 320) -> list[dict]:
    info = video_processor.get_video_info(video_path)
    if not info or not info.duration:
        raise ValueError("Unable to read video duration")

    duration = float(info.duration)
    frame_count = max(1, int(frame_count))
    scale_width = max(120, int(scale_width))

    signature = _video_signature(video_path)
    frames_dir = THUMBNAIL_FRAMES_DIR / signature
    frames_dir.mkdir(parents=True, exist_ok=True)
    for existing in frames_dir.glob("*.jpg"):
        existing.unlink(missing_ok=True)

    timestamps = [(duration * (i + 1) / (frame_count + 1)) for i in range(frame_count)]
    frames: list[dict] = []

    for idx, ts in enumerate(timestamps, start=1):
        frame_path = frames_dir / f"frame_{idx:03d}_{int(ts * 1000)}.jpg"
        cmd = [
            FFMPEG_PATH,
            "-hide_banner",
            "-loglevel", "error",
            "-ss", f"{ts:.3f}",
            "-i", str(video_path),
            "-frames:v", "1",
            "-vf", f"scale={scale_width}:-1",
            "-q:v", "2",
            "-y",
            str(frame_path)
        ]
        subprocess.run(cmd, check=True)
        frames.append({
            "path": str(frame_path),
            "timestamp": ts,
            "timestamp_formatted": format_duration(ts)
        })

    return frames


# ============== Static Routes ==============

@app.route('/')
def index():
    """Serve main page"""
    return send_from_directory('static', 'index.html')


# ============== File Browser Routes ==============

@app.route('/api/browse/videos', methods=['POST'])
def browse_videos():
    """Open native file dialog to select video files"""
    try:
        # Create a hidden Tk window
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Bring dialog to front
        root.focus_force()
        
        # Get initial directory from request or use default
        data = request.json or {}
        initial_dir = data.get('initial_dir', os.path.expanduser('~'))
        
        # Open file dialog
        file_paths = filedialog.askopenfilenames(
            title="Select Video Files",
            initialdir=initial_dir,
            filetypes=VIDEO_EXTENSIONS
        )
        
        root.destroy()
        
        if not file_paths:
            return jsonify({"paths": [], "cancelled": True})
        
        return jsonify({"paths": list(file_paths), "cancelled": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/browse/folder', methods=['POST'])
def browse_folder():
    """Open native folder dialog"""
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.focus_force()
        
        data = request.json or {}
        initial_dir = data.get('initial_dir', os.path.expanduser('~'))
        
        folder_path = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=initial_dir
        )
        
        root.destroy()
        
        if not folder_path:
            return jsonify({"path": None, "cancelled": True})
        
        return jsonify({"path": folder_path, "cancelled": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/browse-files', methods=['POST'])
def browse_files_generic():
    """Open native file dialog for any file type (used for branding assets)"""
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.focus_force()
        
        data = request.json or {}
        title = data.get('title', 'Select File')
        initial_dir = data.get('initial_dir', os.path.expanduser('~'))
        
        # File type filters for video/image files
        filetypes = [
            ('Video Files', '*.mp4 *.mov *.webm *.mkv *.avi *.wmv'),
            ('All Files', '*.*')
        ]
        
        file_paths = filedialog.askopenfilenames(
            title=title,
            initialdir=initial_dir,
            filetypes=filetypes
        )
        
        root.destroy()
        
        if not file_paths:
            return jsonify({"paths": [], "cancelled": True})
        
        return jsonify({"paths": list(file_paths), "cancelled": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/browse/images', methods=['POST'])
def browse_images():
    """Open native file dialog to select image files"""
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.focus_force()

        data = request.json or {}
        initial_dir = data.get('initial_dir', os.path.expanduser('~'))

        file_paths = filedialog.askopenfilenames(
            title="Select Image Files",
            initialdir=initial_dir,
            filetypes=IMAGE_EXTENSIONS
        )

        root.destroy()

        if not file_paths:
            return jsonify({"paths": [], "cancelled": True})

        return jsonify({"paths": list(file_paths), "cancelled": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== Config Routes ==============

@app.route('/api/config/presets', methods=['GET'])
def get_presets():
    """Get available output presets"""
    return jsonify(OUTPUT_PRESETS)


@app.route('/api/config/transitions', methods=['GET'])
def get_transitions():
    """Get available transitions"""
    return jsonify(TRANSITIONS)


# ============== Encoder Routes ==============

@app.route('/api/encoders', methods=['GET'])
def get_available_encoders():
    """Get list of available video encoders (including hardware acceleration)"""
    encoders = video_processor.get_available_encoders()
    return jsonify(encoders)


# ============== Render Preset Routes ==============

@app.route('/api/render-presets', methods=['GET'])
def get_render_presets():
    """Get all render settings presets"""
    presets = render_preset_manager.get_all_presets()
    return jsonify(presets)


@app.route('/api/render-presets', methods=['POST'])
def create_render_preset():
    """Create a new render settings preset"""
    data = request.json
    if not data or not data.get('name'):
        return jsonify({"error": "Preset name is required"}), 400
    
    settings = data.get('settings', {})
    preset = render_preset_manager.create_preset(data['name'], settings)
    return jsonify(preset)


@app.route('/api/render-presets/<preset_id>', methods=['GET'])
def get_render_preset(preset_id):
    """Get a specific render preset"""
    preset = render_preset_manager.get_preset(preset_id)
    if not preset:
        return jsonify({"error": "Preset not found"}), 404
    return jsonify(preset)


@app.route('/api/render-presets/<preset_id>', methods=['PUT'])
def update_render_preset(preset_id):
    """Update a render preset"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    preset = render_preset_manager.update_preset(preset_id, data)
    if not preset:
        return jsonify({"error": "Preset not found"}), 404
    return jsonify(preset)


@app.route('/api/render-presets/<preset_id>', methods=['DELETE'])
def delete_render_preset(preset_id):
    """Delete a render preset"""
    if render_preset_manager.delete_preset(preset_id):
        return jsonify({"success": True})
    return jsonify({"error": "Preset not found"}), 404


@app.route('/api/render-presets/last-used', methods=['GET'])
def get_last_used_settings():
    """Get the last used render settings"""
    settings = render_preset_manager.get_last_used()
    return jsonify(settings or {})


@app.route('/api/render-presets/last-used', methods=['POST'])
def save_last_used_settings():
    """Save the last used render settings"""
    data = request.json
    if data:
        render_preset_manager.save_last_used(data)
    return jsonify({"success": True})


# ============== Profile Routes ==============

@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    """Get all profiles"""
    profiles = profile_manager.get_all_profiles()
    return jsonify(profiles)


@app.route('/api/profiles', methods=['POST'])
def create_profile():
    """Create a new profile"""
    data = request.json
    if not data or not data.get('name'):
        return jsonify({"error": "Profile name is required"}), 400
    
    profile = profile_manager.create_profile(data['name'])
    return jsonify(profile)


@app.route('/api/profiles/<profile_id>', methods=['GET'])
def get_profile(profile_id):
    """Get a single profile"""
    profile = profile_manager.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile)


@app.route('/api/profiles/<profile_id>', methods=['PUT'])
def update_profile(profile_id):
    """Update a profile"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    profile = profile_manager.update_profile(profile_id, data)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile)


@app.route('/api/profiles/<profile_id>', methods=['DELETE'])
def delete_profile(profile_id):
    """Delete a profile"""
    if profile_manager.delete_profile(profile_id):
        return jsonify({"message": "Profile deleted"})
    return jsonify({"error": "Profile not found"}), 404


@app.route('/api/profiles/<profile_id>/intro', methods=['POST'])
def set_intro(profile_id):
    """Set intro file path for a profile (reference only, no copy)"""
    data = request.get_json()
    file_path = data.get('file_path')
    
    if not file_path:
        return jsonify({"error": "No file path provided"}), 400
    
    if not Path(file_path).exists():
        return jsonify({"error": "File not found at specified path"}), 404
    
    overlap = float(data.get('overlap', 0))
    has_audio = data.get('has_audio', True)
    full_overlap = data.get('full_overlap', False)
    
    try:
        profile = profile_manager.set_intro(profile_id, file_path, overlap, has_audio, full_overlap)
        if not profile:
            return jsonify({"error": "Profile not found"}), 404
        return jsonify(profile)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404


@app.route('/api/profiles/<profile_id>/outro', methods=['POST'])
def set_outro(profile_id):
    """Set outro file path for a profile (reference only, no copy)"""
    data = request.get_json()
    file_path = data.get('file_path')
    
    if not file_path:
        return jsonify({"error": "No file path provided"}), 400
    
    if not Path(file_path).exists():
        return jsonify({"error": "File not found at specified path"}), 404
    
    overlap = float(data.get('overlap', 0))
    has_audio = data.get('has_audio', True)
    full_overlap = data.get('full_overlap', False)
    
    try:
        profile = profile_manager.set_outro(profile_id, file_path, overlap, has_audio, full_overlap)
        if not profile:
            return jsonify({"error": "Profile not found"}), 404
        return jsonify(profile)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404


@app.route('/api/profiles/<profile_id>/subscribe', methods=['POST'])
def set_subscribe(profile_id):
    """Set subscribe graphics file path for a profile (reference only, no copy)"""
    data = request.get_json()
    file_path = data.get('file_path')
    
    if not file_path:
        return jsonify({"error": "No file path provided"}), 400
    
    if not Path(file_path).exists():
        return jsonify({"error": "File not found at specified path"}), 404
    
    duration = float(data.get('duration', 8))
    has_audio = data.get('has_audio', True)
    use_full_duration = data.get('use_full_duration', True)
    
    try:
        # Note: interval is now set at render time, not in branding
        profile = profile_manager.set_subscribe_graphics(profile_id, file_path, 300, duration, has_audio, use_full_duration)
        if not profile:
            return jsonify({"error": "Profile not found"}), 404
        return jsonify(profile)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404


@app.route('/api/profiles/<profile_id>/intro', methods=['DELETE'])
def remove_intro(profile_id):
    """Remove intro from profile"""
    profile = profile_manager.remove_intro(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found or no intro set"}), 404
    return jsonify(profile)


@app.route('/api/profiles/<profile_id>/outro', methods=['DELETE'])
def remove_outro(profile_id):
    """Remove outro from profile"""
    profile = profile_manager.remove_outro(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found or no outro set"}), 404
    return jsonify(profile)


@app.route('/api/profiles/<profile_id>/subscribe', methods=['DELETE'])
def remove_subscribe(profile_id):
    """Remove subscribe graphics from profile"""
    profile = profile_manager.remove_subscribe_graphics(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found or no subscribe graphics set"}), 404
    return jsonify(profile)


# ============== Asset Settings Update Routes ==============

@app.route('/api/profiles/<profile_id>/intro/settings', methods=['PUT'])
def update_intro_settings(profile_id):
    """Update intro settings without changing the file"""
    data = request.json
    profile = profile_manager.update_asset_settings(profile_id, 'intro', data)
    if not profile:
        return jsonify({"error": "Profile not found or intro not set"}), 404
    return jsonify(profile)


@app.route('/api/profiles/<profile_id>/outro/settings', methods=['PUT'])
def update_outro_settings(profile_id):
    """Update outro settings without changing the file"""
    data = request.json
    profile = profile_manager.update_asset_settings(profile_id, 'outro', data)
    if not profile:
        return jsonify({"error": "Profile not found or outro not set"}), 404
    return jsonify(profile)


@app.route('/api/profiles/<profile_id>/subscribe/settings', methods=['PUT'])
def update_subscribe_settings(profile_id):
    """Update subscribe settings without changing the file"""
    data = request.json
    profile = profile_manager.update_asset_settings(profile_id, 'subscribe_graphics', data)
    if not profile:
        return jsonify({"error": "Profile not found or subscribe graphics not set"}), 404
    return jsonify(profile)


# ============== Thumbnail Routes ==============

@app.route('/api/thumbnails/presets', methods=['GET'])
def get_thumbnail_presets():
    """Get all thumbnail settings presets"""
    presets = thumbnail_settings_manager.get_all_presets()
    return jsonify(presets)


@app.route('/api/thumbnails/presets', methods=['POST'])
def create_thumbnail_preset():
    """Create a new thumbnail settings preset"""
    data = request.json
    if not data or not data.get('name'):
        return jsonify({"error": "Preset name is required"}), 400
    preset = thumbnail_settings_manager.create_preset(data['name'], data.get('settings', {}))
    return jsonify(preset)


@app.route('/api/thumbnails/presets/<preset_id>', methods=['GET'])
def get_thumbnail_preset(preset_id):
    """Get a specific thumbnail settings preset"""
    preset = thumbnail_settings_manager.get_preset(preset_id)
    if not preset:
        return jsonify({"error": "Preset not found"}), 404
    return jsonify(preset)


@app.route('/api/thumbnails/presets/<preset_id>', methods=['PUT'])
def update_thumbnail_preset(preset_id):
    """Update a thumbnail settings preset"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    preset = thumbnail_settings_manager.update_preset(preset_id, data)
    if not preset:
        return jsonify({"error": "Preset not found"}), 404
    return jsonify(preset)


@app.route('/api/thumbnails/presets/<preset_id>', methods=['DELETE'])
def delete_thumbnail_preset(preset_id):
    """Delete a thumbnail settings preset"""
    if thumbnail_settings_manager.delete_preset(preset_id):
        return jsonify({"success": True})
    return jsonify({"error": "Preset not found"}), 404


@app.route('/api/thumbnails/fonts', methods=['GET'])
def get_thumbnail_fonts():
    """List available system fonts for studio overlays"""
    fonts_dir = Path("C:/Windows/Fonts")
    fonts = []
    seen = set()
    try:
        import winreg
        key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            index = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, index)
                    index += 1
                    font_name = name.split("(")[0].strip()
                    if not font_name or font_name.lower() in seen:
                        continue
                    font_path = Path(value)
                    if not font_path.is_absolute():
                        font_path = fonts_dir / value
                    if font_path.exists():
                        seen.add(font_name.lower())
                        fonts.append({
                            "name": font_name,
                            "path": str(font_path)
                        })
                except OSError:
                    break
    except Exception:
        pass

    if fonts_dir.exists():
        for ext in ("*.ttf", "*.otf"):
            for font_file in fonts_dir.glob(ext):
                name = font_file.stem
                if name.lower() in seen:
                    continue
                seen.add(name.lower())
                fonts.append({
                    "name": name,
                    "path": str(font_file)
                })
    fonts.sort(key=lambda f: f["name"].lower())
    return jsonify(fonts)


@app.route('/api/thumbnails/file', methods=['GET'])
def get_thumbnail_file():
    """Serve an image file for thumbnail preview"""
    raw_path = request.args.get('path')
    try:
        path = _safe_image_path(raw_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return send_file(str(path))


@app.route('/api/thumbnails/font', methods=['GET'])
def get_thumbnail_font():
    """Serve a font file for browser preview"""
    raw_path = request.args.get('path')
    try:
        path = _safe_font_path(raw_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return send_file(str(path))


@app.route('/api/thumbnails/frames', methods=['POST'])
def get_thumbnail_frames():
    """Extract preview frames from a video for thumbnail selection"""
    data = request.json or {}
    video_path = data.get('video_path')
    if not video_path:
        return jsonify({"error": "Video path is required"}), 400
    if not Path(video_path).exists():
        return jsonify({"error": "Video file not found"}), 404

    frame_count = int(data.get('frame_count', 12))
    scale_width = int(data.get('scale_width', 320))

    try:
        frames = _extract_video_frames(video_path, frame_count, scale_width)
        info = video_processor.get_video_info(video_path)
        return jsonify({
            "video_path": video_path,
            "video_name": Path(video_path).name,
            "duration": info.duration if info else None,
            "duration_formatted": format_duration(info.duration) if info else None,
            "frames": frames
        })
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"FFmpeg failed: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/thumbnails/generate', methods=['POST'])
def generate_thumbnails():
    """Generate thumbnails from selected backgrounds and overlay settings"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    backgrounds = data.get('backgrounds', [])
    if not backgrounds:
        return jsonify({"error": "No backgrounds provided"}), 400

    for item in backgrounds:
        path = item.get('path')
        if not path or not Path(path).exists():
            return jsonify({"error": f"Background not found: {path}"}), 400

    overlay = data.get('overlay') or {}
    if overlay.get('type') == 'image':
        overlay_path = overlay.get('path')
        try:
            _safe_image_path(overlay_path)
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    output_dir_input = data.get('output_dir')
    try:
        output_dir = _resolve_output_dir(output_dir_input)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    job = thumbnail_processor.create_job()
    spec = thumbnail_processor.build_job_spec(data)

    def process():
        try:
            thumbnail_processor.process_thumbnails(job, backgrounds, output_dir, spec)
        except Exception as e:
            job.status = "failed"
            job.error = str(e)

    thread = threading.Thread(target=process)
    thread.start()
    thumbnail_threads[job.id] = thread

    return jsonify({"job_id": job.id})


@app.route('/api/thumbnails/jobs/<job_id>', methods=['GET'])
def get_thumbnail_job_status(job_id):
    """Get thumbnail processing job status"""
    job = thumbnail_processor.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "id": job.id,
        "status": job.status,
        "progress": round(job.progress, 1),
        "current_step": job.current_step,
        "current_step_num": job.current_step_num,
        "total_steps": job.total_steps,
        "output_files": job.output_files,
        "failures": job.failures,
        "error": job.error
    })


@app.route('/api/thumbnails/jobs/<job_id>/cancel', methods=['POST'])
def cancel_thumbnail_job(job_id):
    """Cancel a thumbnail processing job"""
    if thumbnail_processor.cancel_job(job_id):
        return jsonify({"message": "Job cancelled"})
    return jsonify({"error": "Could not cancel job"}), 400


# ============== Video Info Routes ==============

@app.route('/api/video/info', methods=['POST'])
def get_video_info():
    """Get video file information"""
    data = request.json
    if not data or not data.get('path'):
        return jsonify({"error": "Video path is required"}), 400
    
    info = video_processor.get_video_info(data['path'])
    if not info:
        return jsonify({"error": "Could not get video info"}), 400
    
    # Build audio tracks list
    audio_tracks = []
    for track in info.audio_tracks:
        audio_tracks.append({
            "index": track.index,
            "track_index": track.track_index,
            "codec": track.codec,
            "channels": track.channels,
            "sample_rate": track.sample_rate,
            "title": track.title,
            "bitrate": track.bitrate,
            "channel_layout": track.channel_layout
        })
    
    return jsonify({
        "path": info.path,
        "duration": info.duration,
        "duration_formatted": format_duration(info.duration),
        "width": info.width,
        "height": info.height,
        "fps": round(info.fps, 2),
        "codec": info.codec,
        "has_audio": info.has_audio,
        "audio_tracks": audio_tracks
    })


@app.route('/api/video/info/batch', methods=['POST'])
def get_videos_info():
    """Get info for multiple video files"""
    data = request.json
    if not data or not data.get('paths'):
        return jsonify({"error": "Video paths are required"}), 400
    
    results = []
    for path in data['paths']:
        info = video_processor.get_video_info(path)
        if info:
            # Build audio tracks list
            audio_tracks = []
            for track in info.audio_tracks:
                audio_tracks.append({
                    "index": track.index,
                    "track_index": track.track_index,
                    "codec": track.codec,
                    "channels": track.channels,
                    "sample_rate": track.sample_rate,
                    "title": track.title,
                    "bitrate": track.bitrate,
                    "channel_layout": track.channel_layout
                })
            
            results.append({
                "path": info.path,
                "filename": Path(info.path).name,
                "duration": info.duration,
                "duration_formatted": format_duration(info.duration),
                "width": info.width,
                "height": info.height,
                "fps": round(info.fps, 2),
                "codec": info.codec,
                "has_audio": info.has_audio,
                "audio_tracks": audio_tracks
            })
    
    return jsonify(results)


# ============== Audio Mixing Routes ==============

@app.route('/api/audio/waveform', methods=['POST'])
def generate_audio_waveform():
    """Generate waveform image for an audio track"""
    data = request.json
    if not data or not data.get('path'):
        return jsonify({"error": "Video path is required"}), 400
    
    video_path = data['path']
    if not Path(video_path).exists():
        return jsonify({"error": "Video file not found"}), 404
    
    track_index = int(data.get('track_index', 0))
    width = int(data.get('width', 800))
    height = int(data.get('height', 80))
    color = data.get('color', '0x3b82f6')
    
    # Generate unique output path
    signature = hashlib.md5(f"{video_path}|{track_index}".encode()).hexdigest()[:12]
    output_path = TEMP_DIR / f"waveform_{signature}.png"
    
    try:
        if video_processor.generate_audio_waveform(
            video_path, str(output_path), 
            width=width, height=height,
            track_index=track_index, color=color
        ):
            return send_file(str(output_path), mimetype='image/png')
        else:
            return jsonify({"error": "Failed to generate waveform"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/audio/preview', methods=['POST'])
def generate_audio_preview():
    """Generate audio preview with mix settings applied"""
    data = request.json
    if not data or not data.get('path'):
        return jsonify({"error": "Video path is required"}), 400
    
    video_path = data['path']
    if not Path(video_path).exists():
        return jsonify({"error": "Video file not found"}), 404
    
    audio_mix = data.get('audio_mix', [])
    start_time = float(data.get('start_time', 0))
    duration = float(data.get('duration', 15))
    voice_effects_preset_id = data.get('voice_effects_preset_id')
    voice_effects_settings = data.get('voice_effects_settings')  # Custom settings from inline editor
    normalize_first = bool(data.get('normalize_first', True))
    normalize_first = bool(data.get('normalize_first', True))
    
    # Generate unique output path - include settings in signature if provided
    if voice_effects_settings:
        voice_sig = hashlib.md5(json.dumps(voice_effects_settings, sort_keys=True).encode()).hexdigest()[:8]
    else:
        voice_sig = voice_effects_preset_id or "none"
    mix_signature = hashlib.md5(f"{audio_mix}|{voice_sig}".encode()).hexdigest()[:8]
    signature = hashlib.md5(f"{video_path}|{start_time}".encode()).hexdigest()[:8]
    output_path = TEMP_DIR / f"audio_preview_{signature}_{mix_signature}.m4a"
    
    try:
        if video_processor.generate_audio_preview(
            video_path, str(output_path),
            audio_mix=audio_mix,
            start_time=start_time,
            duration=duration,
            voice_effects_preset_id=voice_effects_preset_id,
            voice_effects_settings=voice_effects_settings,
            normalize_first=normalize_first
        ):
            return send_file(str(output_path), mimetype='audio/mp4')
        else:
            return jsonify({"error": "Failed to generate audio preview"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== Audio Preset Routes ==============

@app.route('/api/audio-presets', methods=['GET'])
def get_audio_presets():
    """Get all audio mixing presets"""
    return jsonify(audio_preset_manager.get_all_presets())


@app.route('/api/audio-presets', methods=['POST'])
def create_audio_preset():
    """Create a new audio mixing preset"""
    data = request.json
    if not data or not data.get('name'):
        return jsonify({"error": "Preset name is required"}), 400
    
    preset = audio_preset_manager.create_preset(
        name=data['name'],
        tracks=data.get('tracks', {}),
        description=data.get('description', ''),
        voice_effects=data.get('voiceEffects')
    )
    return jsonify(preset)


@app.route('/api/audio-presets/<preset_id>', methods=['GET'])
def get_audio_preset(preset_id):
    """Get a specific audio mixing preset"""
    preset = audio_preset_manager.get_preset(preset_id)
    if not preset:
        return jsonify({"error": "Preset not found"}), 404
    return jsonify(preset)


@app.route('/api/audio-presets/<preset_id>', methods=['PUT'])
def update_audio_preset(preset_id):
    """Update an audio mixing preset"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    preset = audio_preset_manager.update_preset(preset_id, data)
    if not preset:
        return jsonify({"error": "Preset not found"}), 404
    return jsonify(preset)


@app.route('/api/audio-presets/<preset_id>', methods=['DELETE'])
def delete_audio_preset(preset_id):
    """Delete an audio mixing preset"""
    if audio_preset_manager.delete_preset(preset_id):
        return jsonify({"success": True})
    return jsonify({"error": "Cannot delete default preset or preset not found"}), 400


@app.route('/api/audio/track-types', methods=['GET'])
def get_track_types():
    """Get available track types for tagging"""
    return jsonify(audio_preset_manager.get_track_types())


@app.route('/api/audio/auto-level', methods=['POST'])
def calculate_auto_levels():
    """Calculate auto-leveled volumes based on LUFS analysis and track types"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    video_path = data.get('video_path')
    track_types = data.get('track_types', {})
    
    if not video_path:
        # Fallback to type-based levels
        levels = audio_preset_manager.calculate_auto_levels(track_types)
        return jsonify({"levels": levels, "analyzed": False})
    
    if not Path(video_path).exists():
        return jsonify({"error": "Video file not found"}), 404
    
    # Analyze all audio tracks
    analysis = video_processor.analyze_all_tracks_loudness(video_path, duration=30)
    
    if not analysis:
        # Fallback to type-based levels
        levels = audio_preset_manager.calculate_auto_levels(track_types)
        return jsonify({"levels": levels, "analyzed": False})
    
    # Calculate levels based on actual loudness + track types
    levels = audio_preset_manager.calculate_auto_levels_from_analysis(analysis, track_types)
    
    # Ensure analysis contains only JSON-safe numbers
    safe_analysis = []
    for item in analysis:
        if not isinstance(item, dict):
            continue
        safe_item = {}
        for key, value in item.items():
            if isinstance(value, float):
                if value != value or value in (float("inf"), float("-inf")):
                    safe_item[key] = None
                else:
                    safe_item[key] = value
            else:
                safe_item[key] = value
        safe_analysis.append(safe_item)

    return jsonify({
        "levels": levels,
        "analyzed": True,
        "analysis": safe_analysis  # Include sanitized analysis for UI display
    })


@app.route('/api/audio/analyze', methods=['POST'])
def analyze_audio_tracks():
    """Analyze loudness of all audio tracks in a video"""
    data = request.json
    if not data or not data.get('video_path'):
        return jsonify({"error": "Video path is required"}), 400
    
    video_path = data['video_path']
    if not Path(video_path).exists():
        return jsonify({"error": "Video file not found"}), 404
    
    duration = float(data.get('duration', 30))  # Analyze first 30 seconds by default
    
    analysis = video_processor.analyze_all_tracks_loudness(video_path, duration)
    
    return jsonify({"analysis": analysis})


# ============== Voice Effects Routes ==============

@app.route('/api/voice-effects/presets', methods=['GET'])
def get_voice_effects_presets():
    """Get all voice effects presets"""
    return jsonify(voice_effects_processor.get_all_presets())


@app.route('/api/voice-effects/presets', methods=['POST'])
def create_voice_effects_preset():
    """Create a new voice effects preset"""
    data = request.json
    if not data or not data.get('name'):
        return jsonify({"error": "Preset name is required"}), 400
    
    preset = voice_effects_processor.create_preset(
        name=data['name'],
        settings=data.get('settings', {}),
        description=data.get('description', '')
    )
    return jsonify(preset)


@app.route('/api/voice-effects/presets/<preset_id>', methods=['GET'])
def get_voice_effects_preset(preset_id):
    """Get a specific voice effects preset"""
    preset = voice_effects_processor.get_preset(preset_id)
    if not preset:
        return jsonify({"error": "Preset not found"}), 404
    return jsonify(preset)


@app.route('/api/voice-effects/presets/<preset_id>', methods=['PUT'])
def update_voice_effects_preset(preset_id):
    """Update a voice effects preset"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    preset = voice_effects_processor.update_preset(preset_id, data)
    if not preset:
        return jsonify({"error": "Preset not found"}), 404
    return jsonify(preset)


@app.route('/api/voice-effects/presets/<preset_id>', methods=['DELETE'])
def delete_voice_effects_preset(preset_id):
    """Delete a voice effects preset"""
    if voice_effects_processor.delete_preset(preset_id):
        return jsonify({"success": True})
    return jsonify({"error": "Cannot delete default preset or preset not found"}), 400


@app.route('/api/voice-effects/preview', methods=['POST'])
def generate_voice_effects_preview():
    """Generate audio preview with voice effects applied to all voice tracks mixed together"""
    data = request.json
    if not data or not data.get('path'):
        return jsonify({"error": "Video/audio path is required"}), 400
    
    video_path = data['path']
    if not Path(video_path).exists():
        return jsonify({"error": "File not found"}), 404
    
    # Get preset - custom settings take priority over preset_id
    custom_settings = data.get('settings')
    preset_id = data.get('preset_id')
    
    if custom_settings:
        # Use custom settings directly (from inline editor)
        preset = custom_settings
    elif preset_id:
        # Look up preset by ID
        preset = voice_effects_processor.get_preset(preset_id)
        if not preset:
            return jsonify({"error": "Voice effects preset not found"}), 404
    else:
        # No settings provided - use default (no effects)
        preset = {}
    
    # Get all voice track indices (or fall back to single track)
    voice_track_indices = data.get('voice_track_indices', [])
    if not voice_track_indices:
        # Legacy support: use single track_index
        track_index = int(data.get('track_index', 0))
        voice_track_indices = [track_index]
    
    # Get volume settings for each voice track (optional - defaults to 1.0 for all)
    voice_track_volumes = data.get('voice_track_volumes', [])
    
    start_time = float(data.get('start_time', 0))
    duration = float(data.get('duration', 15))
    
    output_path = voice_effects_processor.generate_preview_multi_track(
        video_path=video_path,
        preset=preset,
        voice_track_indices=voice_track_indices,
        voice_track_volumes=voice_track_volumes,
        start_time=start_time,
        duration=duration
    )
    
    if output_path:
        return send_file(output_path, mimetype='audio/mp4')
    return jsonify({"error": "Failed to generate voice effects preview"}), 500


@app.route('/api/voice-effects/presets/reset', methods=['POST'])
def reset_voice_effects_presets():
    """Reset all voice effects presets to defaults (removes custom presets)"""
    try:
        voice_effects_processor.reset_defaults()
        return jsonify({"success": True, "message": "Presets reset to defaults"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/voice-effects/filter-chain', methods=['POST'])
def get_voice_effects_filter_chain():
    """Get the FFmpeg filter chain for a voice effects preset"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    preset_id = data.get('preset_id')
    if preset_id:
        preset = voice_effects_processor.get_preset(preset_id)
        if not preset:
            return jsonify({"error": "Preset not found"}), 404
    else:
        preset = data.get('settings', {})
    
    filter_chain = voice_effects_processor.build_filter_chain(preset)
    return jsonify({"filter_chain": filter_chain})


# ============== Processing Routes ==============

@app.route('/api/process/single', methods=['POST'])
def process_single_video():
    """Process videos into a single output (with optional intro/outro)"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    video_paths = data.get('video_paths', [])
    if not video_paths:
        return jsonify({"error": "No video files provided"}), 400
    
    # Validate all paths exist
    for path in video_paths:
        if not Path(path).exists():
            return jsonify({"error": f"File not found: {path}"}), 400

    # Get trim settings (list of {path, trim_start, trim_end})
    trim_settings = data.get('trim_settings', [])
    trim_map = {t['path']: t for t in trim_settings if isinstance(t, dict) and t.get('path')}

    # Get audio mix settings (list of {path, tracks: [{track_index, volume, mute, solo}]})
    audio_mix_settings = data.get('audio_mix_settings', [])
    audio_mix_map = {}
    for item in audio_mix_settings:
        if isinstance(item, dict) and item.get('path'):
            audio_mix_map[item['path']] = item.get('tracks', [])
    
    # Debug: Log audio mix map for render
    print(f"[ProcessSingle] audio_mix_map keys: {list(audio_mix_map.keys())}")
    for path_key, tracks in audio_mix_map.items():
        track_summary = [f"t{t.get('track_index', '?')}@{t.get('volume', '?')}" for t in tracks] if tracks else ['EMPTY']
        print(f"[ProcessSingle]   {path_key}: {track_summary}")
    print(f"[ProcessSingle] video_paths: {video_paths}")
    
    # Get voice effects preset ID
    voice_effects_preset_id = data.get('voice_effects_preset_id')
    voice_effects_settings = data.get('voice_effects_settings')  # Custom settings from inline editor
    normalize_first = bool(data.get('normalize_first', True))
    
    profile_id = data.get('profile_id')
    transition = data.get('transition', 'cut')
    transition_duration = float(data.get('transition_duration', 1.0))
    preset = data.get('preset', 'youtube_1080p_balanced')
    output_name = data.get('output_name', 'output')
    output_dir_input = data.get('output_dir')
    apply_subscribe = data.get('apply_subscribe', False)
    subscribe_interval = float(data.get('subscribe_interval', 300))  # In seconds
    encoder = data.get('encoder', 'software')  # Hardware acceleration selection

    try:
        output_dir = _resolve_output_dir(output_dir_input)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
    # Create job
    job = video_processor.create_job()
    
    def process():
        try:
            job.status = "processing"
            job.total_steps = 1
            job.current_step = "Processing video..."
            job.current_step_num = 1
            job.progress = 0

            profile = profile_manager.get_profile(profile_id) if profile_id else None

            intro_path = profile.get('intro', {}).get('file_path') if profile and profile.get('intro') else None
            intro_overlap = profile.get('intro', {}).get('overlap_seconds', 0) if profile and profile.get('intro') else 0
            intro_full_overlap = profile.get('intro', {}).get('full_overlap', False) if profile and profile.get('intro') else False

            outro_path = profile.get('outro', {}).get('file_path') if profile and profile.get('outro') else None
            outro_overlap = profile.get('outro', {}).get('overlap_seconds', 0) if profile and profile.get('outro') else 0
            outro_full_overlap = profile.get('outro', {}).get('full_overlap', False) if profile and profile.get('outro') else False

            subscribe_path = None
            subscribe_duration = 8
            if apply_subscribe and profile and profile.get('subscribe_graphics'):
                sub = profile['subscribe_graphics']
                subscribe_path = sub.get('file_path')
                subscribe_duration = sub.get('duration_seconds', 8)

            final_path = _unique_output_path(output_dir, output_name, job.id)
            video_processor.process_single_pass(
                video_paths,
                final_path,
                job,
                transition=transition,
                transition_duration=transition_duration,
                preset=preset,
                trim_map=trim_map,
                encoder=encoder,
                intro_path=intro_path,
                intro_overlap=intro_overlap,
                intro_full_overlap=intro_full_overlap,
                outro_path=outro_path,
                outro_overlap=outro_overlap,
                outro_full_overlap=outro_full_overlap,
                subscribe_path=subscribe_path,
                subscribe_interval=subscribe_interval,
                subscribe_duration=subscribe_duration,
                audio_mix_map=audio_mix_map,
                voice_effects_preset_id=voice_effects_preset_id,
                voice_effects_settings=voice_effects_settings,
                normalize_first=normalize_first
            )

            job.output_files = [final_path]
            job.status = "completed"
            job.progress = 100
            print(f"[Job {job.id}] Completed successfully")
            
        except Exception as e:
            import traceback
            job.status = "failed"
            job.error = str(e)
            print(f"[Job {job.id}] Failed with error: {e}")
            traceback.print_exc()
    
    thread = threading.Thread(target=process)
    thread.start()
    processing_threads[job.id] = thread
    
    return jsonify({"job_id": job.id})


@app.route('/api/process/episodic', methods=['POST'])
def process_episodic():
    """Process videos into episodic format"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    video_paths = data.get('video_paths', [])
    if not video_paths:
        return jsonify({"error": "No video files provided"}), 400
    
    # Validate all paths exist
    for path in video_paths:
        if not Path(path).exists():
            return jsonify({"error": f"File not found: {path}"}), 400

    # Get trim settings (list of {path, trim_start, trim_end})
    trim_settings = data.get('trim_settings', [])
    trim_map = {t['path']: t for t in trim_settings if isinstance(t, dict) and t.get('path')}

    # Get audio mix settings (list of {path, tracks: [...]})
    audio_mix_settings = data.get('audio_mix_settings', [])
    audio_mix_map = {}
    for item in audio_mix_settings:
        if isinstance(item, dict) and item.get('path'):
            audio_mix_map[item['path']] = item.get('tracks', [])
    
    profile_id = data.get('profile_id')
    transition = data.get('transition', 'cut')
    transition_duration = float(data.get('transition_duration', 1.0))
    episode_duration = float(data.get('episode_duration', 3600))  # Default 1 hour
    episode_overlap = float(data.get('episode_overlap', 30))  # Default 30 seconds
    preset = data.get('preset', 'youtube_1080p_balanced')
    output_prefix = data.get('output_prefix', 'Episode')
    output_dir_input = data.get('output_dir')
    apply_subscribe = data.get('apply_subscribe', False)
    voice_effects_preset_id = data.get('voice_effects_preset_id')
    voice_effects_settings = data.get('voice_effects_settings')
    normalize_first = bool(data.get('normalize_first', True))

    try:
        output_dir = _resolve_output_dir(output_dir_input)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
    # Create job
    job = video_processor.create_job()
    output_prefix = _unique_output_prefix(output_dir, output_prefix, job.id)
    
    def process():
        try:
            job.status = "processing"
            
            # Step 1: Preprocess/concatenate (if multiple or if audio/trim effects are needed)
            has_trim = any(
                float(trim_map.get(p, {}).get('trim_start', 0)) > 0 or
                float(trim_map.get(p, {}).get('trim_end', 0)) > 0
                for p in video_paths
            )
            has_audio_mix = bool(audio_mix_map)
            has_voice_fx = bool(voice_effects_preset_id or voice_effects_settings)

            created_concat = False
            if len(video_paths) > 1 or has_trim or has_audio_mix or has_voice_fx:
                job.current_step = "Joining all videos..."
                job.current_step_num = 1
                
                concat_output = str(TEMP_DIR / f"concat_{job.id}.mp4")
                video_processor.concatenate_videos(
                    video_paths, concat_output, job,
                    transition=transition,
                    transition_duration=transition_duration,
                    preset=preset,
                    trim_map=trim_map,
                    audio_mix_map=audio_mix_map,
                    voice_effects_preset_id=voice_effects_preset_id,
                    voice_effects_settings=voice_effects_settings,
                    normalize_first=normalize_first
                )
                source_video = concat_output
                created_concat = True
            else:
                source_video = video_paths[0]
            
            # Step 2: Split into episodes
            job.current_step = "Splitting into episodes..."
            job.progress = 0
            
            episode_files = video_processor.split_into_episodes(
                source_video, job,
                episode_duration=episode_duration,
                overlap_seconds=episode_overlap,
                preset=preset,
                output_prefix=output_prefix,
                output_dir=str(output_dir)
            )
            
            # Clean up concat if we made one
            if created_concat and Path(source_video).exists():
                Path(source_video).unlink()
            
            # Step 3: Apply intro/outro/subscribe to each episode
            if profile_id:
                profile = profile_manager.get_profile(profile_id)
                if profile:
                    final_files = []
                    
                    for i, ep_file in enumerate(episode_files):
                        if job.cancelled:
                            break
                        
                        job.current_step = f"Processing {output_prefix} {i+1} overlays..."
                        job.current_step_num = i + 1
                        job.total_steps = len(episode_files)
                        job.progress = 0
                        
                        current_video = ep_file
                        
                        # Apply intro/outro
                        intro_path = profile.get('intro', {}).get('file_path') if profile.get('intro') else None
                        intro_overlap = profile.get('intro', {}).get('overlap_seconds', 0) if profile.get('intro') else 0
                        outro_path = profile.get('outro', {}).get('file_path') if profile.get('outro') else None
                        outro_overlap = profile.get('outro', {}).get('overlap_seconds', 0) if profile.get('outro') else 0
                        
                        if intro_path or outro_path:
                            overlay_output = str(output_dir / f"{output_prefix}_{i+1:02d}_overlay.mp4")
                            video_processor.apply_intro_outro_overlays(
                                current_video, overlay_output, job,
                                intro_path=intro_path, intro_overlap=intro_overlap,
                                outro_path=outro_path, outro_overlap=outro_overlap,
                                preset=preset
                            )
                            
                            if Path(current_video).exists():
                                Path(current_video).unlink()
                            current_video = overlay_output
                        
                        # Apply subscribe graphics
                        if apply_subscribe and profile.get('subscribe_graphics'):
                            sub = profile['subscribe_graphics']
                            sub_output = str(output_dir / f"{output_prefix}_{i+1:02d}_final.mp4")
                            video_processor.apply_subscribe_graphics(
                                current_video, sub['file_path'], sub_output, job,
                                interval_seconds=sub.get('interval_seconds', 300),
                                duration_seconds=sub.get('duration_seconds', 8),
                                preset=preset
                            )
                            
                            if Path(current_video).exists():
                                Path(current_video).unlink()
                            current_video = sub_output
                        
                        # Rename to final name
                        final_path = str(output_dir / f"{output_prefix}_{i+1:02d}.mp4")
                        if current_video != final_path:
                            if Path(final_path).exists():
                                Path(final_path).unlink()
                            Path(current_video).rename(final_path)
                        
                        final_files.append(final_path)
                    
                    job.output_files = final_files
                else:
                    job.output_files = episode_files
            else:
                job.output_files = episode_files
            
            job.status = "completed"
            job.progress = 100
            print(f"[Job {job.id}] Completed successfully - episodic")
            
        except Exception as e:
            import traceback
            job.status = "failed"
            job.error = str(e)
            print(f"[Job {job.id}] Failed with error: {e}")
            traceback.print_exc()
    
    thread = threading.Thread(target=process)
    thread.start()
    processing_threads[job.id] = thread
    
    return jsonify({"job_id": job.id})


@app.route('/api/process/<job_id>/status', methods=['GET'])
def get_job_status(job_id):
    """Get processing job status"""
    job = video_processor.get_job(job_id)
    if not job:
        # Debug: print all known job IDs
        print(f"[Job Status] Job {job_id} not found. Known jobs: {list(video_processor.jobs.keys())}")
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify({
        "id": job.id,
        "status": job.status,
        "progress": round(job.progress, 1),
        "current_step": job.current_step,
        "current_step_num": job.current_step_num,
        "total_steps": job.total_steps,
        "output_files": job.output_files,
        "error": job.error
    })


@app.route('/api/process/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a processing job"""
    if video_processor.cancel_job(job_id):
        return jsonify({"message": "Job cancelled"})
    return jsonify({"error": "Could not cancel job"}), 400


# ============== Output Routes ==============

@app.route('/api/output', methods=['GET'])
def list_outputs():
    """List all output files"""
    output_dir_input = request.args.get("dir")
    try:
        output_dir = _resolve_output_dir(output_dir_input)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    files = []
    for f in output_dir.glob("*.mp4"):
        stat = f.stat()
        files.append({
            "name": f.name,
            "path": str(f),
            "size": stat.st_size,
            "size_formatted": format_size(stat.st_size),
            "modified": stat.st_mtime
        })
    
    files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify(files)


@app.route('/api/output/<filename>', methods=['DELETE'])
def delete_output(filename):
    """Delete an output file"""
    output_dir_input = request.args.get("dir")
    try:
        output_dir = _resolve_output_dir(output_dir_input, create=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    file_path = output_dir / secure_filename(filename)
    if file_path.exists():
        file_path.unlink()
        return jsonify({"message": "File deleted"})
    return jsonify({"error": "File not found"}), 404


@app.route('/api/output/folder', methods=['GET'])
def get_output_folder():
    """Get output folder path"""
    output_dir_input = request.args.get("dir")
    try:
        output_dir = _resolve_output_dir(output_dir_input)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"path": str(output_dir)})


# ============== Utility Functions ==============

def format_duration(seconds: float) -> str:
    """Format duration as HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_size(bytes: int) -> str:
    """Format file size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"


def cleanup_temp_files():
    """Clean up temporary files (audio previews, thumbnail frames, etc.)"""
    import shutil
    cleaned_count = 0
    
    try:
        # Clean audio preview files
        for f in TEMP_DIR.glob("audio_preview_*.m4a"):
            try:
                f.unlink()
                cleaned_count += 1
            except Exception:
                pass
        
        # Clean waveform images
        for f in TEMP_DIR.glob("waveform_*.png"):
            try:
                f.unlink()
                cleaned_count += 1
            except Exception:
                pass
        
        # Clean thumbnail frame directories (older than 24 hours)
        import time
        current_time = time.time()
        for d in THUMBNAIL_FRAMES_DIR.iterdir():
            if d.is_dir():
                try:
                    # Check if directory is old (24 hours)
                    dir_age = current_time - d.stat().st_mtime
                    if dir_age > 86400:  # 24 hours in seconds
                        shutil.rmtree(d)
                        cleaned_count += 1
                except Exception:
                    pass
        
        if cleaned_count > 0:
            print(f"[Cleanup] Removed {cleaned_count} temp files/folders")
    except Exception as e:
        print(f"[Cleanup] Error during cleanup: {e}")


if __name__ == '__main__':
    print("\nEditFlow - Starting server...")
    print(f"Output folder: {OUTPUT_DIR}")
    
    # Clean up old temp files on startup (in background to not delay startup)
    def _background_cleanup():
        cleanup_temp_files()
    
    threading.Thread(target=_background_cleanup, daemon=True).start()
    
    print(f"Open http://{HOST}:{PORT} in your browser\n")
    # Auto-open browser once when server starts (avoid double-open with reloader)
    if not DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        def _open_browser():
            try:
                webbrowser.open(f"http://{HOST}:{PORT}")
            except Exception as e:
                print(f"[EditFlow] Failed to open browser: {e}")

        threading.Timer(1.0, _open_browser).start()
    app.run(host=HOST, port=PORT, debug=DEBUG, threaded=True)
