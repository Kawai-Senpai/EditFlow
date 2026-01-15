"""
Profile management - handles channel profiles with intro/outro/subscribe graphics
Stores only file path references, NOT copies of files (files can be very large)
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import PROFILES_DIR


class ProfileManager:
    """Manages video profiles for different channels"""
    
    def __init__(self):
        self.profiles_file = PROFILES_DIR / "profiles.json"
        self._ensure_profiles_file()
    
    def _ensure_profiles_file(self):
        """Create profiles file if it doesn't exist"""
        if not self.profiles_file.exists():
            self._save_profiles([])
    
    def _load_profiles(self) -> list:
        """Load all profiles from JSON file"""
        try:
            with open(self.profiles_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_profiles(self, profiles: list):
        """Save profiles to JSON file"""
        with open(self.profiles_file, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2, default=str)
    
    def get_all_profiles(self) -> list:
        """Get all profiles"""
        return self._load_profiles()
    
    def get_profile(self, profile_id: str) -> Optional[dict]:
        """Get a single profile by ID"""
        profiles = self._load_profiles()
        for profile in profiles:
            if profile.get('id') == profile_id:
                return profile
        return None
    
    def create_profile(self, name: str) -> dict:
        """Create a new profile"""
        profiles = self._load_profiles()
        
        new_profile = {
            "id": str(uuid.uuid4())[:8].upper(),
            "name": name,
            "intro": None,
            "outro": None,
            "subscribe_graphics": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        profiles.append(new_profile)
        self._save_profiles(profiles)
        
        return new_profile
    
    def update_profile(self, profile_id: str, updates: dict) -> Optional[dict]:
        """Update a profile"""
        profiles = self._load_profiles()
        
        for i, profile in enumerate(profiles):
            if profile.get('id') == profile_id:
                # Update fields
                for key, value in updates.items():
                    if key not in ['id', 'created_at']:
                        profiles[i][key] = value
                
                profiles[i]['updated_at'] = datetime.now().isoformat()
                self._save_profiles(profiles)
                return profiles[i]
        
        return None
    
    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile"""
        profiles = self._load_profiles()
        
        for i, profile in enumerate(profiles):
            if profile.get('id') == profile_id:
                # Remove from list (no files to delete since we only store references)
                profiles.pop(i)
                self._save_profiles(profiles)
                return True
        
        return False
    
    def set_intro(self, profile_id: str, file_path: str, overlap_seconds: float = 0, 
                  has_audio: bool = True, full_overlap: bool = False) -> Optional[dict]:
        """Set intro for a profile - stores file reference only, no copy"""
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        
        # Verify file exists
        src_path = Path(file_path)
        if not src_path.exists():
            raise FileNotFoundError(f"Intro file not found: {file_path}")
        
        return self.update_profile(profile_id, {
            "intro": {
                "file_path": str(src_path.absolute()),  # Store absolute path reference
                "original_name": src_path.name,
                "overlap_seconds": overlap_seconds,
                "has_audio": has_audio,
                "full_overlap": full_overlap
            }
        })
    
    def set_outro(self, profile_id: str, file_path: str, overlap_seconds: float = 0, 
                  has_audio: bool = True, full_overlap: bool = False) -> Optional[dict]:
        """Set outro for a profile - stores file reference only, no copy"""
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        
        # Verify file exists
        src_path = Path(file_path)
        if not src_path.exists():
            raise FileNotFoundError(f"Outro file not found: {file_path}")
        
        return self.update_profile(profile_id, {
            "outro": {
                "file_path": str(src_path.absolute()),  # Store absolute path reference
                "original_name": src_path.name,
                "overlap_seconds": overlap_seconds,
                "has_audio": has_audio,
                "full_overlap": full_overlap
            }
        })
    
    def set_subscribe_graphics(self, profile_id: str, file_path: str, interval_seconds: float = 300, 
                                duration_seconds: float = 8, has_audio: bool = True,
                                use_full_duration: bool = True) -> Optional[dict]:
        """Set subscribe graphics for a profile - stores file reference only, no copy"""
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        
        # Verify file exists
        src_path = Path(file_path)
        if not src_path.exists():
            raise FileNotFoundError(f"Subscribe graphics file not found: {file_path}")
        
        return self.update_profile(profile_id, {
            "subscribe_graphics": {
                "file_path": str(src_path.absolute()),  # Store absolute path reference
                "original_name": src_path.name,
                "interval_seconds": interval_seconds,
                "duration_seconds": duration_seconds,
                "has_audio": has_audio,
                "use_full_duration": use_full_duration
            }
        })
    
    def remove_intro(self, profile_id: str) -> Optional[dict]:
        """Remove intro from a profile (just removes reference, not the actual file)"""
        profile = self.get_profile(profile_id)
        if not profile or not profile.get('intro'):
            return None
        
        return self.update_profile(profile_id, {"intro": None})
    
    def remove_outro(self, profile_id: str) -> Optional[dict]:
        """Remove outro from a profile (just removes reference, not the actual file)"""
        profile = self.get_profile(profile_id)
        if not profile or not profile.get('outro'):
            return None
        
        return self.update_profile(profile_id, {"outro": None})
    
    def remove_subscribe_graphics(self, profile_id: str) -> Optional[dict]:
        """Remove subscribe graphics from a profile (just removes reference, not the actual file)"""
        profile = self.get_profile(profile_id)
        if not profile or not profile.get('subscribe_graphics'):
            return None
        
        return self.update_profile(profile_id, {"subscribe_graphics": None})
    
    def update_asset_settings(self, profile_id: str, asset_type: str, settings: dict) -> Optional[dict]:
        """Update settings for an asset without changing the file"""
        profile = self.get_profile(profile_id)
        if not profile or not profile.get(asset_type):
            return None
        
        # Merge new settings with existing asset data
        asset_data = profile[asset_type].copy()
        asset_data.update(settings)
        
        return self.update_profile(profile_id, {asset_type: asset_data})


# Global instance
profile_manager = ProfileManager()
