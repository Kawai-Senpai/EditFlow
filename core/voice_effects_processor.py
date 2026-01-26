"""
Voice effects processor - voice audio processing with FFmpeg filters.

Goals:
- Make a bad mic sound cleaner and more "VO ready" without going cartoony.
- Keep everything deterministic and scriptable (no DAW plugins needed).

Reality check:
- This can fix noise, harshness, boom, and level swings.
- It cannot undo clipping/distortion, heavy room reverb, or a mic that is simply unusable.
"""

import json
import uuid
import subprocess
import math
import copy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .config import PROFILES_DIR, FFMPEG_PATH, TEMP_DIR


# Default voice effects presets
# Notes:
# - thresholds in acompressor/agate are linear sample magnitudes (0..1), not dB.
# - the limiter is intentionally set with level=disabled (see build_filter_chain).
DEFAULT_VOICE_PRESETS: List[Dict[str, Any]] = [{'id': 'default_clean',
  'name': 'Clean Voice',
  'description': 'Subtle enhancement for clean recordings - natural sounding',
  'is_default': True,
  'highpass_hz': 80,
  'lowpass_hz': 16000,
  'noise_reduction': {'enabled': True, 'type': 'afftdn', 'nr': 10, 'nf': -55, 'track_noise': False},
  'gate': {'enabled': False, 'threshold': 0.02, 'ratio': 2.0, 'attack_ms': 5, 'release_ms': 120, 'range': 0.06125},
  'eq_bands': [{'f_hz': 120, 'gain_db': -2.0, 'q': 1.0},
               {'f_hz': 250, 'gain_db': -1.5, 'q': 1.0},
               {'f_hz': 3500, 'gain_db': 3.0, 'q': 1.2},
               {'f_hz': 9000, 'gain_db': 2.0, 'q': 1.0}],
  'compressor': {'enabled': True,
                 'threshold': 0.08,
                 'ratio': 2.4,
                 'attack_ms': 15,
                 'release_ms': 250,
                 'makeup': 1.35,
                 'knee': 3.0},
  'deesser': {'enabled': True, 'i': 0.25, 'm': 0.4, 'f': 0.6},
    'exciter': {'enabled': False, 'amount': 0.4, 'drive': 1.4, 'blend': 0.0, 'freq': 7500, 'ceil': 16000},
  'leveling': {'enabled': True,
               'type': 'dynaudnorm',
               'framelen_ms': 900,
               'gausssize': 51,
               'peak': 0.93,
               'compress': 0.0,
               'maxgain': 10.0,
               'threshold': 0.003,
               'volume_restore': 1.0,
               'targetrms': 0.07,
               'overlap': 0.5},
  'limiter': {'enabled': True, 'limit': 0.97, 'attack': 5, 'release': 60},
  'deepening': {'enabled': False, 'semitones': -0.3},
  'loudnorm': {'enabled': False, 'I': -16, 'LRA': 11, 'TP': -1.5, 'two_pass': False}},
 {'id': 'default_authority',
  'name': 'Authority Voice',
  'description': 'Adds subtle gravitas and punch - good for tutorials/presentations',
  'is_default': True,
  'highpass_hz': 70,
  'lowpass_hz': 15000,
  'noise_reduction': {'enabled': True, 'type': 'afftdn', 'nr': 10, 'nf': -48, 'track_noise': False},
  'gate': {'enabled': False, 'threshold': 0.02, 'ratio': 2.2, 'attack_ms': 5, 'release_ms': 140, 'range': 0.06125},
  'eq_bands': [{'f_hz': 80, 'gain_db': 1.5, 'q': 0.7},
               {'f_hz': 150, 'gain_db': 2.0, 'q': 0.9},
               {'f_hz': 300, 'gain_db': -2.0, 'q': 1.0},
               {'f_hz': 3500, 'gain_db': 4.0, 'q': 1.1},
               {'f_hz': 9000, 'gain_db': 2.5, 'q': 1.0}],
  'compressor': {'enabled': True,
                 'threshold': 0.07,
                 'ratio': 3.0,
                 'attack_ms': 10,
                 'release_ms': 220,
                 'makeup': 1.6,
                 'knee': 2.8},
  'deesser': {'enabled': True, 'i': 0.3, 'm': 0.45, 'f': 0.6},
    'exciter': {'enabled': False, 'amount': 0.5, 'drive': 1.6, 'blend': 0.0, 'freq': 7500, 'ceil': 16000},
  'leveling': {'enabled': True,
               'type': 'dynaudnorm',
               'framelen_ms': 900,
               'gausssize': 51,
               'peak': 0.93,
               'compress': 0.0,
               'maxgain': 10.0,
               'threshold': 0.003,
               'volume_restore': 1.0,
               'targetrms': 0.072,
               'overlap': 0.5},
  'limiter': {'enabled': True, 'limit': 0.97, 'attack': 5, 'release': 60},
  'deepening': {'enabled': False, 'semitones': -0.4},
  'loudnorm': {'enabled': False, 'I': -16, 'LRA': 11, 'TP': -1.5, 'two_pass': False}},
 {'id': 'default_podcast',
  'name': 'Podcast Polish',
  'description': 'Radio-like clarity and consistency - designed for voice-only/podcasts',
  'is_default': True,
  'highpass_hz': 70,
  'lowpass_hz': 15000,
  'noise_reduction': {'enabled': True, 'type': 'afftdn', 'nr': 10, 'nf': -52, 'track_noise': False},
  'gate': {'enabled': False, 'threshold': 0.018, 'ratio': 2.2, 'attack_ms': 8, 'release_ms': 160, 'range': 0.06125},
  'eq_bands': [{'f_hz': 120, 'gain_db': -2.0, 'q': 1.0},
               {'f_hz': 250, 'gain_db': -2.0, 'q': 1.0},
               {'f_hz': 3500, 'gain_db': 3.5, 'q': 1.2},
               {'f_hz': 9000, 'gain_db': 2.0, 'q': 1.0}],
  'compressor': {'enabled': True,
                 'threshold': 0.06,
                 'ratio': 3.2,
                 'attack_ms': 10,
                 'release_ms': 240,
                 'makeup': 1.8,
                 'knee': 2.8},
  'deesser': {'enabled': True, 'i': 0.28, 'm': 0.45, 'f': 0.6},
    'exciter': {'enabled': False, 'amount': 0.5, 'drive': 1.5, 'blend': 0.0, 'freq': 7500, 'ceil': 16000},
  'leveling': {'enabled': True,
               'type': 'dynaudnorm',
               'framelen_ms': 1000,
               'gausssize': 61,
               'peak': 0.93,
               'compress': 0.0,
               'maxgain': 9.0,
               'threshold': 0.002,
               'volume_restore': 1.0,
               'targetrms': 0.07,
               'overlap': 0.5},
  'limiter': {'enabled': True, 'limit': 0.97, 'attack': 5, 'release': 60},
  'deepening': {'enabled': False, 'semitones': -0.2},
  'loudnorm': {'enabled': False, 'I': -16, 'LRA': 11, 'TP': -1.5, 'two_pass': True}},
 {'id': 'default_gaming',
  'name': 'Gaming Voice',
  'description': 'Punchy and present - tuned to cut through gameplay mixes',
  'is_default': True,
  'highpass_hz': 85,
  'lowpass_hz': 15000,
  'noise_reduction': {'enabled': True, 'type': 'afftdn', 'nr': 11, 'nf': -50, 'track_noise': False},
  'gate': {'enabled': False, 'threshold': 0.025, 'ratio': 2.5, 'attack_ms': 5, 'release_ms': 100, 'range': 0.06125},
  'eq_bands': [{'f_hz': 140, 'gain_db': -2.5, 'q': 1.0},
               {'f_hz': 300, 'gain_db': -2.0, 'q': 1.0},
               {'f_hz': 3500, 'gain_db': 4.5, 'q': 1.1},
               {'f_hz': 9000, 'gain_db': 2.5, 'q': 1.0}],
  'compressor': {'enabled': True,
                 'threshold': 0.05,
                 'ratio': 4.0,
                 'attack_ms': 5,
                 'release_ms': 180,
                 'makeup': 2.0,
                 'knee': 2.5},
  'deesser': {'enabled': True, 'i': 0.32, 'm': 0.5, 'f': 0.6},
    'exciter': {'enabled': False, 'amount': 0.55, 'drive': 1.6, 'blend': 0.0, 'freq': 7500, 'ceil': 16000},
  'leveling': {'enabled': True,
               'type': 'dynaudnorm',
               'framelen_ms': 750,
               'gausssize': 41,
               'peak': 0.93,
               'compress': 0.0,
               'maxgain': 12.0,
               'threshold': 0.0015,
               'volume_restore': 1.0,
               'targetrms': 0.08,
               'overlap': 0.55},
  'limiter': {'enabled': True, 'limit': 0.97, 'attack': 5, 'release': 60},
  'deepening': {'enabled': False, 'semitones': -0.2},
  'loudnorm': {'enabled': False, 'I': -14, 'LRA': 10, 'TP': -1.0, 'two_pass': False}},
 {'id': 'default_minimal',
  'name': 'Minimal Processing',
  'description': 'Very light touch - keeps recordings close to original',
  'is_default': True,
  'highpass_hz': 80,
  'lowpass_hz': 16000,
  'noise_reduction': {'enabled': True, 'type': 'afftdn', 'nr': 8, 'nf': -50, 'track_noise': False},
  'gate': {'enabled': False, 'threshold': 0.02, 'ratio': 2.0, 'attack_ms': 5, 'release_ms': 120, 'range': 0.06125},
  'eq_bands': [{'f_hz': 120, 'gain_db': -1.0, 'q': 1.0}, {'f_hz': 3500, 'gain_db': 2.0, 'q': 1.2}],
  'compressor': {'enabled': False,
                 'threshold': 0.15,
                 'ratio': 2.0,
                 'attack_ms': 30,
                 'release_ms': 300,
                 'makeup': 1.0,
                 'knee': 3.0},
  'deesser': {'enabled': False, 'i': 0.2, 'm': 0.4, 'f': 0.6},
    'exciter': {'enabled': False, 'amount': 0.4, 'drive': 1.4, 'blend': 0.0, 'freq': 7500, 'ceil': 16000},
  'leveling': {'enabled': False,
               'type': 'dynaudnorm',
               'framelen_ms': 500,
               'gausssize': 31,
               'peak': 0.95,
               'compress': 0.0,
               'maxgain': 6.0,
               'threshold': 0.01,
               'volume_restore': 1.0,
               'targetrms': 0.0,
               'overlap': 0.0},
  'limiter': {'enabled': True, 'limit': 0.98, 'attack': 5, 'release': 50},
  'deepening': {'enabled': False, 'semitones': 0},
  'loudnorm': {'enabled': False, 'I': -16, 'LRA': 11, 'TP': -1.5, 'two_pass': False}}]


