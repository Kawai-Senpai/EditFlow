"""
Video processor - handles all FFmpeg operations for video processing
"""
import subprocess
import json
import os
import uuid
import re
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field
from .config import FFMPEG_PATH, FFPROBE_PATH, TEMP_DIR, OUTPUT_DIR, OUTPUT_PRESETS, TRANSITIONS, HW_ENCODERS
from .voice_effects_processor import voice_effects_processor


@dataclass
class AudioTrackInfo:
    """Audio track information"""
    index: int  # Stream index in the file
    track_index: int  # Audio-only index (0, 1, 2...)
    codec: str
    channels: int
    sample_rate: int
    title: Optional[str] = None
    bitrate: Optional[int] = None
    channel_layout: Optional[str] = None


@dataclass
class VideoInfo:
    """Video file information"""
    path: str
    duration: float
    width: int
    height: int
    fps: float
    codec: str
    bitrate: Optional[int] = None
    audio_codec: Optional[str] = None
    audio_bitrate: Optional[int] = None
    has_audio: bool = True
    audio_tracks: list = field(default_factory=list)  # List of AudioTrackInfo


@dataclass
class ProcessingJob:
    """Represents a video processing job"""
    id: str
    status: str = "pending"  # pending, processing, completed, failed, cancelled
    progress: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    current_step_num: int = 0
    output_files: list = field(default_factory=list)
    error: Optional[str] = None
    cancelled: bool = False


