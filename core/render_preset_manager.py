"""
Render Settings Presets Manager
Saves and loads render configuration presets
"""
import json
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import PROFILES_DIR

# Default presets directory
PRESETS_FILE = PROFILES_DIR / "render_presets.json"


class RenderPresetManager:
    """Manages render settings presets"""
    
    def __init__(self, presets_file: Path = PRESETS_FILE):
        self.presets_file = presets_file
        self.presets_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize with empty presets if file doesn't exist
        if not self.presets_file.exists():
            self._save_presets([])
    
    def _load_presets(self) -> list:
        """Load presets from file"""
        try:
            with open(self.presets_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_presets(self, presets: list):
        """Save presets to file"""
        with open(self.presets_file, 'w') as f:
            json.dump(presets, f, indent=2, default=str)
    
    def get_all_presets(self) -> list:
        """Get all render presets"""
        return self._load_presets()
    
    def get_preset(self, preset_id: str) -> Optional[dict]:
        """Get a specific preset by ID"""
        presets = self._load_presets()
        for preset in presets:
            if preset['id'] == preset_id:
                return preset
        return None
    
    def create_preset(self, name: str, settings: dict) -> dict:
        """Create a new render preset"""
        presets = self._load_presets()
        
        preset = {
            "id": str(uuid.uuid4())[:8].upper(),
            "name": name,
            "settings": settings,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        presets.append(preset)
        self._save_presets(presets)
        return preset
    
    def update_preset(self, preset_id: str, data: dict) -> Optional[dict]:
        """Update an existing preset"""
        presets = self._load_presets()
        
        for i, preset in enumerate(presets):
            if preset['id'] == preset_id:
                if 'name' in data:
                    preset['name'] = data['name']
                if 'settings' in data:
                    preset['settings'] = data['settings']
                preset['updated_at'] = datetime.now().isoformat()
                presets[i] = preset
                self._save_presets(presets)
                return preset
        
        return None
    
    def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset"""
        presets = self._load_presets()
        
        for i, preset in enumerate(presets):
            if preset['id'] == preset_id:
                presets.pop(i)
                self._save_presets(presets)
                return True
        
        return False
    
    def get_last_used(self) -> Optional[dict]:
        """Get the last used render settings (if saved)"""
        try:
            last_used_file = self.presets_file.parent / "last_render_settings.json"
            if last_used_file.exists():
                with open(last_used_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return None
    
    def save_last_used(self, settings: dict):
        """Save the last used render settings"""
        last_used_file = self.presets_file.parent / "last_render_settings.json"
        with open(last_used_file, 'w') as f:
            json.dump(settings, f, indent=2)


# Global instance
render_preset_manager = RenderPresetManager()
