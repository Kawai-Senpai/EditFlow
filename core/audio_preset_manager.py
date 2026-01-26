"""
Audio preset manager - handles audio mixing presets with track levels, types, and voice effects
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from .config import PROFILES_DIR


# Track types for auto-leveling
# Auto-level values are relative to voice (1.0 = same level as voice after normalization)
# These are used when no LUFS analysis is available
TRACK_TYPES = {
    "voice": {"name": "Voice/Commentary", "auto_level": 1.0},     # Full volume - primary content
    "game_audio": {"name": "Game Audio", "auto_level": 0.25},    # 12 dB reduction - background, shouldn't compete
    "music": {"name": "Background Music", "auto_level": 0.20},   # 14 dB reduction - subtle ambience
    "sfx": {"name": "Sound Effects", "auto_level": 0.40},        # 8 dB reduction - occasional, not competing
    "other": {"name": "Other", "auto_level": 0.40}               # Default - treat like sfx
}


# Default presets included with the application
DEFAULT_AUDIO_PRESETS = [
    {
        "id": "default_gaming",
        "name": "Gaming Setup",
        "description": "Optimized for gaming with voice commentary",
        "is_default": True,
        "tracks": {
            "Track 1": {"volume": 1.0, "mute": False, "solo": False, "trackType": "voice"},
            "Track 2": {"volume": 0.6, "mute": False, "solo": False, "trackType": "game_audio"},
            "Track 3": {"volume": 0.3, "mute": False, "solo": False, "trackType": "music"},
        },
        "voiceEffects": {"enabled": False, "presetId": None}
    },
    {
        "id": "default_podcast",
        "name": "Podcast",
        "description": "Voice-focused with subtle background music",
        "is_default": True,
        "tracks": {
            "Track 1": {"volume": 1.0, "mute": False, "solo": False, "trackType": "voice"},
            "Track 2": {"volume": 0.25, "mute": False, "solo": False, "trackType": "music"},
        },
        "voiceEffects": {"enabled": True, "presetId": "default_podcast_voice"}
    },
    {
        "id": "default_music_video",
        "name": "Music Video",
        "description": "Music-focused with optional voice",
        "is_default": True,
        "tracks": {
            "Track 1": {"volume": 0.5, "mute": False, "solo": False, "trackType": "voice"},
            "Track 2": {"volume": 1.0, "mute": False, "solo": False, "trackType": "music"},
        },
        "voiceEffects": {"enabled": False, "presetId": None}
    },
    {
        "id": "default_balanced",
        "name": "Balanced Mix",
        "description": "Equal emphasis on all tracks",
        "is_default": True,
        "tracks": {
            "Track 1": {"volume": 0.8, "mute": False, "solo": False, "trackType": "voice"},
            "Track 2": {"volume": 0.7, "mute": False, "solo": False, "trackType": "game_audio"},
            "Track 3": {"volume": 0.5, "mute": False, "solo": False, "trackType": "music"},
        },
        "voiceEffects": {"enabled": False, "presetId": None}
    }
]


class AudioPresetManager:
    """Manages audio mixing presets for different recording setups"""
    
    def __init__(self):
        self.presets_file = PROFILES_DIR / "audio_presets.json"
        self._ensure_presets_file()
    
    def _ensure_presets_file(self):
        """Create presets file with defaults if it doesn't exist"""
        if not self.presets_file.exists():
            self._save_presets(DEFAULT_AUDIO_PRESETS)
    
    def _load_presets(self) -> list:
        """Load all presets from JSON file"""
        try:
            with open(self.presets_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return DEFAULT_AUDIO_PRESETS.copy()
    
    def _save_presets(self, presets: list):
        """Save presets to JSON file"""
        with open(self.presets_file, 'w', encoding='utf-8') as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
    
    def get_all_presets(self) -> list:
        """Get all audio presets"""
        return self._load_presets()
    
    def get_preset(self, preset_id: str) -> Optional[dict]:
        """Get a single preset by ID"""
        presets = self._load_presets()
        for preset in presets:
            if preset.get("id") == preset_id:
                return preset
        return None
    
    def create_preset(self, name: str, tracks: dict, description: str = "", 
                      voice_effects: dict = None) -> dict:
        """Create a new audio preset"""
        presets = self._load_presets()
        
        new_preset = {
            "id": str(uuid.uuid4())[:8].upper(),
            "name": name,
            "description": description,
            "is_default": False,
            "tracks": tracks,
            "voiceEffects": voice_effects or {"enabled": False, "presetId": None},
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
                # Don't allow modifying default presets' core identity
                if preset.get("is_default"):
                    # Only allow updating tracks and voiceEffects for defaults
                    allowed_keys = {"tracks", "voiceEffects"}
                    updates = {k: v for k, v in updates.items() if k in allowed_keys}
                
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
                    return False  # Cannot delete default presets
                presets.pop(i)
                self._save_presets(presets)
                return True
        
        return False
    
    def get_track_types(self) -> dict:
        """Get available track types for tagging"""
        return TRACK_TYPES
    
    def calculate_auto_levels(self, track_types: dict) -> dict:
        """
        Calculate auto-leveled volume settings based on track types.
        This is a fallback when no audio analysis is provided.
        
        Args:
            track_types: Dict mapping track name to track type string
            
        Returns:
            Dict mapping track name to recommended volume (0.0 - 1.0)
        """
        result = {}
        for track_name, track_type in track_types.items():
            type_info = TRACK_TYPES.get(track_type, TRACK_TYPES["other"])
            result[track_name] = type_info["auto_level"]
        return result
    
    def calculate_auto_levels_from_analysis(self, track_analysis: list, track_types: dict) -> dict:
        """
        Calculate auto-leveled volume settings based on actual LUFS analysis and track types.
        
        Current approach:
        - Use type-based relative levels (voice/game/music/sfx)
        - Let runtime leveling (dynaudnorm) handle raising low parts smoothly
        - Avoid aggressive per-track gain that can cause clipping
        
        Args:
            track_analysis: List of dicts with {track_name, track_index, loudness_lufs, peak_db}
            track_types: Dict mapping track name to track type string
            
        Returns:
            Dict mapping track name to recommended volume (0.0 - 2.0)
        """
        if not track_analysis:
            # No analysis available, use type-based fallback
            return self.calculate_auto_levels(track_types)

        # Reference level to normalize all tracks to (before type-based adjustment)
        REFERENCE_LUFS = -16.0

        result = {}

        for track_info in track_analysis:
            track_name = track_info.get("track_name", f"Track {track_info.get('track_index', 0) + 1}")
            current_lufs = track_info.get("loudness_lufs")

            # Skip tracks with no valid LUFS reading
            if current_lufs is None or current_lufs < -70:
                # Silent or very quiet track - use type-based level only
                track_type = track_types.get(track_name, "other")
                type_info = TRACK_TYPES.get(track_type, TRACK_TYPES["other"])
                result[track_name] = type_info["auto_level"]
                continue

            # Step 1: Calculate gain needed to reach reference level
            gain_db = REFERENCE_LUFS - current_lufs

            # Convert dB to linear gain
            normalization_gain = 10 ** (gain_db / 20.0)

            # Step 2: Get type-based relative reduction
            track_type = track_types.get(track_name, "other")
            type_info = TRACK_TYPES.get(track_type, TRACK_TYPES["other"])
            type_reduction = type_info["auto_level"]

            # Step 3: Combine normalization gain with type reduction
            final_volume = normalization_gain * type_reduction

            # Clamp to reasonable range (0.0 - 2.0)
            final_volume = max(0.0, min(2.0, final_volume))

            result[track_name] = round(final_volume, 3)

        # Handle any tracks in track_types but not in analysis
        for track_name in track_types:
            if track_name not in result:
                track_type = track_types.get(track_name, "other")
                type_info = TRACK_TYPES.get(track_type, TRACK_TYPES["other"])
                result[track_name] = type_info["auto_level"]

        return result
    
    def reset_defaults(self):
        """Reset all presets to defaults (removes custom presets)"""
        self._save_presets(DEFAULT_AUDIO_PRESETS.copy())


# Global instance
audio_preset_manager = AudioPresetManager()
