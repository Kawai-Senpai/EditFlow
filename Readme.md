<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FFmpeg-Required-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg">
  <img src="https://img.shields.io/badge/Flask-Backend-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/Version-2.0.0-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>

<h1 align="center">⚡ EditFlow</h1>

<p align="center">
  <strong>The All-in-One Video Post-Production Powerhouse</strong>
</p>

<p align="center">
  <em>
    Concatenate, mix, brand, and thumbnail your videos - all from one sleek interface.<br>
    Built for content creators, streamers, podcasters, and anyone who hates repetitive editing.
  </em>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> · <a href="#-feature-deep-dive">Features</a> · <a href="#-usage-guide">Usage Guide</a> · <a href="#%EF%B8%8F-configuration">Configuration</a> · <a href="#-contributing">Contributing</a>
</p>

---

## 🏆 Why EditFlow?

Ever spent hours repeating the same editing steps across dozens of recordings? EditFlow eliminates the grind. Drop your raw clips in, set your branding, dial in your audio mix, generate thumbnails - and let FFmpeg do the heavy lifting.

- **One-pass rendering** - Concatenation + transitions + intros/outros + subscribe popups + audio mixing + voice effects - all processed in a single FFmpeg pass.
- **Hardware-accelerated** - Auto-detects NVIDIA NVENC, Intel QuickSync, and AMD AMF for blazing-fast encodes.
- **Multi-track audio mixer** - OBS, Streamlabs, or any multi-track recording? Per-track volume, mute, solo, auto-level, and a full voice effects chain.
- **Thumbnail Studio** - Generate polished thumbnails with text overlays, image compositing, numbering, font picker, and size optimization.
- **Batch mode** - Process every file with the same preset in one click.
- **Zero re-encoding overhead** - References original files, never copies.

---

## ✨ Feature Highlights

<table>
<tr>
<td width="50%" valign="top">

### 🎬 Video Processing
- Concatenate multiple clips with transitions
- Cut, Crossfade, Fade to Black, Dip to White
- Per-video & global trimming
- Episode splitting with configurable overlap
- Intro/outro overlay or append
- Subscribe graphics at timed intervals
- Batch processing with naming strategies

</td>
<td width="50%" valign="top">

### 🎧 Multi-Track Audio Mixer
- Auto-detect all audio tracks (OBS, etc.)
- Per-track volume, mute, and solo
- LUFS-aware auto-leveling
- Track type tagging (Voice, Game, Music, SFX)
- Audio mix presets (save/load/update/delete)
- Real-time audio preview before render
- Final limiter to prevent clipping

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🎙️ Voice Effects Suite
- 11-stage processing pipeline
- Noise reduction, gate, EQ, compressor
- De-esser, exciter, dynamic leveling
- EBU R128 loudnorm (optional two-pass)
- 5 built-in presets + custom presets
- Inline editor & full-screen editor
- Preview effects before rendering

</td>
<td width="50%" valign="top">

### 🖼️ Thumbnail Studio
- Image & video-frame backgrounds
- Text elements with 500+ system fonts
- Image overlay compositing
- Drag-to-position, resize, rotate
- Auto-numbering (episodes, series)
- JPEG/PNG/WebP output with size optimization
- Thumbnail presets for batch workflows

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🎨 Branding System
- Channel profiles (intro, outro, subscribe)
- Full-overlap mode for transparent overlays
- Partial-overlap for animated transitions
- Append mode for sequential branding
- Subscribe graphics at configurable intervals
- Per-asset audio & timing settings

</td>
<td width="50%" valign="top">

### ⚡ Performance & Workflow
- NVENC / QuickSync / AMF / Software encoding
- 9 quality presets (4K → 720p + Original)
- Custom render presets (save & reuse)
- Last-used settings persistence
- Real-time progress tracking
- Job cancellation support

</td>
</tr>
</table>

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Details |
|---|---|
| **Python** | 3.10 or newer |
| **FFmpeg** | Must be in your PATH. For hardware acceleration, build with NVENC/QSV/AMF support. |
| **Tkinter** | Usually included with Python (used for native file dialogs) |

