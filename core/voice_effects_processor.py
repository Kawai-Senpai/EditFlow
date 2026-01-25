"""
Voice effects processor - handles voice audio processing with FFmpeg filters
Provides noise reduction, EQ, compression, leveling, de-esser, limiter, and voice deepening
"""
import json
import uuid
import subprocess
import math
from datetime import datetime
from pathlib import Path
from typing import Optional
from .config import PROFILES_DIR, FFMPEG_PATH, TEMP_DIR


# Default voice effects presets
DEFAULT_VOICE_PRESETS = [
    {
        "id": "default_clean",
        "name": "Clean Voice",
        "description": "Subtle enhancement for clean recordings",
        "is_default": True,
        "highpass_hz": 80,
        "lowpass_hz": 16000,
        "noise_reduction": {
            "enabled": True,
            "type": "afftdn",
            "nr": 12,
            "nf": -50,
            "track_noise": True
        },
        "eq_bands": [
            {"f_hz": 120, "gain_db": -2.0, "q": 1.0},
            {"f_hz": 250, "gain_db": -1.5, "q": 1.0},
            {"f_hz": 3500, "gain_db": 3.0, "q": 1.2},
            {"f_hz": 9000, "gain_db": 2.0, "q": 1.0}
        ],
        "deesser": {"enabled": True, "i": 0.25, "m": 0.4, "f": 0.6},
        "compressor": {
            "enabled": True,
            "threshold": 0.10,
            "ratio": 3.0,
            "attack_ms": 20,
            "release_ms": 250,
            "makeup": 1.5,
            "knee": 2.8
        },
        "leveling": {
            "enabled": True,
            "type": "dynaudnorm",
            "framelen_ms": 500,
            "gausssize": 31,
            "peak": 0.95,
            "compress": 5.0
        },
        "limiter": {"enabled": True, "limit": 0.98, "attack": 5, "release": 50},
        "deepening": {"enabled": False, "semitones": -2.0},
        "loudnorm": {"enabled": False, "I": -16, "LRA": 11, "TP": -1.5}
    },
    {
        "id": "default_podcast",
        "name": "Podcast Pro",
        "description": "Warm, broadcast-ready voice with moderate compression",
        "is_default": True,
        "highpass_hz": 80,
        "lowpass_hz": 15000,
        "noise_reduction": {
            "enabled": True,
            "type": "afftdn",
            "nr": 15,
            "nf": -45,
            "track_noise": True
        },
        "eq_bands": [
            {"f_hz": 100, "gain_db": -3.0, "q": 0.8},
            {"f_hz": 200, "gain_db": 2.0, "q": 1.0},
            {"f_hz": 2500, "gain_db": 2.5, "q": 1.5},
            {"f_hz": 5000, "gain_db": 1.5, "q": 1.0},
            {"f_hz": 10000, "gain_db": 1.0, "q": 1.0}
        ],
        "deesser": {"enabled": True, "i": 0.3, "m": 0.5, "f": 0.65},
        "compressor": {
            "enabled": True,
            "threshold": 0.08,
            "ratio": 4.0,
            "attack_ms": 15,
            "release_ms": 200,
            "makeup": 2.0,
            "knee": 3.0
        },
        "leveling": {
            "enabled": True,
            "type": "dynaudnorm",
            "framelen_ms": 400,
            "gausssize": 31,
            "peak": 0.95,
            "compress": 6.0
        },
        "limiter": {"enabled": True, "limit": 0.95, "attack": 5, "release": 50},
        "deepening": {"enabled": False, "semitones": -1.5},
        "loudnorm": {"enabled": True, "I": -16, "LRA": 11, "TP": -1.5}
    },
    {
        "id": "default_gaming",
        "name": "Gaming Voice",
        "description": "Punchy, bright voice for gaming commentary",
        "is_default": True,
        "highpass_hz": 100,
        "lowpass_hz": 14000,
        "noise_reduction": {
            "enabled": True,
            "type": "afftdn",
            "nr": 18,
            "nf": -40,
            "track_noise": True
        },
        "eq_bands": [
            {"f_hz": 150, "gain_db": -2.0, "q": 1.0},
            {"f_hz": 300, "gain_db": -1.0, "q": 1.0},
            {"f_hz": 3000, "gain_db": 4.0, "q": 1.2},
            {"f_hz": 7000, "gain_db": 2.5, "q": 1.0}
        ],
        "deesser": {"enabled": True, "i": 0.35, "m": 0.45, "f": 0.6},
        "compressor": {
            "enabled": True,
            "threshold": 0.12,
            "ratio": 5.0,
            "attack_ms": 10,
            "release_ms": 150,
            "makeup": 1.8,
            "knee": 2.5
        },
        "leveling": {
            "enabled": True,
            "type": "dynaudnorm",
            "framelen_ms": 300,
            "gausssize": 21,
            "peak": 0.95,
            "compress": 7.0
        },
        "limiter": {"enabled": True, "limit": 0.96, "attack": 3, "release": 40},
        "deepening": {"enabled": False, "semitones": -1.0},
        "loudnorm": {"enabled": False, "I": -16, "LRA": 11, "TP": -1.5}
    },
    {
        "id": "default_deep",
        "name": "Deep Voice",
        "description": "Voice deepening with subtle enhancement",
        "is_default": True,
        "highpass_hz": 60,
        "lowpass_hz": 14000,
        "noise_reduction": {
            "enabled": True,
            "type": "afftdn",
            "nr": 10,
            "nf": -50,
            "track_noise": True
        },
        "eq_bands": [
            {"f_hz": 100, "gain_db": 2.0, "q": 0.8},
            {"f_hz": 200, "gain_db": 1.5, "q": 1.0},
            {"f_hz": 3000, "gain_db": 2.0, "q": 1.2},
            {"f_hz": 8000, "gain_db": 1.0, "q": 1.0}
        ],
        "deesser": {"enabled": True, "i": 0.2, "m": 0.35, "f": 0.55},
        "compressor": {
            "enabled": True,
            "threshold": 0.12,
            "ratio": 3.5,
            "attack_ms": 25,
            "release_ms": 300,
            "makeup": 1.5,
            "knee": 3.0
        },
        "leveling": {
            "enabled": True,
            "type": "dynaudnorm",
            "framelen_ms": 500,
            "gausssize": 31,
            "peak": 0.90,
            "compress": 4.0
        },
        "limiter": {"enabled": True, "limit": 0.95, "attack": 5, "release": 60},
        "deepening": {"enabled": True, "semitones": -2.5},
        "loudnorm": {"enabled": False, "I": -16, "LRA": 11, "TP": -1.5}
    },
    {
        "id": "default_minimal",
        "name": "Minimal Processing",
        "description": "Just noise reduction and limiting - for clean sources",
        "is_default": True,
        "highpass_hz": 60,
        "lowpass_hz": 18000,
        "noise_reduction": {
            "enabled": True,
            "type": "afftdn",
            "nr": 8,
            "nf": -55,
            "track_noise": True
        },
        "eq_bands": [],
        "deesser": {"enabled": False, "i": 0.25, "m": 0.4, "f": 0.6},
        "compressor": {
            "enabled": False,
            "threshold": 0.15,
            "ratio": 2.0,
            "attack_ms": 30,
            "release_ms": 300,
            "makeup": 1.2,
            "knee": 3.0
        },
        "leveling": {
            "enabled": False,
            "type": "dynaudnorm",
            "framelen_ms": 500,
            "gausssize": 31,
            "peak": 0.95,
            "compress": 5.0
        },
        "limiter": {"enabled": True, "limit": 0.98, "attack": 5, "release": 50},
        "deepening": {"enabled": False, "semitones": -2.0},
        "loudnorm": {"enabled": False, "I": -16, "LRA": 11, "TP": -1.5}
    }
]


