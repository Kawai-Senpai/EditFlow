"""
Thumbnail Settings Presets Manager
Stores full thumbnail generator settings presets.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import THUMBNAIL_SETTINGS_PRESETS_FILE


class ThumbnailSettingsManager:
    """Manages thumbnail settings presets."""

    def __init__(self, presets_file: Path = THUMBNAIL_SETTINGS_PRESETS_FILE):
        self.presets_file = presets_file
        self.presets_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.presets_file.exists():
            self._save_presets([])

    def _load_presets(self) -> list:
        try:
            with open(self.presets_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_presets(self, presets: list):
        with open(self.presets_file, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, default=str)

    def get_all_presets(self) -> list:
        return self._load_presets()

    def get_preset(self, preset_id: str) -> Optional[dict]:
        presets = self._load_presets()
        for preset in presets:
            if preset.get("id") == preset_id:
                return preset
        return None

    def create_preset(self, name: str, settings: dict) -> dict:
        presets = self._load_presets()
        preset = {
            "id": str(uuid.uuid4())[:8].upper(),
            "name": name,
            "settings": settings,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        presets.append(preset)
        self._save_presets(presets)
        return preset

    def update_preset(self, preset_id: str, data: dict) -> Optional[dict]:
        presets = self._load_presets()
        for i, preset in enumerate(presets):
            if preset.get("id") == preset_id:
                if "name" in data:
                    preset["name"] = data["name"]
                if "settings" in data:
                    preset["settings"] = data["settings"]
                preset["updated_at"] = datetime.now().isoformat()
                presets[i] = preset
                self._save_presets(presets)
                return preset
        return None

    def delete_preset(self, preset_id: str) -> bool:
        presets = self._load_presets()
        for i, preset in enumerate(presets):
            if preset.get("id") == preset_id:
                presets.pop(i)
                self._save_presets(presets)
                return True
        return False


thumbnail_settings_manager = ThumbnailSettingsManager()