### Installation

```bash
# 1. Clone
git clone https://github.com/KawaiSenpai/EditFlow.git
cd EditFlow

# 2. Virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch
python app.py
```

The app opens automatically at **http://localhost:5000**.

> **Tip:** On Windows, you can also double-click the included `run.bat` to launch with one click.

---

## 📖 Usage Guide

### 1. Drop Your Videos

Drag files into the drop zone or click to browse. EditFlow auto-detects resolution, FPS, codec, duration, and all audio tracks.

Drag the handles to **reorder clips**. Use the **×** button to remove files.

### 2. Configure Your Render

| Setting | Description |
|---|---|
| **Transition** | Cut (instant), Crossfade, Fade to Black, Dip to White |
| **Duration** | Transition overlap in seconds (for non-cut transitions) |
| **Quality Preset** | YouTube 4K, 1440p, 1080p, 720p, or Original (stream copy) |
| **Encoder** | NVENC (fastest), QuickSync, AMF, or Software |
| **Output Name** | Custom filename (auto-deduplication if exists) |
| **Output Dir** | Custom folder for rendered files |

### 3. Multi-Track Audio Mixing

When videos have multiple audio tracks (e.g., OBS recordings with separate mic, game, Discord), the **Audio Mixer** panel appears automatically.

| Control | What It Does |
|---|---|
| **Volume Slider** | 0% – 1000% per track |
| **M (Mute)** | Silence a track |
| **S (Solo)** | Hear only the selected track(s) |
| **Track Type** | Tag as Voice, Game Audio, Music, SFX, or Other |
| **Auto-Level** | Analyze LUFS loudness and balance tracks by type |
| **Preview** | Listen to a configurable segment before rendering |
| **Preset** | Save/load your favorite mix & tag setups |

#### Track Type Auto-Level Targets

| Type | Target Relative Level | Use Case |
|---|---|---|
| **Voice** | 100% | Commentary, narration |
| **Game Audio** | 25% | Gameplay sounds |
| **Music** | 20% | Background music |
| **SFX** | 40% | Sound effects, alerts |
| **Other** | 60% | Miscellaneous |

When LUFS analysis is available (via ffprobe), levels are calculated from measured loudness. Otherwise, the table above is used as a fallback.

### 4. Voice Effects

Enable the voice effects toggle to apply a professional audio processing chain to all tracks tagged as **Voice**.

<details>
<summary><strong>🔧 Full Voice Processing Chain (11 stages)</strong></summary>

| Stage | Filter | What It Does |
|---|---|---|
| 1 | **Deepening** | Pitch-shift voice down by semitones |
| 2 | **Highpass / Lowpass** | Remove rumble & hiss outside vocal range |
| 3 | **Noise Reduction** | FFT-based noise removal (afftdn) |
| 4 | **Noise Gate** | Silence audio below a threshold |
| 5 | **Parametric EQ** | Multi-band frequency shaping |
| 6 | **Compressor** | Tame dynamic range (threshold, ratio, attack/release) |
| 7 | **Exciter** | Add brightness & harmonic presence |
| 8 | **De-esser** | Reduce sibilance (placed after compressor) |
| 9 | **Dynamic Leveling** | Even out volume over time (dynaudnorm) |
| 10 | **Loudnorm** | EBU R128 normalization (optional two-pass) |
| 11 | **Limiter** | Hard ceiling to prevent clipping |

</details>

**Built-in Presets:** Clean Voice · Authority Voice · Podcast Polish · Gaming Voice · Minimal Processing

You can also create, edit, and delete custom presets via the inline or full-screen editor.

### 5. Branding Profiles

Go to the **Branding** tab to set up reusable channel profiles.

| Asset | Modes |
|---|---|
| **Intro** | Append (play before video) · Overlap (crossfade into video) · Full Overlap (transparent overlay) |
| **Outro** | Append (play after video) · Overlap (crossfade out) · Full Overlap (transparent overlay) |
| **Subscribe** | Overlay graphic that appears at configurable intervals with configurable duration |

