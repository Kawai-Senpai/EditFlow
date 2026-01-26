<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FFmpeg-Required-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg">
  <img src="https://img.shields.io/badge/Flask-Backend-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
   <img src="https://img.shields.io/badge/Version-1.2.0-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>

<h1 align="center">⚡ EditFlow</h1>

<p align="center">
  <strong>Professional Video Processing Workflow Tool</strong>
</p>

<p align="center">
  A sleek, modern desktop application for processing videos with custom branding, hardware acceleration, and automated workflow features. Perfect for content creators, streamers, and video editors.
</p>

---

## ✨ Features

### 🎬 Video Processing
- **Concatenate multiple videos** with seamless transitions (cut, crossfade, fade to black, dip to white)
- **Trim videos** - Remove unwanted seconds from start/end of each clip
- **Episode splitting** - Automatically split long recordings into episodes with configurable overlap

### 🎧 Multi-Track Audio Mixing
- **Support for multi-track recordings** (OBS, Streamlabs, etc.)
- **Per-track volume control** - Adjust levels for each audio track independently
- **Mute/Solo functionality** - Quickly isolate or mute specific tracks
- **Audio preview** - Listen to your mix before processing
- **Global or per-video settings** - Apply same mix to all videos or customize each
- **Audio mix presets** - Save/load your favorite level and tag setups
- **Track type tagging** - Voice, game audio, music, SFX, other
- **Auto-level (LUFS-aware)** - Analyze loudness and balance tracks by type
- **Voice effects suite** - Noise reduction, gate, EQ, compressor, de-esser, exciter, leveler, limiter
- **Voice effects preview** - Hear effects before render

### 🎨 Branding System
- **Intro/Outro support** - Prepend or overlay intro/outro clips with your branding
- **Full overlap mode** - Overlay transparent intros/outros on top of video content
- **Append mode** - Add intros/outros sequentially before/after main content
- **Subscribe graphics** - Automated overlay popups at configurable intervals

### ⚡ Performance
- **Hardware acceleration** - Auto-detects NVIDIA NVENC, Intel QuickSync, AMD AMF
- **Multiple quality presets** - YouTube 4K, 1440p, 1080p, 720p optimized
- **Real-time progress tracking** - Live encoding progress and detailed status

### 💾 Workflow
- **Branding profiles** - Save and reuse branding configurations
- **Non-destructive** - References original files, no unnecessary copies
- **Output management** - Browse, preview, and manage rendered outputs
- **Collapsible sections** - Clean UI with expandable trim and audio mixer panels
- **Batch mode** - Process each file separately with consistent settings

---

## 🖥️ Screenshots

<p align="center">
  <em>Modern dark-themed interface with intuitive controls</em>
</p>

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **FFmpeg** (with NVENC/QSV support for hardware acceleration)
- **Tkinter** (usually included with Python)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/KawaiSenpai/EditFlow.git
   cd EditFlow
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   ```
   http://localhost:5000
   ```

---

## 📖 Usage Guide

### Basic Workflow

1. **Add Videos** - Drop files or click to browse for video files
2. **Configure Settings**
   - Choose transition type (cut, crossfade, fade to black, dip to white)
   - Select quality preset (4K, 1440p, 1080p, 720p)
   - Pick encoder (NVENC for fastest rendering)
   - Set trim values if needed
3. **Select Branding** - Choose a branding profile (optional)
4. **Process** - Click "Process Videos" and watch the progress

### Multi-Track Audio Mixing

If your recordings have multiple audio tracks (e.g., OBS multi-track recording with separate mic, game, Discord):

1. **Audio Mixer panel** - Automatically appears when multi-track videos are detected
2. **Adjust volume** - Use sliders to set the level for each track (0-200%)
3. **Mute (M)** - Temporarily silence a track
4. **Solo (S)** - Listen only to selected tracks
5. **Preview** - Click "Play Preview" to hear your mix before processing
6. **Apply to all** - Toggle to apply same settings to all videos

### Audio Presets + Auto-Level