class VideoProcessor:
    """Handles all video processing operations"""
    
    def __init__(self):
        self.jobs: dict[str, ProcessingJob] = {}
        self.available_encoders = self._detect_hw_encoders()
        print(f"[VideoProcessor] Available encoders: {list(self.available_encoders.keys())}")
    
    def _detect_hw_encoders(self) -> dict:
        """Detect available hardware encoders"""
        available = {}
        
        for encoder_id, encoder_config in HW_ENCODERS.items():
            if encoder_config.get("test_cmd") is None:
                # Software encoder always available
                available[encoder_id] = encoder_config
                continue
            
            try:
                result = subprocess.run(
                    encoder_config["test_cmd"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    available[encoder_id] = encoder_config
                    print(f"[VideoProcessor] Hardware encoder available: {encoder_config['name']}")
            except Exception as e:
                print(f"[VideoProcessor] Hardware encoder not available ({encoder_id}): {e}")
        
        return available
    
    def get_available_encoders(self) -> list:
        """Return list of available encoders for frontend"""
        return [
            {"id": eid, "name": cfg["name"]}
            for eid, cfg in self.available_encoders.items()
        ]
    
    def get_video_info(self, file_path: str) -> Optional[VideoInfo]:
        """Get video file information using ffprobe"""
        try:
            cmd = [
                FFPROBE_PATH,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            # Find video stream and collect ALL audio streams
            video_stream = None
            audio_streams = []
            first_audio_stream = None
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video' and not video_stream:
                    video_stream = stream
                elif stream.get('codec_type') == 'audio':
                    audio_streams.append(stream)
                    if not first_audio_stream:
                        first_audio_stream = stream
            
            if not video_stream:
                return None
            
            # Parse FPS
            fps_str = video_stream.get('r_frame_rate', '30/1')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den) if float(den) != 0 else 30.0
            else:
                fps = float(fps_str)
            
            # Get duration
            duration = float(data.get('format', {}).get('duration', 0))
            
            # Build audio track info list
            audio_tracks = []
            for track_idx, stream in enumerate(audio_streams):
                title = stream.get('tags', {}).get('title') or stream.get('tags', {}).get('TITLE')
                audio_tracks.append(AudioTrackInfo(
                    index=stream.get('index', 0),
                    track_index=track_idx,
                    codec=stream.get('codec_name', 'unknown'),
                    channels=int(stream.get('channels', 2)),
                    sample_rate=int(stream.get('sample_rate', 48000)),
                    title=title,
                    bitrate=int(stream.get('bit_rate', 0)) if stream.get('bit_rate') else None,
                    channel_layout=stream.get('channel_layout')
                ))
            
            return VideoInfo(
                path=file_path,
                duration=duration,
                width=int(video_stream.get('width', 0)),
                height=int(video_stream.get('height', 0)),
                fps=fps,
                codec=video_stream.get('codec_name', 'unknown'),
                bitrate=int(data.get('format', {}).get('bit_rate', 0)) if data.get('format', {}).get('bit_rate') else None,
                audio_codec=first_audio_stream.get('codec_name') if first_audio_stream else None,
                audio_bitrate=int(first_audio_stream.get('bit_rate', 0)) if first_audio_stream and first_audio_stream.get('bit_rate') else None,
                has_audio=len(audio_streams) > 0,
                audio_tracks=audio_tracks
            )
        except Exception as e:
            print(f"Error getting video info: {e}")
            return None
    
    def _get_scale_filter(self, target_w: int, target_h: int, mode: str = "fit") -> str:
        """
        Get FFmpeg scale filter for target resolution.
        
        Modes:
        - "fit": Scale to fit inside target, letterbox with black bars if aspect differs (no cropping, no stretch)
        - "fill": Scale to fill target, crop if necessary (no black bars, no stretch)
        - "cover": Scale to cover target area, may extend beyond (for overlays)
        
        All modes preserve aspect ratio - NO STRETCHING ever.
        """
        if mode == "fill":
            # Scale to fill and crop if needed (crop from center)
            return f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}"
        elif mode == "cover":
            # Scale to cover the area (for transparent overlays)
            return f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase"
        else:  # "fit" - default
            # Scale to fit inside, pad with black bars if needed
            return f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black"
    
    def _get_overlay_scale_filter(self, target_w: int, target_h: int) -> str:
        """
        Get FFmpeg scale filter for overlay content (intro/outro/subscribe).
        Overlays should fill the frame completely - scale to cover then crop to exact size.
        """
        return f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}"

    def _resolve_target_dimensions(self, preset_config: dict, fallback_info: VideoInfo) -> tuple[int, int]:
        """Resolve output dimensions using preset or fallback video info."""
        target_w = preset_config.get("width") or fallback_info.width
        target_h = preset_config.get("height") or fallback_info.height
        return target_w, target_h
    
    def create_job(self) -> ProcessingJob:
        """Create a new processing job"""
        job_id = str(uuid.uuid4())[:8].upper()
        job = ProcessingJob(id=job_id)
        self.jobs[job_id] = job
        return job
    
    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get a processing job by ID"""
        return self.jobs.get(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a processing job"""
        job = self.jobs.get(job_id)
        if job and job.status == "processing":
            job.cancelled = True
            job.status = "cancelled"
            return True
        return False
    
    def _get_encoder_args(self, encoder_id: str, preset_config: dict) -> list:
        """Build encoder arguments based on selected encoder"""
        encoder = self.available_encoders.get(encoder_id, self.available_encoders.get("software"))
        
        if not encoder:
            # Fallback to software
            encoder = HW_ENCODERS["software"]
        
        quality = preset_config.get("quality")
        def _apply_quality(args_list: list, flag: str, value: Optional[float]) -> list:
            if value is None:
                return args_list
            if flag in args_list:
                idx = args_list.index(flag)
                if idx + 1 < len(args_list):
                    args_list[idx + 1] = str(value)
                else:
                    args_list.append(str(value))
            else:
                args_list.extend([flag, str(value)])
            return args_list

        args = ["-c:v", encoder["codec"]]
        
        if encoder_id == "nvenc" and "nvenc" in self.available_encoders:
            # NVIDIA NVENC settings
            args.extend(["-preset", encoder.get("preset", "p4")])
            nvenc_args = list(encoder.get("extra_args", []))
            _apply_quality(nvenc_args, "-cq", quality)
            args.extend(nvenc_args)
        elif encoder_id == "qsv" and "qsv" in self.available_encoders:
            # Intel QuickSync settings
            args.extend(["-preset", encoder.get("preset", "medium")])
            qsv_args = list(encoder.get("extra_args", []))
            _apply_quality(qsv_args, "-global_quality", quality)
            args.extend(qsv_args)
        elif encoder_id == "amf" and "amf" in self.available_encoders:
            # AMD AMF settings
            args.extend(["-quality", encoder.get("preset", "balanced")])
            amf_args = list(encoder.get("extra_args", []))
            _apply_quality(amf_args, "-qp_i", quality)
            _apply_quality(amf_args, "-qp_p", quality)
            args.extend(amf_args)
        else:
            # Software encoding (libx264)
            if preset_config.get("preset"):
                args.extend(["-preset", preset_config["preset"]])
            if preset_config.get("crf"):
                args.extend(["-crf", str(preset_config["crf"])])
        
        return args

    def _get_audio_codec(self, preset_config: dict) -> str:
        """Resolve audio codec for filter-based outputs."""
        codec = preset_config.get("audio_codec", "aac")
        return "aac" if codec == "copy" else codec
    
    def _build_audio_mix_filter(self, input_idx: int, audio_mix: list, duration: float = None,
                                 async_resample: bool = True, 
                                 voice_effects_preset_id: str = None,
                                 normalize_first: bool = True) -> tuple[str, str]:
        """
        Build audio filter chain that mixes multiple audio tracks with volume levels.
        
        Workflow for proper audio leveling:
        1. Extract each track
        2. Normalize each track to a common reference level (-16 LUFS)
        3. Apply relative volume adjustments based on track types
        4. Mix all tracks together
        5. Apply final limiter to prevent clipping
        
        Args:
            input_idx: The input file index in the FFmpeg command
            audio_mix: List of dicts with {track_index, volume, mute, solo, trackType} for each track
            duration: Optional duration limit for atrim
            async_resample: Whether to apply async resampling
            voice_effects_preset_id: Optional voice effects preset ID to apply to voice tracks
            normalize_first: Whether to normalize tracks before applying volume (recommended)
        
        Returns:
            Tuple of (filter_string, output_label)
        """
        if not audio_mix:
            # Default: use first audio track as-is
            base_filter = f"[{input_idx}:a:0]"
            if async_resample:
                base_filter += "aresample=async=1"
            if duration:
                if async_resample:
                    base_filter += f",atrim=duration={duration},asetpts=PTS-STARTPTS"
                else:
                    base_filter += f"atrim=duration={duration},asetpts=PTS-STARTPTS"
            return base_filter + f"[a{input_idx}]", f"a{input_idx}"
        
        # Get voice effects filter chain if preset is specified
        voice_filter_chain = ""
        if voice_effects_preset_id:
            voice_filter_chain = voice_effects_processor.get_filter_for_track(voice_effects_preset_id)
        
        # Check for solo - if any track is solo, only include solo tracks
        has_solo = any(t.get('solo', False) for t in audio_mix)
        
        filter_parts = []
        mix_labels = []
        
        for track in audio_mix:
            track_idx = track.get('track_index', 0)
            volume = track.get('volume', 1.0)
            muted = track.get('mute', False)
            solo = track.get('solo', False)
            track_type = track.get('trackType', 'other')
            
            # Skip muted tracks
            if muted:
                continue
            
            # If solo mode is active, skip non-solo tracks
            if has_solo and not solo:
                continue
            
            label = f"at{input_idx}_{track_idx}"
            
            # Build individual track filter
            track_filter = f"[{input_idx}:a:{track_idx}]"
            filters = []
            
            if async_resample:
                filters.append("aresample=async=1")
            
            if duration:
                filters.append(f"atrim=duration={duration}")
                filters.append("asetpts=PTS-STARTPTS")
            
            # Apply voice effects to voice-tagged tracks FIRST (before normalization)
            if track_type == 'voice' and voice_filter_chain:
                filters.append(voice_filter_chain)
            
            # Step 1: Normalize track to reference level (-16 LUFS)
            # This ensures all tracks start at the same perceived loudness
            if normalize_first:
                # Use dynaudnorm for realtime normalization (faster than loudnorm which requires 2-pass)
                # This normalizes the perceived loudness while preserving dynamics
                filters.append("dynaudnorm=f=150:g=15:p=0.9:m=10")
            
            # Step 2: Apply relative volume adjustment
            # Now the volume parameter represents relative level adjustment from normalized state
            if volume != 1.0:
                filters.append(f"volume={volume}")
            
            if filters:
                track_filter += ",".join(filters)
            
            track_filter += f"[{label}]"
            filter_parts.append(track_filter)
            mix_labels.append(f"[{label}]")
        
        # If all tracks are muted, generate silence
        if not mix_labels:
            silence = "anullsrc=channel_layout=stereo:sample_rate=48000"
            if duration:
                silence += f",atrim=duration={duration},asetpts=PTS-STARTPTS"
            return f"{silence}[a{input_idx}]", f"a{input_idx}"
        
        # If only one track, no need for amix
        if len(mix_labels) == 1:
            return filter_parts[0], mix_labels[0].strip('[]')
        
        # Mix multiple tracks with normalize=0 (we already normalized individually)
        output_label = f"amix{input_idx}"
        mix_inputs = "".join(mix_labels)
        # After mixing, apply a limiter to prevent clipping
        filter_parts.append(f"{mix_inputs}amix=inputs={len(mix_labels)}:duration=first:normalize=0,alimiter=limit=0.98:attack=5:release=50[{output_label}]")
        
        return ";".join(filter_parts), output_label
    
    def generate_audio_waveform(self, video_path: str, output_path: str, 
                                 width: int = 800, height: int = 120,
                                 track_index: int = 0, color: str = "0x3b82f6") -> bool:
        """
        Generate waveform image for an audio track.
        
        Args:
            video_path: Path to the video file
            output_path: Output PNG file path
            width: Image width
            height: Image height per track
            track_index: Which audio track to visualize
            color: Waveform color in 0xRRGGBB format
        
        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = [
                FFMPEG_PATH, "-y",
                "-i", video_path,
                "-filter_complex", f"[0:a:{track_index}]showwavespic=s={width}x{height}:colors={color}:scale=sqrt[out]",
                "-map", "[out]",
                "-frames:v", "1",
                output_path
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            return True
        except Exception as e:
            print(f"Error generating waveform: {e}")
            return False
    
    def analyze_audio_loudness(self, video_path: str, track_index: int = 0, 
                                duration: float = None) -> Optional[dict]:
        """
        Analyze audio loudness using FFmpeg's loudnorm filter (EBU R128).
        
        Args:
            video_path: Path to the video file
            track_index: Which audio track to analyze
            duration: Optional duration limit (analyzes first N seconds for speed)
            
        Returns:
            Dict with {loudness_lufs, loudness_range, peak_db} or None on failure
        """
        try:
            # Use ebur128 filter to measure loudness
            filter_str = f"[0:a:{track_index}]ebur128=peak=true"
            
            cmd = [
                FFMPEG_PATH,
                "-hide_banner",
            ]
            
            if duration:
                cmd.extend(["-t", str(duration)])
            
            cmd.extend([
                "-i", video_path,
                "-filter_complex", filter_str,
                "-f", "null", "-"
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Parse the output - ebur128 outputs summary at the end
            stderr = result.stderr
            
            # Look for the summary line
            # Format: Summary: Integrated: -XX.X LUFS ...
            loudness_lufs = -23.0  # EBU R128 default
            loudness_range = 7.0
            peak_db = -1.0
            
            for line in stderr.split('\n'):
                if 'I:' in line and 'LUFS' in line:
                    # Parse integrated loudness
                    try:
                        # Find the LUFS value
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if p == 'I:':
                                loudness_lufs = float(parts[i + 1])
                                break
                    except (ValueError, IndexError):
                        pass
                        
                if 'LRA:' in line and 'LU' in line:
                    try:
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if p == 'LRA:':
                                loudness_range = float(parts[i + 1])
                                break
                    except (ValueError, IndexError):
                        pass
                        
                if 'Peak:' in line or 'True peak:' in line.lower():
                    try:
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if 'peak' in p.lower() and i + 1 < len(parts):
                                peak_db = float(parts[i + 1])
                                break
                    except (ValueError, IndexError):
                        pass
            
            return {
                "loudness_lufs": loudness_lufs,
                "loudness_range": loudness_range,
                "peak_db": peak_db
            }
            
        except Exception as e:
            print(f"Error analyzing audio loudness: {e}")
            return None
    
    def analyze_all_tracks_loudness(self, video_path: str, duration: float = 30) -> list:
        """
        Analyze loudness of all audio tracks in a video.
        
        Args:
            video_path: Path to the video file
            duration: Duration to analyze (in seconds, for speed)
            
        Returns:
            List of dicts with {track_index, track_name, loudness_lufs, loudness_range, peak_db}
        """
        info = self.get_video_info(video_path)
        if not info or not info.audio_tracks:
            return []
        
        results = []
        for track in info.audio_tracks:
            analysis = self.analyze_audio_loudness(video_path, track.track_index, duration)
            if analysis:
                track_name = track.title if track.title else f"Track {track.track_index + 1}"
                results.append({
                    "track_index": track.track_index,
                    "track_name": track_name,
                    **analysis
                })
        
        return results
    
    def generate_audio_preview(self, video_path: str, output_path: str,
                               audio_mix: list, start_time: float = 0,
                               duration: float = 15,
                               voice_effects_preset_id: str = None) -> bool:
        """
        Generate a short audio preview with the specified mix settings.
        
        Args:
            video_path: Path to the video file
            output_path: Output audio file path (mp3/aac)
            audio_mix: List of dicts with {track_index, volume, mute, solo, trackType}
            start_time: Start time in seconds
            duration: Preview duration in seconds
            voice_effects_preset_id: Optional voice effects preset ID to apply to voice tracks
        
        Returns:
            True if successful, False otherwise
        """
        try:
            filter_str, output_label = self._build_audio_mix_filter(
                0, audio_mix, duration=duration, async_resample=False,
                voice_effects_preset_id=voice_effects_preset_id
            )
            
            cmd = [
                FFMPEG_PATH, "-y",
                "-ss", str(start_time),
                "-i", video_path,
                "-filter_complex", filter_str,
                "-map", f"[{output_label}]",
                "-t", str(duration),
                "-c:a", "aac",
                "-b:a", "192k",
                output_path
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            return True
        except Exception as e:
            print(f"Error generating audio preview: {e}")
            return False

    def _run_ffmpeg(self, cmd: list, job: ProcessingJob, duration: float, progress_callback: Optional[Callable] = None):
        """Run FFmpeg command with progress tracking"""
        import threading
        import queue

        def _format_step() -> str:
            if job.current_step:
                if job.total_steps:
                    return f" | Step {job.current_step_num}/{job.total_steps}: {job.current_step}"
                return f" | Step: {job.current_step}"
            return ""
        
        # Add progress reporting to stderr (not stdout, to avoid pipe issues)
        cmd_with_progress = cmd + ["-progress", "pipe:2", "-nostats"]
        
        print(f"[FFmpeg] Running: {' '.join(cmd_with_progress)}{_format_step()}")  # Debug log
        
        process = subprocess.Popen(
            cmd_with_progress,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Read stderr in a separate thread to avoid blocking
        stderr_lines = []
        stderr_queue = queue.Queue()
        
        def read_stderr():
            try:
                for line in process.stderr:
                    stderr_queue.put(line)
                    stderr_lines.append(line)
            except:
                pass
        
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        
        # Process stderr for progress updates
        saw_progress_end = False
        while True:
            if job.cancelled:
                process.terminate()
                raise Exception("Job cancelled by user")
            
            try:
                line = stderr_queue.get(timeout=0.1)
            except queue.Empty:
                if process.poll() is not None:
                    break
                continue
            
            if line.startswith("out_time_ms="):
                try:
                    time_ms = int(line.split("=")[1])
                    current_time = time_ms / 1_000_000
                    # Avoid reporting 100% until FFmpeg finishes
                    progress = min(current_time / duration * 100, 99.9) if duration > 0 else 0
                    job.progress = progress
                    print(f"[FFmpeg] Progress: {progress:.1f}%{_format_step()}")  # Debug log
                    if progress_callback:
                        progress_callback(progress)
                except ValueError:
                    pass
            elif line.startswith("progress="):
                if line.strip() == "progress=end":
                    saw_progress_end = True
                    job.progress = 100.0
                    if progress_callback:
                        progress_callback(100.0)
        
        # Wait for stderr thread to finish
        stderr_thread.join(timeout=2)
        
        # Read any remaining stdout
        stdout_output = process.stdout.read()
        
        if process.returncode != 0:
            error_msg = "".join(stderr_lines) if stderr_lines else "Unknown FFmpeg error"
            print(f"[FFmpeg] Error: {error_msg}")  # Debug log
            raise Exception(f"FFmpeg error: {error_msg}")
        if not saw_progress_end:
            job.progress = 100.0
            if progress_callback:
                progress_callback(100.0)
    
    def concatenate_videos(self, video_paths: list[str], output_path: str, job: ProcessingJob,
                          transition: str = "cut", transition_duration: float = 1.0,
                          preset: str = "youtube_1080p", trim_map: dict = None,
                          encoder: str = "software") -> str:
        """Concatenate multiple videos with optional transitions and trim settings"""
        if not video_paths:
            raise ValueError("No video files provided")
        
        trim_map = trim_map or {}
        
        # Get total duration (accounting for trim)
        total_duration = 0
        video_infos = []
        for path in video_paths:
            info = self.get_video_info(path)
            if info:
                video_infos.append(info)
                # Get trim values for this video
                trim = trim_map.get(path, {})
                trim_start = float(trim.get('trim_start', 0))
                trim_end = float(trim.get('trim_end', 0))
                # Calculate effective duration after trim
                effective_duration = max(0, info.duration - trim_start - trim_end)
                total_duration += effective_duration
        
        if not video_infos:
            raise ValueError("Could not get info for any video files")
        
        preset_config = OUTPUT_PRESETS.get(preset, OUTPUT_PRESETS["youtube_1080p"])
        
        if transition == "cut" or len(video_paths) == 1:
            return self._concat_cut(video_paths, output_path, job, preset_config, total_duration, trim_map, encoder)
        else:
            return self._concat_with_transition(video_paths, output_path, job, transition, 
                                                transition_duration, preset_config, total_duration, trim_map, encoder)
    
    def _concat_cut(self, video_paths: list[str], output_path: str, job: ProcessingJob, 
                    preset_config: dict, total_duration: float, trim_map: dict = None,
                    encoder: str = "software") -> str:
        """Concatenate videos with simple cut (no transition), applying trim settings"""
        trim_map = trim_map or {}
        
        first_info = self.get_video_info(video_paths[0])
        if first_info:
            target_w, target_h = self._resolve_target_dimensions(preset_config, first_info)
        else:
            target_w, target_h = 1920, 1080
        
        # Check if any trim is needed
        has_trim = any(
            float(trim_map.get(p, {}).get('trim_start', 0)) > 0 or 
            float(trim_map.get(p, {}).get('trim_end', 0)) > 0 
            for p in video_paths
        )
        
        if preset_config.get("codec") == "copy" and len(video_paths) == 1 and not has_trim:
            # Simple copy for single video without trim
            cmd = [FFMPEG_PATH, "-y", "-i", video_paths[0], "-c", "copy", output_path]
            self._run_ffmpeg(cmd, job, total_duration)
            return output_path
        
        # Build inputs with trim applied via -ss
        inputs = []
        input_durations = []
        video_infos = []
        for path in video_paths:
            info = self.get_video_info(path)
            if not info:
                raise ValueError(f"Could not get info for video: {path}")
            trim = trim_map.get(path, {})
            trim_start = float(trim.get('trim_start', 0))
            trim_end = float(trim.get('trim_end', 0))
            
            # Calculate actual duration after trim
            actual_duration = info.duration - trim_start - trim_end
            if actual_duration <= 0:
                raise ValueError(f"Trim duration too long for: {path}")
            input_durations.append(actual_duration)
            video_infos.append(info)
            
            # Add input with trim
            if trim_start > 0:
                inputs.extend(["-ss", str(trim_start)])
            inputs.extend(["-i", path])
        
        # Build filter complex to normalize all inputs to same resolution
        n = len(video_paths)
        scale_filter = self._get_scale_filter(target_w, target_h, mode="fit")
        
        # Scale and normalize all inputs, applying trim_end via trim filter
        filter_parts = []
        for i in range(n):
            info = video_infos[i]
            duration = input_durations[i]
            
            video_filter = f"[{i}:v]{scale_filter},setsar=1,fps=30,trim=duration={duration},setpts=PTS-STARTPTS"
            if info.has_audio:
                audio_filter = f"[{i}:a]aresample=async=1,atrim=duration={duration},asetpts=PTS-STARTPTS"
            else:
                audio_filter = f"anullsrc=channel_layout=stereo:sample_rate=48000,atrim=duration={duration},asetpts=PTS-STARTPTS"
            
            filter_parts.append(f"{video_filter}[v{i}]")
            filter_parts.append(f"{audio_filter}[a{i}]")
        
        # Concatenate all scaled videos
        concat_inputs = "".join([f"[v{i}]" for i in range(n)])
        filter_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=0[vout]")
        
        # Handle audio - concat all audio streams (using the processed audio labels)
        audio_concat = "".join([f"[a{i}]" for i in range(n)])
        filter_parts.append(f"{audio_concat}concat=n={n}:v=0:a=1[aout]")
        
        filter_complex = ";".join(filter_parts)
        
        try:
            cmd = [FFMPEG_PATH, "-y"] + inputs + ["-filter_complex", filter_complex]
            
            # Map outputs
            cmd.extend(["-map", "[vout]", "-map", "[aout]"])
            
            # Video encoding (use hardware acceleration if selected)
            encoder_args = self._get_encoder_args(encoder, preset_config)
            cmd.extend(encoder_args)
            
            # Audio encoding
            audio_codec = self._get_audio_codec(preset_config)
            cmd.extend(["-c:a", audio_codec])
            if audio_codec != "copy" and preset_config.get("audio_bitrate"):
                cmd.extend(["-b:a", preset_config["audio_bitrate"]])
            
            cmd.append(output_path)
            
            self._run_ffmpeg(cmd, job, total_duration)
            
            return output_path
        except Exception as e:
            raise Exception(f"Failed to concatenate videos: {e}")
    
    def _concat_with_transition(self, video_paths: list[str], output_path: str, job: ProcessingJob,
                                transition: str, transition_duration: float, preset_config: dict, 
                                total_duration: float, trim_map: dict = None,
                                encoder: str = "software") -> str:
        """Concatenate videos with transitions using complex filtergraph, with trim support"""
        trim_map = trim_map or {}
        n = len(video_paths)
        
        # Build input arguments with trim_start via -ss
        inputs = []
        input_durations = []
        video_infos = []
        for path in video_paths:
            info = self.get_video_info(path)
            if not info:
                raise ValueError(f"Could not get info for video: {path}")
            trim = trim_map.get(path, {})
            trim_start = float(trim.get('trim_start', 0))
            trim_end = float(trim.get('trim_end', 0))
            
            # Calculate actual duration after trim
            actual_duration = info.duration - trim_start - trim_end
            if actual_duration <= 0:
                raise ValueError(f"Trim duration too long for: {path}")
            input_durations.append(actual_duration)
            video_infos.append(info)
            
            # Add input with trim_start
            if trim_start > 0:
                inputs.extend(["-ss", str(trim_start)])
            inputs.extend(["-i", path])
        
        # Build filter complex
        filter_parts = []
        
        # Scale all inputs to same size - use FIT mode (no stretch, letterbox if needed)
        first_info = self.get_video_info(video_paths[0])
        if first_info:
            target_w, target_h = self._resolve_target_dimensions(preset_config, first_info)
        else:
            target_w, target_h = 1920, 1080
        scale_filter = self._get_scale_filter(target_w, target_h, mode="fit")
        
        for i in range(n):
            info = video_infos[i]
            duration = input_durations[i]
            
            video_filter = f"[{i}:v]{scale_filter},setsar=1,fps=30,trim=duration={duration},setpts=PTS-STARTPTS"
            if info.has_audio:
                audio_filter = f"[{i}:a]aresample=async=1:first_pts=0,atrim=duration={duration},asetpts=PTS-STARTPTS"
            else:
                audio_filter = f"anullsrc=channel_layout=stereo:sample_rate=48000,atrim=duration={duration},asetpts=PTS-STARTPTS"
            
            filter_parts.append(f"{video_filter}[v{i}];")
            filter_parts.append(f"{audio_filter}[a{i}];")
        
        # Apply transitions
        transition_map = {
            "crossfade": "fade",
            "fade_black": "fadeblack",
            "dip_white": "fadewhite"
        }
        transition_name = transition_map.get(transition)
        transition_durations = []

        if transition_name:
            prev_v = "v0"
            prev_a = "a0"
            offset = 0

            for i in range(1, n):
                curr_v = f"v{i}"
                curr_a = f"a{i}"
                out_v = f"vout{i}" if i < n - 1 else "vfinal"
                out_a = f"aout{i}" if i < n - 1 else "afinal"

                pair_duration = min(transition_duration, input_durations[i - 1], input_durations[i])
                if pair_duration <= 0:
                    raise ValueError("Transition duration too long for clip length")
                transition_durations.append(pair_duration)

                offset += input_durations[i - 1] - pair_duration

                filter_parts.append(
                    f"[{prev_v}][{curr_v}]xfade=transition={transition_name}:duration={pair_duration}:offset={offset}[{out_v}];"
                )
                filter_parts.append(f"[{prev_a}][{curr_a}]acrossfade=d={pair_duration}[{out_a}];")

                prev_v = out_v
                prev_a = out_a
        else:
            raise ValueError(f"Unsupported transition: {transition}")
        
        filter_complex = "".join(filter_parts)
        # Remove trailing semicolon
        if filter_complex.endswith(";"):
            filter_complex = filter_complex[:-1]
        
        cmd = [FFMPEG_PATH, "-y"] + inputs
        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", "[vfinal]", "-map", "[afinal]"])
        
        # Output encoding (use hardware acceleration if selected)
        encoder_args = self._get_encoder_args(encoder, preset_config)
        cmd.extend(encoder_args)
        audio_codec = self._get_audio_codec(preset_config)
        cmd.extend(["-c:a", audio_codec])
        if audio_codec != "copy" and preset_config.get("audio_bitrate"):
            cmd.extend(["-b:a", preset_config["audio_bitrate"]])
        
        cmd.append(output_path)
        
        adjusted_duration = total_duration - sum(transition_durations)
        self._run_ffmpeg(cmd, job, adjusted_duration)
        
        return output_path
    
    def split_into_episodes(self, video_path: str, job: ProcessingJob,
                           episode_duration: float = 3600,
                           overlap_seconds: float = 30,
                           preset: str = "youtube_1080p",
                           output_prefix: str = "Episode",
                           output_dir: Optional[str] = None) -> list[str]:
        """Split a video into episodes with overlap"""
        video_info = self.get_video_info(video_path)
        if not video_info:
            raise ValueError("Could not get video info")
        
        total_duration = video_info.duration
        preset_config = OUTPUT_PRESETS.get(preset, OUTPUT_PRESETS["youtube_1080p"])
        
        # Calculate episodes
        episodes = []
        current_time = 0
        episode_num = 1
        
        while current_time < total_duration:
            start_time = current_time
            end_time = min(start_time + episode_duration, total_duration)
            
            # For last episode, check if remaining is too short
            remaining = total_duration - start_time
            if remaining < episode_duration:
                # If very short, extend overlap from previous
                if remaining < episode_duration * 0.3 and episode_num > 1:
                    # Add more overlap to previous episode end
                    end_time = total_duration
                else:
                    # Just make it bigger
                    end_time = total_duration
            
            episodes.append({
                "num": episode_num,
                "start": start_time,
                "end": end_time,
                "duration": end_time - start_time
            })
            
            # Next episode starts with overlap
            if end_time < total_duration:
                current_time = end_time - overlap_seconds
            else:
                break
            
            episode_num += 1
        
        # Process each episode
        output_files = []
        job.total_steps = len(episodes)
        
        output_base = Path(output_dir) if output_dir else OUTPUT_DIR
        output_base.mkdir(parents=True, exist_ok=True)

        for i, ep in enumerate(episodes):
            if job.cancelled:
                break
            
            job.current_step = f"Processing {output_prefix} {ep['num']}"
            job.current_step_num = i + 1
            
            output_path = str(output_base / f"{output_prefix}_{ep['num']:02d}.mp4")
            
            target_w = preset_config.get("width", 1920)
            target_h = preset_config.get("height", 1080)
            scale_filter = self._get_scale_filter(target_w, target_h, mode="fit")
            
            cmd = [
                FFMPEG_PATH, "-y",
                "-ss", str(ep["start"]),
                "-i", video_path,
                "-t", str(ep["duration"])
            ]
            
            if preset_config.get("codec") == "copy":
                cmd.extend(["-c", "copy"])
            else:
                cmd.extend(["-c:v", preset_config["codec"]])
                if preset_config.get("preset"):
                    cmd.extend(["-preset", preset_config["preset"]])
                if preset_config.get("crf"):
                    cmd.extend(["-crf", str(preset_config["crf"])])
                if preset_config.get("width") and preset_config.get("height"):
                    cmd.extend(["-vf", scale_filter])
                cmd.extend(["-c:a", preset_config.get("audio_codec", "aac")])
                if preset_config.get("audio_bitrate"):
                    cmd.extend(["-b:a", preset_config["audio_bitrate"]])
            
            cmd.append(output_path)
            
            self._run_ffmpeg(cmd, job, ep["duration"])
            output_files.append(output_path)
        
        return output_files
    
    def apply_overlay(self, video_path: str, overlay_path: str, output_path: str,
                     job: ProcessingJob, start_time: float = 0,
                     overlay_has_audio: bool = True, preset: str = "youtube_1080p",
                     encoder: str = "software") -> str:
        """Apply a transparent overlay to video at specified time"""
        video_info = self.get_video_info(video_path)
        overlay_info = self.get_video_info(overlay_path)
        
        if not video_info or not overlay_info:
            raise ValueError("Could not get video info")
        
        preset_config = OUTPUT_PRESETS.get(preset, OUTPUT_PRESETS["youtube_1080p"])
        target_w = preset_config.get("width") or video_info.width
        target_h = preset_config.get("height") or video_info.height
        
        # Scale filters - FIT for base, FILL for overlay
        scale_filter = self._get_scale_filter(target_w, target_h, mode="fit")
        overlay_scale = self._get_overlay_scale_filter(target_w, target_h)
        
        # Build filter for overlay
        filter_complex = f"[0:v]{scale_filter},setsar=1[base];[1:v]format=rgba,{overlay_scale}[ovr];[base][ovr]overlay=0:0:enable='between(t,{start_time},{start_time + overlay_info.duration})'"
        
        cmd = [
            FFMPEG_PATH, "-y",
            "-i", video_path,
            "-i", overlay_path,
            "-filter_complex", filter_complex
        ]
        
        # Handle audio mixing if overlay has audio
        if overlay_has_audio and overlay_info.has_audio:
            audio_filter = f"[1:a]adelay={int(start_time * 1000)}|{int(start_time * 1000)}[aud];[0:a][aud]amix=inputs=2:duration=first"
            cmd[-1] = f"{filter_complex};{audio_filter}"
        
        # Output encoding
        encoder_args = self._get_encoder_args(encoder, preset_config)
        cmd.extend(encoder_args)
        audio_codec = self._get_audio_codec(preset_config)
        cmd.extend(["-c:a", audio_codec])
        if audio_codec != "copy" and preset_config.get("audio_bitrate"):
            cmd.extend(["-b:a", preset_config["audio_bitrate"]])
        
        cmd.append(output_path)
        
        self._run_ffmpeg(cmd, job, video_info.duration)
        
        return output_path
    
    def apply_intro_outro_overlays(self, video_path: str, output_path: str, job: ProcessingJob,
                                   intro_path: Optional[str] = None, intro_overlap: float = 0,
                                   intro_full_overlap: bool = False,
                                   outro_path: Optional[str] = None, outro_overlap: float = 0,
                                   outro_full_overlap: bool = False,
                                   preset: str = "youtube_1080p",
                                   encoder: str = "software") -> str:
        """
        Apply intro and outro to video.
        
        Modes:
        - full_overlap=True OR overlap > 0: Overlay on top of video (transparent overlay)
        - full_overlap=False AND overlap=0: Concatenate (append/prepend) to video
        """
        video_info = self.get_video_info(video_path)
        if not video_info:
            raise ValueError("Could not get video info")
        
        preset_config = OUTPUT_PRESETS.get(preset, OUTPUT_PRESETS["youtube_1080p"])
        target_w = preset_config.get("width") or video_info.width
        target_h = preset_config.get("height") or video_info.height
        
        # Determine which method to use for intro and outro
        intro_mode = "overlay" if (intro_full_overlap or intro_overlap > 0) else "concat"
        outro_mode = "overlay" if (outro_full_overlap or outro_overlap > 0) else "concat"
        
        # If both are concat mode, we can use simple concatenation
        # If any is overlay mode, we need complex filter
        
        intro_info = self.get_video_info(intro_path) if intro_path else None
        outro_info = self.get_video_info(outro_path) if outro_path else None
        
        # Determine total expected duration
        total_duration = video_info.duration
        if intro_info and intro_mode == "concat":
            total_duration += intro_info.duration
        if outro_info and outro_mode == "concat":
            total_duration += outro_info.duration
        
        # Build the filter complex
        inputs = []
        input_map = {}  # Maps logical name to input index
        
        current_input_idx = 0
        
        # Collect all inputs
        videos_to_concat_before = []
        videos_to_concat_after = []
        
        # Add intro as concat if needed
        if intro_path and intro_mode == "concat":
            inputs.extend(["-i", intro_path])
            videos_to_concat_before.append(current_input_idx)
            input_map["intro"] = current_input_idx
            current_input_idx += 1
        
        # Add main video
        inputs.extend(["-i", video_path])
        input_map["main"] = current_input_idx
        current_input_idx += 1
        
        # Add intro as overlay if needed (after main video in inputs)
        if intro_path and intro_mode == "overlay":
            inputs.extend(["-i", intro_path])
            input_map["intro_overlay"] = current_input_idx
            current_input_idx += 1
        
        # Add outro as concat if needed
        if outro_path and outro_mode == "concat":
            inputs.extend(["-i", outro_path])
            videos_to_concat_after.append(current_input_idx)
            input_map["outro"] = current_input_idx
            current_input_idx += 1
        
        # Add outro as overlay if needed (after everything else)
        if outro_path and outro_mode == "overlay":
            inputs.extend(["-i", outro_path])
            input_map["outro_overlay"] = current_input_idx
            current_input_idx += 1
        
        filter_parts = []
        scale_filter = self._get_scale_filter(target_w, target_h, mode="fit")
        overlay_scale = self._get_overlay_scale_filter(target_w, target_h)
        
        # Process intro concat videos
        concat_video_labels = []
        concat_audio_labels = []
        
        for idx in videos_to_concat_before:
            filter_parts.append(f"[{idx}:v]{scale_filter},setsar=1,fps=30[cv{idx}]")
            filter_parts.append(f"[{idx}:a]aresample=async=1[ca{idx}]")
            concat_video_labels.append(f"[cv{idx}]")
            concat_audio_labels.append(f"[ca{idx}]")
        
        # Process main video
        main_idx = input_map["main"]
        filter_parts.append(f"[{main_idx}:v]{scale_filter},setsar=1,fps=30[mainv]")
        filter_parts.append(f"[{main_idx}:a]aresample=async=1[maina]")
        main_video_label = "mainv"
        main_audio_label = "maina"
        
        # Apply intro overlay if needed (on top of main video)
        if intro_path and intro_mode == "overlay":
            intro_idx = input_map["intro_overlay"]
            intro_start = 0
            filter_parts.append(f"[{intro_idx}:v]format=rgba,{overlay_scale}[introv]")
            filter_parts.append(f"[{main_video_label}][introv]overlay=0:0:enable='between(t,{intro_start},{intro_info.duration})'[withintro]")
            main_video_label = "withintro"
            
            # Mix intro audio
            if intro_info.has_audio:
                filter_parts.append(f"[{intro_idx}:a]aresample=async=1[introa]")
                filter_parts.append(f"[{main_audio_label}][introa]amix=inputs=2:duration=first:dropout_transition=2[withintroaudio]")
                main_audio_label = "withintroaudio"
        
        # Apply outro overlay if needed (on top of main video)
        if outro_path and outro_mode == "overlay":
            outro_idx = input_map["outro_overlay"]
            # Outro starts X seconds before end
            outro_start = video_info.duration - outro_overlap - outro_info.duration
            if outro_start < 0:
                outro_start = video_info.duration - outro_info.duration
            
            filter_parts.append(f"[{outro_idx}:v]format=rgba,{overlay_scale}[outrov]")
            filter_parts.append(f"[{main_video_label}][outrov]overlay=0:0:enable='between(t,{outro_start},{outro_start + outro_info.duration})'[withoutro]")
            main_video_label = "withoutro"
            
            # Mix outro audio
            if outro_info.has_audio:
                delay_ms = int(outro_start * 1000)
                filter_parts.append(f"[{outro_idx}:a]adelay={delay_ms}|{delay_ms},aresample=async=1[outroa]")
                filter_parts.append(f"[{main_audio_label}][outroa]amix=inputs=2:duration=first:dropout_transition=2[withoutroaudio]")
                main_audio_label = "withoutroaudio"
        
        # Add processed main video to concat list
        concat_video_labels.append(f"[{main_video_label}]")
        concat_audio_labels.append(f"[{main_audio_label}]")
        
        # Process outro concat videos
        for idx in videos_to_concat_after:
            filter_parts.append(f"[{idx}:v]{scale_filter},setsar=1,fps=30[cv{idx}]")
            filter_parts.append(f"[{idx}:a]aresample=async=1[ca{idx}]")
            concat_video_labels.append(f"[cv{idx}]")
            concat_audio_labels.append(f"[ca{idx}]")
        
        # Concatenate all video and audio streams
        n_concat = len(concat_video_labels)
        if n_concat > 1:
            concat_v = "".join(concat_video_labels)
            concat_a = "".join(concat_audio_labels)
            filter_parts.append(f"{concat_v}concat=n={n_concat}:v=1:a=0[finalv]")
            filter_parts.append(f"{concat_a}concat=n={n_concat}:v=0:a=1[finala]")
            final_video = "finalv"
            final_audio = "finala"
        else:
            final_video = main_video_label
            final_audio = main_audio_label
        
        filter_complex = ";".join(filter_parts)
        
        cmd = [FFMPEG_PATH, "-y"] + inputs
        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", f"[{final_video}]", "-map", f"[{final_audio}]"])
        
        # Output encoding (use hardware acceleration if selected)
        encoder_args = self._get_encoder_args(encoder, preset_config)
        cmd.extend(encoder_args)
        audio_codec = self._get_audio_codec(preset_config)
        cmd.extend(["-c:a", audio_codec])
        if audio_codec != "copy" and preset_config.get("audio_bitrate"):
            cmd.extend(["-b:a", preset_config["audio_bitrate"]])
        
        cmd.append(output_path)
        
        self._run_ffmpeg(cmd, job, total_duration)
        
        return output_path
    
    def apply_subscribe_graphics(self, video_path: str, subscribe_path: str, output_path: str,
                                 job: ProcessingJob, interval_seconds: float = 300,
                                 duration_seconds: float = 8, preset: str = "youtube_1080p",
                                 encoder: str = "software") -> str:
        """Apply subscribe graphics at regular intervals"""
        video_info = self.get_video_info(video_path)
        subscribe_info = self.get_video_info(subscribe_path)
        
        if not video_info or not subscribe_info:
            raise ValueError("Could not get video info")
        
        preset_config = OUTPUT_PRESETS.get(preset, OUTPUT_PRESETS["youtube_1080p"])
        
        # Calculate appearance times
        appearances = []
        if interval_seconds > 0 and duration_seconds > 0:
            current_time = interval_seconds
            while current_time < video_info.duration - duration_seconds:
                appearances.append(current_time)
                current_time += interval_seconds
        
        if not appearances:
            # Just copy the video
            import shutil
            shutil.copy2(video_path, output_path)
            return output_path
        
        target_w = preset_config.get("width") or video_info.width
        target_h = preset_config.get("height") or video_info.height
        
        # Build enable expression for all appearances
        enable_expr = " + ".join([f"between(t,{t},{t + duration_seconds})" for t in appearances])
        
        # Scale filters - FIT for base video, FILL for overlay
        scale_filter = self._get_scale_filter(target_w, target_h, mode="fit")
        overlay_scale = self._get_overlay_scale_filter(target_w, target_h)
        
        filter_parts = []
        filter_parts.append(f"[0:v]{scale_filter},setsar=1[base]")
        filter_parts.append(
            f"[1:v]format=rgba,{overlay_scale},trim=duration={duration_seconds},setpts=PTS-STARTPTS[subbase]"
        )

        sub_inputs = []
        if len(appearances) > 1:
            sub_labels = "".join([f"[sub{i}]" for i in range(len(appearances))])
            filter_parts.append(f"[subbase]split={len(appearances)}{sub_labels}")
            sub_inputs = [f"sub{i}" for i in range(len(appearances))]
        else:
            sub_inputs = ["subbase"]

        current_label = "base"
        for i, t in enumerate(appearances):
            sub_label = sub_inputs[i] if len(sub_inputs) > 1 else sub_inputs[0]
            filter_parts.append(f"[{sub_label}]setpts=PTS+{t}/TB[subt{i}]")
            filter_parts.append(
                f"[{current_label}][subt{i}]overlay=0:0:enable='between(t,{t},{t + duration_seconds})':eof_action=pass[v{i}]"
            )
            current_label = f"v{i}"
        
        filter_complex = ";".join(filter_parts)
        
        # Audio mixing for subscribe sound at each appearance
        audio_filters = []
        if subscribe_info.has_audio:
            audio_filters.append(
                f"[1:a]atrim=duration={duration_seconds},asetpts=PTS-STARTPTS[suba]"
            )

            suba_inputs = []
            if len(appearances) > 1:
                suba_labels = "".join([f"[suba{i}]" for i in range(len(appearances))])
                audio_filters.append(f"[suba]asplit={len(appearances)}{suba_labels}")
                suba_inputs = [f"suba{i}" for i in range(len(appearances))]
            else:
                suba_inputs = ["suba"]

            audio_inputs = []
            for i, t in enumerate(appearances):
                delay_ms = int(t * 1000)
                src = suba_inputs[i] if len(suba_inputs) > 1 else suba_inputs[0]
                audio_filters.append(f"[{src}]adelay={delay_ms}|{delay_ms}[subad{i}]")
                audio_inputs.append(f"[subad{i}]")

            if audio_inputs:
                mix_inputs = "[0:a]" + "".join(audio_inputs)
                audio_filters.append(
                    f"{mix_inputs}amix=inputs={len(audio_inputs) + 1}:duration=first:dropout_transition=2[aout]"
                )
                filter_complex += ";" + ";".join(audio_filters)
        
        cmd = [
            FFMPEG_PATH, "-y",
            "-i", video_path,
            "-i", subscribe_path,
            "-filter_complex", filter_complex,
            "-map", f"[{current_label}]"
        ]
        
        if subscribe_info.has_audio and audio_filters:
            cmd.extend(["-map", "[aout]"])
        else:
            cmd.extend(["-map", "0:a"])
        
        # Output encoding
        encoder_args = self._get_encoder_args(encoder, preset_config)
        cmd.extend(encoder_args)
        audio_codec = self._get_audio_codec(preset_config)
        cmd.extend(["-c:a", audio_codec])
        if audio_codec != "copy" and preset_config.get("audio_bitrate"):
            cmd.extend(["-b:a", preset_config["audio_bitrate"]])
        cmd.append(output_path)
        
        self._run_ffmpeg(cmd, job, video_info.duration)
        
        return output_path

    def process_single_pass(self, video_paths: list[str], output_path: str, job: ProcessingJob,
                            transition: str = "cut", transition_duration: float = 1.0,
                            preset: str = "youtube_1080p", trim_map: dict = None,
                            encoder: str = "software",
                            intro_path: Optional[str] = None, intro_overlap: float = 0,
                            intro_full_overlap: bool = False,
                            outro_path: Optional[str] = None, outro_overlap: float = 0,
                            outro_full_overlap: bool = False,
                            subscribe_path: Optional[str] = None,
                            subscribe_interval: float = 300,
                            subscribe_duration: float = 8,
                            audio_mix_map: dict = None,
                            voice_effects_preset_id: str = None) -> str:
        """
        Render the full single-video pipeline in one FFmpeg pass.
        
        Args:
            audio_mix_map: Dict mapping video path to audio mix settings.
                           Each value is a list of {track_index, volume, mute, solo, trackType}
                           If None or empty for a video, all tracks mixed at 1.0 volume.
            voice_effects_preset_id: Optional voice effects preset ID to apply to voice-tagged tracks.
        """
        if not video_paths:
            raise ValueError("No video files provided")

        trim_map = trim_map or {}
        audio_mix_map = audio_mix_map or {}
        preset_config = OUTPUT_PRESETS.get(preset, OUTPUT_PRESETS["youtube_1080p"])
        if transition_duration <= 0:
            transition = "cut"
        if transition_duration <= 0:
            transition = "cut"

        inputs = []
        video_infos = []
        input_durations = []

        for path in video_paths:
            info = self.get_video_info(path)
            if not info:
                raise ValueError(f"Could not get video info for: {path}")
            video_infos.append(info)

            trim = trim_map.get(path, {})
            trim_start = float(trim.get('trim_start', 0))
            trim_end = float(trim.get('trim_end', 0))

            duration = info.duration - trim_start - trim_end
            if duration <= 0:
                raise ValueError(f"Trim duration too long for: {path}")
            input_durations.append(duration)

            if trim_start > 0:
                inputs.extend(["-ss", str(trim_start)])
            inputs.extend(["-i", path])

        intro_info = self.get_video_info(intro_path) if intro_path else None
        outro_info = self.get_video_info(outro_path) if outro_path else None
        subscribe_info = self.get_video_info(subscribe_path) if subscribe_path else None

        if intro_path and not intro_info:
            raise ValueError("Could not get intro video info")
        if outro_path and not outro_info:
            raise ValueError("Could not get outro video info")
        if subscribe_path and not subscribe_info:
            raise ValueError("Could not get subscribe graphics info")

        intro_mode = "overlay" if (intro_path and (intro_full_overlap or intro_overlap > 0)) else "concat"
        outro_mode = "overlay" if (outro_path and (outro_full_overlap or outro_overlap > 0)) else "concat"

        transition_durations = []
        if transition != "cut" and len(video_paths) > 1:
            for i in range(1, len(video_paths)):
                pair_duration = min(transition_duration, input_durations[i - 1], input_durations[i])
                if pair_duration <= 0:
                    raise ValueError("Transition duration too long for clip length")
                transition_durations.append(pair_duration)

        main_duration = sum(input_durations) - sum(transition_durations)

        concat_intro_duration = intro_info.duration if intro_info and intro_mode == "concat" else 0
        concat_outro_duration = outro_info.duration if outro_info and outro_mode == "concat" else 0
        total_duration = main_duration + concat_intro_duration + concat_outro_duration

        appearances = []
        if subscribe_path and subscribe_interval > 0 and subscribe_duration > 0 and total_duration > 0:
            current_time = float(subscribe_interval)
            while current_time < total_duration - subscribe_duration:
                appearances.append(current_time)
                current_time += subscribe_interval

        has_trim = any(
            float(trim_map.get(p, {}).get('trim_start', 0)) > 0 or
            float(trim_map.get(p, {}).get('trim_end', 0)) > 0
            for p in video_paths
        )
        has_subscribe = bool(subscribe_path and appearances)

        if (len(video_paths) == 1 and transition == "cut" and not has_trim and
                not intro_path and not outro_path and not has_subscribe and
                preset_config.get("codec") == "copy"):
            cmd = [FFMPEG_PATH, "-y", "-i", video_paths[0], "-c", "copy", output_path]
            self._run_ffmpeg(cmd, job, input_durations[0])
            return output_path

        target_w, target_h = self._resolve_target_dimensions(preset_config, video_infos[0])
        scale_filter = self._get_scale_filter(target_w, target_h, mode="fit")
        overlay_scale = self._get_overlay_scale_filter(target_w, target_h)

        filter_parts = []
        use_first_pts = transition != "cut" and len(video_paths) > 1
        audio_async = "aresample=async=1:first_pts=0" if use_first_pts else "aresample=async=1"

        # Normalize main inputs (video and audio with multi-track mixing).
        for i, info in enumerate(video_infos):
            duration = input_durations[i]
            path = video_paths[i]

            video_filter = f"[{i}:v]{scale_filter},setsar=1,fps=30,trim=duration={duration},setpts=PTS-STARTPTS"
            filter_parts.append(f"{video_filter}[v{i}]")

            if info.has_audio:
                # Get audio mix settings for this video
                audio_mix = audio_mix_map.get(path, [])
                
                if audio_mix and len(info.audio_tracks) > 1:
                    # Multi-track mixing with custom levels
                    audio_filter_str, audio_label = self._build_audio_mix_filter(
                        i, audio_mix, duration=duration, 
                        async_resample=True,
                        voice_effects_preset_id=voice_effects_preset_id
                    )
                    # The _build_audio_mix_filter returns a complete filter with output label
                    # But we need to integrate with our naming scheme
                    # Split the filter and rename the output
                    if audio_label != f"a{i}":
                        # Replace the output label in the filter
                        audio_filter_str = audio_filter_str.replace(f"[{audio_label}]", f"[a{i}]")
                    filter_parts.append(audio_filter_str)
                else:
                    # Single track or no mix settings - use default (first track or mix all)
                    if len(info.audio_tracks) > 1 and not audio_mix:
                        # Mix all tracks at 1.0 volume by default
                        default_mix = [{"track_index": t.track_index, "volume": 1.0} for t in info.audio_tracks]
                        audio_filter_str, audio_label = self._build_audio_mix_filter(
                            i, default_mix, duration=duration,
                            async_resample=True,
                            voice_effects_preset_id=voice_effects_preset_id
                        )
                        if audio_label != f"a{i}":
                            audio_filter_str = audio_filter_str.replace(f"[{audio_label}]", f"[a{i}]")
                        filter_parts.append(audio_filter_str)
                    else:
                        # Single track video - use traditional filter
                        audio_filter = f"[{i}:a]{audio_async},atrim=duration={duration},asetpts=PTS-STARTPTS[a{i}]"
                        filter_parts.append(audio_filter)
            else:
                audio_filter = f"anullsrc=channel_layout=stereo:sample_rate=48000,atrim=duration={duration},asetpts=PTS-STARTPTS[a{i}]"
                filter_parts.append(audio_filter)

        # Build main sequence (with optional transitions).
        main_video_label = "v0"
        main_audio_label = "a0"
        if len(video_paths) > 1:
            if transition == "cut":
                concat_v = "".join([f"[v{i}]" for i in range(len(video_paths))])
                concat_a = "".join([f"[a{i}]" for i in range(len(video_paths))])
                filter_parts.append(f"{concat_v}concat=n={len(video_paths)}:v=1:a=0[vmain]")
                filter_parts.append(f"{concat_a}concat=n={len(video_paths)}:v=0:a=1[amain]")
                main_video_label = "vmain"
                main_audio_label = "amain"
            else:
                transition_map = {
                    "crossfade": "fade",
                    "fade_black": "fadeblack",
                    "dip_white": "fadewhite"
                }
                transition_name = transition_map.get(transition)
                if not transition_name:
                    raise ValueError(f"Unsupported transition: {transition}")

                prev_v = "v0"
                prev_a = "a0"
                offset = 0
                for i in range(1, len(video_paths)):
                    curr_v = f"v{i}"
                    curr_a = f"a{i}"
                    out_v = f"vxf{i}" if i < len(video_paths) - 1 else "vmain"
                    out_a = f"axf{i}" if i < len(video_paths) - 1 else "amain"

                    pair_duration = transition_durations[i - 1]
                    offset += input_durations[i - 1] - pair_duration
                    filter_parts.append(
                        f"[{prev_v}][{curr_v}]xfade=transition={transition_name}:duration={pair_duration}:offset={offset}[{out_v}]"
                    )
                    filter_parts.append(f"[{prev_a}][{curr_a}]acrossfade=d={pair_duration}[{out_a}]")

                    prev_v = out_v
                    prev_a = out_a

                main_video_label = "vmain"
                main_audio_label = "amain"

        # Apply intro/outro overlays on the main sequence.
        next_input_index = len(video_paths)
        if intro_path and intro_mode == "overlay":
            intro_idx = next_input_index
            inputs.extend(["-i", intro_path])
            next_input_index += 1

            filter_parts.append(f"[{intro_idx}:v]format=rgba,{overlay_scale}[introv]")
            filter_parts.append(
                f"[{main_video_label}][introv]overlay=0:0:enable='between(t,0,{intro_info.duration})'[withintro]"
            )
            main_video_label = "withintro"

            if intro_info.has_audio:
                filter_parts.append(f"[{intro_idx}:a]aresample=async=1[introa]")
                filter_parts.append(
                    f"[{main_audio_label}][introa]amix=inputs=2:duration=first:dropout_transition=2[withintroaudio]"
                )
                main_audio_label = "withintroaudio"

        if outro_path and outro_mode == "overlay":
            outro_idx = next_input_index
            inputs.extend(["-i", outro_path])
            next_input_index += 1

            outro_start = main_duration - outro_overlap - outro_info.duration
            if outro_start < 0:
                outro_start = main_duration - outro_info.duration
            if outro_start < 0:
                outro_start = 0

            filter_parts.append(f"[{outro_idx}:v]format=rgba,{overlay_scale}[outrov]")
            filter_parts.append(
                f"[{main_video_label}][outrov]overlay=0:0:enable='between(t,{outro_start},{outro_start + outro_info.duration})'[withoutro]"
            )
            main_video_label = "withoutro"

            if outro_info.has_audio:
                delay_ms = max(0, int(outro_start * 1000))
                filter_parts.append(f"[{outro_idx}:a]adelay={delay_ms}|{delay_ms},aresample=async=1[outroa]")
                filter_parts.append(
                    f"[{main_audio_label}][outroa]amix=inputs=2:duration=first:dropout_transition=2[withoutroaudio]"
                )
                main_audio_label = "withoutroaudio"

        # Concatenate intro/outro clips (concat mode) around the main sequence.
        concat_video_labels = []
        concat_audio_labels = []

        if intro_path and intro_mode == "concat":
            intro_idx = next_input_index
            inputs.extend(["-i", intro_path])
            next_input_index += 1

            filter_parts.append(f"[{intro_idx}:v]{scale_filter},setsar=1,fps=30[cv{intro_idx}]")
            if intro_info.has_audio:
                filter_parts.append(f"[{intro_idx}:a]aresample=async=1[ca{intro_idx}]")
            else:
                intro_audio = "anullsrc=channel_layout=stereo:sample_rate=48000"
                if intro_info.duration > 0:
                    intro_audio += f",atrim=duration={intro_info.duration},asetpts=PTS-STARTPTS"
                filter_parts.append(f"{intro_audio}[ca{intro_idx}]")

            concat_video_labels.append(f"[cv{intro_idx}]")
            concat_audio_labels.append(f"[ca{intro_idx}]")

        concat_video_labels.append(f"[{main_video_label}]")
        concat_audio_labels.append(f"[{main_audio_label}]")

        if outro_path and outro_mode == "concat":
            outro_idx = next_input_index
            inputs.extend(["-i", outro_path])
            next_input_index += 1

            filter_parts.append(f"[{outro_idx}:v]{scale_filter},setsar=1,fps=30[cv{outro_idx}]")
            if outro_info.has_audio:
                filter_parts.append(f"[{outro_idx}:a]aresample=async=1[ca{outro_idx}]")
            else:
                outro_audio = "anullsrc=channel_layout=stereo:sample_rate=48000"
                if outro_info.duration > 0:
                    outro_audio += f",atrim=duration={outro_info.duration},asetpts=PTS-STARTPTS"
                filter_parts.append(f"{outro_audio}[ca{outro_idx}]")

            concat_video_labels.append(f"[cv{outro_idx}]")
            concat_audio_labels.append(f"[ca{outro_idx}]")

        if len(concat_video_labels) > 1:
            concat_v = "".join(concat_video_labels)
            concat_a = "".join(concat_audio_labels)
            filter_parts.append(f"{concat_v}concat=n={len(concat_video_labels)}:v=1:a=0[vtimeline]")
            filter_parts.append(f"{concat_a}concat=n={len(concat_audio_labels)}:v=0:a=1[atimeline]")
            timeline_video_label = "vtimeline"
            timeline_audio_label = "atimeline"
        else:
            timeline_video_label = main_video_label
            timeline_audio_label = main_audio_label

        final_video_label = timeline_video_label
        final_audio_label = timeline_audio_label

        # Apply subscribe overlay on the full timeline.
        if subscribe_path and appearances:
            subscribe_idx = next_input_index
            inputs.extend(["-i", subscribe_path])
            next_input_index += 1

            filter_parts.append(
                f"[{subscribe_idx}:v]format=rgba,{overlay_scale},trim=duration={subscribe_duration},setpts=PTS-STARTPTS[subbase]"
            )

            sub_inputs = []
            if len(appearances) > 1:
                sub_labels = "".join([f"[sub{i}]" for i in range(len(appearances))])
                filter_parts.append(f"[subbase]split={len(appearances)}{sub_labels}")
                sub_inputs = [f"sub{i}" for i in range(len(appearances))]
            else:
                sub_inputs = ["subbase"]

            current_label = timeline_video_label
            for i, t in enumerate(appearances):
                sub_label = sub_inputs[i] if len(sub_inputs) > 1 else sub_inputs[0]
                filter_parts.append(f"[{sub_label}]setpts=PTS+{t}/TB[subt{i}]")
                filter_parts.append(
                    f"[{current_label}][subt{i}]overlay=0:0:enable='between(t,{t},{t + subscribe_duration})':eof_action=pass[vsub{i}]"
                )
                current_label = f"vsub{i}"

            final_video_label = current_label

            if subscribe_info.has_audio:
                audio_filters = []
                audio_filters.append(
                    f"[{subscribe_idx}:a]atrim=duration={subscribe_duration},asetpts=PTS-STARTPTS[suba]"
                )

                suba_inputs = []
                if len(appearances) > 1:
                    suba_labels = "".join([f"[suba{i}]" for i in range(len(appearances))])
                    audio_filters.append(f"[suba]asplit={len(appearances)}{suba_labels}")
                    suba_inputs = [f"suba{i}" for i in range(len(appearances))]
                else:
                    suba_inputs = ["suba"]

                audio_inputs = []
                for i, t in enumerate(appearances):
                    delay_ms = int(t * 1000)
                    src = suba_inputs[i] if len(suba_inputs) > 1 else suba_inputs[0]
                    audio_filters.append(f"[{src}]adelay={delay_ms}|{delay_ms}[subad{i}]")
                    audio_inputs.append(f"[subad{i}]")

                if audio_inputs:
                    mix_inputs = f"[{timeline_audio_label}]" + "".join(audio_inputs)
                    audio_filters.append(
                        f"{mix_inputs}amix=inputs={len(audio_inputs) + 1}:duration=first:dropout_transition=2[asub]"
                    )
                    filter_parts.extend(audio_filters)
                    final_audio_label = "asub"

        filter_complex = ";".join(filter_parts)

        cmd = [FFMPEG_PATH, "-y"] + inputs
        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", f"[{final_video_label}]", "-map", f"[{final_audio_label}]"])

        encoder_args = self._get_encoder_args(encoder, preset_config)
        cmd.extend(encoder_args)
        audio_codec = self._get_audio_codec(preset_config)
        cmd.extend(["-c:a", audio_codec])
        if audio_codec != "copy" and preset_config.get("audio_bitrate"):
            cmd.extend(["-b:a", preset_config["audio_bitrate"]])

        cmd.append(output_path)

        self._run_ffmpeg(cmd, job, total_duration)

        return output_path


# Global instance
video_processor = VideoProcessor()