Each asset stores only a file reference - no copies are made.

### 6. Thumbnail Studio

Switch to the **Thumbnails** tab for a full-featured thumbnail generator.

1. **Add backgrounds** - Browse images or extract frames from your videos
2. **Build your layout** - Add text and image elements with drag-to-position
3. **Style everything** - Fonts, colors, stroke, opacity, rotation, alignment
4. **Auto-number** - Sequential numbering for episode/series thumbnails
5. **Optimize** - Target a max file size (e.g., 2 MB for YouTube) with automatic quality adjustment
6. **Generate** - Batch-generate thumbnails for all queued backgrounds

| Feature | Details |
|---|---|
| **Font Picker** | Browse 500+ system fonts with live preview, search, and favorites |
| **Overlay Modes** | Scale to Canvas, Fit Width, Fit Height, Center Original |
| **Resize Modes** | Cover (crop to fill) or Contain (letterbox with custom bg color) |
| **Output Formats** | JPEG, PNG, WebP, or Keep Original |
| **File Optimization** | Auto quality ramp-down to meet max file size target |
| **Presets** | Save & load complete thumbnail configurations |

### 7. Batch Processing

Select **Batch** mode to process each loaded video individually with identical settings.

| Naming Strategy | Example Output |
|---|---|
| Original | `gameplay_2026-01-15.mp4` |
| Prefix | `EP01_gameplay_2026-01-15.mp4` |
| Suffix | `gameplay_2026-01-15_final.mp4` |
| Sequential | `01.mp4`, `02.mp4`, `03.mp4` |

### 8. Output Management

Switch to the **Outputs** tab to see all rendered files. You can view file sizes, modification dates, and delete files you no longer need.

---

## ⚙️ Configuration

### Hardware Acceleration

EditFlow probes for available encoders at startup and shows only what's available on your system.

| Encoder | GPU Required | Speed | Quality |
|---|---|---|---|
| **NVENC** | NVIDIA GTX 600+ | ⚡⚡⚡ Fastest | Excellent |
| **QuickSync** | Intel CPU with iGPU | ⚡⚡ Fast | Good |
| **AMF** | AMD GPU | ⚡⚡ Fast | Good |
| **Software (x264)** | None | ⚡ Standard | Best |

### Quality Presets

| Preset | Resolution | Bitrate | Best For |
|---|---|---|---|
| YouTube 4K | 3840×2160 | 45 Mbps | Maximum quality uploads |
| YouTube 1440p | 2560×1440 | 24 Mbps | High quality gaming content |
| YouTube 1080p | 1920×1080 | 12 Mbps | Standard content (recommended) |
| YouTube 1080p Fast | 1920×1080 | 12 Mbps | Quick previews |
| YouTube 1080p Balanced | 1920×1080 | 8 Mbps | Faster renders, smaller files |
| YouTube 1080p Small | 1920×1080 | 6 Mbps | Compact exports |
| YouTube 720p | 1280×720 | 7.5 Mbps | Faster uploads, limited bandwidth |
| YouTube 720p Small | 1280×720 | 4 Mbps | Compact exports |
| Original Quality | Source | Source | Stream copy - no re-encoding (fastest) |

You can also **save custom render presets** with your preferred profile, transition, encoder, and quality settings.

### Overlap Modes Explained

| Setting | Behavior |
|---|---|
| `Full Overlap = ON` | Intro/outro plays **on top** of video (for transparent PNGs/MOVs) |
| `Full Overlap = OFF`, `Overlap > 0` | Intro/outro crossfades into/out of video by N seconds |
| `Full Overlap = OFF`, `Overlap = 0` | Intro/outro is **appended** sequentially (no overlap) |

---

## 📁 Project Structure