def _semitones_to_ratio(semitones: float) -> float:
    """Convert semitones to pitch ratio for rubberband filter"""
    return 2 ** (semitones / 12.0)


class VoiceEffectsProcessor:
    """Handles voice effects processing and preset management"""
    
    def __init__(self):
        self.presets_file = PROFILES_DIR / "voice_effects_presets.json"
        self._ensure_presets_file()
    
    def _ensure_presets_file(self):
        """Create presets file with defaults if it doesn't exist"""
        if not self.presets_file.exists():
            self._save_presets(DEFAULT_VOICE_PRESETS)
    
    def _load_presets(self) -> list:
        """Load all presets from JSON file"""
        try:
            with open(self.presets_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return DEFAULT_VOICE_PRESETS.copy()
    
    def _save_presets(self, presets: list):
        """Save presets to JSON file"""
        with open(self.presets_file, 'w', encoding='utf-8') as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
    
    def get_all_presets(self) -> list:
        """Get all voice effects presets"""
        return self._load_presets()
    
    def get_preset(self, preset_id: str) -> Optional[dict]:
        """Get a single preset by ID"""
        presets = self._load_presets()
        for preset in presets:
            if preset.get("id") == preset_id:
                return preset
        return None
    
    def create_preset(self, name: str, settings: dict, description: str = "") -> dict:
        """Create a new voice effects preset"""
        presets = self._load_presets()
        
        # Start with a copy of default clean preset
        default = DEFAULT_VOICE_PRESETS[0].copy()
        
        new_preset = {
            **default,
            **settings,
            "id": str(uuid.uuid4())[:8].upper(),
            "name": name,
            "description": description,
            "is_default": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        presets.append(new_preset)
        self._save_presets(presets)
        
        return new_preset
    
    def update_preset(self, preset_id: str, updates: dict) -> Optional[dict]:
        """Update a preset"""
        presets = self._load_presets()
        
        for i, preset in enumerate(presets):
            if preset.get("id") == preset_id:
                # Don't allow modifying default presets' identity
                if preset.get("is_default"):
                    # For defaults, only allow updating effect parameters
                    protected_keys = {"id", "is_default", "created_at"}
                    updates = {k: v for k, v in updates.items() if k not in protected_keys}
                
                presets[i].update(updates)
                presets[i]["updated_at"] = datetime.now().isoformat()
                self._save_presets(presets)
                return presets[i]
        
        return None
    
    def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset (cannot delete default presets)"""
        presets = self._load_presets()
        
        for i, preset in enumerate(presets):
            if preset.get("id") == preset_id:
                if preset.get("is_default"):
                    return False
                presets.pop(i)
                self._save_presets(presets)
                return True
        
        return False
    
    def build_filter_chain(self, preset: dict) -> str:
        """
        Build FFmpeg audio filter chain from preset settings.
        
        Args:
            preset: Voice effects preset dict
            
        Returns:
            FFmpeg filter chain string
        """
        filters = []
        
        # 0) Voice deepening (pitch shift) - must be first
        deep = preset.get("deepening", {})
        if deep.get("enabled", False):
            semitones = float(deep.get("semitones", -2.0))
            ratio = _semitones_to_ratio(semitones)
            # rubberband with formant preservation for natural sound
            filters.append(f"rubberband=pitch={ratio:.6f}:formant=preserved")
        
        # 1) Highpass filter (remove rumble)
        hp = preset.get("highpass_hz", 80)
        if hp > 0:
            filters.append(f"highpass=f={hp}")
        
        # 2) Lowpass filter (remove hiss)
        lp = preset.get("lowpass_hz", 16000)
        if lp > 0 and lp < 20000:
            filters.append(f"lowpass=f={lp}")
        
        # 3) Noise reduction
        nr = preset.get("noise_reduction", {})
        if nr.get("enabled", False):
            nr_type = nr.get("type", "afftdn")
            if nr_type == "afftdn":
                # afftdn - good general-purpose denoise
                nr_val = nr.get("nr", 12)
                nf_val = nr.get("nf", -50)
                tn_val = 1 if nr.get("track_noise", True) else 0
                filters.append(f"afftdn=nr={nr_val}:nf={nf_val}:tn={tn_val}")
            elif nr_type == "arnndn":
                # arnndn - ML-based, requires model file
                model_path = nr.get("model_path", "")
                if model_path:
                    mix_val = nr.get("mix", 1.0)
                    filters.append(f"arnndn=model={model_path}:mix={mix_val}")
        
        # 4) EQ bands
        eq_bands = preset.get("eq_bands", [])
        for band in eq_bands:
            f = band.get("f_hz", 1000)
            g = band.get("gain_db", 0)
            q = band.get("q", 1.0)
            if g != 0:  # Skip bands with no gain
                filters.append(f"equalizer=f={f}:t=q:w={q}:g={g}")
        
        # 5) De-esser
        ds = preset.get("deesser", {})
        if ds.get("enabled", False):
            i_val = ds.get("i", 0.25)
            m_val = ds.get("m", 0.4)
            f_val = ds.get("f", 0.6)
            filters.append(f"deesser=i={i_val}:m={m_val}:f={f_val}:s=o")
        
        # 6) Compressor
        comp = preset.get("compressor", {})
        if comp.get("enabled", False):
            threshold = comp.get("threshold", 0.10)
            ratio = comp.get("ratio", 3.0)
            attack = comp.get("attack_ms", 20)
            release = comp.get("release_ms", 250)
            makeup = comp.get("makeup", 1.5)
            knee = comp.get("knee", 2.8)
            filters.append(
                f"acompressor=threshold={threshold}:ratio={ratio}:"
                f"attack={attack}:release={release}:makeup={makeup}:knee={knee}"
            )
        
        # 7) Leveling (dynamic normalization)
        lev = preset.get("leveling", {})
        if lev.get("enabled", False):
            lev_type = lev.get("type", "dynaudnorm")
            if lev_type == "dynaudnorm":
                framelen = lev.get("framelen_ms", 500)
                gausssize = lev.get("gausssize", 31)
                peak = lev.get("peak", 0.95)
                compress = lev.get("compress", 5.0)
                filters.append(
                    f"dynaudnorm=f={framelen}:g={gausssize}:p={peak}:s={compress}"
                )
            elif lev_type == "speechnorm":
                peak = lev.get("peak", 0.95)
                expansion = lev.get("expansion", 2.0)
                compression = lev.get("compression", 6.0)
                threshold = lev.get("threshold", 0.02)
                filters.append(
                    f"speechnorm=p={peak}:e={expansion}:c={compression}:t={threshold}"
                )
        
        # 8) Limiter (prevent clipping)
        lim = preset.get("limiter", {})
        if lim.get("enabled", False):
            limit = lim.get("limit", 0.98)
            attack = lim.get("attack", 5)
            release = lim.get("release", 50)
            filters.append(f"alimiter=limit={limit}:attack={attack}:release={release}")
        
        # 9) Loudness normalization (broadcast standard)
        ln = preset.get("loudnorm", {})
        if ln.get("enabled", False):
            I_val = ln.get("I", -16)
            LRA_val = ln.get("LRA", 11)
            TP_val = ln.get("TP", -1.5)
            filters.append(f"loudnorm=I={I_val}:LRA={LRA_val}:TP={TP_val}")
        
        return ",".join(filters) if filters else ""
    
    def generate_preview(self, video_path: str, preset: dict, 
                        audio_track_index: int = 0,
                        start_time: float = 0, 
                        duration: float = 15) -> Optional[str]:
        """
        Generate a preview audio clip with voice effects applied.
        
        Uses the same audio processing pipeline as final render:
        1. Apply voice effects
        2. Normalize (dynaudnorm)
        3. Apply limiter
        
        Args:
            video_path: Path to source video/audio file
            preset: Voice effects preset dict
            audio_track_index: Which audio track to process
            start_time: Start time in seconds
            duration: Duration in seconds
            
        Returns:
            Path to preview audio file or None on failure
        """
        try:
            import hashlib
            
            # Generate unique output path
            preset_sig = hashlib.md5(json.dumps(preset, sort_keys=True).encode()).hexdigest()[:8]
            path_sig = hashlib.md5(f"{video_path}|{start_time}|{audio_track_index}".encode()).hexdigest()[:8]
            output_path = TEMP_DIR / f"voice_preview_{path_sig}_{preset_sig}.m4a"
            
            # Build filter chain
            filter_chain = self.build_filter_chain(preset)
            
            if not filter_chain:
                filter_chain = "anull"  # Pass-through if no effects
            
            # Add normalization and limiter to match final render pipeline
            # effects → normalize → limiter (same as _build_audio_mix_filter)
            full_chain = f"{filter_chain},dynaudnorm=f=150:g=15:p=0.9:m=10,alimiter=limit=0.98:attack=5:release=50"
            
            cmd = [
                FFMPEG_PATH, "-y",
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(duration),
                "-map", f"0:a:{audio_track_index}",
                "-af", full_chain,
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and output_path.exists():
                return str(output_path)
            else:
                print(f"Voice effects preview failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error generating voice effects preview: {e}")
            return None
    
    def generate_preview_multi_track(self, video_path: str, preset: dict, 
                                      voice_track_indices: list[int],
                                      start_time: float = 0, 
                                      duration: float = 15) -> Optional[str]:
        """
        Generate an audio preview with voice effects applied to multiple voice tracks mixed together.
        
        Uses the same audio processing pipeline as final render:
        1. Apply voice effects
        2. Normalize each track (dynaudnorm)
        3. Mix together
        4. Apply limiter
        
        Args:
            video_path: Path to the video file
            preset: Voice effects preset dict
            voice_track_indices: List of audio track indices to process and mix
            start_time: Start time in seconds
            duration: Duration in seconds
            
        Returns:
            Path to preview audio file or None on failure
        """
        try:
            import hashlib
            
            if not voice_track_indices:
                return None
            
            # Generate unique output path
            preset_sig = hashlib.md5(json.dumps(preset, sort_keys=True).encode()).hexdigest()[:8]
            tracks_sig = "-".join(map(str, voice_track_indices))
            path_sig = hashlib.md5(f"{video_path}|{start_time}|{tracks_sig}".encode()).hexdigest()[:8]
            output_path = TEMP_DIR / f"voice_preview_multi_{path_sig}_{preset_sig}.m4a"
            
            # Build filter chain (voice effects)
            filter_chain = self.build_filter_chain(preset)
            if not filter_chain:
                filter_chain = "anull"
            
            # Build complex filter for multiple tracks
            # Match final render pipeline: effects → normalize → mix → limiter
            filter_parts = []
            mix_inputs = []
            
            for i, track_idx in enumerate(voice_track_indices):
                label = f"v{i}"
                # Apply voice effects THEN normalize (same as final render)
                # dynaudnorm settings match _build_audio_mix_filter
                track_filter = f"[0:a:{track_idx}]{filter_chain},dynaudnorm=f=150:g=15:p=0.9:m=10[{label}]"
                filter_parts.append(track_filter)
                mix_inputs.append(f"[{label}]")
            
            # Mix all processed voice tracks with limiter (matches final render)
            if len(voice_track_indices) > 1:
                mix_label = "vmix"
                filter_parts.append(f"{''.join(mix_inputs)}amix=inputs={len(voice_track_indices)}:duration=longest:normalize=0,alimiter=limit=0.98:attack=5:release=50[{mix_label}]")
                final_label = f"[{mix_label}]"
            else:
                # Single track still gets limiter
                orig_label = mix_inputs[0].strip('[]')
                new_label = "vlim"
                filter_parts.append(f"[{orig_label}]alimiter=limit=0.98:attack=5:release=50[{new_label}]")
                final_label = f"[{new_label}]"
            
            filter_complex = ";".join(filter_parts)
            
            cmd = [
                FFMPEG_PATH, "-y",
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(duration),
                "-filter_complex", filter_complex,
                "-map", final_label,
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and output_path.exists():
                return str(output_path)
            else:
                print(f"Voice effects multi-track preview failed: {result.stderr}")
                # Fallback to single track
                if voice_track_indices:
                    return self.generate_preview(video_path, preset, voice_track_indices[0], start_time, duration)
                return None
                
        except Exception as e:
            print(f"Error generating voice effects multi-track preview: {e}")
            return None
    
    def get_filter_for_track(self, preset_id: str) -> str:
        """
        Get the FFmpeg filter chain for a preset ID.
        
        Args:
            preset_id: ID of the voice effects preset
            
        Returns:
            FFmpeg filter chain string, or empty string if not found
        """
        preset = self.get_preset(preset_id)
        if preset:
            return self.build_filter_chain(preset)
        return ""
    
    def reset_defaults(self):
        """Reset all presets to defaults (removes custom presets)"""
        self._save_presets(DEFAULT_VOICE_PRESETS.copy())


# Global instance
voice_effects_processor = VoiceEffectsProcessor()