class VoiceEffectsProcessor:
    """
    VoiceEffectsProcessor:
    - stores presets (JSON)
    - builds FFmpeg audio filter strings
    - generates preview renders (single track and multi-track)
    - can apply full processing with optional two-pass loudnorm
    """

    def __init__(self) -> None:
        self.presets_file = PROFILES_DIR / "voice_effects_presets.json"
        self.ffmpeg_path = str(FFMPEG_PATH)
        self.temp_dir = TEMP_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self._filters_cache: Optional[set] = None

        self._ensure_presets_file()

    # ----------------------------
    # Preset storage
    # ----------------------------

    def _ensure_presets_file(self) -> None:
        if self.presets_file.exists():
            return
        self.presets_file.parent.mkdir(parents=True, exist_ok=True)
        self._save_presets_data(DEFAULT_VOICE_PRESETS)

    def _load_presets(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self.presets_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                presets = data
            if isinstance(data, dict) and "presets" in data:
                presets = data["presets"]
            else:
                presets = DEFAULT_VOICE_PRESETS
        except Exception:
            presets = DEFAULT_VOICE_PRESETS

        merged = self._merge_default_presets(presets)
        if merged != presets:
            self._save_presets_data(merged)
        return merged

    def _merge_default_presets(self, presets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensure default presets are updated to the latest shipping values
        without overwriting custom presets.
        """
        defaults_by_id = {p["id"]: copy.deepcopy(p) for p in DEFAULT_VOICE_PRESETS}
        updated: List[Dict[str, Any]] = []

        for preset in presets:
            preset_id = preset.get("id")
            if preset_id in defaults_by_id and preset.get("is_default", False):
                updated.append(defaults_by_id[preset_id])
            else:
                updated.append(preset)

        existing_ids = {p.get("id") for p in updated}
        for preset_id, default in defaults_by_id.items():
            if preset_id not in existing_ids:
                updated.append(default)

        return updated

    def _save_presets_data(self, presets: List[Dict[str, Any]]) -> None:
        self.presets_file.write_text(json.dumps(presets, indent=2), encoding="utf-8")

    def get_all_presets(self) -> List[Dict[str, Any]]:
        return self._load_presets()

    def get_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        for p in self._load_presets():
            if p.get("id") == preset_id:
                return p
        return None

    def create_preset(self, name: str, settings: Dict[str, Any], description: str = "") -> Dict[str, Any]:
        presets = self._load_presets()
        
        # Start with default and merge settings
        base = json.loads(json.dumps(DEFAULT_VOICE_PRESETS[0]))
        
        def deep_merge(dst: dict, src: dict) -> dict:
            for k, v in src.items():
                if isinstance(v, dict) and isinstance(dst.get(k), dict):
                    deep_merge(dst[k], v)
                else:
                    dst[k] = v
            return dst
        
        new_preset = deep_merge(base, settings)
        new_preset["id"] = str(uuid.uuid4())[:8].upper()
        new_preset["name"] = name
        new_preset["description"] = description
        new_preset["is_default"] = False
        new_preset["created_at"] = datetime.now().isoformat()
        
        presets.append(new_preset)
        self._save_presets_data(presets)
        return new_preset

    def update_preset(self, preset_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        presets = self._load_presets()
        
        def deep_merge(dst: dict, src: dict) -> dict:
            for k, v in src.items():
                if isinstance(v, dict) and isinstance(dst.get(k), dict):
                    deep_merge(dst[k], v)
                else:
                    dst[k] = v
            return dst
        
        for i, p in enumerate(presets):
            if p.get("id") == preset_id:
                if p.get("is_default"):
                    # Don't allow modifying default presets' core identity
                    protected = {"id", "is_default"}
                    updates = {k: v for k, v in updates.items() if k not in protected}
                
                deep_merge(presets[i], updates)
                presets[i]["updated_at"] = datetime.now().isoformat()
                self._save_presets_data(presets)
                return presets[i]
        return None

    def delete_preset(self, preset_id: str) -> bool:
        presets = self._load_presets()
        new_presets = [p for p in presets if p.get("id") != preset_id or p.get("is_default")]
        if len(new_presets) == len(presets):
            return False
        self._save_presets_data(new_presets)
        return True

    def reset_defaults(self) -> None:
        self._save_presets_data(json.loads(json.dumps(DEFAULT_VOICE_PRESETS)))

    # ----------------------------
    # FFmpeg filter support
    # ----------------------------

    def _load_available_filters(self) -> set:
        if self._filters_cache is not None:
            return self._filters_cache

        try:
            proc = subprocess.run(
                [self.ffmpeg_path, "-hide_banner", "-filters"],
                check=True,
                capture_output=True,
                text=True,
            )
            filters = set()
            for line in proc.stdout.splitlines():
                # format: " T.. filtername  description"
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].startswith((".", "T", "S", "A", "V")):
                    filters.add(parts[1])
            self._filters_cache = filters
        except Exception:
            # If we can't detect filters, assume they're there and let FFmpeg error loudly.
            self._filters_cache = set()
        return self._filters_cache

    def _has_filter(self, name: str) -> bool:
        filters = self._load_available_filters()
        return (not filters) or (name in filters)

    def _get_filter_help(self, name: str) -> str:
        if not hasattr(self, "_filter_help_cache"):
            self._filter_help_cache = {}
        if name in self._filter_help_cache:
            return self._filter_help_cache[name]

        try:
            proc = subprocess.run(
                [self.ffmpeg_path, "-hide_banner", "-h", f"filter={name}"],
                check=True,
                capture_output=True,
                text=True,
            )
            help_text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        except Exception:
            help_text = ""

        self._filter_help_cache[name] = help_text
        return help_text

    def _filter_supports(self, filter_name: str, needle: str) -> bool:
        return needle in self._get_filter_help(filter_name)

    # ----------------------------
    # Filterchain builders
    # ----------------------------

    def _build_deepening_chain(self, preset: Dict[str, Any]) -> List[str]:
        """
        Build deepening filter chain.
        
        Supports two methods:
        - "shelf": Low shelf EQ boost for natural weight/gravitas (recommended)
        - "pitch": Rubberband pitch shift with formant preservation (for actual pitch change)
        """
        deep = preset.get("deepening", {}) or {}
        if not deep.get("enabled"):
            return []

        method = deep.get("method", "pitch")  # Default to pitch for backward compat
        
        if method == "shelf":
            # Natural studio deepening via low shelf boost
            # This adds "weight" without changing perceived pitch
            bass_gain_db = float(deep.get("bass_gain_db", 2.0))
            bass_f_hz = int(deep.get("bass_f_hz", 150))
            
            if bass_gain_db == 0:
                return []
            
            # FFmpeg "bass" filter: two-pole shelving filter
            if self._has_filter("bass"):
                return [f"bass=g={bass_gain_db}:f={bass_f_hz}:t=s"]
            # Fallback to equalizer if bass not available
            if self._has_filter("equalizer"):
                return [f"equalizer=f={bass_f_hz}:t=s:w=1:g={bass_gain_db}"]
            return []
        
        else:  # method == "pitch" (default)
            # Rubberband pitch shift with formant preservation
            semitones = float(deep.get("semitones", -0.3))
            if semitones == 0:
                return []
            
            pitch_ratio = 2 ** (semitones / 12.0)
            
            if self._has_filter("rubberband"):
                return [f"rubberband=pitch={pitch_ratio:.6f}:formant=preserved"]
            return []

    def _build_noise_reduction_chain(self, preset: Dict[str, Any]) -> List[str]:
        nr = preset.get("noise_reduction", {}) or {}
        if not nr.get("enabled"):
            return []

        nr_type = nr.get("type", "afftdn")
        if nr_type == "afftdn" and self._has_filter("afftdn"):
            track_noise = bool(nr.get("track_noise", False))
            tn_val = 1 if track_noise else 0
            return [f"afftdn=nr={nr.get('nr', 12)}:nf={nr.get('nf', -50)}:tn={tn_val}"]
        return []

    def _build_gate_chain(self, preset: Dict[str, Any]) -> List[str]:
        g = preset.get("gate", {}) or {}
        if not g.get("enabled") or not self._has_filter("agate"):
            return []

        thr = float(g.get("threshold", 0.02))
        ratio = float(g.get("ratio", 2.0))
        attack = float(g.get("attack_ms", 5))
        release = float(g.get("release_ms", 120))
        rng = float(g.get("range", 0.06125))

        return [f"agate=threshold={thr}:ratio={ratio}:attack={attack}:release={release}:range={rng}"]

    def _build_eq_chain(self, preset: Dict[str, Any]) -> List[str]:
        bands = preset.get("eq_bands", []) or []
        out: List[str] = []
        if not self._has_filter("equalizer"):
            return out

        for b in bands:
            f_hz = float(b.get("f_hz", 1000))
            gain_db = float(b.get("gain_db", 0.0))
            q = float(b.get("q", 1.0))
            if abs(gain_db) < 0.01:
                continue
            out.append(f"equalizer=f={f_hz}:t=q:w={q}:g={gain_db}")
        return out

    def _build_compressor_chain(self, preset: Dict[str, Any]) -> List[str]:
        comp = preset.get("compressor", {}) or {}
        if not comp.get("enabled") or not self._has_filter("acompressor"):
            return []

        threshold = float(comp.get("threshold", 0.11))
        ratio = float(comp.get("ratio", 3.0))
        # acompressor expects seconds; convert from milliseconds
        attack_ms = float(comp.get("attack_ms", 20))
        release_ms = float(comp.get("release_ms", 250))
        attack = max(0.01, attack_ms / 1000.0)
        release = max(0.01, release_ms / 1000.0)
        makeup = float(comp.get("makeup", 1.5))
        knee = float(comp.get("knee", 2.8))

        return [
            f"acompressor=threshold={threshold}:ratio={ratio}:attack={attack}:release={release}:makeup={makeup}:knee={knee}"
        ]

    def _build_exciter_chain(self, preset: Dict[str, Any]) -> List[str]:
        ex = preset.get("exciter", {}) or {}
        if not ex.get("enabled") or not self._has_filter("aexciter"):
            return []

        amount = float(ex.get("amount", 0.6))
        drive = float(ex.get("drive", 2.0))
        blend = float(ex.get("blend", 0.0))
        freq = int(ex.get("freq", 7500))
        ceil = int(ex.get("ceil", 16000))
        return [f"aexciter=amount={amount}:drive={drive}:blend={blend}:freq={freq}:ceil={ceil}"]

    def _build_deesser_chain(self, preset: Dict[str, Any]) -> List[str]:
        ds = preset.get("deesser", {}) or {}
        if not ds.get("enabled") or not self._has_filter("deesser"):
            return []

        intensity = float(ds.get("i", 0.25))
        amount = float(ds.get("m", 0.45))
        keep = float(ds.get("f", 0.6))
        # s=o means output the processed signal (s=i outputs unprocessed input)
        return [f"deesser=i={intensity}:m={amount}:f={keep}:s=o"]

    def _build_leveling_chain(self, preset: Dict[str, Any]) -> List[str]:
        lvl = preset.get("leveling", {}) or {}
        if not lvl.get("enabled"):
            return []

        lvl_type = lvl.get("type", "dynaudnorm")
        if lvl_type != "dynaudnorm" or not self._has_filter("dynaudnorm"):
            return []

        framelen = int(lvl.get("framelen_ms", 500))
        gausssize = int(lvl.get("gausssize", 31))
        peak = float(lvl.get("peak", 0.93))
        maxgain = float(lvl.get("maxgain", 10.0))
        threshold = float(lvl.get("threshold", 0.003))
        compress = float(lvl.get("compress", 0.0))
        targetrms = float(lvl.get("targetrms", 0.0))
        overlap = float(lvl.get("overlap", 0.0))

        if 0.0 < compress < 3.0:
            compress = 3.0

        filt = f"dynaudnorm=f={framelen}:g={gausssize}:p={peak}:m={maxgain}:t={threshold}"
        if compress > 0.0:
            filt += f":s={compress}"
        if targetrms > 0.0 and self._filter_supports("dynaudnorm", "targetrms, r"):
            filt += f":r={targetrms}"
        if overlap > 0.0 and self._filter_supports("dynaudnorm", "overlap, o"):
            filt += f":o={overlap}"
        # NOTE: Some FFmpeg builds do not support dynaudnorm's overlap option.
        # We skip it for compatibility.

        chain = [filt]
        volume_restore = float(lvl.get("volume_restore", 1.0))
        if volume_restore != 1.0:
            chain.append(f"volume={volume_restore}")
        return chain

    def _build_loudnorm_chain(self, preset: Dict[str, Any]) -> List[str]:
        ln = preset.get("loudnorm", {}) or {}
        if not ln.get("enabled") or ln.get("two_pass") or not self._has_filter("loudnorm"):
            return []
        I = float(ln.get("I", -16))
        LRA = float(ln.get("LRA", 11))
        TP = float(ln.get("TP", -1.5))
        return [f"loudnorm=I={I}:LRA={LRA}:TP={TP}"]

    def _build_limiter_chain(self, preset: Dict[str, Any]) -> List[str]:
        lim = preset.get("limiter", {}) or {}
        if not lim.get("enabled") or not self._has_filter("alimiter"):
            return []

        limit = float(lim.get("limit", 0.98))
        attack = float(lim.get("attack", 5))
        release = float(lim.get("release", 50))

        # CRITICAL: level=disabled prevents auto-level fighting with loudness
        return [f"alimiter=limit={limit}:attack={attack}:release={release}:level=disabled"]

    def build_filter_chain(self, preset: Dict[str, Any], include_mastering: bool = True) -> str:
        """
        Build the FFmpeg -af chain for a single voice track.

        include_mastering=True includes leveling + loudness normalization + limiter.
        For mixing (multi-track), you usually want per-track cleanup only, then master once.
        """
        filters: List[str] = []

        # 1. Deepening (pitch shift) first
        filters += self._build_deepening_chain(preset)

        # 2. Highpass/Lowpass
        hp = int(preset.get("highpass_hz", 80))
        lp = int(preset.get("lowpass_hz", 16000))
        if self._has_filter("highpass"):
            filters.append(f"highpass=f={hp}")
        if lp > 0 and self._has_filter("lowpass"):
            filters.append(f"lowpass=f={lp}")

        # 3. Noise reduction
        filters += self._build_noise_reduction_chain(preset)

        # 4. Gate
        filters += self._build_gate_chain(preset)

        # 5. EQ
        filters += self._build_eq_chain(preset)

        # 6. Compressor
        filters += self._build_compressor_chain(preset)

        # 7. Exciter (can add brightness, but also creates more "S" energy)
        filters += self._build_exciter_chain(preset)

        # 8. De-esser AFTER compression (and after exciter if enabled) - compression often exaggerates sibilance
        filters += self._build_deesser_chain(preset)

        # 9-11. Mastering chain (only if requested)
        if include_mastering:
            filters += self._build_leveling_chain(preset)
            filters += self._build_loudnorm_chain(preset)
            filters += self._build_limiter_chain(preset)

        return ",".join(filters)

    def build_track_chain_for_mix(self, preset: Dict[str, Any]) -> str:
        """
        Build per-track chain for mixing.
        Includes cleanup + dynamics + leveling, but EXCLUDES limiter/loudnorm so
        final limiting happens once on the mixed output.
        """
        filters: List[str] = []

        # 1. Deepening
        filters += self._build_deepening_chain(preset)

        # 2. Highpass/Lowpass
        hp = int(preset.get("highpass_hz", 80))
        lp = int(preset.get("lowpass_hz", 16000))
        if self._has_filter("highpass"):
            filters.append(f"highpass=f={hp}")
        if lp > 0 and self._has_filter("lowpass"):
            filters.append(f"lowpass=f={lp}")

        # 3. Noise reduction
        filters += self._build_noise_reduction_chain(preset)

        # 4. Gate (kept off in defaults)
        filters += self._build_gate_chain(preset)

        # 5. EQ
        filters += self._build_eq_chain(preset)

        # 6. Compressor
        filters += self._build_compressor_chain(preset)

        # 7. Exciter
        filters += self._build_exciter_chain(preset)

        # 8. De-esser (after compression/exciter)
        filters += self._build_deesser_chain(preset)

        # 9. Leveling (no limiter/loudnorm here)
        filters += self._build_leveling_chain(preset)

        return ",".join(filters)

    def get_filter_for_track(self, preset_id: str) -> str:
        preset = self.get_preset(preset_id)
        if not preset:
            return ""
        return self.build_filter_chain(preset, include_mastering=True)

    # ----------------------------
    # Loudnorm two-pass (optional)
    # ----------------------------

    def loudnorm_analyze(self, input_path: Union[str, Path], preset: Dict[str, Any]) -> Dict[str, Any]:
        ln = preset.get("loudnorm", {}) or {}
        I = float(ln.get("I", -16))
        LRA = float(ln.get("LRA", 11))
        TP = float(ln.get("TP", -1.5))

        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-nostats",
            "-i", str(input_path),
            "-af", f"loudnorm=I={I}:LRA={LRA}:TP={TP}:print_format=json",
            "-f", "null",
            "-"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "loudnorm analyze failed")

        stderr = proc.stderr
        start = stderr.rfind("{")
        end = stderr.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError("Could not parse loudnorm JSON from ffmpeg output")
        blob = stderr[start:end+1]
        return json.loads(blob)

    def loudnorm_apply_two_pass(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        preset: Dict[str, Any],
        audio_codec: str = "aac",
        bitrate: str = "192k",
        overwrite: bool = True,
    ) -> None:
        stats = self.loudnorm_analyze(input_path, preset)

        ln = preset.get("loudnorm", {}) or {}
        I = float(ln.get("I", -16))
        LRA = float(ln.get("LRA", 11))
        TP = float(ln.get("TP", -1.5))

        measured_I = stats.get("input_i")
        measured_TP = stats.get("input_tp")
        measured_LRA = stats.get("input_lra")
        measured_thresh = stats.get("input_thresh")
        offset = stats.get("target_offset")

        base = self.build_filter_chain(preset, include_mastering=False)
        leveling = ",".join(self._build_leveling_chain(preset))
        limiter = ",".join(self._build_limiter_chain(preset))

        chain_parts = [p for p in [base, leveling] if p]
        pre_loudnorm = ",".join(chain_parts)

        loudnorm2 = (
            f"loudnorm=I={I}:LRA={LRA}:TP={TP}"
            f":measured_I={measured_I}:measured_TP={measured_TP}:measured_LRA={measured_LRA}"
            f":measured_thresh={measured_thresh}:offset={offset}"
            f":linear=true:print_format=summary"
        )

        full_chain = ",".join([p for p in [pre_loudnorm, loudnorm2, limiter] if p])

        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-y" if overwrite else "-n",
            "-i", str(input_path),
            "-af", full_chain,
            "-c:a", audio_codec,
            "-b:a", bitrate,
            str(output_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "loudnorm 2-pass apply failed")

    # ----------------------------
    # Preview renders
    # ----------------------------

    def generate_preview(
        self,
        video_path: Union[str, Path],
        preset: Dict[str, Any],
        audio_track_index: int = 0,
        start_time: float = 0,
        duration: float = 15,
    ) -> Optional[str]:
        """
        Generate a preview audio clip with voice track FX applied.
        
        IMPORTANT: This applies the track chain + mastering tail ONCE, not stacked.
        """
        try:
            output_path = self.temp_dir / f"voice_preview_{uuid.uuid4().hex[:8]}.m4a"

            # Build the full chain INCLUDING mastering (leveling + limiter)
            # This is applied ONCE - no double processing
            full_chain = self.build_filter_chain(preset, include_mastering=True)

            if not full_chain:
                full_chain = "anull"

            cmd = [
                self.ffmpeg_path,
                "-hide_banner",
                "-y",
                "-ss", str(start_time),
                "-i", str(video_path),
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

            print(f"Voice effects preview failed: {result.stderr}")
            return None
        except Exception as e:
            print(f"Error generating voice effects preview: {e}")
            return None

    def generate_preview_multi_track(
        self,
        video_path: Union[str, Path],
        preset: Dict[str, Any],
        voice_track_indices: List[int],
        voice_track_volumes: List[float] = None,
        start_time: float = 0,
        duration: float = 15,
    ) -> Optional[str]:
        """
        Generate an audio preview with voice effects applied to multiple voice tracks mixed together.
        
        Pipeline:
        - Per-track: cleanup only (no mastering), then apply user volume
        - Mix tracks
        - Master ONCE on the mix (leveling + limiter)
        
        Args:
            voice_track_volumes: Optional list of volume multipliers (0.0 to 1.0+) for each track.
                                 If not provided, all tracks use volume 1.0.
        """
        try:
            if not voice_track_indices:
                return None

            # Default volumes to 1.0 if not provided
            if not voice_track_volumes:
                voice_track_volumes = [1.0] * len(voice_track_indices)
            elif len(voice_track_volumes) < len(voice_track_indices):
                # Pad with 1.0 if not enough volumes provided
                voice_track_volumes = voice_track_volumes + [1.0] * (len(voice_track_indices) - len(voice_track_volumes))

            output_path = self.temp_dir / f"voice_preview_multi_{uuid.uuid4().hex[:8]}.m4a"
            
            # Per-track: cleanup + leveling (no limiter/loudnorm)
            per_track_chain = self.build_track_chain_for_mix(preset)
            
            # Master chain to apply ONCE on the mix (limiter only)
            master_parts = []
            master_parts += self._build_limiter_chain(preset)
            master_chain = ",".join(master_parts)

            filter_parts: List[str] = []
            mix_inputs: List[str] = []

            for i, track_idx in enumerate(voice_track_indices):
                volume = voice_track_volumes[i] if i < len(voice_track_volumes) else 1.0
                
                # Skip muted tracks (volume = 0)
                if volume <= 0:
                    continue
                
                label_in = f"[0:a:{track_idx}]"
                label_out = f"[a{i}]"
                
                # Build chain: voice effects -> volume adjustment
                chain_parts = []
                if per_track_chain:
                    chain_parts.append(per_track_chain)
                
                # Apply user volume setting (linear -> dB)
                if volume != 1.0:
                    if volume > 0:
                        volume_db = 20 * math.log10(volume)
                        chain_parts.append(f"volume={volume_db:.2f}dB")
                    else:
                        chain_parts.append("volume=0")
                
                if chain_parts:
                    filter_parts.append(f"{label_in}{','.join(chain_parts)}{label_out}")
                else:
                    filter_parts.append(f"{label_in}anull{label_out}")
                mix_inputs.append(label_out)

            # If all tracks are muted, return None
            if not mix_inputs:
                print("All voice tracks are muted, cannot generate preview")
                return None

            # Mix tracks
            mix_out = "[mix]"
            if len(mix_inputs) > 1:
                amix = f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=longest:normalize=0{mix_out}"
                filter_parts.append(amix)
            else:
                # Single track, just rename
                filter_parts[-1] = filter_parts[-1].replace(mix_inputs[0], mix_out)

            # Apply master chain ONCE on the mixed output
            if master_chain:
                filter_parts.append(f"{mix_out}{master_chain}[out]")
                out_label = "[out]"
            else:
                out_label = mix_out

            filter_complex = ";".join(filter_parts)

            cmd = [
                self.ffmpeg_path,
                "-hide_banner",
                "-y",
                "-ss", str(start_time),
                "-i", str(video_path),
                "-t", str(duration),
                "-filter_complex", filter_complex,
                "-map", out_label,
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and output_path.exists():
                return str(output_path)

            print(f"Voice effects multi-track preview failed: {result.stderr}")
            # Fallback to single track preview
            if voice_track_indices:
                return self.generate_preview(video_path, preset, voice_track_indices[0], start_time, duration)
            return None
        except Exception as e:
            print(f"Error generating voice effects multi-track preview: {e}")
            return None


# Global instance
voice_effects_processor = VoiceEffectsProcessor()