1. **Tag tracks** - Assign Voice, Game, Music, SFX, or Other
2. **Auto-Level** - Analyze loudness and balance by track type
3. **Save Preset** - Store your favorite mix and tags for reuse

### Voice Effects

1. **Enable Voice Effects** - Applies to tracks tagged as Voice
2. **Choose a preset** - Clean Voice, Authority, Podcast, Gaming, Minimal
3. **Preview** - Hear the effects before rendering

### Batch Mode

1. Select **Batch** mode in the top section
2. Choose naming strategy (original, prefix, suffix, sequential)
3. Process all files individually with the same settings

### Branding Profiles

1. Go to **Branding** tab
2. Click **+ Add Profile**
3. Configure your branding elements:
   - **Intro** - Video to play before main content
   - **Outro** - Video to play after main content
   - **Subscribe Popup** - Overlay that appears periodically during the video

### Overlap Modes Explained

| Setting | Behavior |
|---------|----------|
| `Full Overlap = ON` | Intro/outro plays **on top** of video (for transparent overlays) |
| `Full Overlap = OFF`, `Overlap > 0` | Intro/outro overlaps into video by specified seconds |
| `Full Overlap = OFF`, `Overlap = 0` | Intro/outro is **appended** sequentially (no overlap) |

---

## ⚙️ Configuration

### Hardware Acceleration

EditFlow automatically detects and uses available hardware encoders for faster processing:

| Encoder | GPU Required | Speed | Quality |
|---------|-------------|-------|---------|
| **NVENC** | NVIDIA GTX 600+ | ⚡⚡⚡ Fastest | Excellent |
| **QuickSync** | Intel CPU with iGPU | ⚡⚡ Fast | Good |
| **AMF** | AMD GPU | ⚡⚡ Fast | Good |
| **Software** | None | ⚡ Standard | Best |

### Quality Presets

| Preset | Resolution | Bitrate | Best For |
|--------|------------|---------|----------|
| YouTube 4K | 3840×2160 | 45 Mbps | Maximum quality uploads |
| YouTube 1440p | 2560×1440 | 24 Mbps | High quality gaming content |
| YouTube 1080p | 1920×1080 | 12 Mbps | Standard content (recommended) |
| YouTube 1080p Fast | 1920×1080 | 12 Mbps | Quick previews |
| YouTube 1080p Balanced | 1920×1080 | 8 Mbps | Faster renders, smaller files |
| YouTube 1080p Small | 1920×1080 | 6 Mbps | Compact exports |
| YouTube 720p | 1280×720 | 7.5 Mbps | Faster uploads, limited bandwidth |
| YouTube 720p Small | 1280×720 | 4 Mbps | Compact exports |
| Original | Source | Source | Stream copy (fastest, no re-encoding) |

---

## 📁 Project Structure

```
EditFlow/
├── app.py              # Flask API server
├── core/
│   ├── video_processor.py   # FFmpeg processing engine
│   ├── profile_manager.py   # Branding profiles handler
│   ├── render_preset_manager.py # Render presets manager
│   └── config.py            # Configuration and presets
├── static/
│   ├── index.html      # Main UI
│   ├── app.js          # Frontend logic
│   └── styles.css      # Dark theme styling
├── data/
│   ├── output/         # Rendered videos
│   ├── profiles/       # Branding profiles JSON
│   └── temp/           # Temporary processing files
└── requirements.txt    # Python dependencies
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.10+, Flask |
| **Processing** | FFmpeg with hardware acceleration |
| **Frontend** | Vanilla JavaScript, CSS3 (Dark theme) |
| **File Dialog** | Tkinter native dialogs |
| **Data Storage** | JSON files |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**KawaiSenpai**
- 💼 GitHub: [@KawaiSenpai](https://github.com/KawaiSenpai)

---

## 🙏 Acknowledgments

- [FFmpeg](https://ffmpeg.org/) - The amazing video processing library
- [Flask](https://flask.palletsprojects.com/) - Lightweight web framework

---

<p align="center">
  <strong>Made with ❤️ for content creators</strong>
</p>

<p align="center">
  <sub>⭐ Star this repo if you find it useful!</sub>
</p>