```
EditFlow/
├── app.py                          # Flask API server (all routes & job management)
├── run.bat                         # One-click launcher (Windows)
├── requirements.txt                # Python dependencies
├── profiles.example.json           # Example branding profile
│
├── core/
│   ├── config.py                   # Global paths, output presets, track types
│   ├── video_processor.py          # FFmpeg rendering engine (concat, mix, FX)
│   ├── profile_manager.py          # Branding profile CRUD
│   ├── render_preset_manager.py    # Render preset CRUD & last-used persistence
│   ├── audio_preset_manager.py     # Audio mix preset CRUD
│   ├── voice_effects_processor.py  # Voice FX chain builder & preset management
│   ├── thumbnail_processor.py      # Legacy thumbnail processor
│   ├── thumbnail_settings_manager.py # Thumbnail preset & overlay preset CRUD
│   └── thumbnail_generator/
│       ├── studio.py               # Thumbnail Studio compositor (text + images)
│       ├── thumbnailer.py          # Orchestrator: resize → overlay → optimize
│       ├── batch.py                # Batch thumbnail generation (async jobs)
│       ├── optimizer.py            # JPEG quality ramp-down & metadata stripping
│       ├── fs.py                   # Frame extraction & file management
│       ├── models.py               # Pydantic models for thumbnail config
│       └── util.py                 # Font discovery & system helpers
│
├── static/
│   ├── index.html                  # SPA shell (Video, Branding, Thumbnails, Outputs)
│   ├── app.js                      # Frontend logic (~5600 lines)
│   └── styles.css                  # Dark theme UI
│
├── data/
│   ├── branding/                   # Uploaded branding assets (if any)
│   ├── output/                     # Default rendered output directory
│   ├── profiles/
│   │   ├── profiles.json           # Branding profiles
│   │   ├── audio_presets.json      # Audio mix presets
│   │   ├── render_presets.json     # Custom render presets
│   │   ├── voice_effects_presets.json  # Voice FX presets
│   │   └── last_render_settings.json   # Last-used render settings
│   ├── temp/
│   │   └── thumbnail_frames/       # Extracted video frames for thumbnails
│   └── thumbnails/
│       ├── thumbnail_presets.json   # Thumbnail Studio presets
│       └── overlay_presets.json     # Overlay configuration presets
│
└── tests/
    ├── test_ffmpeg.py              # FFmpeg integration tests
    └── test_pipeline.py            # End-to-end pipeline tests
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Backend** | Python 3.10+, Flask, Threading |
| **Video Engine** | FFmpeg (ffmpeg + ffprobe) |
| **Image Engine** | Pillow (PIL) |
| **Frontend** | Vanilla JavaScript, HTML5, CSS3 |
| **UI Theme** | Custom dark theme with responsive design |
| **File Dialogs** | Tkinter native OS dialogs |
| **Data Storage** | JSON files (no database needed) |
| **Font Discovery** | Windows Registry + Fonts directory scanning |

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch → `git checkout -b feature/YourFeature`
3. **Commit** your changes → `git commit -m 'Add YourFeature'`
4. **Push** to the branch → `git push origin feature/YourFeature`
5. **Open** a Pull Request

### Development Notes

- The Flask server runs on `localhost:5000` with threaded mode enabled.
- All FFmpeg processing happens in background threads - the API never blocks.
- Temp files (previews, waveforms, extracted frames) are auto-cleaned after 24 hours on server start.
- The frontend is a single-page app - no build tools needed.

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**KawaiSenpai**

- 💼 GitHub: [@KawaiSenpai](https://github.com/KawaiSenpai)

---

## 🙏 Acknowledgments

- [FFmpeg](https://ffmpeg.org/) - The backbone of all video/audio processing
- [Flask](https://flask.palletsprojects.com/) - Lightweight and elegant Python web framework
- [Pillow](https://python-pillow.org/) - Image processing for thumbnail generation

---

<p align="center">
  <strong>Made with ❤️ for content creators everywhere</strong>
</p>

<p align="center">
  <sub>⭐ Star this repo if EditFlow saves you time!</sub>
</p>
