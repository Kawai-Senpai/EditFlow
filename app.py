"""
Flask API for EditFlow application
"""
import os
import threading
import uuid
import tkinter as tk
import webbrowser
from tkinter import filedialog
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from core.config import (
    HOST, PORT, DEBUG, OUTPUT_PRESETS, TRANSITIONS,
    PROFILES_DIR, TEMP_DIR, OUTPUT_DIR
)
from core.profile_manager import profile_manager
from core.video_processor import video_processor
from core.render_preset_manager import render_preset_manager


app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Store active processing threads
processing_threads = {}

# Supported video extensions
VIDEO_EXTENSIONS = [
    ('Video Files', '*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v *.ts *.mts'),
    ('All Files', '*.*')
]


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
    
    return jsonify({
        "path": info.path,
        "duration": info.duration,
        "duration_formatted": format_duration(info.duration),
        "width": info.width,
        "height": info.height,
        "fps": round(info.fps, 2),
        "codec": info.codec,
        "has_audio": info.has_audio
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
            results.append({
                "path": info.path,
                "filename": Path(info.path).name,
                "duration": info.duration,
                "duration_formatted": format_duration(info.duration),
                "width": info.width,
                "height": info.height,
                "fps": round(info.fps, 2),
                "codec": info.codec,
                "has_audio": info.has_audio
            })
    
    return jsonify(results)


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
    trim_map = {t['path']: t for t in trim_settings}
    
    profile_id = data.get('profile_id')
    transition = data.get('transition', 'cut')
    transition_duration = float(data.get('transition_duration', 1.0))
    preset = data.get('preset', 'youtube_1080p_balanced')
    output_name = data.get('output_name', 'output')
    apply_subscribe = data.get('apply_subscribe', False)
    subscribe_interval = float(data.get('subscribe_interval', 300))  # In seconds
    encoder = data.get('encoder', 'software')  # Hardware acceleration selection
    
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

            final_path = _unique_output_path(OUTPUT_DIR, output_name, job.id)
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
                subscribe_duration=subscribe_duration
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
    
    profile_id = data.get('profile_id')
    transition = data.get('transition', 'cut')
    transition_duration = float(data.get('transition_duration', 1.0))
    episode_duration = float(data.get('episode_duration', 3600))  # Default 1 hour
    episode_overlap = float(data.get('episode_overlap', 30))  # Default 30 seconds
    preset = data.get('preset', 'youtube_1080p_balanced')
    output_prefix = data.get('output_prefix', 'Episode')
    apply_subscribe = data.get('apply_subscribe', False)
    
    # Create job
    job = video_processor.create_job()
    output_prefix = _unique_output_prefix(OUTPUT_DIR, output_prefix, job.id)
    
    def process():
        try:
            job.status = "processing"
            
            # Step 1: Concatenate all videos first (if multiple)
            if len(video_paths) > 1:
                job.current_step = "Joining all videos..."
                job.current_step_num = 1
                
                concat_output = str(TEMP_DIR / f"concat_{job.id}.mp4")
                video_processor.concatenate_videos(
                    video_paths, concat_output, job,
                    transition=transition,
                    transition_duration=transition_duration,
                    preset=preset
                )
                source_video = concat_output
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
                output_prefix=output_prefix
            )
            
            # Clean up concat if we made one
            if len(video_paths) > 1 and Path(source_video).exists():
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
                            overlay_output = str(OUTPUT_DIR / f"{output_prefix}_{i+1:02d}_overlay.mp4")
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
                            sub_output = str(OUTPUT_DIR / f"{output_prefix}_{i+1:02d}_final.mp4")
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
                        final_path = str(OUTPUT_DIR / f"{output_prefix}_{i+1:02d}.mp4")
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
    files = []
    for f in OUTPUT_DIR.glob("*.mp4"):
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
    file_path = OUTPUT_DIR / secure_filename(filename)
    if file_path.exists():
        file_path.unlink()
        return jsonify({"message": "File deleted"})
    return jsonify({"error": "File not found"}), 404


@app.route('/api/output/folder', methods=['GET'])
def get_output_folder():
    """Get output folder path"""
    return jsonify({"path": str(OUTPUT_DIR)})


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


if __name__ == '__main__':
    print("\nEditFlow - Starting server...")
    print(f"Output folder: {OUTPUT_DIR}")
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
